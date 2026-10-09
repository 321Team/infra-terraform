"""Offline only: no AWS/Terraform process or credentials required."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('fixture', Path(__file__).parents[1] / 'tools/u1_lock_fixture.py')
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


class Fake:
    def __init__(self, fault=None):
        self.fault = fault
        self.current = None
        self.calls = []

    def empty_prefix(self, label):
        self.calls.append(('list', label))
        if self.fault == 'existing-state' and label == 'before':
            raise m.Stop('state exists')

    def get_lock(self, label):
        self.calls.append(('get', label))
        if self.fault == 'read-denied':
            raise m.Stop('AccessDenied')
        if self.fault == 'existing-lock' and label == 'before':
            return b'foreign', 'foreign-etag'
        if self.fault == 'replaced' and label == 'pre-delete':
            self.current = (b'{"ID":"foreign"}', 'foreign-etag')
        if self.fault == 'changed-etag' and label == 'pre-delete':
            self.current = (self.current[0], 'different-etag')
        if self.fault == 'retained-after-delete' and label == 'deleted':
            return b'foreign', 'foreign-etag'
        if self.fault == 'retry-lock-left' and label == 'after-retry':
            return b'foreign', 'foreign-etag'
        return self.current

    def put_lock(self, body):
        self.calls.append(('put', body))
        if self.fault == 'put-race':
            self.current = (b'foreign', 'foreign-etag')
            raise m.Stop('412')
        self.current = (body, 'own-etag')
        if self.fault == 'put-timeout':
            raise m.Stop('timeout; response uncertain')
        return 'own-etag'

    def plan(self, name, seconds):
        self.calls.append(('plan', name))
        if self.fault == 'plan-timeout':
            raise m.Stop('Plan timeout')
        if name == 'collision':
            ident = json.loads(self.current[0])['ID']
            if self.fault == 'wrong-lock-id':
                ident = 'foreign'
            err = ('Error acquiring the state lock\nLock Info:\n  ID: ' + ident + '\n').encode()
            if self.fault == 'permission-error':
                err = b'AccessDenied'
            return subprocess.CompletedProcess([], 0 if self.fault == 'unexpected-plan-success' else 1, b'', err)
        return subprocess.CompletedProcess([], 1 if self.fault == 'retry-failed' else 2, b'', b'')

    def delete_lock(self, etag):
        self.calls.append(('delete', etag))
        if self.fault == 'delete-race':
            self.current = (b'foreign', 'foreign-etag')
            raise m.Stop('412')
        if self.fault == 'delete-timeout':
            raise m.Stop('timeout; deletion uncertain')
        self.current = None

    def check_plan(self):
        self.calls.append(('check-plan', None))
        if self.fault == 'unexpected-changes':
            raise m.Stop('unexpected plan')


class Tests(unittest.TestCase):
    def test_success_order_and_single_owned_delete(self):
        f = Fake()
        m.exercise(f, m.fixture_bytes())
        self.assertEqual([x for x in f.calls if x[0] == 'plan'], [('plan', 'collision'), ('plan', 'retry')])
        self.assertEqual([x for x in f.calls if x[0] == 'delete'], [('delete', 'own-etag')])
        self.assertIsNone(f.current)

    def test_read_failures_or_existing_data_never_write(self):
        for fault in ['existing-state', 'existing-lock', 'read-denied']:
            with self.subTest(fault=fault):
                f = Fake(fault)
                with self.assertRaises(m.Stop): m.exercise(f, m.fixture_bytes())
                self.assertFalse(any(x[0] in ('put', 'delete', 'plan') for x in f.calls))

    def test_conditional_put_race_and_timeout_never_retry_or_delete(self):
        for fault in ['put-race', 'put-timeout']:
            with self.subTest(fault=fault):
                f = Fake(fault)
                with self.assertRaises(m.Stop): m.exercise(f, m.fixture_bytes())
                self.assertEqual(sum(x[0] == 'put' for x in f.calls), 1)
                self.assertFalse(any(x[0] in ('delete', 'plan') for x in f.calls))
                self.assertIsNotNone(f.current)

    def test_unproven_collision_does_not_remove_lock(self):
        for fault in ['wrong-lock-id', 'permission-error', 'unexpected-plan-success', 'plan-timeout']:
            with self.subTest(fault=fault):
                f = Fake(fault)
                with self.assertRaises(m.Stop): m.exercise(f, m.fixture_bytes())
                self.assertFalse(any(x[0] == 'delete' for x in f.calls))

    def test_content_or_etag_change_blocks_deletion(self):
        for fault in ['replaced', 'changed-etag']:
            with self.subTest(fault=fault):
                f = Fake(fault)
                with self.assertRaises(m.Stop): m.exercise(f, m.fixture_bytes())
                self.assertFalse(any(x[0] == 'delete' for x in f.calls))

    def test_delete_uncertainty_never_retries_or_runs_next_plan(self):
        for fault in ['delete-race', 'delete-timeout', 'retained-after-delete']:
            with self.subTest(fault=fault):
                f = Fake(fault)
                with self.assertRaises(m.Stop): m.exercise(f, m.fixture_bytes())
                self.assertEqual(sum(x[0] == 'delete' for x in f.calls), 1)
                self.assertNotIn(('plan', 'retry'), f.calls)

    def test_retry_failure_drift_or_remaining_lock_cannot_pass(self):
        for fault in ['retry-failed', 'unexpected-changes', 'retry-lock-left']:
            with self.subTest(fault=fault):
                f = Fake(fault)
                with self.assertRaises(m.Stop): m.exercise(f, m.fixture_bytes())
                self.assertEqual(sum(x[0] == 'delete' for x in f.calls), 1)

    def test_execute_requires_window_record_before_any_process(self):
        for note in [[], ['--window-confirmation', '  ']]:
            with self.subTest(note=note), patch.object(sys, 'argv', ['runner', '--repo', '.', '--terraform', '/tf', '--execute', *note]), patch.object(m.subprocess, 'run') as proc:
                with self.assertRaises(m.Stop): m.main()
                proc.assert_not_called()

    def test_exact_conditional_mutation_commands(self):
        with tempfile.TemporaryDirectory() as td:
            api = m.Live(Path(td), '/tf', {})
            responses = [subprocess.CompletedProcess([], 0, b'{"ETag":"own-etag","VersionId":"synthetic-version"}', b''),
                         subprocess.CompletedProcess([], 0, b'{}', b'')]
            with patch.object(api, 'call', side_effect=responses) as call:
                api.put_lock(m.fixture_bytes()); api.delete_lock('own-etag')
            put, delete = [c.args[1] for c in call.call_args_list]
            for cmd in [put, delete]:
                self.assertEqual(cmd[cmd.index('--key') + 1], m.LOCK)
                self.assertEqual(cmd[cmd.index('--expected-bucket-owner') + 1], m.ACCOUNT)
                self.assertNotIn('--version-id', cmd)
            self.assertEqual(put[put.index('--if-none-match') + 1], '*')
            self.assertEqual(delete[delete.index('--if-match') + 1], 'own-etag')

    def test_unversioned_fixture_stops_before_deletion(self):
        with tempfile.TemporaryDirectory() as td:
            api = m.Live(Path(td), '/tf', {})
            with patch.object(api, 'call', return_value=subprocess.CompletedProcess([], 0, b'{"ETag":"own-etag","VersionId":"null"}', b'')) as call:
                with self.assertRaises(m.Stop): api.put_lock(m.fixture_bytes())
                self.assertEqual(call.call_count, 1)
            self.assertTrue((Path(td) / 'owned-lock-receipt.json').exists())

    def test_only_nosuchkey_counts_as_absent(self):
        with tempfile.TemporaryDirectory() as td:
            api = m.Live(Path(td), '/tf', {})
            for err, absent in [(b'(NoSuchKey)', True), (b'(AccessDenied)', False), (b'(403)', False), (b'network timeout', False)]:
                with self.subTest(err=err), patch.object(api, 's3', return_value=subprocess.CompletedProcess([], 254, b'', err)):
                    if absent: self.assertIsNone(api.get_lock('test'))
                    else:
                        with self.assertRaises(m.Stop): api.get_lock('test')

    def test_secret_redaction_happens_before_persistence(self):
        with tempfile.TemporaryDirectory() as td:
            env = dict(AWS_ACCESS_KEY_ID='synthetic-key', AWS_SECRET_ACCESS_KEY='synthetic-secret', AWS_SESSION_TOKEN='synthetic-token')
            api = m.Live(Path(td), '/tf', env)
            payload = b'synthetic-key synthetic-secret synthetic-token'
            with patch.object(m.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, payload, payload)):
                api.call('test', ['synthetic-command'])
            for p in Path(td).iterdir():
                self.assertNotIn(payload, p.read_bytes())
                for value in env.values(): self.assertNotIn(value.encode(), p.read_bytes())

    def test_timeout_is_recorded_without_automatic_retry(self):
        with tempfile.TemporaryDirectory() as td:
            api = m.Live(Path(td), '/tf', {})
            with patch.object(m.subprocess, 'run', side_effect=subprocess.TimeoutExpired(['synthetic'], 1, output=b'partial')) as run:
                with self.assertRaises(m.Stop): api.call('test', ['synthetic'])
                self.assertEqual(run.call_count, 1)
            self.assertTrue(api.records[0]['timeout'])
            self.assertEqual(api.records[0]['rc'], 124)

    def test_wrong_identity_stops_before_backend_or_writes(self):
        with tempfile.TemporaryDirectory() as td:
            api = m.Live(Path(td), '/tf', {})
            with patch.object(api, 'aws', return_value=subprocess.CompletedProcess([], 0, b'{"Arn":"arn:aws:iam::774055931866:root"}', b'')), patch.object(api, 'call') as call:
                with self.assertRaises(m.Stop): api.preflight(Path('.'))
                call.assert_not_called()

    def test_relocated_backend_is_authoritative_and_still_enforces_scope(self):
        with tempfile.TemporaryDirectory() as td:
            evidence = Path(td) / 'evidence'; evidence.mkdir()
            data = Path(td) / 'data'; data.mkdir()
            api = m.Live(evidence, '/tf', {'TF_DATA_DIR': str(data)})
            api.root.mkdir()
            lock = api.root / '.terraform.lock.hcl'; lock.write_bytes(b'pinned-lock')
            manifest = {'terraform/network/.terraform.lock.hcl': m.sha(lock.read_bytes())}
            valid = dict(type='s3', config=dict(bucket=m.BUCKET, key=m.STATE,
                         region=m.REGION, use_lockfile=True, encrypt=True))
            # A valid stale HOME metadata file must not hide wrong relocated metadata.
            old = api.root / '.terraform'; old.mkdir()
            (old / 'terraform.tfstate').write_text(json.dumps({'backend': valid}))
            for field, value in [('bucket', 'foreign'), ('key', 'foreign'),
                                 ('region', 'us-east-1'), ('use_lockfile', False),
                                 ('encrypt', False)]:
                with self.subTest(field=field):
                    wrong = json.loads(json.dumps(valid)); wrong['config'][field] = value
                    (data / 'terraform.tfstate').write_text(json.dumps({'backend': wrong}))
                    with self.assertRaises(m.Stop): api.verify_backend(manifest)
            (data / 'terraform.tfstate').write_text(json.dumps({'backend': valid}))
            (old / 'terraform.tfstate').write_text('not valid JSON')
            api.verify_backend(manifest)
            lock.write_bytes(b'changed-lock')
            with self.assertRaises(m.Stop): api.verify_backend(manifest)

    def test_missing_relocated_metadata_cannot_fall_back_to_home(self):
        with tempfile.TemporaryDirectory() as td:
            api = m.Live(Path(td), '/tf', {'TF_DATA_DIR': str(Path(td) / 'absent')})
            with self.assertRaises(FileNotFoundError): api.verify_backend({})


if __name__ == '__main__':
    unittest.main()
