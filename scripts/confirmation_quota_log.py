"""Optional response observer: retain limit categories, never provider error text."""

import json
from datetime import datetime, timezone

from heschema.confirmation_run import journal
from heschema.providers import Provider


def quota_record(response, model):
    if response.status_code != 429:
        return None
    try:
        message = str(response.json().get('error', {}).get('message', '')).lower()
    except (ValueError, AttributeError):
        message = ''
    categories = []
    for category, markers in {
        'tokens_per_day': ('tokens per day', 'tpd'),
        'tokens_per_minute': ('tokens per minute', 'tpm'),
        'requests_per_day': ('requests per day', 'rpd'),
        'requests_per_minute': ('requests per minute', 'rpm'),
    }.items():
        if any(marker in message for marker in markers):
            categories.append(category)
    return {'event': 'provider_quota', 'model': model, 'status': 429,
            'recordedAt': datetime.now(timezone.utc).isoformat(),
            'categories': categories or ['unspecified'],
            'headers': {key: value for key, value in response.headers.items()
                        if key.startswith('x-ratelimit-') or key == 'retry-after'}}


def observed_provider_factory(out, request_interval=0):
    def factory(name, model, interval):
        provider = Provider(name, model=model, interval=max(interval, request_interval))

        async def observe(response):
            if response.status_code == 429:
                await response.aread()
                record = quota_record(response, model)
                journal(out / 'transport_events.jsonl', record)

        provider.client.event_hooks['response'].append(observe)
        return provider

    return factory


if __name__ == '__main__':
    print(json.dumps({'notice': 'Import observed_provider_factory; this module makes no requests itself.'}))
