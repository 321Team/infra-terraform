#!/usr/bin/env python3
"""Owned S3 lock collision fixture; default preflight is read-only in AWS.

No credential acquisition, Apply, state payload write/delete, or force-unlock.
Execution requires an externally confirmed exclusive window and existing own MFA role.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import tempfile
import uuid

ACCOUNT = '774055931866'
REGION = 'ap-northeast-2'
BUCKET = 'fds-tfstate-774055931866-ap-northeast-2'
STATE = 'phase2/network/terraform.tfstate'
LOCK = STATE + '.tflock'
CALLER = f'arn:aws:sts::{ACCOUNT}:assumed-role/FDS-IaC-Operator/321team-gwonuk'
SOURCE = '81162467bb2f99a099cb7067fbc3f63e1c0dbed8'
VERSION = '1.16.4'


class Stop(RuntimeError):
    pass


def require(condition, message):
    if not condition:
        raise Stop(message)


def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def fixture_bytes():
    return (json.dumps(dict(ID=str(uuid.uuid4()), Operation='OperationTypePlan',
                           Info='U1-I3 owned test fixture', Who=CALLER,
                           Version=VERSION, Created=utc(), Path=BUCKET + '/' + STATE),
                       sort_keys=True) + '\n').encode()


def owned(current, body, etag):
    require(current is not None, 'Owned lock disappeared; stop without deletion')
    require(current[0] == body and current[1] == etag,
            'Lock content/ETag changed; do not delete')
    require(json.loads(current[0])['ID'] == json.loads(body)['ID'], 'Lock ID mismatch')


def exercise(api, body):
    """No finally-delete: ambiguous writes/timeouts require readback and human recovery."""
    api.empty_prefix('before')
    require(api.get_lock('before') is None, 'Existing lock; no overwrite')
    etag = api.put_lock(body)  # exactly one conditional attempt
    require(isinstance(etag, str) and etag not in ('', '*'), 'Missing exact ETag')
    owned(api.get_lock('created'), body, etag)
    result = api.plan('collision', 5)
    lock_id = json.loads(body)['ID']
    output = (result.stdout + result.stderr).decode(errors='replace')
    require(result.returncode == 1 and 'Error acquiring the state lock' in output
            and re.search(r'(?m)^\s*ID:\s*' + re.escape(lock_id) + r'\s*$', output),
            'Expected lock-acquisition failure with our ID not observed')
    owned(api.get_lock('pre-delete'), body, etag)
    api.delete_lock(etag)  # exact key + If-Match, no version ID
    require(api.get_lock('deleted') is None, 'Lock remains after conditional deletion')
    api.empty_prefix('after-fixture')
    result = api.plan('retry', 60)
    require(result.returncode == 2, 'Retry must produce expected nonempty plan (rc2)')
    api.check_plan()
    require(api.get_lock('after-retry') is None, 'Terraform retry left a lock')
    api.empty_prefix('after-retry')


class Live:
    def __init__(self, evidence, terraform, env):
        self.e = evidence
        self.tf = str(Path(terraform).resolve())
        self.env = dict(env)
        self.records = []
        self.sequence = 0
        self.root = evidence / 'network'
        self.secrets = [env.get(k, '').encode() for k in
                        ('AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_SESSION_TOKEN')]

    def call(self, name, argv, timeout=45):
        self.sequence += 1
        stem = f'{self.sequence:02d}-{name}'
        record = dict(name=name, argv=argv, started_utc=utc())
        try:
            result = subprocess.run(argv, capture_output=True, env=self.env, timeout=timeout)
        except subprocess.TimeoutExpired as ex:
            result = subprocess.CompletedProcess(argv, 124, ex.stdout or b'', ex.stderr or b'')
            record['timeout'] = True
        # Defensive redaction occurs before any stdout/stderr is persisted.
        for stream in ('stdout', 'stderr'):
            data = getattr(result, stream)
            for secret in self.secrets:
                if secret:
                    data = data.replace(secret, b'[REDACTED]')
            (self.e / (stem + '.' + stream)).write_bytes(data)
            record[stream + '_sha256'] = sha(data)
        record.update(rc=result.returncode, finished_utc=utc())
        self.records.append(record)
        (self.e / 'execution-records.json').write_text(json.dumps(self.records, indent=2))
        if record.get('timeout'):
            raise Stop(name + ' timed out; no automatic mutation retry or cleanup')
        return result

    def aws(self, name, args):
        return self.call(name, ['aws', *args, '--region', REGION, '--output', 'json',
                               '--no-cli-pager', '--cli-connect-timeout', '10',
                               '--cli-read-timeout', '20'])

    def ok(self, result):
        require(result.returncode == 0, 'Command failed; inspect private execution records')
        return json.loads(result.stdout or b'{}')

    def s3(self, name, operation, extra):
        return self.aws(name, ['s3api', operation, '--bucket', BUCKET,
                              '--expected-bucket-owner', ACCOUNT, *extra])

    def empty_prefix(self, label):
        d = self.ok(self.s3(label + '-list', 'list-objects-v2',
                           ['--prefix', STATE, '--max-keys', '10', '--no-paginate']))
        require(not d.get('IsTruncated') and not d.get('Contents'),
                'State/lock prefix is not empty; this runner only supports pre-Apply empty state')

    def get_lock(self, label):
        dest = self.e / (label + '-lock.json')
        r = self.s3(label + '-get', 'get-object', ['--key', LOCK, str(dest)])
        if r.returncode != 0:
            # Only a service NoSuchKey is absence. AccessDenied/generic errors STOP.
            require(r.returncode == 254 and b'(NoSuchKey)' in r.stderr,
                    'Lock read not confirmed absent; do not mutate')
            return None
        d = self.ok(r)
        return dest.read_bytes(), d['ETag']

    def put_lock(self, body):
        p = self.e / 'fixture.json'
        p.write_bytes(body)
        d = self.ok(self.s3('put-fixture', 'put-object',
                           ['--key', LOCK, '--body', str(p), '--if-none-match', '*',
                            '--server-side-encryption', 'AES256']))
        (self.e / 'owned-lock-receipt.json').write_text(json.dumps(
            dict(id=json.loads(body)['ID'], sha256=sha(body), etag=d['ETag'],
                 bucket=BUCKET, key=LOCK, version_id=d.get('VersionId')), indent=2))
        require(d.get('VersionId') not in (None, '', 'null'),
                'Fixture lacks a non-null version ID; stop without deletion')
        return d['ETag']

    def delete_lock(self, etag):
        self.ok(self.s3('delete-fixture', 'delete-object',
                        ['--key', LOCK, '--if-match', etag]))

    def plan(self, name, seconds):
        return self.call(name, [self.tf, '-chdir=' + str(self.root), 'plan', '-no-color',
                               '-input=false', '-detailed-exitcode',
                               '-var=execution_enabled=true', '-lock-timeout=' + str(seconds) + 's',
                               '-out=' + str(self.e / (name + '.tfplan'))], timeout=240)

    def check_plan(self):
        d = self.ok(self.call('show-retry', [self.tf, '-chdir=' + str(self.root),
                                           'show', '-json', str(self.e / 'retry.tfplan')]))
        changes = [x for x in d.get('resource_changes', []) if x['mode'] == 'managed']
        require(len(changes) == 20 and all(x['change']['actions'] == ['create'] for x in changes),
                'Unexpected retry changes; no Apply')

    def preflight(self, repo):
        require(self.ok(self.aws('caller', ['sts', 'get-caller-identity']))['Arn'] == CALLER,
                'Use only own approved MFA IaC role; no root/personal user substitute')
        # Generate skeleton locally; no remote mutation, proves CLI conditional options exist.
        for op, key in [('put-object', 'IfNoneMatch'), ('delete-object', 'IfMatch')]:
            d = self.ok(self.call(op + '-syntax', ['aws', 's3api', op, '--generate-cli-skeleton', 'input']))
            require(key in d, 'AWS CLI lacks required conditional option')
        version = self.ok(self.call('terraform-version', [self.tf, 'version', '-json']))
        require(version['terraform_version'] == VERSION, 'Terraform version mismatch')
        self.root.mkdir()
        files = self.call('source-files', ['git', '-C', str(repo), 'ls-tree', '-r',
                                        '--name-only', SOURCE, '--', 'terraform/network/'])
        require(files.returncode == 0, 'Pinned source commit unavailable')
        names = files.stdout.decode().splitlines()
        require(len(names) == 6, 'Pinned source file set changed')
        manifest = {}
        for i, name in enumerate(names):
            require(name.startswith('terraform/network/'), 'Source path mismatch')
            r = self.call('source-blob-' + str(i), ['git', '-C', str(repo), 'show', SOURCE + ':' + name])
            require(r.returncode == 0, 'Source blob unavailable')
            dest = self.root / name.removeprefix('terraform/network/')
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(r.stdout)
            manifest[name] = sha(r.stdout)
        (self.e / 'source-manifest.json').write_text(json.dumps(manifest, indent=2))
        for name, args in [('init', ['init', '-input=false', '-lockfile=readonly',
                                     '-backend-config=backend.hcl.example']),
                           ('workspace', ['workspace', 'show']), ('validate', ['validate', '-json'])]:
            r = self.call(name, [self.tf, '-chdir=' + str(self.root), *args], timeout=240)
            require(r.returncode == 0, name + ' failed')
            if name == 'workspace':
                require(r.stdout.strip() == b'default', 'Only default workspace supported')
            if name == 'validate':
                require(json.loads(r.stdout)['valid'], 'Validation failed')
        self.verify_backend(manifest)
        self.empty_prefix('preflight')
        require(self.get_lock('preflight') is None, 'Existing lock')

    def verify_backend(self, manifest):
        # init writes backend metadata alongside providers in the private data directory.
        config = json.loads((Path(self.env['TF_DATA_DIR']) / 'terraform.tfstate').read_text())['backend']
        require(config['type'] == 's3', 'Backend mismatch')
        c = config['config']
        require(c['bucket'] == BUCKET and c['key'] == STATE and c['region'] == REGION
                and c['use_lockfile'] is True and c['encrypt'] is True,
                'Backend target/locking/encryption mismatch')
        require(sha((self.root / '.terraform.lock.hcl').read_bytes()) ==
                manifest['terraform/network/.terraform.lock.hcl'], 'Provider lock changed')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo', type=Path, required=True)
    p.add_argument('--terraform', required=True)
    p.add_argument('--execute', action='store_true')
    p.add_argument('--window-confirmation', help='Actual coordination record/reference, not a substitute for confirmation')
    a = p.parse_args()
    require(not a.execute or bool(a.window_confirmation and a.window_confirmation.strip()),
            'Execution requires the confirmed exclusive-window record')
    require(os.name == 'posix', 'Live runner supports Linux CloudShell only; tests are portable')
    env = dict(os.environ)
    require(all(env.get(k) for k in ('AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_SESSION_TOKEN')),
            'Prepare existing own temporary role session in environment; never supply secrets as arguments')
    require(not any(k.startswith(('TF_', 'AWS_ENDPOINT_URL')) or k in
                    ('AWS_PROFILE', 'AWS_DEFAULT_PROFILE', 'AWS_CA_BUNDLE', 'AWS_DATA_PATH',
                     'AWS_CONFIG_FILE', 'AWS_SHARED_CREDENTIALS_FILE') for k in env),
            'Unreviewed Terraform/AWS configuration overrides detected')
    os.umask(0o077)
    e = Path(tempfile.mkdtemp(prefix='fds-u1-lock-', dir=Path.home()))
    data = Path(tempfile.mkdtemp(prefix='fds-u1-data-', dir='/tmp'))
    blank = e / 'empty-config'; blank.write_text('')
    env.update(AWS_REGION=REGION, AWS_DEFAULT_REGION=REGION, AWS_MAX_ATTEMPTS='1',
               AWS_CONFIG_FILE=str(blank), AWS_SHARED_CREDENTIALS_FILE=str(blank),
               AWS_PAGER='', TF_CLI_CONFIG_FILE=str(blank), TF_DATA_DIR=str(data),
               TF_IN_AUTOMATION='1', CHECKPOINT_DISABLE='1')
    api = Live(e, a.terraform, env)
    summary = dict(started_utc=utc(), host=socket.gethostname(), source=SOURCE,
                   terraform_data_dir=str(data),
                   window_confirmation=a.window_confirmation, mode='RUNTIME' if a.execute else 'PREFLIGHT',
                   apply='NOT_RUN', real_process_crash='NOT_RUN', outcome='STOP')
    shutil.copyfile(__file__, e / 'runner.py')
    try:
        api.preflight(a.repo.resolve())
        if a.execute:
            exercise(api, fixture_bytes())
        summary['outcome'] = 'FIXTURE_COLLISION_RETRY_PASS' if a.execute else 'READ_ONLY_PREFLIGHT_PASS'
    except (Exception, KeyboardInterrupt) as ex:
        summary['error'] = type(ex).__name__ + ': ' + str(ex)
        summary['recovery'] = 'No automatic delete/retry. Inspect records and current lock ownership/processes first.'
    finally:
        summary['finished_utc'] = utc()
        (e / 'summary.json').write_text(json.dumps(summary, indent=2))
        # Backend/plugin caches are excluded; top-level logs and own lock/plan evidence only.
        files = sorted(x for x in e.iterdir() if x.is_file())
        (e / 'SHA256SUMS').write_text(''.join(sha(x.read_bytes()) + '  ' + x.name + '\n' for x in files))
        print(summary['outcome'], str(e))
    return 0 if summary['outcome'].endswith('PASS') else 1


if __name__ == '__main__':
    raise SystemExit(main())
