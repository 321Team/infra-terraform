"""Read-only before inventory for the proposed IaC grant. Never grants access."""
import argparse
import importlib.util
import os
import platform
import subprocess
from pathlib import Path
import tempfile

spec = importlib.util.spec_from_file_location('capture', Path(__file__).with_name('central-iam-validation.py'))
capture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(capture)
SOURCE = 'c699d667f8af3f983f54fd54629401562789bdd4'
USERS = ['321team-gwonuk', '321team-hayeoung']
POLICIES = ['FDS-IaC-State-PassRole', 'FDS-IaC-Network', 'FDS-IaC-Vpn', 'FDS-IaC-Guardrails']
# Replace rather than extend: this collector cannot call simulation or mutation APIs.
capture.ALLOWED = {('sts', 'get-caller-identity')} | {('iam', op) for op in (
    'get-role', 'get-user', 'get-policy', 'get-policy-version', 'list-entities-for-policy',
    'list-attached-user-policies', 'list-user-policies', 'get-user-policy', 'list-groups-for-user',
    'list-attached-group-policies', 'list-group-policies', 'get-group-policy')}

def run(parent, expected_arn):
    if expected_arn != 'arn:aws:iam::774055931866:root':
        raise RuntimeError('This before capture is bound to the existing central validation caller')
    if any(k.startswith('AWS_ENDPOINT_URL') or k in ('AWS_CA_BUNDLE', 'AWS_DATA_PATH') for k in os.environ):
        raise RuntimeError('Review environment overrides first')
    out = Path(tempfile.mkdtemp(prefix='fds-grant-before-', dir=parent))
    out.chmod(0o700)
    cap = capture.Capture(out)
    summary = {'source': SOURCE, 'collector_sha256': capture.digest(__file__),
               'capture_helper_sha256': capture.digest(capture.__file__),
               'host': platform.node(), 'platform': platform.platform(),
               'started_utc': capture.now(), 'aws_mutation': 'NOT_RUN', 'status': 'INCOMPLETE'}
    seen = set()
    def managed(arn):
        if arn in seen:
            return
        seen.add(arn)
        name = 'managed-' + str(len(seen))
        doc = cap.call(name, 'iam', 'get-policy', ['--policy-arn', arn])
        cap.call(name+'-version', 'iam', 'get-policy-version',
                 ['--policy-arn', arn, '--version-id', doc['Policy']['DefaultVersionId']])
    try:
        cli = subprocess.run(['aws','--version'], capture_output=True, timeout=10)
        (out/'aws-version.stdout').write_bytes(cli.stdout)
        (out/'aws-version.stderr').write_bytes(cli.stderr)
        summary['aws_version_rc'] = cli.returncode
        if cli.returncode != 0:
            raise RuntimeError('AWS CLI version failed')
        who = cap.call('identity', 'sts', 'get-caller-identity')
        if who.get('Account') != capture.ACCOUNT or who.get('Arn') != expected_arn:
            raise RuntimeError('Caller mismatch; STOP')
        for role in ['FDS-IaC-Operator', 'FDS-Network-Operator', 'FDS-ReadOnly-Audit']:
            cap.call('role-'+role, 'iam', 'get-role', ['--role-name', role], absent=True)
        for name in POLICIES:
            arn = 'arn:aws:iam::774055931866:policy/' + name
            doc = cap.call('candidate-'+name, 'iam', 'get-policy', ['--policy-arn', arn], absent=True)
            if doc.get('observed') != 'ABSENT':
                managed(arn)
                cap.call('candidate-entities-'+name, 'iam', 'list-entities-for-policy', ['--policy-arn', arn])
        groups = set()
        for user in USERS:
            doc = cap.call('user-'+user, 'iam', 'get-user', ['--user-name', user])
            if doc['User']['Arn'] != 'arn:aws:iam::774055931866:user/'+user:
                raise RuntimeError('User path differs from reviewed trust; STOP')
            if doc['User'].get('PermissionsBoundary'):
                managed(doc['User']['PermissionsBoundary']['PermissionsBoundaryArn'])
            inline = cap.call('inline-'+user, 'iam', 'list-user-policies', ['--user-name', user])
            for i, name in enumerate(inline['PolicyNames']):
                cap.call('inline-'+user+'-'+str(i), 'iam', 'get-user-policy', ['--user-name', user, '--policy-name', name])
            attached = cap.call('attached-'+user, 'iam', 'list-attached-user-policies', ['--user-name', user])
            for item in attached['AttachedPolicies']:
                managed(item['PolicyArn'])
            member = cap.call('groups-'+user, 'iam', 'list-groups-for-user', ['--user-name', user])
            groups.update(x['GroupName'] for x in member['Groups'])
        for i, group in enumerate(sorted(groups)):
            prefix = 'group-'+str(i)
            inline = cap.call(prefix+'-inline', 'iam', 'list-group-policies', ['--group-name', group])
            for j, name in enumerate(inline['PolicyNames']):
                cap.call(prefix+'-inline-'+str(j), 'iam', 'get-group-policy', ['--group-name', group, '--policy-name', name])
            attached = cap.call(prefix+'-attached', 'iam', 'list-attached-group-policies', ['--group-name', group])
            for item in attached['AttachedPolicies']:
                managed(item['PolicyArn'])
        summary['status'] = 'BEFORE_CAPTURE_COMPLETE_REVIEW_REQUIRED'
    except Exception as exc:
        summary['error'] = str(exc)
        raise
    finally:
        summary.update(finished_utc=capture.now(), records=cap.records)
        capture.write(out/'summary.json', summary)
        capture.write(out/'capture-manifest.json', {p.name:capture.digest(p) for p in out.iterdir() if p.is_file()})
        print(out)
    return out

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-parent', required=True, type=Path)
    parser.add_argument('--expected-caller-arn', required=True)
    args = parser.parse_args()
    os.umask(0o077)
    run(args.output_parent, args.expected_caller_arn)
