"""Write-ahead study evidence. Never infer a response from a result's status.

One process owns a run directory; async workers use synchronous atomic writes.
Only final model content is retained here, not reasoning or HTTP headers.
"""

import copy
import os
import tempfile
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .jsonio import canonical, digest, read_json

VERSION = 'request-evidence-v1'


class EvidenceError(RuntimeError):
    pass


def _sync_directory(path):
    if os.name == 'posix':
        descriptor = os.open(path, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def _mkdir(path):
    if not path.exists():
        _mkdir(path.parent)
        path.mkdir(mode=0o700)
        _sync_directory(path.parent)


def atomic_json(path, value):
    """Sync contents before rename; sync the directory on POSIX systems."""
    path = Path(path)
    _mkdir(path.parent)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix='.pending-')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as stream:
            stream.write(canonical(value) + '\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        _sync_directory(path.parent)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def append_jsonl(stream, value):
    stream.write(canonical(value) + '\n')
    stream.flush()
    os.fsync(stream.fileno())


def generation_record(generated):
    value = asdict(generated) if not isinstance(generated, dict) else copy.deepcopy(generated)
    value.pop('reasoning', None)
    # These are adapter-controlled metadata fields, not arbitrary HTTP headers.
    value['metadata'] = {k: v for k, v in value.get('metadata', {}).items() if k in {
        'finish_reason', 'resolvedModelConfirmed', 'requestControls', 'responseId',
        'systemFingerprint', 'timing', 'durationsMs', 'synthetic', 'contentReasoningMarkers',
        'nativeStrictRequested', 'reasoningEffortRequested', 'seedRequested'}}
    return value


def _now():
    return datetime.now(timezone.utc).isoformat()


def _receipt_path(root, identity):
    if not isinstance(identity, str) or len(identity) != 32 or any(c not in '0123456789abcdef' for c in identity):
        raise EvidenceError('Invalid evidence identifier')
    return root / (identity + '.json')


def _check_request(record):
    if record.get('version') != VERSION or record.get('state') not in {'started', 'returned', 'replayed', 'failed'}:
        raise EvidenceError('Unknown request evidence format')
    if record['state'] in {'returned', 'replayed'}:
        generated = record['generation']
        if not isinstance(generated['text'], str) or any(
                generated[k] is not None and (type(generated[k]) is not int or generated[k] < 0)
                for k in ('input_tokens', 'output_tokens')):
            raise EvidenceError('Invalid response or usage evidence')


class StudyEvidence:
    def __init__(self, out):
        self.out = Path(out)
        self.root = self.out / 'request-evidence'
        self.requests = self.root / 'requests'
        self.results = self.root / 'results'
        _mkdir(self.requests)
        _mkdir(self.results)

    def set_schedule(self, slots):
        path = self.out / 'evidence_schedule.json'
        if path.exists() and read_json(path) != slots:
            raise EvidenceError('Evidence schedule differs')
        atomic_json(path, slots)

    def session(self, slot):
        return EvidenceSession(self, slot)

    def receipt(self, ref):
        try:
            value = read_json(_receipt_path(self.requests, ref['id']))
            if digest(value) != ref['sha256'] or value['id'] != ref['id']:
                raise EvidenceError('Evidence hash mismatch')
            _check_request(value)
            return value
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise EvidenceError('Missing or corrupt request evidence') from exc

    def verify_row(self, row):
        proof = row.get('evidence', {})
        if proof.get('version') != VERSION:
            raise EvidenceError('Legacy row has no verifiable request evidence')
        recovery = row.get('result', row)
        ledger = recovery.get('requestLedger', [])
        refs = proof['requests']
        if refs != [entry['evidenceRef'] for entry in ledger if 'evidenceRef' in entry]:
            raise EvidenceError('Result request references differ from ledger')
        if len(refs) != len(ledger):
            raise EvidenceError('Result ledger lacks evidence')
        received = {}
        for entry, ref in zip(ledger, refs):
            record = self.receipt(ref)
            if record['slot'] != proof['slot'] or record['attempt'] != entry['attempt']:
                raise EvidenceError('Request belongs to a different slot or attempt')
            if record['state'] in {'returned', 'replayed'}:
                received[entry['attempt']] = record['generation']
            elif record['state'] != 'failed':
                raise EvidenceError('Response evidence is missing after request start')
        for index, attempt in enumerate(recovery.get('attempts', [])):
            if received.get(index) != generation_record(attempt['generation']):
                raise EvidenceError('Result generation differs from durable response')
        missing_usage = sum(any(record.get(key) is None for key in ('input_tokens', 'output_tokens'))
                            for record in received.values())
        expected = 'usage_missing' if missing_usage else 'complete' if ledger else 'not_requested'
        if proof.get('status') != expected:
            raise EvidenceError('Result evidence status differs from saved usage')
        return missing_usage

    def _committed(self):
        rows = []
        for path in sorted(self.results.glob('*.json')):
            value = read_json(path)
            if digest(value['row']) != value['sha256']:
                raise EvidenceError('Committed result hash mismatch')
            self.verify_row(value['row'])
            rows.append(value)
        return [value['row'] for value in sorted(rows, key=lambda r: (r['committedAt'], r['row']['evidence']['resultId']))]

    def load_rows(self):
        """Recover results committed before a crash prevented the runs.jsonl append."""
        try:
            committed = self._committed()
            by_id = {row['evidence']['resultId']: row for row in committed}
            path = self.out / 'runs.jsonl'
            rows = [read_json_line(line) for line in path.read_text(encoding='utf-8').splitlines()] if path.exists() else []
            for row in rows:
                self.verify_row(row)
                if by_id.get(row['evidence']['resultId']) != row:
                    raise EvidenceError('Result journal differs from committed evidence')
            present = {row['evidence']['resultId'] for row in rows}
            recovered = [row for row in committed if row['evidence']['resultId'] not in present]
            if recovered:
                with path.open('a', encoding='utf-8') as stream:
                    for row in recovered:
                        append_jsonl(stream, row)
            report = self.audit()
            if not report['recordsVerified']:
                raise EvidenceError('Unresolved evidence; inspect evidence_report.json before resuming')
            return rows + recovered
        except (OSError, ValueError, KeyError, TypeError, EvidenceError) as exc:
            self.audit()
            raise EvidenceError('Missing, interrupted or corrupt evidence; inspect evidence_report.json. No requests resumed.') from exc

    def audit(self):
        """Offline, read-only evidence assessment (apart from the audit output)."""
        issues, referenced, missing_usage = [], set(), 0
        try:
            rows = self._committed()
        except (OSError, ValueError, KeyError, TypeError, EvidenceError):
            rows = []
            issues.append({'status': 'result_evidence_missing_or_corrupt'})
        for row in rows:
            missing_usage += self.verify_row(row)
            referenced.update(ref['id'] for ref in row['evidence']['requests'])
        log = self.out / 'runs.jsonl'
        try:
            logged = [read_json_line(line) for line in log.read_text(encoding='utf-8').splitlines()] if log.exists() else []
            committed_ids = {row['evidence']['resultId']: row for row in rows}
            for index, row in enumerate(logged):
                if not row.get('evidence'):
                    issues.append({'row': index, 'status': 'legacy_unverified'})
                elif committed_ids.get(row['evidence'].get('resultId')) != row:
                    issues.append({'row': index, 'status': 'result_evidence_missing_or_corrupt'})
        except (OSError, ValueError, KeyError, TypeError):
            issues.append({'status': 'result_journal_corrupt'})
        request_counts = {'returned': 0, 'replayed': 0, 'failed': 0, 'started': 0}
        returned_usage = []
        for path in sorted(self.requests.glob('*.json')):
            try:
                record = read_json(path)
                _check_request(record)
                request_counts[record['state']] += 1
                if record['state'] == 'returned':
                    returned_usage.append(record['generation'])
                if record['id'] not in referenced:
                    issues.append({'id': record['id'], 'slot': record['slot'],
                                   'status': 'response_missing_unknown_outcome' if record['state'] == 'started' else 'result_missing'})
            except (OSError, ValueError, KeyError, TypeError, EvidenceError):
                issues.append({'file': path.name, 'status': 'request_evidence_corrupt'})
        report = {'version': VERSION, 'recordsVerified': not issues,
                  'evidenceComplete': bool(rows) and not issues and all(row['evidence']['status'] == 'complete' for row in rows),
                  'committedResults': len(rows), 'returnedUsageMissing': missing_usage,
                  'requestsByState': request_counts, 'issues': issues,
                  'notice': 'Final model content and reported usage only, not raw HTTP or billing. Started requests without saved returns have unknown remote outcomes. Failed requests may have unknown usage. Historical missing evidence is never reconstructed from expected answers.'}
        report['observedReturnedUsage'] = {
            key: {'knownSubtotal': sum(g[key] for g in returned_usage if g.get(key) is not None),
                  'missing': sum(g.get(key) is None for g in returned_usage),
                  'total': sum(g[key] for g in returned_usage) if all(g.get(key) is not None for g in returned_usage) else None}
            for key in ('input_tokens', 'output_tokens')}
        report['observedReturnedUsage']['scope'] = 'All durable returned responses, including uncommitted results and earlier failed runs. Replayed source generations are excluded. Does not include unknown in-flight/provider-error usage.'
        report['availability'] = 'recorded' if rows else 'no_verifiable_results'
        schedule_path = self.out / 'evidence_schedule.json'
        if schedule_path.exists():
            planned = read_json(schedule_path)
            finished = {digest(row['evidence']['slot']) for row in rows}
            report['plannedSlots'] = len(planned)
            report['missingResultSlots'] = [slot for slot in planned if digest(slot) not in finished]
            report['scheduleComplete'] = not report['missingResultSlots']
            if not planned and not issues:
                report['evidenceComplete'] = True
        atomic_json(self.out / 'evidence_report.json', report)
        return report


def read_json_line(line):
    from .jsonio import loads
    return loads(line)


class EvidenceSession:
    def __init__(self, store, slot):
        self.store, self.slot = store, copy.deepcopy(slot)

    def started(self, attempt, messages, replay=None):
        record = {'version': VERSION, 'id': uuid.uuid4().hex, 'slot': self.slot,
                  'attempt': attempt, 'startedAt': _now(), 'messagesHash': digest(messages),
                  'state': 'started'}
        if replay is not None:
            record.update(state='replayed', generation=generation_record(replay))
        return self._write(record)

    def _write(self, record):
        atomic_json(_receipt_path(self.store.requests, record['id']), record)
        return {'id': record['id'], 'sha256': digest(record)}

    def returned(self, ref, generated):
        record = self.store.receipt(ref)
        record.update(state='returned', returnedAt=_now(), generation=generation_record(generated))
        return self._write(record)

    def failed(self, ref, failure):
        record = self.store.receipt(ref)
        record.update(state='failed', failure=failure)
        return self._write(record)

    def commit(self, row, recovery):
        refs = [entry['evidenceRef'] for entry in recovery['requestLedger']]
        missing = any(any(value['generation'].get(key) is None for key in ('input_tokens', 'output_tokens'))
                      for value in map(self.store.receipt, refs) if value['state'] in {'returned', 'replayed'})
        row = {**row, 'evidence': {'version': VERSION, 'resultId': uuid.uuid4().hex, 'slot': self.slot,
                                 'status': 'usage_missing' if missing else 'complete' if refs else 'not_requested', 'requests': refs}}
        self.store.verify_row(row)
        atomic_json(_receipt_path(self.store.results, row['evidence']['resultId']),
                    {'row': row, 'sha256': digest(row), 'committedAt': _now()})
        return row
