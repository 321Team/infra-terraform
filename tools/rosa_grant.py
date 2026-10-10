#!/usr/bin/env python3
"""ROSA prereq (infra-terraform#12) grant runner for FDS-IaC-Operator. Central executor only.

One reviewed IAM write per invocation. Each `run <step>`:
  1. verifies repo policy files against SHA256SUMS,
  2. reads live state (read-only calls) and checks the step precondition,
  3. without --execute: prints the exact aws argv and stops (default),
  4. with --execute: runs that single write, re-reads state until the postcondition holds,
     and appends argv/RC/UTC/IDs to a private ledger (no credentials are recorded).

Steps (A1 → A3; rollback steps are listed in STEPS too):
  guardrails-v2     FDS-IaC-Guardrails new default version = v2 candidate (v1 + 11 NotAction)
  subscribe-create  CreatePolicy FDS-RosaBootstrap-Subscribe (not attached)
  subscribe-attach  attach to FDS-IaC-Operator (A1 only)
  subscribe-detach  detach right after A1 activation readback
  prereq-create     CreatePolicy FDS-IaC-RosaPrereq (read-only policy)
  prereq-attach     attach to FDS-IaC-Operator
  rollback: prereq-detach, subscribe-delete / prereq-delete (only the PolicyId this ledger created),
            guardrails-v1 (set default back to the version whose document equals v1)

Not done here: any IAM role/OIDC creation (terraform/rosa-prereq on the central path), trust
changes, user/group policies, deleting Guardrails versions, adopting pre-existing policies.

Exit: 0 OK (dry-run printed or step verified), 1 STOP, 2 input error.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ACCOUNT = '774055931866'
ROLE = 'FDS-IaC-Operator'
ROOT = Path(__file__).resolve().parents[1]
ROSA_DIR = ROOT / 'iam/rosa-prereq-draft-20261009'
BASE_DIR = ROOT / 'iam/full-policy-draft-20261009'

FILES = {
    'v1': (BASE_DIR, 'policies/FDS-IaC-Guardrails.json'),
    'v2': (ROSA_DIR, 'guardrails-candidate/FDS-IaC-Guardrails.v2-candidate.json'),
    'subscribe': (ROSA_DIR, 'policies/FDS-RosaBootstrap-Subscribe.json'),
    'prereq': (ROSA_DIR, 'policies/FDS-IaC-RosaPrereq.json'),
}


def arn(name):
    return f'arn:aws:iam::{ACCOUNT}:policy/{name}'


GUARDRAILS = arn('FDS-IaC-Guardrails')
BASE_ATTACHED = {arn(n) for n in ('FDS-IaC-Guardrails', 'FDS-IaC-State-PassRole', 'FDS-IaC-Network', 'FDS-IaC-Vpn')}
NEW = {
    'subscribe': ('FDS-RosaBootstrap-Subscribe', 'phase2-rosa-a1-subscribe'),
    'prereq': ('FDS-IaC-RosaPrereq', 'phase2-rosa-a3-read'),
}
MAX_POLICY_VERSIONS = 5


class Stop(RuntimeError):
    pass


class InputError(RuntimeError):
    pass


def utc():
    return dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def load_sources():
    """Return {key: (path, parsed json)} after checking each file against its folder SHA256SUMS."""
    out = {}
    for key, (folder, rel) in FILES.items():
        sums = {}
        for line in (folder / 'SHA256SUMS').read_text().splitlines():
            digest, name = line.split(maxsplit=1)
            sums[name.lstrip('*')] = digest
        data = (folder / rel).read_bytes()
        if sums.get(rel) != sha256(data):
            raise InputError(f'{folder.name}/{rel} does not match SHA256SUMS')
        out[key] = (folder / rel, json.loads(data))
    return out


def aws_cli(*args):
    proc = subprocess.run(['aws', *args, '--output', 'json'], capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


class Aws:
    """Read helpers. `call` returns (rc, stdout, stderr) for argv without the leading 'aws'."""

    def __init__(self, call=aws_cli):
        self.call = call

    def read(self, *args, missing_ok=False):
        rc, out, err = self.call(*args)
        if rc != 0:
            if missing_ok and 'NoSuchEntity' in err:
                return None
            raise Stop(f'read failed: aws {" ".join(args[:2])} rc={rc} {err.strip()[:300]}')
        return json.loads(out or '{}')

    def state(self):
        s = {'caller': self.read('sts', 'get-caller-identity')}
        s['attached'] = {p['PolicyArn'] for p in self.read(
            'iam', 'list-attached-role-policies', '--role-name', ROLE)['AttachedPolicies']}
        s['inline'] = self.read('iam', 'list-role-policies', '--role-name', ROLE)['PolicyNames']
        s['policies'] = {}
        for key, name in [('guardrails', 'FDS-IaC-Guardrails')] + [(k, v[0]) for k, v in NEW.items()]:
            got = self.read('iam', 'get-policy', '--policy-arn', arn(name), missing_ok=True)
            if got is None:
                s['policies'][key] = None
                continue
            pol = got['Policy']
            versions = self.read('iam', 'list-policy-versions', '--policy-arn', arn(name))['Versions']
            docs = {v['VersionId']: self.read('iam', 'get-policy-version', '--policy-arn', arn(name),
                                              '--version-id', v['VersionId'])['PolicyVersion']['Document']
                    for v in versions}
            ent = self.read('iam', 'list-entities-for-policy', '--policy-arn', arn(name))
            s['policies'][key] = {
                'id': pol['PolicyId'], 'default': pol['DefaultVersionId'], 'docs': docs,
                'roles': sorted(r['RoleName'] for r in ent.get('PolicyRoles', [])),
                'users': ent.get('PolicyUsers', []), 'groups': ent.get('PolicyGroups', []),
            }
        return s


def default_doc(p):
    return p['docs'][p['default']] if p else None


def version_with(p, doc):
    return next((v for v, d in sorted(p['docs'].items()) if d == doc), None)


def only_role(p):
    return p['roles'] == [ROLE] and not p['users'] and not p['groups']


def unattached(p):
    return p['roles'] == [] and not p['users'] and not p['groups']


# ---------------- steps ----------------
# Each step: pre(state, src, ledger) -> list of failed checks; argv(state, src, ledger) -> list;
# post(state, src, ledger) -> list of failed checks; record(state) -> dict for the ledger.

def common_pre(s, src, allowed_extra):
    fails = []
    if s['inline']:
        fails.append(f'role inline policies must be 0, got {s["inline"]}')
    missing = BASE_ATTACHED - s['attached']
    extra = s['attached'] - BASE_ATTACHED - {arn(NEW[k][0]) for k in allowed_extra}
    if missing:
        fails.append(f'base policies missing from role: {sorted(missing)}')
    if extra:
        fails.append(f'unexpected policies on role: {sorted(extra)}')
    g = s['policies']['guardrails']
    if g is None:
        fails.append('FDS-IaC-Guardrails not found')
    elif not only_role(g):
        fails.append(f'FDS-IaC-Guardrails attached to others: roles={g["roles"]} users={g["users"]} groups={g["groups"]}')
    return fails


def guardrails_is(s, src, key):
    g = s['policies']['guardrails']
    return [] if g and default_doc(g) == src[key][1] else [f'Guardrails default version is not {key}']


def make_create(key):
    name, purpose = NEW[key]

    def pre(s, src, ledger):
        f = common_pre(s, src, ['subscribe', 'prereq']) + guardrails_is(s, src, 'v2')
        if s['policies'][key] is not None:
            f.append(f'{name} already exists (no adopt, no update)')
        return f

    def argv(s, src, ledger):
        return ['iam', 'create-policy', '--policy-name', name, '--path', '/',
                '--policy-document', f'file://{src[key][0]}',
                '--description', f'infra-terraform#12 {purpose}',
                '--tags', 'Key=Project,Value=fds-hybrid', 'Key=ManagedBy,Value=project-bootstrap',
                f'Key=Purpose,Value={purpose}']

    def post(s, src, ledger):
        p = s['policies'][key]
        if p is None:
            return [f'{name} not visible yet']
        f = []
        if len(p['docs']) != 1 or default_doc(p) != src[key][1]:
            f.append(f'{name} document/version count differs from repo file')
        if not unattached(p):
            f.append(f'{name} must not be attached yet')
        return f

    return {'pre': pre, 'argv': argv, 'post': post,
            'record': lambda s: {'policy_arn': arn(name), 'policy_id': s['policies'][key]['id']}}


def owned(key, s, ledger):
    """Policy must be the exact one this ledger created (PolicyId match), not just the same name."""
    p = s['policies'][key]
    created = [e for e in ledger if e.get('step') == f'{key}-create' and e.get('verified')]
    if p is None:
        return [f'{NEW[key][0]} not found']
    if not created or created[-1]['ids'].get('policy_id') != p['id']:
        return [f'{NEW[key][0]} PolicyId {p["id"]} is not recorded as created by this ledger']
    return []


def make_attach(key):
    name = NEW[key][0]
    others = [k for k in NEW if k != key]

    def pre(s, src, ledger):
        f = common_pre(s, src, others) + guardrails_is(s, src, 'v2') + owned(key, s, ledger)
        p = s['policies'][key]
        if p and (default_doc(p) != src[key][1] or len(p['docs']) != 1):
            f.append(f'{name} document differs from repo file')
        if p and not unattached(p):
            f.append(f'{name} already attached somewhere')
        return f

    def post(s, src, ledger):
        p = s['policies'][key]
        f = [] if arn(name) in s['attached'] else [f'{name} not attached to {ROLE}']
        if p is None or not only_role(p):
            f.append(f'{name} must be attached to {ROLE} only')
        return f + common_pre(s, src, ['subscribe', 'prereq'])

    return {'pre': pre, 'post': post,
            'argv': lambda s, src, l: ['iam', 'attach-role-policy', '--role-name', ROLE, '--policy-arn', arn(name)],
            'record': lambda s: {'policy_arn': arn(name), 'policy_id': s['policies'][key]['id']}}


def make_detach(key):
    name = NEW[key][0]

    def pre(s, src, ledger):
        f = common_pre(s, src, ['subscribe', 'prereq'])
        if arn(name) not in s['attached']:
            f.append(f'{name} is not attached to {ROLE}')
        return f

    def post(s, src, ledger):
        p = s['policies'][key]
        f = [] if arn(name) not in s['attached'] else [f'{name} still attached']
        if p is not None and not unattached(p):
            f.append(f'{name} still attached somewhere')
        return f

    return {'pre': pre, 'post': post,
            'argv': lambda s, src, l: ['iam', 'detach-role-policy', '--role-name', ROLE, '--policy-arn', arn(name)],
            'record': lambda s: {'policy_arn': arn(name)}}


def make_delete(key):
    name = NEW[key][0]

    def pre(s, src, ledger):
        f = owned(key, s, ledger)
        p = s['policies'][key]
        if p and not unattached(p):
            f.append(f'{name} still attached')
        if p and len(p['docs']) != 1:
            f.append(f'{name} has {len(p["docs"])} versions; review manually')
        return f

    return {'pre': pre,
            'post': lambda s, src, l: [] if s['policies'][key] is None else [f'{name} still exists'],
            'argv': lambda s, src, l: ['iam', 'delete-policy', '--policy-arn', arn(name)],
            'record': lambda s: {'policy_arn': arn(name)}}


def gr_v2_pre(s, src, ledger):
    f = common_pre(s, src, []) + guardrails_is(s, src, 'v1')
    g = s['policies']['guardrails']
    if g and len(g['docs']) >= MAX_POLICY_VERSIONS:
        f.append(f'Guardrails already has {len(g["docs"])} versions (max {MAX_POLICY_VERSIONS}); '
                 'deleting versions is out of scope')
    if g and version_with(g, src['v2'][1]):
        f.append('a v2 version already exists; use review, not a second create')
    return f


def gr_v1_pre(s, src, ledger):
    f = common_pre(s, src, []) + guardrails_is(s, src, 'v2')
    g = s['policies']['guardrails']
    if g and not version_with(g, src['v1'][1]):
        f.append('no Guardrails version equals v1')
    return f


STEPS = {
    'guardrails-v2': {
        'pre': gr_v2_pre,
        'argv': lambda s, src, l: ['iam', 'create-policy-version', '--policy-arn', GUARDRAILS,
                                   '--policy-document', f'file://{src["v2"][0]}', '--set-as-default'],
        'post': lambda s, src, l: guardrails_is(s, src, 'v2') + common_pre(s, src, []),
        'record': lambda s: {'default_version': s['policies']['guardrails']['default']},
    },
    'subscribe-create': make_create('subscribe'),
    'subscribe-attach': make_attach('subscribe'),
    'subscribe-detach': make_detach('subscribe'),
    'prereq-create': make_create('prereq'),
    'prereq-attach': make_attach('prereq'),
    'prereq-detach': make_detach('prereq'),
    'subscribe-delete': make_delete('subscribe'),
    'prereq-delete': make_delete('prereq'),
    'guardrails-v1': {
        'pre': gr_v1_pre,
        'argv': lambda s, src, l: ['iam', 'set-default-policy-version', '--policy-arn', GUARDRAILS,
                                   '--version-id', version_with(s['policies']['guardrails'], src['v1'][1])],
        'post': lambda s, src, l: guardrails_is(s, src, 'v1'),
        'record': lambda s: {'default_version': s['policies']['guardrails']['default']},
    },
}


def summary(s, src):
    g = s['policies']['guardrails']
    gv = 'absent' if g is None else ('v1' if default_doc(g) == src['v1'][1] else
                                     'v2' if default_doc(g) == src['v2'][1] else 'OTHER')
    lines = [f'caller={s["caller"].get("Arn")}', f'guardrails_default={gv} versions={0 if g is None else len(g["docs"])}',
             f'role_attached={sorted(a.rsplit("/", 1)[1] for a in s["attached"])} inline={s["inline"]}']
    for key, (name, _) in NEW.items():
        p = s['policies'][key]
        lines.append(f'{name}=' + ('absent' if p is None else
                                    f'id={p["id"]} versions={len(p["docs"])} roles={p["roles"]}'))
    return lines


def read_ledger(path):
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def run(step, expected_caller, ledger_dir, execute, aws=None, sleep=time.sleep, attempts=12):
    aws = aws or Aws()
    src = load_sources()
    ledger_dir = Path(ledger_dir)
    ledger_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    if ledger_dir.stat().st_mode & 0o077:
        raise InputError(f'ledger dir must be private (0700): {ledger_dir}')
    ledger_path = ledger_dir / 'rosa-grant-ledger.jsonl'
    ledger = read_ledger(ledger_path)

    s = aws.state()
    if s['caller'].get('Account') != ACCOUNT or s['caller'].get('Arn') != expected_caller:
        raise Stop(f'caller mismatch: {s["caller"].get("Arn")} != {expected_caller}')
    for line in summary(s, src):
        print(line)
    if step == 'status':
        return 0

    spec = STEPS[step]
    fails = spec['pre'](s, src, ledger)
    for f in fails:
        print(f'STOP  pre: {f}')
    if fails:
        return 1
    argv = spec['argv'](s, src, ledger)
    print('PLAN  aws ' + ' '.join(argv))
    if not execute:
        print('dry-run: no write. Re-run with --execute inside the approved window.')
        return 0

    entry = {'utc_start': utc(), 'step': step, 'caller': s['caller'].get('Arn'), 'argv': ['aws', *argv],
             'source_sha256': {k: sha256(Path(p).read_bytes()) for k, (p, _) in src.items()}}
    rc, out, err = aws.call(*argv)
    entry.update(rc=rc, stdout_sha256=sha256(out.encode()), stderr=err.strip()[:500], utc_end=utc())
    fails = [f'write rc={rc}'] if rc != 0 else []
    if rc == 0:
        for i in range(attempts):
            s = aws.state()
            fails = spec['post'](s, src, ledger)
            if not fails:
                break
            sleep(5)
        entry['ids'] = spec['record'](s) if not fails else {}
    entry.update(verified=not fails, post_failures=fails, utc_readback=utc())
    with ledger_path.open('a') as fh:
        fh.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + '\n')
    os.chmod(ledger_path, 0o600)
    for line in summary(s, src):
        print(line)
    for f in fails:
        print(f'STOP  post: {f}')
    print(f'result={"VERIFIED" if not fails else "STOP"} step={step} ledger={ledger_path}')
    return 0 if not fails else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--expected-caller', required=True, help='exact ARN of the approved central session')
    ap.add_argument('--ledger-dir', required=True, help='private 0700 directory outside the repo')
    ap.add_argument('step', choices=['status', *STEPS])
    ap.add_argument('--execute', action='store_true', help='perform the single write (default: dry-run)')
    args = ap.parse_args(argv)
    try:
        return run(args.step, args.expected_caller, args.ledger_dir, args.execute)
    except InputError as e:
        print(f'INPUT ERROR: {e}', file=sys.stderr)
        return 2
    except (Stop, KeyError, ValueError) as e:
        print(f'STOP: {e}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
