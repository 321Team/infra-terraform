#!/usr/bin/env python3
"""ROSA prereq (infra-terraform#12 A3) central-path checks.

plan:     compare `terraform show -json <plan>` with the approved table before apply. Offline.
readback: compare live IAM after apply with the same table. AWS read calls only
          (get-role, list-attached-role-policies, list-role-policies, list/get OIDC provider);
          FDS-IaC-RosaPrereq.json is enough.

The expected table below is written independently of terraform/rosa-prereq/main.tf on purpose:
it mirrors ROSA CLI 1.2.53 `--mode manual` output (2026-10-09). If either side changes, both
change in the same reviewed PR.

Exit: 0 PASS, 1 STOP (any mismatch), 2 input/usage error.
No create/update/delete call, no credential handling. ocm-role / user-role are out of scope.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ACCOUNT = '774055931866'
TF_VERSION = '1.16.4'
OIDC_PREFIX = 'oidc.op1.openshiftapps.com/'
AWS_POLICY = 'arn:aws:iam::aws:policy'
INSTALLER = 'arn:aws:iam::710019948333:role/RH-Managed-OpenShift-Installer'
SUPPORT_RE = re.compile(r'^arn:aws:iam::[0-9]{12}:role/RH-Technical-Support-[0-9]+$')
CLIENT_IDS = ['openshift', 'sts.amazonaws.com']

ACCOUNT_ROLES = {
    'installer': ('fds-rosa-HCP-ROSA-Installer-Role', 'AWS', None,
                  ['service-role/ROSAInstallerPolicy']),
    'support': ('fds-rosa-HCP-ROSA-Support-Role', 'AWS', None,
                ['service-role/ROSASRESupportPolicy']),
    'worker': ('fds-rosa-HCP-ROSA-Worker-Role', 'Service', 'ec2.amazonaws.com',
               ['service-role/ROSAWorkerInstancePolicy', 'AmazonEC2ContainerRegistryReadOnly']),
}

# key: (namespace, name, service accounts, policy)
OPERATOR_ROLES = {
    'ingress': ('openshift-ingress-operator', 'cloud-credentials',
                ['ingress-operator'], 'ROSAIngressOperatorPolicy'),
    'ebs_csi': ('openshift-cluster-csi-drivers', 'ebs-cloud-credentials',
                ['aws-ebs-csi-driver-operator', 'aws-ebs-csi-driver-controller-sa'],
                'ROSAAmazonEBSCSIDriverOperatorPolicy'),
    'cloud_network_config': ('openshift-cloud-network-config-controller', 'cloud-credentials',
                             ['cloud-network-config-controller'], 'ROSACloudNetworkConfigOperatorPolicy'),
    'image_registry': ('openshift-image-registry', 'installer-cloud-credentials',
                       ['cluster-image-registry-operator', 'registry'], 'ROSAImageRegistryOperatorPolicy'),
    'kube_controller_manager': ('kube-system', 'kube-controller-manager',
                                ['kube-controller-manager'], 'ROSAKubeControllerPolicy'),
    'capa_controller_manager': ('kube-system', 'capa-controller-manager',
                                ['capa-controller-manager'], 'ROSANodePoolManagementPolicy'),
    'control_plane_operator': ('kube-system', 'control-plane-operator',
                               ['control-plane-operator'], 'ROSAControlPlaneOperatorPolicy'),
    'kms_provider': ('kube-system', 'kms-provider', ['kms-provider'], 'ROSAKMSProviderPolicy'),
}


class Stop(RuntimeError):
    pass


class InputError(RuntimeError):
    pass


def operator_role_name(namespace, name):
    return f'fds-rosa-{namespace}-{name}'[:64]


def as_list(value):
    return value if isinstance(value, list) else [value]


def normalize_trust(doc):
    """IAM may return single-element lists as strings; compare as sorted lists."""
    if isinstance(doc, str):
        doc = json.loads(doc)
    out = []
    for st in as_list(doc.get('Statement', [])):
        cond = {}
        for op, kv in (st.get('Condition') or {}).items():
            cond[op] = {k: sorted(as_list(v)) for k, v in kv.items()}
        out.append({
            'Effect': st.get('Effect'),
            'Action': sorted(as_list(st.get('Action'))),
            'Principal': {k: sorted(as_list(v)) for k, v in (st.get('Principal') or {}).items()},
            'Condition': cond,
            'extra': sorted(set(st) - {'Effect', 'Action', 'Principal', 'Condition', 'Sid'}),
        })
    return out


def expected_roles(stage, support_arn, oidc_host):
    """name -> (normalized trust, sorted managed policy ARNs)."""
    roles = {}
    for key, (name, ptype, pid, policies) in ACCOUNT_ROLES.items():
        ident = {'installer': INSTALLER, 'support': support_arn}.get(key, pid)
        trust = {'Statement': [{'Effect': 'Allow', 'Action': 'sts:AssumeRole',
                                'Principal': {ptype: [ident]}}]}
        roles[name] = (normalize_trust(trust), sorted(f'{AWS_POLICY}/{p}' for p in policies))
    if stage == 2:
        provider = f'arn:aws:iam::{ACCOUNT}:oidc-provider/{oidc_host}'
        for ns, name, sas, policy in OPERATOR_ROLES.values():
            trust = {'Statement': [{
                'Effect': 'Allow', 'Action': 'sts:AssumeRoleWithWebIdentity',
                'Principal': {'Federated': provider},
                'Condition': {'StringEquals': {
                    f'{oidc_host}:sub': [f'system:serviceaccount:{ns}:{sa}' for sa in sas]}},
            }]}
            roles[operator_role_name(ns, name)] = (
                normalize_trust(trust), [f'{AWS_POLICY}/service-role/{policy}'])
    return roles


def mask(text):
    """Hide the Red Hat org external ID in printed output."""
    return re.sub(r'(RH-Technical-Support-)[0-9]+', r'\1<masked>', str(text))


class Report:
    def __init__(self):
        self.rows = []

    def check(self, item, ok, detail=''):
        self.rows.append((ok, item, mask(detail)))

    def stops(self):
        return [r for r in self.rows if not r[0]]

    def print(self, title):
        print(f'== {title}')
        for ok, item, detail in self.rows:
            print(f"{'PASS' if ok else 'STOP'}  {item}" + (f'  -- {detail}' if detail and not ok else ''))
        n_stop = len(self.stops())
        print(f'result={"PASS" if n_stop == 0 else "STOP"} checks={len(self.rows)} stop={n_stop}')
        return 0 if n_stop == 0 else 1


def validate_args(stage, support_arn, oidc_host):
    if not SUPPORT_RE.match(support_arn or ''):
        raise InputError('--support-principal must be arn:aws:iam::<12 digits>:role/RH-Technical-Support-<digits>')
    if oidc_host is not None and not (oidc_host.startswith(OIDC_PREFIX)
                                      and re.fullmatch(r'[a-z0-9]+', oidc_host[len(OIDC_PREFIX):])):
        raise InputError(f'oidc host must be {OIDC_PREFIX}<lowercase alnum id>')
    if stage not in (1, 2):
        raise InputError('--stage must be 1 or 2')


# ---------------- plan ----------------

def account_addresses():
    roles = {f'aws_iam_role.account["{k}"]' for k in ACCOUNT_ROLES}
    att = {f'aws_iam_role_policy_attachment.account["{k}:{p.rsplit("/", 1)[-1]}"]'
           for k, v in ACCOUNT_ROLES.items() for p in v[3]}
    return roles | att | {'rhcs_rosa_oidc_config.managed', 'aws_iam_openid_connect_provider.rosa'}


def operator_addresses():
    return ({f'aws_iam_role.operator["{k}"]' for k in OPERATOR_ROLES}
            | {f'aws_iam_role_policy_attachment.operator["{k}"]' for k in OPERATOR_ROLES})


def check_plan(plan, stage, support_arn, oidc_host=None):
    """oidc_host: required for stage 2 (from stage 1 readback); ignored for stage 1."""
    validate_args(stage, support_arn, oidc_host if stage == 2 else None)
    if stage == 2 and oidc_host is None:
        raise InputError('stage 2 needs --oidc-host from stage 1 readback')
    r = Report()
    r.check('terraform_version', plan.get('terraform_version') == TF_VERSION,
            f"got {plan.get('terraform_version')}")
    r.check('plan not errored', plan.get('errored') is False, f"errored={plan.get('errored')}")

    changes = {}
    for rc in plan.get('resource_changes', []):
        if rc.get('mode') == 'data':
            continue
        changes[rc['address']] = rc

    create = account_addresses() if stage == 1 else operator_addresses()
    noop = set() if stage == 1 else account_addresses()
    actual = set(changes)
    r.check('resource set exact', actual == create | noop,
            f'unexpected={sorted(actual - create - noop)} missing={sorted((create | noop) - actual)}')
    for addr in sorted(actual):
        actions = changes[addr]['change']['actions']
        want = ['create'] if addr in create else ['no-op'] if addr in noop else None
        r.check(f'{addr} actions={actions}', actions == want, f'want {want}')

    after = {a: (c['change'].get('after') or {}) for a, c in changes.items()}
    unknown = {a: (c['change'].get('after_unknown') or {}) for a, c in changes.items()}

    if stage == 1:
        cfg = after.get('rhcs_rosa_oidc_config.managed', {})
        r.check('oidc config managed=true', cfg.get('managed') is True, f"managed={cfg.get('managed')}")
        prov = after.get('aws_iam_openid_connect_provider.rosa', {})
        url = prov.get('url')
        # URL is known after the rhcs config exists; at stage 1 plan time it is normally unknown.
        if url is None:
            r.check('oidc provider url unknown at plan (checked at readback)',
                    unknown.get('aws_iam_openid_connect_provider.rosa', {}).get('url') is True)
        else:
            r.check('oidc provider url host', url.startswith('https://' + OIDC_PREFIX), url)
        r.check('oidc provider client_id_list', sorted(prov.get('client_id_list') or []) == CLIENT_IDS,
                f"got {prov.get('client_id_list')}")

    exp = expected_roles(stage, support_arn, oidc_host)
    # Stage 2 also re-checks the no-op stage 1 roles and attachments as they are in state.
    role_addrs = [a for a in create | noop if a.startswith('aws_iam_role.')]
    by_name = {}
    for addr in sorted(role_addrs):
        a = after.get(addr, {})
        name = a.get('name')
        by_name[name] = addr
        r.check(f'{addr} name in approved table', name in exp, f'name={name}')
        if name not in exp:
            continue
        trust = a.get('assume_role_policy')
        if trust is None:
            r.check(f'{name} trust known at plan', False, 'assume_role_policy unknown')
            continue
        got = normalize_trust(trust)
        r.check(f'{name} trust == approved', got == exp[name][0],
                f'got {json.dumps(got, sort_keys=True)}')
        r.check(f'{name} no inline policy', not a.get('inline_policy'), f"inline={a.get('inline_policy')}")
        r.check(f'{name} no permissions boundary', not a.get('permissions_boundary'))
        r.check(f'{name} path /', a.get('path', '/') == '/', f"path={a.get('path')}")
    r.check('approved roles all planned', set(by_name) == set(exp),
            f'missing={sorted(set(exp) - set(by_name))}')

    got_att = {}
    for addr in sorted(a for a in create | noop if a.startswith('aws_iam_role_policy_attachment.')):
        a = after.get(addr, {})
        role = a.get('role')
        if role is None:
            # role name is a reference to a role created in the same plan; resolve via address.
            role_addr = addr.replace('aws_iam_role_policy_attachment.', 'aws_iam_role.')
            if addr.startswith('aws_iam_role_policy_attachment.account'):
                key = addr.split('["', 1)[1].split(':', 1)[0]
                role_addr = f'aws_iam_role.account["{key}"]'
            role = after.get(role_addr, {}).get('name')
        got_att.setdefault(role, []).append(a.get('policy_arn'))
    for name, (_, policies) in sorted(exp.items()):
        r.check(f'{name} attachments == approved', sorted(got_att.get(name, [])) == policies,
                f'got {sorted(got_att.get(name, []))}')
    r.check('no attachment to unapproved role', set(got_att) <= set(exp),
            f'extra={sorted(set(got_att) - set(exp))}')
    return r


# ---------------- readback ----------------

def aws(*args):
    proc = subprocess.run(['aws', *args, '--output', 'json'], capture_output=True, text=True)
    if proc.returncode != 0:
        raise Stop(f'aws {" ".join(args[:2])} rc={proc.returncode}: {proc.stderr.strip()[:300]}')
    return json.loads(proc.stdout or '{}')


def check_readback(stage, support_arn, oidc_host=None, call=aws):
    validate_args(stage, support_arn, oidc_host)
    r = Report()
    ident = call('sts', 'get-caller-identity')
    r.check('account', ident.get('Account') == ACCOUNT, f"got {ident.get('Account')}")

    arns = [p['Arn'] for p in call('iam', 'list-open-id-connect-providers').get('OpenIDConnectProviderList', [])]
    prefix = f'arn:aws:iam::{ACCOUNT}:oidc-provider/{OIDC_PREFIX}'
    rosa = [a for a in arns if a.startswith(prefix)]
    if oidc_host is None:
        r.check('exactly one oidc.op1 provider', len(rosa) == 1, f'found {len(rosa)}')
        if len(rosa) != 1:
            return r
        oidc_host = rosa[0].split(':oidc-provider/', 1)[1]
    provider_arn = f'arn:aws:iam::{ACCOUNT}:oidc-provider/{oidc_host}'
    r.check('oidc provider exists', provider_arn in arns, provider_arn)
    if provider_arn in arns:
        prov = call('iam', 'get-open-id-connect-provider', '--open-id-connect-provider-arn', provider_arn)
        r.check('oidc provider url', prov.get('Url') == oidc_host, f"got {prov.get('Url')}")
        r.check('oidc provider client ids', sorted(prov.get('ClientIDList', [])) == CLIENT_IDS,
                f"got {prov.get('ClientIDList')}")

    for name, (trust, policies) in sorted(expected_roles(stage, support_arn, oidc_host).items()):
        try:
            role = call('iam', 'get-role', '--role-name', name)['Role']
        except Stop as e:
            r.check(f'{name} exists', False, str(e))
            continue
        r.check(f'{name} trust == approved', normalize_trust(role['AssumeRolePolicyDocument']) == trust,
                f"got {json.dumps(normalize_trust(role['AssumeRolePolicyDocument']), sort_keys=True)}")
        r.check(f'{name} no permissions boundary', 'PermissionsBoundary' not in role)
        att = call('iam', 'list-attached-role-policies', '--role-name', name).get('AttachedPolicies', [])
        got = sorted(p['PolicyArn'] for p in att)
        r.check(f'{name} attachments == approved', got == policies, f'got {got}')
        inline = call('iam', 'list-role-policies', '--role-name', name).get('PolicyNames', [])
        r.check(f'{name} inline policies = 0', inline == [], f'got {inline}')
    print(f'oidc_host={oidc_host}')
    return r


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    for name in ('plan', 'readback'):
        p = sub.add_parser(name)
        p.add_argument('--stage', type=int, required=True, choices=(1, 2))
        p.add_argument('--support-principal', required=True,
                       help='value from ROSA CLI sts_support_trust_policy.json (do not commit)')
        p.add_argument('--oidc-host', help=f'{OIDC_PREFIX}<id>; stage 2 plan requires it')
        if name == 'plan':
            p.add_argument('plan_json', help='output of `terraform show -json <plan>`')
    args = ap.parse_args(argv)
    try:
        if args.cmd == 'plan':
            try:
                raw = Path(args.plan_json).read_bytes()
                plan = json.loads(raw)
            except (OSError, ValueError) as e:
                raise InputError(f'cannot read plan JSON: {e}')
            print(f'plan_json_sha256={hashlib.sha256(raw).hexdigest()}')
            report = check_plan(plan, args.stage, args.support_principal, args.oidc_host)
        else:
            report = check_readback(args.stage, args.support_principal, args.oidc_host)
    except InputError as e:
        print(f'INPUT ERROR: {mask(e)}', file=sys.stderr)
        return 2
    except (Stop, KeyError, ValueError) as e:
        print(f'STOP: {mask(e)}', file=sys.stderr)
        return 1
    return report.print(f'rosa-prereq {args.cmd} stage {args.stage}')


if __name__ == '__main__':
    sys.exit(main())
