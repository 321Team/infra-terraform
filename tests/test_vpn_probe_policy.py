"""#37 vpn-probe: 보충 정책·Terraform root·mock 시험이 서로, 그리고 승인된 정책과 어긋나지 않는지 정적으로 확인한다.

AWS·Terraform을 실행하지 않는다. 중앙 validate-policy·시뮬레이션과 실제 Plan은 별도 절차다.
"""
import hashlib
import json
import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ROOT = REPO / "terraform/vpn-probe"
IAM = REPO / "iam/vpn-probe-20261009"
APPROVED = REPO / "iam/full-policy-draft-20261009/policies"
OPERATOR = "arn:aws:iam::774055931866:role/FDS-IaC-Operator"
STATE = "arn:aws:s3:::fds-tfstate-774055931866-ap-northeast-2/phase2/vpn-probe/terraform.tfstate"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def by_sid(doc):
    return {s["Sid"]: s for s in doc["Statement"]}


class ProbePolicyTests(unittest.TestCase):
    def setUp(self):
        self.iac = load(IAM / "policies/FDS-IaC-VpnProbe.json")
        self.net = load(IAM / "policies/FDS-Network-Operator-Probe.json")
        self.main = (ROOT / "main.tf").read_text(encoding="utf-8")

    def test_size_and_unique_sids(self):
        for path in sorted((IAM / "policies").glob("*.json")) + sorted((IAM / "trust").glob("*.json")):
            doc = load(path)
            self.assertLessEqual(len(json.dumps(doc, separators=(",", ":"))), 6144, path)
            sids = [s.get("Sid") for s in doc["Statement"]]
            self.assertEqual(len(sids), len(set(sids)), path)

    def test_every_iac_allow_is_bound_to_operator_except_image(self):
        for sid, s in by_sid(self.iac).items():
            if s["Effect"] != "Allow" or sid == "RunWithExactProbeAmi":
                continue
            self.assertEqual(s["Condition"]["ArnEquals"]["aws:PrincipalArn"], OPERATOR, sid)
        self.assertNotIn("*", json.dumps([s["Resource"] for s in self.iac["Statement"] if s["Effect"] == "Allow"]),
                         "probe 보충 Allow에 와일드카드 자원 없음")

    def test_trust_is_ec2_only_without_source_conditions(self):
        # EC2 instance-profile 발급 요청에는 aws:SourceAccount/SourceArn이 없다 → 조건을 두면 AssumeRole이 거부된다(PR25 B1).
        trust = load(IAM / "trust/trust-FDS-P2-VPN-Probe-SSM.json")
        self.assertEqual(len(trust["Statement"]), 1)
        s = trust["Statement"][0]
        self.assertEqual((s["Effect"], s["Principal"], s["Action"]),
                         ("Allow", {"Service": "ec2.amazonaws.com"}, "sts:AssumeRole"))
        self.assertNotIn("Condition", s)
        self.assertNotIn("aws:Source", json.dumps(trust))

    def test_supplement_only_adds_probe_scope(self):
        s = by_sid(self.iac)
        self.assertEqual(s["PassApprovedProbeToEC2"]["Resource"], "arn:aws:iam::774055931866:role/FDS-P2-VPN-Probe-SSM")
        self.assertEqual(s["PassApprovedProbeToEC2"]["Condition"]["StringEquals"]["iam:PassedToService"], "ec2.amazonaws.com")
        self.assertEqual(s["ReadWriteProbeState"]["Resource"], STATE)
        self.assertEqual(s["ReadWriteDeleteProbeLock"]["Resource"], STATE + ".tflock")
        self.assertEqual(s["ReadWriteProbeState"]["Condition"]["Bool"]["aws:SecureTransport"], "true")
        self.assertIn("s3:DeleteObject", s["DenyProbeStateDeletion"]["Action"])
        actions = {a for st in self.iac["Statement"] if st["Effect"] == "Allow"
                   for a in ([st["Action"]] if isinstance(st["Action"], str) else st["Action"])}
        self.assertEqual(actions, {"ec2:RunInstances", "iam:GetRole", "iam:GetInstanceProfile", "iam:PassRole",
                                   "s3:GetObject", "s3:PutObject", "s3:DeleteObject"})

    def test_ami_pinned_consistently(self):
        local = re.search(r'probe_ami_id\s*=\s*"([^"]+)"', self.main).group(1)
        image = by_sid(self.iac)["RunWithExactProbeAmi"]["Resource"]
        self.assertEqual(image, f"arn:aws:ec2:ap-northeast-2::image/{local}")
        tests = (ROOT / "tests/vpn-probe.tftest.hcl").read_text(encoding="utf-8")
        self.assertIn(f'id               = "{local}"', tests)
        self.assertIn(f'aws_instance.probe.ami == "{local}"', tests)

    def test_ami_is_fixed_before_review(self):
        local = re.search(r'probe_ami_id\s*=\s*"([^"]+)"', self.main).group(1)
        self.assertRegex(local, r"^ami-[0-9a-f]{17}$", "AL2023 AMI ID를 PR 단계에서 고정해야 한다(#35 조건 3)")

    def test_terraform_matches_approved_deny_and_session_tags(self):
        self.assertIn('instance_type               = "t3.medium"', self.main)
        vpn = by_sid(load(APPROVED / "FDS-IaC-Vpn.json"))
        self.assertEqual(vpn["DenyRunOtherThanT3Medium"]["Condition"]["StringNotEquals"]["ec2:InstanceType"], "t3.medium")
        self.assertIn('http_tokens   = "required"', self.main)
        self.assertRegex(self.main, r"volume_size\s*=\s*8\b")  # 승인 정책 gp3 ≤40GiB 범위
        cond = by_sid(self.net)["StartSessionOnTaggedProbeWithDocumentCheck"]["Condition"]["StringEquals"]
        self.assertIn(f'Purpose = "{cond["ssm:resourceTag/Purpose"]}"', self.main)
        self.assertIn(f'Ticket  = "{cond["ssm:resourceTag/Ticket"]}"', self.main)
        versions = (ROOT / "versions.tf").read_text(encoding="utf-8")
        for tag in ["Project", "ManagedBy"]:
            self.assertRegex(versions, rf'{tag}\s*=\s*"{cond["ssm:resourceTag/" + tag]}"')
        self.assertEqual(by_sid(self.net)["StartSessionOnTaggedProbeWithDocumentCheck"]["Condition"]["BoolIfExists"]
                         ["ssm:SessionDocumentAccessCheck"], "true")

    def test_backend_key_matches_policy(self):
        for path in (ROOT / "backend.hcl.example", REPO / "terraform/backends/vpn-probe.hcl.example"):
            self.assertIn('key                 = "phase2/vpn-probe/terraform.tfstate"', path.read_text(encoding="utf-8"))

    def test_probe_hashes_match_sums_and_manifest(self):
        listed = {}
        for line in (IAM / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
            digest, name = line.split(" *", 1)
            listed[name] = digest
        present = {p.relative_to(IAM).as_posix() for p in IAM.rglob("*") if p.is_file() and p.name != "SHA256SUMS"}
        self.assertEqual(set(listed), present, "SHA256SUMS는 폴더의 모든 파일을 정확히 나열한다")
        for name, digest in listed.items():
            self.assertEqual(hashlib.sha256((IAM / name).read_bytes()).hexdigest(), digest, name)
        manifest = load(REPO / "validation/vpn-probe-20261009/source.json")["components"]["vpn-probe"]["files"]
        current = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in ROOT.rglob("*") if p.is_file()}
        self.assertEqual(current, manifest, "terraform/vpn-probe가 검증 manifest와 다르면 정적·MOCK 검증을 다시 한다")

    def test_approved_policy_set_untouched(self):
        sums = (REPO / "iam/full-policy-draft-20261009/SHA256SUMS").read_text(encoding="utf-8")
        self.assertNotIn("VpnProbe", sums)
        self.assertNotIn("vpn-probe", sums)


if __name__ == "__main__":
    unittest.main()
