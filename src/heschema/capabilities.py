"""Versioned evidence records: request acceptance is not keyword enforcement."""

from .jsonio import digest

PROFILE_VERSION = '1'


def capability_profile(provider, mode, *, backend_version=None, model=None, evidence_date=None, observations=None):
    if mode not in {'prompt_only', 'native_original', 'native_projected'}:
        raise ValueError('Unknown decoding mode')
    implemented = provider in {'ollama', 'mock', 'groq'}
    return {'profileVersion': PROFILE_VERSION, 'provider': provider, 'apiMode': mode,
            'backendVersion': backend_version, 'model': model, 'evidenceDate': evidence_date,
            'adapterStatus': 'implemented' if mode == 'prompt_only' or implemented else 'unsupported',
            'documented': {'schemaRequest': 'available' if provider in {'ollama','groq'} else 'unknown',
                           'source': 'https://docs.ollama.com/capabilities/structured-outputs' if provider == 'ollama' else 'https://console.groq.com/docs/structured-outputs' if provider == 'groq' else None},
            'keywordEnforcement': 'unknown', 'observations': observations or [],
            'notice': 'Passing samples establish observed validity, not universal keyword enforcement.'}


def record_probe(profile, *, schema, request_accepted, original_valid=None, completion=None, failure=None, provenance='observed'):
    if provenance not in {'observed', 'mock', 'synthetic_mutation', 'historical_pilot'}:
        raise ValueError('Unknown probe provenance')
    observation = {'schemaHash': digest(schema), 'requestAccepted': request_accepted,
                   'originalSchemaValid': original_valid, 'completion': completion,
                   'failure': failure, 'provenance': provenance,
                   'outcome': 'request_rejected' if not request_accepted else 'observed_violation' if original_valid is False else 'observed_valid' if original_valid else 'unknown'}
    return {**profile, 'observations': [*profile['observations'], observation]}
