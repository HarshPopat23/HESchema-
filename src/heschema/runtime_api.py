"""Versioned contract/context API independent of generation and benchmark scoring."""

from typing import Any, Literal

from fastapi import Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from .capabilities import capability_profile
from .context_schema import ContextError, check_context, effective_schema
from .contract_prompt import contract_messages
from .contracts import generation_envelope
from .providers import Provider, ProviderError
from .repair import RepairLimits, coordinate, request_generation
from .schema_projection import project_schema
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


class ContractGenerationBody(StrictBody):
    contractId: str
    contractVersion: str
    contextId: str | None = None
    contextVersion: int | None = Field(default=None, ge=1)
    prompt: str = Field(min_length=1, max_length=20000)
    provider: str
    model: str | None = None
    mode: str = 'prompt_only'
    promptStyle: Literal['full', 'compact'] = 'full'
    repairs: int = Field(default=0, ge=0, le=5)
    maxRequests: int | None = Field(default=None, ge=1, le=6)
    maxTokens: int = Field(default=1024, ge=1, le=128000)
    tokenBudget: int | None = Field(default=None, ge=0)
    deadlineSeconds: float = Field(default=180, gt=0, le=600)
    feedbackStyle: str = 'actionable'
    seed: int = 0
    temperature: float | None = Field(default=None, ge=0, le=2)


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
            raw = 'null' if body.output is None and 'output' in body.model_fields_set else body.output
            result = validate_contract(raw, engine, contract, snap)
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

    @app.post('/contracts/generate')
    async def generate(body: ContractGenerationBody, identity=Depends(owner)):
        contract = definition(body.contractId, body.contractVersion)
        snap = context_snapshot(contract, body.contextId, body.contextVersion, identity)
        try:
            effective, evidence = effective_schema(contract, snap)
            original_envelope = generation_envelope(contract, contract.schema)
            effective_envelope = generation_envelope(contract, effective)
            prompt_envelope = original_envelope if body.promptStyle == 'compact' else effective_envelope
            projected, manifest = project_schema(original_envelope, prompt_envelope)
            profile = capability_profile(body.provider, body.mode, model=body.model)
            if profile['adapterStatus'] == 'unsupported':
                raise ValueError('Native mode is not implemented for this provider')
            limits = RepairLimits(body.repairs, body.maxRequests, body.maxTokens, body.tokenBudget, body.deadlineSeconds)
            messages = contract_messages(contract, snap, evidence, prompt_envelope, body.prompt,
                                         style=body.promptStyle)
            provider = Provider(body.provider, body.model)
            generation_schema = None if body.mode == 'prompt_only' else projected if body.mode == 'native_projected' else prompt_envelope
            def checkpoint():
                try:
                    context_snapshot(contract, body.contextId, body.contextVersion, identity)
                except HTTPException as exc:
                    raise ContextError(str(exc.detail)) from None
            async def request(messages, attempt):
                return await request_generation(provider, messages, body.seed, body.maxTokens, body.temperature, generation_schema)
            try:
                run = await coordinate(request, lambda g: validate_contract(g.text, engine, contract, snap, generation=g), messages,
                                       limits=limits, feedback_style=body.feedbackStyle, context_check=checkpoint)
            finally:
                await provider.close()
        except (ValueError, ProviderError) as exc:
            raise HTTPException(422, str(exc)) from None
        for evaluation in (run['firstEvaluation'], run['finalEvaluation']):
            evaluation.setdefault('contract', contract.identity)
            evaluation.setdefault('context', evidence)
        return {'protocolVersion': 2, 'output': run['attempts'][-1]['generation']['text'] if run['attempts'] else None,
                'promptStyle': body.promptStyle,
                'validation': run['finalEvaluation'], 'repair': run,
                'projection': manifest if body.mode == 'native_projected' else None,
                'capability': profile, 'executionAuthorized': False}

    @app.get('/capabilities/{provider}/{mode}')
    def capabilities(provider: str, mode: str, identity=Depends(owner)):
        try:
            return capability_profile(provider, mode)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from None

    return definition, context_snapshot
