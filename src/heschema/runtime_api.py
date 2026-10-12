"""Versioned contract/context API independent of generation and benchmark scoring."""

from typing import Any

from fastapi import Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from .context_schema import ContextError, check_context, effective_schema
from .validation import validate_contract


class StrictBody(BaseModel):
    model_config = ConfigDict(extra='forbid')


class ContractBody(StrictBody):
    id: str = Field(min_length=1, max_length=100)
    version: str = Field(min_length=1, max_length=100)
    schema_: dict | bool = Field(alias='schema')
    outputKind: str = 'document'
    tool: str | None = None
    description: str = ''
    contextSchema: dict | bool = Field(default_factory=lambda: {'type': 'object'})
    bindings: list[dict] = Field(default_factory=list)
    relationships: list[dict] = Field(default_factory=list)


class ContextBody(StrictBody):
    contractId: str
    contractVersion: str
    data: Any
    approvedPointers: list[str] = Field(default_factory=list)
    facts: list[dict] = Field(default_factory=list)
    expiresAt: str | None = None


class VersionBody(StrictBody):
    version: int = Field(ge=1)


class ContractValidationBody(StrictBody):
    contractId: str
    contractVersion: str
    output: Any = None
    contextId: str | None = None
    contextVersion: int | None = Field(default=None, ge=1)


def install_contract_routes(app, store, engine, owner, registry):
    def definition(contract_id, version):
        try:
            return registry.get(contract_id, version)
        except KeyError:
            raise HTTPException(404, 'Contract/version not found') from None

    def context_snapshot(contract, context_id, version, identity):
        if context_id is None:
            if version is not None:
                raise HTTPException(422, 'contextVersion requires contextId')
            return None
        if version is None:
            raise HTTPException(422, 'contextVersion required')
        try:
            snap = store.get_context(context_id, identity)
            check_context(snap, version=version)
        except KeyError:
            raise HTTPException(404, 'Context not found') from None
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from None
        if snap['contractHash'] != contract.identity['hash']:
            raise HTTPException(409, 'Context belongs to a different contract/version')
        return snap

    @app.get('/contracts')
    def list_contracts(identity=Depends(owner)):
        return {'protocolVersion': 2, 'contracts': registry.list()}

    @app.post('/contracts', status_code=201)
    def register_contract(body: ContractBody, identity=Depends(owner)):
        try:
            return registry.register(body.model_dump(by_alias=True)).as_dict()
        except (ValueError, KeyError, TypeError) as exc:
            raise HTTPException(422, str(exc)) from None

    @app.get('/contracts/{contract_id}/{version}')
    def get_contract(contract_id: str, version: str, identity=Depends(owner)):
        return definition(contract_id, version).as_dict()

    @app.post('/contexts', status_code=201)
    def create_context(body: ContextBody, identity=Depends(owner)):
        contract = definition(body.contractId, body.contractVersion)
        try:
            return store.create_context(identity, contract, body.data, body.approvedPointers, body.facts, body.expiresAt)
        except (ValueError, KeyError, TypeError, OverflowError) as exc:
            raise HTTPException(422, str(exc)) from None

    @app.get('/contexts/{context_id}')
    def get_context(context_id: str, identity=Depends(owner)):
        try:
            return store.get_context(context_id, identity)
        except KeyError:
            raise HTTPException(404, 'Context not found') from None

    @app.post('/contexts/{context_id}/confirm')
    def confirm_context(context_id: str, body: VersionBody, identity=Depends(owner)):
        try:
            return store.confirm_context(context_id, identity, body.version)
        except (KeyError, ValueError) as exc:
            raise HTTPException(409, str(exc)) from None

    @app.post('/contexts/{context_id}/invalidate')
    def invalidate_context(context_id: str, body: VersionBody, identity=Depends(owner)):
        try:
            return store.invalidate_context(context_id, identity, body.version)
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from None

    @app.post('/contracts/validate')
    def validate(body: ContractValidationBody, identity=Depends(owner)):
        contract = definition(body.contractId, body.contractVersion)
        snap = context_snapshot(contract, body.contextId, body.contextVersion, identity)
        try:
            result = validate_contract(body.output, engine, contract, snap)
        except ContextError as exc:
            raise HTTPException(422, str(exc)) from None
        context_snapshot(contract, body.contextId, body.contextVersion, identity)
        return result

    @app.post('/contracts/effective-schema')
    def project_context(body: ContractValidationBody, identity=Depends(owner)):
        contract = definition(body.contractId, body.contractVersion)
        snap = context_snapshot(contract, body.contextId, body.contextVersion, identity)
        try:
            schema, evidence = effective_schema(contract, snap)
        except ContextError as exc:
            raise HTTPException(422, str(exc)) from None
        return {'schema': schema, 'contract': contract.identity, 'context': evidence}

    return definition, context_snapshot
