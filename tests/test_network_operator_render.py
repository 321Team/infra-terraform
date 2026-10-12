"""Network-Operator Relay 정책 렌더러 정적 시험. AWS를 호출하지 않는다."""
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "render_relay_policy", REPO / "iam/network-operator-grant-20261012/render_relay_policy.py")
R = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(R)
GOOD = "i-0123456789abcdef0"


class RenderTest(unittest.TestCase):
    def test_template_is_reviewed_bytes(self):
        self.assertEqual(hashlib.sha256(R.TEMPLATE.read_bytes()).hexdigest(), R.TEMPLATE_SHA256)

    def test_render_fills_every_placeholder(self):
        doc = json.loads(R.render(GOOD))
        text = json.dumps(doc)
        self.assertNotIn("__", text)
        self.assertEqual(text.count(f"instance/{GOOD}"), 4)
        self.assertNotIn("instance/*", text)
        cond = [s for s in doc["Statement"] if s["Sid"] == "ManageOnlyOwnSessionsOnExactRelay"][0]["Condition"]
        self.assertEqual(cond["StringEquals"]["ssm:resourceTag/aws:ssmmessages:target-id"], GOOD)

    def test_rejects_bad_ids(self):
        for bad in ("", "i-123", "I-0123456789ABCDEF0", "i-0123456789abcdef0*", "i-*", "*",
                    "i-0123456789abcdef0 ", "i-0123456789abcdefg"):
            with self.subTest(bad=bad), self.assertRaises(R.Stop):
                R.render(bad)

    def test_cli_writes_file_and_stops_on_bad_input(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(R.main([GOOD, "--out", d]), 0)
            self.assertTrue((Path(d) / f"FDS-Network-Operator-Relay.{GOOD}.json").exists())
            self.assertEqual(R.main(["i-bad", "--out", d]), 1)

    def test_companion_policies_unchanged(self):
        expected = {
            "iam/full-policy-draft-20261009/policies/FDS-Network-Operator-StateDeny.json":
                "e222cddb82a388be6f7c565f3e670ee761575a3cbd994cdbf56a6a29fb4a6e77",
            "iam/full-policy-draft-20261009/trust/trust-FDS-Network-Operator.json":
                "13e134a09d309e58ad6e6c7d04a5ca14605b629caf5d7feff8eb2305e2c11e10",
            "iam/vpn-probe-20261009/policies/FDS-Network-Operator-Probe.json":
                "33053efe4e9ab326b3dcffe2541442ffd71faa7af371b6a9b3ebb004de5e2dcd",
        }
        for path, h in expected.items():
            with self.subTest(path=path):
                self.assertEqual(hashlib.sha256((REPO / path).read_bytes()).hexdigest(), h)


if __name__ == "__main__":
    unittest.main()
