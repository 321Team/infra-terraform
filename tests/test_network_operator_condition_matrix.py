"""Relay StartSession 조건 비교표 — 현행(Bool) vs 후보(BoolIfExists). AWS를 호출하지 않는다.

IAM 조건 연산자 규칙(공식 문서: reference_policies_elements_condition_operators)만 단순 모형으로 옮겨
ssm:SessionDocumentAccessCheck 가 true / false / 부재일 때 instance statement 의 조건 일치 여부를 비교한다.
실제 StartSession 요청에 키가 있었는지는 관측하지 않으며, 중앙 시뮬레이션·수정 전후 실제 시험을 대신하지 않는다.
"""
import json
import subprocess
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TEMPLATE = "iam/full-policy-draft-20261009/policies/FDS-Network-Operator-Relay.template.json"
SID = "StartSessionOnExactRelayWithDocumentCheck"
KEY = "ssm:SessionDocumentAccessCheck"
ABSENT = object()


def bool_match(op, want, ctx):
    """Bool: 키가 없으면 불일치. BoolIfExists: 키가 없으면 일치, 있으면 값 비교."""
    have = ctx.get(KEY, ABSENT)
    if have is ABSENT:
        return op == "BoolIfExists"
    return str(have).lower() == str(want).lower()


def statement_matches(st, ctx):
    cond = st["Condition"]
    if cond["StringEquals"]["aws:RequestedRegion"] != ctx["aws:RequestedRegion"]:
        return False
    ops = [o for o in cond if o in ("Bool", "BoolIfExists")]
    assert len(ops) == 1, ops
    return bool_match(ops[0], cond[ops[0]][KEY], ctx)


def instance_statement(raw):
    return [s for s in json.loads(raw)["Statement"] if s["Sid"] == SID][0]


CASES = {"true": {KEY: "true"}, "false": {KEY: "false"}, "absent": {}}
# 현행(main HEAD 이전 템플릿)과 후보의 기대 결과
EXPECTED = {
    "Bool":         {"true": True, "false": False, "absent": False},
    "BoolIfExists": {"true": True, "false": False, "absent": True},
}


class ConditionMatrixTest(unittest.TestCase):
    def test_candidate_matrix(self):
        st = instance_statement((REPO / TEMPLATE).read_text(encoding="utf-8"))
        self.assertIn("BoolIfExists", st["Condition"])
        for name, extra in CASES.items():
            with self.subTest(key=name):
                ctx = {"aws:RequestedRegion": "ap-northeast-2", **extra}
                self.assertEqual(statement_matches(st, ctx), EXPECTED["BoolIfExists"][name])

    def test_previous_matrix_from_git_parent(self):
        try:
            raw = subprocess.run(["git", "-C", str(REPO), "show", f"6847d906f974136a5a4aad5ffe47d45930f142e7:{TEMPLATE}"],
                                 capture_output=True, check=True).stdout.decode("utf-8")
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.skipTest("기준 커밋 없음(얕은 clone)")
        st = instance_statement(raw)
        self.assertIn("Bool", st["Condition"])
        for name, extra in CASES.items():
            with self.subTest(key=name):
                ctx = {"aws:RequestedRegion": "ap-northeast-2", **extra}
                self.assertEqual(statement_matches(st, ctx), EXPECTED["Bool"][name])

    def test_other_limits_unchanged_and_region_still_required(self):
        st = instance_statement((REPO / TEMPLATE).read_text(encoding="utf-8"))
        for name, extra in CASES.items():
            with self.subTest(key=name):
                ctx = {"aws:RequestedRegion": "us-east-1", **extra}
                self.assertFalse(statement_matches(st, ctx))
        self.assertTrue(st["Resource"].endswith("instance/__RELAY_INSTANCE_ID__"))


if __name__ == "__main__":
    unittest.main()
