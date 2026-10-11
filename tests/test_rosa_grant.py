"""Offline only: no AWS process or credentials required. POSIX only, like the runner itself."""
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout

SPEC = importlib.util.spec_from_file_location('rg', Path(__file__).parents[1] / 'tools/rosa_grant.py')
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)

CALLER = 'arn:aws:sts::774055931866:assumed-role/Central/approved'
SRC = m.load_sources()
WRITES = {'create-policy', 'create-policy-version', 'attach-role-policy', 'detach-role-policy',
          'delete-policy', 'set-default-policy-version'}


class FakeIam:
    """Minimal IAM state machine for the calls the runner makes."""

    def __init__(self):
        self.caller = {'Account': m.ACCOUNT, 'Arn': CALLER}
        self.inline = []
        self.policies = {}  # name -> {'id', 'default', 'docs', 'roles', 'users', 'groups'}
        self.attached = set()
        self.n = 0
        for n in ('FDS-IaC-Guardrails', 'FDS-IaC-State-PassRole', 'FDS-IaC-Network', 'FDS-IaC-Vpn'):
            self._create(n, SRC['v1'][1] if n == 'FDS-IaC-Guardrails' else {'Statement': []})
            self._attach(m.arn(n))
        self.writes = []
        self.fail_write = None
        self.lag = 0  # readbacks that still show the old state

    def _create(self, name, doc):
        self.n += 1
        self.policies[name] = {'id': f'ANPA{self.n:04d}', 'default': 'v1', 'docs': {'v1': doc},
                               'roles': [], 'users': [], 'groups': []}

    def _attach(self, a):
        self.attached.add(a)
        self.policies[a.rsplit('/', 1)[1]]['roles'] = [m.ROLE]

    def __call__(self, *args):
        op = args[1]
        opt = dict(zip(args[2::2], args[3::2]))
        name = opt.get('--policy-arn', '').rsplit('/', 1)[-1] or opt.get('--policy-name')
        ok = lambda body=None: (0, json.dumps(body or {}), '')
        if op in WRITES:
            self.writes.append(args)
            if self.fail_write == op:
                return 254, '', 'AccessDenied'
        if op == 'get-caller-identity':
            return ok(self.caller)
        if op == 'list-attached-role-policies':
            return ok({'AttachedPolicies': [{'PolicyArn': a} for a in sorted(self.attached)]})
        if op == 'list-role-policies':
            return ok({'PolicyNames': self.inline})
        p = self.policies.get(name)
        if op in ('get-policy', 'list-policy-versions', 'get-policy-version', 'list-entities-for-policy',
                  'delete-policy', 'attach-role-policy', 'detach-role-policy',
                  'create-policy-version', 'set-default-policy-version') and p is None:
            return 254, '', f'An error occurred (NoSuchEntity): {name}'
        if op == 'get-policy':
            return ok({'Policy': {'PolicyId': p['id'], 'DefaultVersionId': p['default']}})
        if op == 'list-policy-versions':
            return ok({'Versions': [{'VersionId': v} for v in p['docs']]})
        if op == 'get-policy-version':
            return ok({'PolicyVersion': {'Document': p['docs'][opt['--version-id']]}})
        if op == 'list-entities-for-policy':
            return ok({'PolicyRoles': [{'RoleName': r} for r in p['roles']],
                       'PolicyUsers': p['users'], 'PolicyGroups': p['groups']})
        doc = lambda: json.loads(Path(opt['--policy-document'][len('file://'):]).read_text())
        if op == 'create-policy':
            self._create(name, doc())
            return ok({'Policy': {'PolicyId': self.policies[name]['id'], 'Arn': m.arn(name)}})
        elif op == 'create-policy-version':
            v = f'v{len(p["docs"]) + 1}'
            p['docs'][v] = doc()
            p['default'] = v
            return ok({'PolicyVersion': {'VersionId': v, 'IsDefaultVersion': True}})
        elif op == 'set-default-policy-version':
            p['default'] = opt['--version-id']
        elif op == 'attach-role-policy':
            self._attach(opt['--policy-arn'])
        elif op == 'detach-role-policy':
            self.attached.discard(opt['--policy-arn'])
            p['roles'] = []
        elif op == 'delete-policy':
            del self.policies[name]
        else:
            raise AssertionError(args)
        return ok()


class Lagging(m.Aws):
    """First N readbacks after a write return the pre-write snapshot (eventual consistency)."""

    def __init__(self, fake, lag):
        super().__init__(fake)
        self.lag, self.snapshot = lag, None

    def state(self):
        if self.snapshot is None or not self.call.writes:
            self.snapshot = super().state()
            return self.snapshot
        if self.lag:
            self.lag -= 1
            return self.snapshot
        return super().state()


class ReadErrorsAfterWrite(m.Aws):
    """After the first write, the next N state reads fail (denied / corrupt JSON / timeout)."""

    def __init__(self, fake, n, kind='denied'):
        super().__init__(fake)
        self.n, self.kind, self.base = n, kind, len(fake.writes)

    def state(self):
        if len(self.call.writes) > self.base and self.n:
            self.n -= 1
            if self.kind == 'denied':
                raise m.Stop('read failed: aws iam get-policy rc=254 AccessDenied')
            if self.kind == 'corrupt':
                raise ValueError('Expecting value: line 1 column 1 (char 0)')
            raise m.subprocess.TimeoutExpired(['aws'], 120)
        return super().state()


class StaleView(m.Aws):
    """IAM reads keep returning a fixed earlier snapshot for N calls (eventual consistency), then live."""

    def __init__(self, fake, snapshot, n):
        super().__init__(fake)
        self.snapshot, self.n = snapshot, n

    def state(self):
        if self.n:
            self.n -= 1
            return self.snapshot
        return super().state()


EVIDENCE = 'CloudTrail eventID 00000000-0000-0000-0000-000000000000 errorCode=AccessDenied'


def raising_call(fake, apply_first):
    def call(*args):
        if args[1] in WRITES:
            if apply_first:
                fake(*args)
            else:
                fake.writes.append(args)
            raise m.subprocess.TimeoutExpired(['aws', *args], 120)
        return fake(*args)
    return call


@unittest.skipUnless(os.name == 'posix', 'runner is POSIX only (Linux / CloudShell)')
class Runner(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ledger = Path(self.tmp.name) / 'ledger'
        self.fake = FakeIam()

    def tearDown(self):
        self.tmp.cleanup()

    def run_step(self, step, execute=True, aws=None, caller=CALLER, run_id=None, evidence=None, reviewer=None):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = m.run(step, caller, self.ledger, execute, aws=aws or m.Aws(self.fake), sleep=lambda s: None,
                       run_id=run_id, evidence=evidence, reviewer=reviewer)
        self.out = buf.getvalue()
        return rc

    def full_forward(self):
        for step in ('guardrails-v2', 'subscribe-create', 'subscribe-attach', 'subscribe-detach',
                     'prereq-create', 'prereq-attach'):
            self.assertEqual(self.run_step(step), 0, (step, self.out))

    def ledger_entries(self):
        return [json.loads(x) for x in (self.ledger / m.LEDGER_NAME).read_text(encoding='utf-8').splitlines()]

    def runs(self):
        return m.runs_of(self.ledger_entries())

    def only_unresolved(self):
        bad = m.unresolved(self.ledger_entries())
        self.assertEqual(len(bad), 1, bad)
        return bad[0][0]

    def test_full_forward_then_rollback(self):
        self.full_forward()
        self.assertEqual(self.fake.attached - m.BASE_ATTACHED, {m.arn('FDS-IaC-RosaPrereq')})
        self.assertEqual(self.fake.policies['FDS-IaC-Guardrails']['docs']['v2'], SRC['v2'][1])
        for step in ('prereq-detach', 'prereq-delete', 'subscribe-delete', 'guardrails-v1'):
            self.assertEqual(self.run_step(step), 0, (step, self.out))
        self.assertEqual(self.fake.attached, m.BASE_ATTACHED)
        self.assertNotIn('FDS-IaC-RosaPrereq', self.fake.policies)
        self.assertEqual(self.fake.policies['FDS-IaC-Guardrails']['default'], 'v1')
        runs = self.runs()
        self.assertEqual(len(runs), 10)
        for entries in runs.values():
            self.assertEqual([e['phase'] for e in entries], ['INTENT', 'WRITE_RETURNED', 'READBACK'])
            self.assertEqual(entries[1]['rc'], 0)
            self.assertTrue(entries[2]['verified'])
        self.assertEqual(m.unresolved(self.ledger_entries()), [])
        self.assertEqual(m.file_mode(self.ledger), 0o700)
        self.assertEqual(m.file_mode(self.ledger / m.LEDGER_NAME), 0o600)
        self.assertFalse((self.ledger / m.LOCK_NAME).exists())

    def test_dry_run_never_writes(self):
        self.assertEqual(self.run_step('guardrails-v2', execute=False), 0)
        self.assertIn('PLAN  aws iam create-policy-version', self.out)
        self.assertEqual(self.fake.writes, [])
        self.assertFalse((self.ledger / m.LEDGER_NAME).exists())

    def test_one_write_per_run(self):
        self.run_step('guardrails-v2')
        self.assertEqual(len(self.fake.writes), 1)

    def test_wrong_caller_stops_before_write(self):
        with self.assertRaises(m.Stop):
            self.run_step('guardrails-v2', caller='arn:aws:sts::774055931866:assumed-role/Other/x')
        self.assertEqual(self.fake.writes, [])

    def test_order_enforced(self):
        self.assertEqual(self.run_step('subscribe-create'), 1)  # Guardrails still v1
        self.run_step('guardrails-v2')
        self.assertEqual(self.run_step('prereq-attach'), 1)  # not created yet
        self.assertEqual(self.run_step('guardrails-v1'), 0)
        self.assertEqual(self.fake.writes[-1][1], 'set-default-policy-version')
        self.assertEqual(len(self.fake.writes), 2)

    def test_existing_policy_is_not_adopted(self):
        self.run_step('guardrails-v2')
        self.fake._create('FDS-IaC-RosaPrereq', SRC['prereq'][1])
        self.assertEqual(self.run_step('prereq-create'), 1)
        self.assertIn('already exists', self.out)
        # same name, but not created by this ledger: attach/delete refused
        self.assertEqual(self.run_step('prereq-attach'), 1)
        self.assertEqual(self.run_step('prereq-delete'), 1)
        self.assertIn('not recorded as created by this ledger', self.out)

    def test_live_guardrails_drift_stops(self):
        self.fake.policies['FDS-IaC-Guardrails']['docs']['v1'] = {'Statement': []}
        self.assertEqual(self.run_step('guardrails-v2'), 1)
        self.assertIn('Guardrails default version is not v1', self.out)

    def test_guardrails_shared_with_other_principal_stops(self):
        self.fake.policies['FDS-IaC-Guardrails']['users'] = [{'UserName': 'someone'}]
        self.assertEqual(self.run_step('guardrails-v2'), 1)

    def test_version_limit_stops(self):
        g = self.fake.policies['FDS-IaC-Guardrails']
        for i in range(2, 6):
            g['docs'][f'v{i}'] = {'Statement': [], 'n': i}
        self.assertEqual(self.run_step('guardrails-v2'), 1)
        self.assertIn('versions', self.out)

    def test_unexpected_role_policy_or_inline_stops(self):
        self.fake._create('AdminLike', {'Statement': []})
        self.fake._attach(m.arn('AdminLike'))
        self.assertEqual(self.run_step('guardrails-v2'), 1)
        self.fake.attached.discard(m.arn('AdminLike'))
        self.fake.inline = ['FDS-Grant-Quarantine-20261009']
        self.assertEqual(self.run_step('guardrails-v2'), 1)
        self.assertEqual(self.fake.writes, [])

    def test_write_failure_recorded_and_stops(self):
        self.fake.fail_write = 'create-policy-version'
        self.assertEqual(self.run_step('guardrails-v2'), 1)
        returned, readback = self.ledger_entries()[1:]
        self.assertEqual((returned['rc'], readback['verified']), (254, False))
        # a failed write is still unresolved until compared with live state
        rid = self.only_unresolved()
        self.fake.fail_write = None
        self.assertEqual(self.run_step('guardrails-v2'), 1)
        self.assertIn('unresolved run', self.out)
        # B3: reconcile never decides "not applied" by itself; a person closes it with evidence
        self.assertEqual(self.run_step('reconcile', run_id=rid), 1)
        self.assertIn('outcome=AMBIGUOUS', self.out)
        self.assertEqual(self.only_unresolved(), rid)
        self.assertEqual(self.run_step('confirm-not-applied', run_id=rid, evidence=EVIDENCE, reviewer='GWONUK'), 0,
                         self.out)
        last = self.ledger_entries()[-1]
        self.assertEqual((last['outcome'], last['evidence'], last['reviewer']),
                         ('NOT_APPLIED_CONFIRMED', EVIDENCE, 'GWONUK'))
        self.assertEqual(self.run_step('guardrails-v2'), 0, self.out)

    def test_eventual_consistency_retries_readback(self):
        self.assertEqual(self.run_step('guardrails-v2', aws=Lagging(self.fake, 3)), 0, self.out)

    def test_readback_never_converges_stops(self):
        self.assertEqual(self.run_step('guardrails-v2', aws=Lagging(self.fake, 99)), 1)
        self.assertFalse(self.ledger_entries()[-1]['verified'])
        self.only_unresolved()

    # --- PR21 review B1: write succeeded, readback raised ---
    def test_create_then_read_denied(self):
        self.check_create_then_read_error('denied')

    def test_create_then_read_corrupt_json(self):
        self.check_create_then_read_error('corrupt')

    def test_create_then_read_timeout(self):
        self.check_create_then_read_error('timeout')

    def check_create_then_read_error(self, kind):
        self.run_step('guardrails-v2')
        self.assertEqual(self.run_step('subscribe-create', aws=ReadErrorsAfterWrite(self.fake, 99, kind)), 1)
        created = self.fake.policies['FDS-RosaBootstrap-Subscribe']['id']
        rid = self.only_unresolved()
        returned = self.runs()[rid][1]
        self.assertEqual(returned['phase'], 'WRITE_RETURNED')
        self.assertEqual(returned['response_ids']['PolicyId'], created)
        self.assertIn('readback failed', self.ledger_entries()[-1]['post_failures'][0])
        # no new write, not even rollback, until reconciled
        n = len(self.fake.writes)
        self.assertEqual(self.run_step('subscribe-attach'), 1)
        self.assertEqual(self.run_step('subscribe-delete'), 1)
        self.assertEqual(len(self.fake.writes), n)
        # reconcile: dry-run does not touch the ledger, --execute records APPLIED with the same id
        before = len(self.ledger_entries())
        self.assertEqual(self.run_step('reconcile', execute=False, run_id=rid), 0)
        self.assertEqual(len(self.ledger_entries()), before)
        self.assertEqual(self.run_step('reconcile', run_id=rid), 0, self.out)
        last = self.ledger_entries()[-1]
        self.assertEqual((last['outcome'], last['ids']['policy_id']), ('APPLIED', created))
        # the reviewer's case: subscribe-delete can now find its own PolicyId
        self.assertEqual(self.run_step('subscribe-delete'), 0, self.out)

    def test_transient_read_error_then_recovers(self):
        self.run_step('guardrails-v2')
        self.assertEqual(self.run_step('subscribe-create', aws=ReadErrorsAfterWrite(self.fake, 2)), 0, self.out)
        self.assertEqual(m.unresolved(self.ledger_entries()), [])

    def test_write_call_raises_outcome_unknown(self):
        self.run_step('guardrails-v2')
        # reconcile never closes an outcome-unknown create by itself: not applied -> AMBIGUOUS (B3),
        # applied without a response PolicyId -> AMBIGUOUS (B1).
        for apply_first in (False, True):
            with self.subTest(apply_first=apply_first):
                with self.assertRaises(m.Stop):
                    self.run_step('subscribe-create', aws=m.Aws(raising_call(self.fake, apply_first)))
                rid = self.only_unresolved()
                self.assertEqual([e['phase'] for e in self.runs()[rid]], ['INTENT', 'OUTCOME_UNKNOWN'])
                self.assertFalse((self.ledger / m.LOCK_NAME).exists())
                self.assertEqual(self.run_step('reconcile', run_id=rid), 1, self.out)
                self.assertIn('outcome=AMBIGUOUS', self.out)
                if not apply_first:  # really not applied: a reviewer closes it with evidence
                    self.assertEqual(self.run_step('confirm-not-applied', run_id=rid, evidence=EVIDENCE,
                                                   reviewer='GWONUK'), 0, self.out)
        self.assertIn('missing durable create PolicyId/Arn', self.out)
        # applied: live shows the policy, so it cannot be confirmed as not applied either
        self.assertEqual(self.run_step('confirm-not-applied', run_id=rid, evidence=EVIDENCE, reviewer='GWONUK'), 1)
        self.assertIn('already shows the postcondition', self.out)
        self.assertEqual(self.only_unresolved(), rid)
        n = len(self.fake.writes)
        self.assertEqual(self.run_step('subscribe-delete'), 1)
        self.assertEqual(len(self.fake.writes), n)

    # --- PR24 review B1: live object must be the one this run's write returned ---
    def test_outcome_unknown_then_foreign_same_policy_not_adopted(self):
        self.run_step('guardrails-v2')
        with self.assertRaises(m.Stop):  # timeout before the server applied the create
            self.run_step('subscribe-create', aws=m.Aws(raising_call(self.fake, apply_first=False)))
        rid = self.only_unresolved()
        self.fake._create('FDS-RosaBootstrap-Subscribe', SRC['subscribe'][1])  # someone else, same name+doc
        foreign = self.fake.policies['FDS-RosaBootstrap-Subscribe']['id']
        self.assertEqual(self.run_step('reconcile', run_id=rid), 1)
        self.assertIn('outcome=AMBIGUOUS', self.out)
        self.assertEqual(self.only_unresolved(), rid)
        n = len(self.fake.writes)
        self.assertEqual(self.run_step('subscribe-delete'), 1)
        self.assertEqual(len(self.fake.writes), n)
        self.assertEqual(self.fake.policies['FDS-RosaBootstrap-Subscribe']['id'], foreign)

    def test_policy_replaced_between_create_and_readback(self):
        self.run_step('guardrails-v2')
        fake = self.fake

        class ReplaceAfterCreate(m.Aws):
            done = False

            def state(self):
                if not self.done and fake.writes and fake.writes[-1][1] == 'create-policy':
                    self.done = True
                    del fake.policies['FDS-RosaBootstrap-Subscribe']
                    fake._create('FDS-RosaBootstrap-Subscribe', SRC['subscribe'][1])
                return super().state()

        self.assertEqual(self.run_step('subscribe-create', aws=ReplaceAfterCreate(fake)), 1)
        returned = self.runs()[self.only_unresolved()][1]['response_ids']['PolicyId']
        live = fake.policies['FDS-RosaBootstrap-Subscribe']['id']
        self.assertNotEqual(returned, live)
        last = self.ledger_entries()[-1]
        self.assertEqual((last['phase'], last['verified'], last['ids']), ('READBACK', False, {}))
        self.assertIn('differs from create response', last['post_failures'][0])
        rid = self.only_unresolved()
        self.assertEqual(self.run_step('reconcile', run_id=rid), 1)
        self.assertIn('outcome=AMBIGUOUS', self.out)
        n = len(fake.writes)
        self.assertEqual(self.run_step('subscribe-delete'), 1)
        self.assertEqual(len(fake.writes), n)
        self.assertEqual(fake.policies['FDS-RosaBootstrap-Subscribe']['id'], live)

    def test_guardrails_version_bound_to_returned_version_id(self):
        fake = self.fake

        class OtherVersionBecomesDefault(m.Aws):
            done = False

            def state(self):
                if not self.done and fake.writes:
                    self.done = True
                    g = fake.policies['FDS-IaC-Guardrails']
                    g['docs']['v3'] = SRC['v2'][1]  # same document, different version made the default
                    g['default'] = 'v3'
                return super().state()

        self.assertEqual(self.run_step('guardrails-v2', aws=OtherVersionBecomesDefault(fake)), 1)
        self.assertIn('differs from VersionId v2', self.ledger_entries()[-1]['post_failures'][0])
        rid = self.only_unresolved()
        self.assertEqual(self.run_step('reconcile', run_id=rid), 1)
        self.assertIn('outcome=AMBIGUOUS', self.out)

    def test_guardrails_outcome_unknown_not_adopted(self):
        with self.assertRaises(m.Stop):
            self.run_step('guardrails-v2', aws=m.Aws(raising_call(self.fake, apply_first=True)))
        rid = self.only_unresolved()
        self.assertEqual(self.run_step('reconcile', run_id=rid), 1)
        self.assertIn('missing durable create-policy-version VersionId', self.out)

    # --- PR24 review B3: a stale read is not proof that a write was not applied ---
    def test_stale_read_after_success_response_stays_unresolved(self):
        before = m.Aws(self.fake).state()  # pre-write view that reads keep returning
        self.assertEqual(self.run_step('guardrails-v2', aws=StaleView(self.fake, before, 99)), 1)
        self.assertEqual(self.fake.policies['FDS-IaC-Guardrails']['default'], 'v2')  # really applied
        rid = self.only_unresolved()
        n_reconciled = sum(e['phase'] == 'RECONCILED' for e in self.ledger_entries())
        self.assertEqual(self.run_step('reconcile', run_id=rid, aws=StaleView(self.fake, before, 99)), 1)
        self.assertIn('outcome=AMBIGUOUS', self.out)
        self.assertIn('not proof of "not applied"', self.out)
        self.assertEqual(sum(e['phase'] == 'RECONCILED' for e in self.ledger_entries()), n_reconciled)
        self.assertEqual(self.only_unresolved(), rid)
        # a success response can never be confirmed as not applied, and nothing is rewritten
        with self.assertRaises(m.InputError):
            self.run_step('confirm-not-applied', run_id=rid, evidence=EVIDENCE, reviewer='GWONUK',
                          aws=StaleView(self.fake, before, 99))
        self.assertEqual(self.run_step('guardrails-v2', aws=StaleView(self.fake, before, 99)), 1)
        self.assertEqual(len(self.fake.writes), 1)
        # once reads converge, the returned VersionId binds and the run is APPLIED
        self.assertEqual(self.run_step('reconcile', run_id=rid), 0, self.out)
        self.assertEqual(self.ledger_entries()[-1]['outcome'], 'APPLIED')

    def test_stale_read_after_outcome_unknown_stays_unresolved(self):
        before = m.Aws(self.fake).state()
        with self.assertRaises(m.Stop):  # timeout, but the server applied the new default version
            self.run_step('guardrails-v2', aws=m.Aws(raising_call(self.fake, apply_first=True)))
        rid = self.only_unresolved()
        self.assertEqual(self.run_step('reconcile', run_id=rid, aws=StaleView(self.fake, before, 99)), 1)
        self.assertIn('outcome=AMBIGUOUS', self.out)
        self.assertEqual(self.only_unresolved(), rid)
        # with the real (converged) view a person cannot record "not applied" either
        self.assertEqual(self.run_step('confirm-not-applied', run_id=rid, evidence=EVIDENCE, reviewer='GWONUK'), 1)
        self.assertEqual(self.only_unresolved(), rid)
        self.assertEqual(self.run_step('guardrails-v2'), 1)  # no automatic second write
        self.assertEqual(len(self.fake.writes), 1)

    def test_confirm_not_applied_requires_evidence_reviewer_and_execute(self):
        self.fake.fail_write = 'create-policy-version'
        self.run_step('guardrails-v2')
        rid = self.only_unresolved()
        for ev, rv in ((None, 'GWONUK'), (EVIDENCE, None), ('  ', 'GWONUK')):
            with self.assertRaises(m.InputError):
                self.run_step('confirm-not-applied', run_id=rid, evidence=ev, reviewer=rv)
        n = len(self.ledger_entries())
        self.assertEqual(self.run_step('confirm-not-applied', execute=False, run_id=rid, evidence=EVIDENCE,
                                       reviewer='GWONUK'), 0)
        self.assertEqual(len(self.ledger_entries()), n)
        self.assertEqual(self.only_unresolved(), rid)

    # --- PR24 review B2: everything an --execute run decides on is read under the lock ---
    def inject_before_lock(self, action):
        real = m.Lock.__enter__

        def enter(lock):
            action()
            return real(lock)
        m.Lock.__enter__ = enter
        self.addCleanup(setattr, m.Lock, '__enter__', real)

    def test_foreign_intent_just_before_lock_stops_write(self):
        self.run_step('status')
        self.inject_before_lock(lambda: m.append_journal(
            self.ledger / m.LEDGER_NAME, {'run_id': 'other', 'step': 'guardrails-v2', 'phase': 'INTENT'}))
        self.assertEqual(self.run_step('guardrails-v2'), 1)
        self.assertIn('UNRESOLVED run_id=other', self.out)
        self.assertEqual(self.fake.writes, [])
        self.assertFalse((self.ledger / m.LOCK_NAME).exists())

    def test_live_change_just_before_lock_rechecked(self):
        def drift():
            self.fake._create('AdminLike', {'Statement': []})
            self.fake._attach(m.arn('AdminLike'))
        self.inject_before_lock(drift)
        self.assertEqual(self.run_step('guardrails-v2'), 1)
        self.assertIn('unexpected policies on role', self.out)
        self.assertEqual(self.fake.writes, [])

    def test_reconcile_rereads_ledger_under_lock(self):
        self.fake.fail_write = 'create-policy-version'
        self.run_step('guardrails-v2')
        rid = self.only_unresolved()
        self.fake.fail_write = None
        path = self.ledger / m.LEDGER_NAME
        self.inject_before_lock(lambda: m.append_journal(path, {
            'run_id': rid, 'step': 'guardrails-v2', 'phase': 'RECONCILED', 'outcome': 'NOT_APPLIED', 'ids': {}}))
        with self.assertRaises(m.InputError):  # already resolved by the other run
            self.run_step('reconcile', run_id=rid)
        self.assertEqual(sum(e['phase'] == 'RECONCILED' for e in self.ledger_entries()), 1)

    def test_status_and_dry_run_do_not_take_lock(self):
        self.run_step('status')
        (self.ledger / m.LOCK_NAME).write_text('pid=1\n')
        self.assertEqual(self.run_step('status'), 0)
        self.assertEqual(self.run_step('guardrails-v2', execute=False), 0)
        self.assertTrue((self.ledger / m.LOCK_NAME).exists())
        self.assertEqual(self.fake.writes, [])

    def test_intent_not_durable_means_no_write(self):
        real = m.append_journal
        try:
            def broken(path, entry):
                raise m.Stop('ledger write failed (INTENT): No space left on device')
            m.append_journal = broken
            with self.assertRaises(m.Stop):
                self.run_step('guardrails-v2')
        finally:
            m.append_journal = real
        self.assertEqual(self.fake.writes, [])

    def test_readback_record_not_durable_leaves_run_unresolved(self):
        real = m.append_journal
        try:
            def broken(path, entry):
                if entry['phase'] == 'READBACK':
                    raise m.Stop('ledger write failed (READBACK): I/O error')
                real(path, entry)
            m.append_journal = broken
            with self.assertRaises(m.Stop):
                self.run_step('guardrails-v2')
        finally:
            m.append_journal = real
        rid = self.only_unresolved()
        self.assertEqual(self.runs()[rid][-1]['phase'], 'WRITE_RETURNED')
        self.assertEqual(self.run_step('subscribe-create'), 1)

    def test_lock_blocks_concurrent_run(self):
        self.run_step('status')
        (self.ledger / m.LOCK_NAME).write_text('pid=1\n')
        with self.assertRaises(m.Stop):
            self.run_step('guardrails-v2')
        self.assertEqual(self.fake.writes, [])

    def test_ambiguous_reconcile_stays_unresolved(self):
        self.fake.fail_write = 'create-policy-version'
        self.run_step('guardrails-v2')
        rid = self.only_unresolved()
        g = self.fake.policies['FDS-IaC-Guardrails']
        g['docs']['v2'] = SRC['v2'][1]  # v2 version exists but is not default: neither pre nor post
        self.assertEqual(self.run_step('reconcile', run_id=rid), 1)
        self.assertIn('AMBIGUOUS', self.out)
        self.assertEqual(self.only_unresolved(), rid)

    def test_reconcile_input_errors(self):
        self.run_step('guardrails-v2')
        rid = next(iter(self.runs()))
        with self.assertRaises(m.InputError):
            self.run_step('reconcile', run_id=rid)  # already resolved
        with self.assertRaises(m.InputError):
            self.run_step('reconcile', run_id='nope')
        with self.assertRaises(m.InputError):
            self.run_step('reconcile')

    def test_corrupt_or_old_format_ledger_refused(self):
        self.run_step('status')
        path = self.ledger / m.LEDGER_NAME
        for line in ('not json', json.dumps({'step': 'guardrails-v2', 'verified': True})):
            path.write_text(line + '\n')
            os.chmod(path, 0o600)
            with self.assertRaises(m.InputError):
                self.run_step('status')

    def test_public_ledger_file_refused(self):
        self.run_step('guardrails-v2')
        os.chmod(self.ledger / m.LEDGER_NAME, 0o644)
        with self.assertRaises(m.InputError):
            self.run_step('status')

    def test_rollback_v1_requires_rosa_policies_detached(self):
        self.full_forward()
        self.assertEqual(self.run_step('guardrails-v1'), 1)
        self.assertIn('unexpected policies on role', self.out)

    def test_delete_refuses_attached_policy(self):
        self.full_forward()
        self.assertEqual(self.run_step('prereq-delete'), 1)

    def test_public_ledger_dir_refused(self):
        self.ledger.mkdir(mode=0o755)
        os.chmod(self.ledger, 0o755)
        with self.assertRaises(m.InputError):
            self.run_step('status')

    def test_source_hash_mismatch_refused(self):
        orig = m.FILES['prereq']
        try:
            with tempfile.TemporaryDirectory() as d:
                Path(d, 'SHA256SUMS').write_text('0' * 64 + ' *p.json\n')
                Path(d, 'p.json').write_text('{}')
                m.FILES['prereq'] = (Path(d), 'p.json')
                with self.assertRaises(m.InputError):
                    m.load_sources()
        finally:
            m.FILES['prereq'] = orig

    def test_v2_candidate_is_v1_plus_eleven_notactions(self):
        v1, v2 = SRC['v1'][1], SRC['v2'][1]
        s1 = {s['Sid']: s for s in v1['Statement']}
        s2 = {s['Sid']: s for s in v2['Statement']}
        self.assertEqual(set(s1), set(s2))
        for sid in s1:
            if sid != 'DenyOutsideSeoul':
                self.assertEqual(s1[sid], s2[sid])
        a1, a2 = s1['DenyOutsideSeoul']['NotAction'], s2['DenyOutsideSeoul']['NotAction']
        self.assertEqual(a2[:len(a1)], a1)
        self.assertEqual(len(a2) - len(a1), 11)


class Platform(unittest.TestCase):
    def test_non_posix_refused_at_start(self):
        real = m.os.name
        try:
            m.os.name = 'nt'
            with self.assertRaises(m.InputError):
                m.require_posix()
        finally:
            m.os.name = real


if __name__ == '__main__':
    unittest.main()
