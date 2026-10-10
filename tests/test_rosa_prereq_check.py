"""Offline only: no AWS/Terraform process or credentials required."""
import importlib.util
import json
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location('rpc', Path(__file__).parents[1] / 'tools/rosa_prereq_check.py')
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)

SUPPORT = 'arn:aws:iam::710019948333:role/RH-Technical-Support-12345678'
HOST = 'oidc.op1.openshiftapps.com/abc123def456'
PROVIDER = f'arn:aws:iam::{m.ACCOUNT}:oidc-provider/{HOST}'


def account_trust(key):
    ptype, ident = {'installer': ('AWS', [m.INSTALLER]), 'support': ('AWS', [SUPPORT]),
                    'worker': ('Service', ['ec2.amazonaws.com'])}[key]
    return json.dumps({'Version': '2012-10-17', 'Statement': [
        {'Effect': 'Allow', 'Action': 'sts:AssumeRole', 'Principal': {ptype: ident}}]})


def operator_trust(key):
    ns, _, sas, _ = m.OPERATOR_ROLES[key]
    return json.dumps({'Version': '2012-10-17', 'Statement': [{
        'Effect': 'Allow', 'Action': 'sts:AssumeRoleWithWebIdentity',
        'Principal': {'Federated': PROVIDER},
        'Condition': {'StringEquals': {f'{HOST}:sub': [f'system:serviceaccount:{ns}:{sa}' for sa in sas]}}}]})


# Provider-computed role fields are unknown on create (after: absent, after_unknown: true).
COMPUTED_ROLE_UNKNOWN = {'inline_policy': True, 'managed_policy_arns': True}


def role_after(name, trust):
    return {'name': name, 'assume_role_policy': trust, 'path': '/', 'permissions_boundary': None}


# Mirrors terraform/rosa-prereq/main.tf: no inline_policy / managed_policy_arns / boundary configured.
CONFIGURATION = {'root_module': {'resources': [
    {'address': 'aws_iam_role.account', 'expressions': {'name': {}, 'assume_role_policy': {}, 'tags': {}}},
    {'address': 'aws_iam_role_policy_attachment.account', 'expressions': {'role': {}, 'policy_arn': {}}},
    {'address': 'rhcs_rosa_oidc_config.managed', 'expressions': {'managed': {}}},
    {'address': 'aws_iam_openid_connect_provider.rosa',
     'expressions': {'url': {}, 'client_id_list': {}, 'thumbprint_list': {}}},
    {'address': 'aws_iam_role.operator', 'expressions': {'name': {}, 'assume_role_policy': {}, 'tags': {}}},
    {'address': 'aws_iam_role_policy_attachment.operator', 'expressions': {'role': {}, 'policy_arn': {}}},
]}}


def rc(addr, actions, after, unknown=None):
    return {'address': addr, 'mode': 'managed',
            'change': {'actions': actions, 'after': after, 'after_unknown': unknown or {}}}


def account_changes(action):
    out = []
    for k, (name, _, _, policies) in m.ACCOUNT_ROLES.items():
        if action == 'create':
            out.append(rc(f'aws_iam_role.account["{k}"]', [action], role_after(name, account_trust(k)),
                          COMPUTED_ROLE_UNKNOWN))
        else:
            out.append(rc(f'aws_iam_role.account["{k}"]', [action],
                          dict(role_after(name, account_trust(k)), inline_policy=[],
                               managed_policy_arns=[f'{m.AWS_POLICY}/{p}' for p in policies])))
        for p in policies:
            out.append(rc(f'aws_iam_role_policy_attachment.account["{k}:{p.rsplit("/", 1)[-1]}"]', [action],
                          {'role': name, 'policy_arn': f'{m.AWS_POLICY}/{p}'}))
    out.append(rc('rhcs_rosa_oidc_config.managed', [action], {'managed': True}))
    prov = {'client_id_list': ['openshift', 'sts.amazonaws.com']}
    if action == 'no-op':
        prov['url'] = 'https://' + HOST
    out.append(rc('aws_iam_openid_connect_provider.rosa', [action], prov,
                  {'url': True} if action == 'create' else {}))
    return out


def operator_changes():
    out = []
    for k, (ns, name, _, policy) in m.OPERATOR_ROLES.items():
        role = m.operator_role_name(ns, name)
        out.append(rc(f'aws_iam_role.operator["{k}"]', ['create'], role_after(role, operator_trust(k)),
                      COMPUTED_ROLE_UNKNOWN))
        out.append(rc(f'aws_iam_role_policy_attachment.operator["{k}"]', ['create'],
                      {'role': role, 'policy_arn': f'{m.AWS_POLICY}/service-role/{policy}'}))
    return out


def plan(stage):
    changes = account_changes('create') if stage == 1 else account_changes('no-op') + operator_changes()
    return {'format_version': '1.2', 'terraform_version': m.TF_VERSION, 'errored': False,
            'resource_changes': changes, 'configuration': json.loads(json.dumps(CONFIGURATION))}


def find(p, addr):
    return next(c for c in p['resource_changes'] if c['address'] == addr)


class Plan(unittest.TestCase):
    def stops(self, p, stage=1):
        return m.check_plan(p, stage, SUPPORT, HOST if stage == 2 else None).stops()

    def test_stage1_pass(self):
        self.assertEqual(self.stops(plan(1)), [])

    def test_stage2_pass(self):
        self.assertEqual(self.stops(plan(2), 2), [])

    def test_extra_trust_principal_stops(self):
        p = plan(1)
        c = find(p, 'aws_iam_role.account["support"]')
        doc = json.loads(c['change']['after']['assume_role_policy'])
        doc['Statement'][0]['Principal']['AWS'].append('arn:aws:iam::111111111111:root')
        c['change']['after']['assume_role_policy'] = json.dumps(doc)
        self.assertTrue(self.stops(p))

    def test_extra_statement_stops(self):
        p = plan(1)
        c = find(p, 'aws_iam_role.account["worker"]')
        doc = json.loads(c['change']['after']['assume_role_policy'])
        doc['Statement'].append(dict(doc['Statement'][0], Principal={'AWS': ['*']}))
        c['change']['after']['assume_role_policy'] = json.dumps(doc)
        self.assertTrue(self.stops(p))

    def test_wrong_operator_condition_stops(self):
        p = plan(2)
        c = find(p, 'aws_iam_role.operator["kms_provider"]')
        c['change']['after']['assume_role_policy'] = c['change']['after']['assume_role_policy'].replace(
            'StringEquals', 'StringLike')
        self.assertTrue(self.stops(p, 2))

    def test_admin_policy_attachment_stops(self):
        p = plan(1)
        find(p, 'aws_iam_role_policy_attachment.account["worker:AmazonEC2ContainerRegistryReadOnly"]')[
            'change']['after']['policy_arn'] = 'arn:aws:iam::aws:policy/AdministratorAccess'
        self.assertTrue(self.stops(p))

    def test_unexpected_resource_stops(self):
        p = plan(1)
        p['resource_changes'].append(rc('aws_iam_user.x', ['create'], {'name': 'x'}))
        self.assertTrue(self.stops(p))

    def test_update_or_delete_stops(self):
        for actions in (['update'], ['delete'], ['delete', 'create']):
            p = plan(2)
            find(p, 'aws_iam_role.account["installer"]')['change']['actions'] = actions
            self.assertTrue(self.stops(p, 2), actions)

    def test_inline_policy_stops(self):
        p = plan(1)
        find(p, 'aws_iam_role.account["installer"]')['change']['after']['inline_policy'] = [
            {'name': 'x', 'policy': '{}'}]
        self.assertTrue(self.stops(p))

    def test_unknown_trust_stops(self):
        p = plan(2)
        find(p, 'aws_iam_role.operator["ingress"]')['change']['after']['assume_role_policy'] = None
        self.assertTrue(self.stops(p, 2))

    def test_normal_plan_labels_deferred_fields(self):
        rows = m.check_plan(plan(1), 1, SUPPORT).rows
        deferred = [item for ok, item, _ in rows if item.startswith('DEFERRED')]
        self.assertTrue(all(ok for ok, item, _ in rows if item.startswith('DEFERRED')))
        self.assertEqual(len(deferred), 3 * 2 + 1)  # 3 roles x (inline, managed) + OIDC url

    # --- PR21 review B2 counterexamples ---
    def test_unknown_attachment_role_stops(self):
        p = plan(1)
        c = find(p, 'aws_iam_role_policy_attachment.account["worker:AmazonEC2ContainerRegistryReadOnly"]')
        del c['change']['after']['role']
        c['change']['after_unknown'] = {'role': True}
        self.assertTrue(self.stops(p))

    def test_unknown_attachment_policy_stops(self):
        p = plan(2)
        c = find(p, 'aws_iam_role_policy_attachment.operator["ingress"]')
        del c['change']['after']['policy_arn']
        c['change']['after_unknown'] = {'policy_arn': True}
        self.assertTrue(self.stops(p, 2))

    def test_unknown_inline_policy_when_configured_stops(self):
        p = plan(1)
        p['configuration']['root_module']['resources'][0]['expressions']['inline_policy'] = [{}]
        self.assertTrue(self.stops(p))

    def test_unknown_computed_field_without_configuration_stops(self):
        p = plan(1)
        del p['configuration']
        self.assertTrue(self.stops(p))

    def test_unknown_permissions_boundary_stops(self):
        p = plan(1)
        c = find(p, 'aws_iam_role.account["installer"]')
        del c['change']['after']['permissions_boundary']
        c['change']['after_unknown'] = dict(c['change']['after_unknown'], permissions_boundary=True)
        self.assertTrue(self.stops(p))

    def test_known_managed_policy_arns_extra_stops(self):
        p = plan(2)
        c = find(p, 'aws_iam_role.account["worker"]')
        c['change']['after']['managed_policy_arns'].append('arn:aws:iam::aws:policy/AdministratorAccess')
        self.assertTrue(self.stops(p, 2))

    def test_stage2_changed_oidc_client_ids_stops(self):
        p = plan(2)
        find(p, 'aws_iam_openid_connect_provider.rosa')['change']['after']['client_id_list'] = ['openshift', 'x']
        self.assertTrue(self.stops(p, 2))

    def test_stage2_oidc_url_mismatch_stops(self):
        p = plan(2)
        find(p, 'aws_iam_openid_connect_provider.rosa')['change']['after']['url'] = (
            'https://oidc.op1.openshiftapps.com/other000')
        self.assertTrue(self.stops(p, 2))

    def test_stage2_oidc_not_managed_stops(self):
        p = plan(2)
        find(p, 'rhcs_rosa_oidc_config.managed')['change']['after']['managed'] = False
        self.assertTrue(self.stops(p, 2))

    def test_terraform_version_stops(self):
        p = plan(1)
        p['terraform_version'] = '1.15.0'
        self.assertTrue(self.stops(p))

    def test_bad_inputs(self):
        with self.assertRaises(m.InputError):
            m.check_plan(plan(1), 1, 'arn:aws:iam::1:root')
        with self.assertRaises(m.InputError):
            m.check_plan(plan(2), 2, SUPPORT)
        with self.assertRaises(m.InputError):
            m.check_plan(plan(2), 2, SUPPORT, 'evil.example.com/abc')

    def test_output_masks_org_id(self):
        p = plan(1)
        find(p, 'aws_iam_role.account["support"]')['change']['after']['assume_role_policy'] = '{"Statement":[]}'
        r = m.check_plan(p, 1, SUPPORT)
        self.assertNotIn('12345678', json.dumps(r.rows))


class FakeAws:
    def __init__(self, stage):
        self.roles = {}
        for name, (trust, policies) in m.expected_roles(stage, SUPPORT, HOST).items():
            doc = {'Version': '2012-10-17', 'Statement': [
                {k: v for k, v in st.items() if k != 'extra' and v} for st in trust]}
            # IAM returns single values as strings.
            for st in doc['Statement']:
                st['Action'] = st['Action'][0]
                st['Principal'] = {k: v[0] if len(v) == 1 else v for k, v in st['Principal'].items()}
            self.roles[name] = {'doc': doc, 'att': list(policies), 'inline': []}
        self.providers = [PROVIDER]

    def __call__(self, *args):
        if args[:2] == ('sts', 'get-caller-identity'):
            return {'Account': m.ACCOUNT}
        if args[1] == 'list-open-id-connect-providers':
            return {'OpenIDConnectProviderList': [{'Arn': a} for a in self.providers]}
        if args[1] == 'get-open-id-connect-provider':
            return {'Url': HOST, 'ClientIDList': ['sts.amazonaws.com', 'openshift']}
        role = self.roles.get(args[-1])
        if role is None:
            raise m.Stop('NoSuchEntity')
        if args[1] == 'get-role':
            return {'Role': {'RoleName': args[-1], 'AssumeRolePolicyDocument': role['doc']}}
        if args[1] == 'list-attached-role-policies':
            return {'AttachedPolicies': [{'PolicyArn': a} for a in role['att']]}
        if args[1] == 'list-role-policies':
            return {'PolicyNames': role['inline']}
        raise AssertionError(args)


class Readback(unittest.TestCase):
    def test_stage1_and_stage2_pass(self):
        for stage in (1, 2):
            self.assertEqual(m.check_readback(stage, SUPPORT, call=FakeAws(stage)).stops(), [], stage)

    def test_missing_role_stops(self):
        fake = FakeAws(2)
        del fake.roles['fds-rosa-kube-system-kms-provider']
        self.assertTrue(m.check_readback(2, SUPPORT, call=fake).stops())

    def test_extra_attachment_and_inline_stop(self):
        fake = FakeAws(1)
        fake.roles['fds-rosa-HCP-ROSA-Worker-Role']['att'].append('arn:aws:iam::aws:policy/AdministratorAccess')
        fake.roles['fds-rosa-HCP-ROSA-Installer-Role']['inline'] = ['x']
        self.assertEqual(len(m.check_readback(1, SUPPORT, call=fake).stops()), 2)

    def test_changed_trust_stops(self):
        fake = FakeAws(1)
        fake.roles['fds-rosa-HCP-ROSA-Support-Role']['doc']['Statement'][0]['Principal']['AWS'] = '*'
        self.assertTrue(m.check_readback(1, SUPPORT, call=fake).stops())

    def test_two_rosa_providers_stop(self):
        fake = FakeAws(1)
        fake.providers.append(PROVIDER + 'x')
        self.assertTrue(m.check_readback(1, SUPPORT, call=fake).stops())


if __name__ == '__main__':
    unittest.main()
