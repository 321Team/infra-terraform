"""Synthetic offline tests; no AWS identity, credentials, or network used."""
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("preflight", Path(__file__).resolve().parents[1] / "scripts/collect-phase2-preflight.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class CollectorTests(unittest.TestCase):
    def make_runner(self, account=None, bad_image=False, denial=False, timeout=False, old_image=False):
        self.calls = []
        def runner(cmd, **kwargs):
            self.calls.append(cmd)
            service, op = cmd[1:3]
            if timeout:
                raise subprocess.TimeoutExpired(cmd, 90, output=b"partial")
            if service == "sts":
                data = {"Account": account or m.ACCOUNT, "Arn": "SYNTHETIC_ONLY"}
            elif service == "ec2":
                self.assertEqual(cmd[cmd.index("--image-ids") + 1], "ami-08d855918a18d0cf9")
                data = {"Images": [] if bad_image else [{"ImageId": m.AMI, "OwnerId": m.OWNER,
                    "State": "available", "Architecture": "x86_64", "RootDeviceType": "ebs"}]}
                if old_image:
                    data["Images"][0]["ImageId"] = "ami-079a2667364cee804"
            else:
                error = "AccessDenied" if denial else ("NoSuchEntity" if service == "iam" else "InvalidDocument")
                return subprocess.CompletedProcess(cmd, 254, b"", f"An error occurred ({error}) when calling the operation".encode())
            return subprocess.CompletedProcess(cmd, 0, json.dumps(data).encode(), b"")
        return runner

    def execute(self, **kwargs):
        with tempfile.TemporaryDirectory() as temp:
            rc = m.run(Path(temp), self.make_runner(**kwargs))
            root = next(Path(temp).iterdir())
            result = json.loads((root / "summary.json").read_text())
            self.assertTrue((root / "SHA256SUMS").is_file())
            return rc, result

    def test_wrong_account_stops_before_inventory(self):
        rc, result = self.execute(account="000000000000")
        self.assertEqual(rc, 2)
        self.assertEqual(result["stop_reason"], "WRONG_ACCOUNT")
        self.assertEqual(len(self.calls), 1)

    def test_image_mismatch_stops_before_role_reads(self):
        rc, result = self.execute(bad_image=True)
        self.assertEqual(rc, 2)
        self.assertEqual(result["stop_reason"], "AMI_IDENTITY_OR_AVAILABILITY_MISMATCH")
        self.assertEqual(len(self.calls), 2)

    def test_missing_role_is_recorded_without_granting_readiness(self):
        rc, result = self.execute()
        self.assertEqual(rc, 0)
        self.assertEqual(result["roles"]["FDS-IaC-Operator"], "ABSENT")
        self.assertEqual(result["stage_a_ready"], "NO")
        self.assertEqual(result["ami_os_packages_services"], "NOT_VERIFIED")
        self.assertEqual(result["session_document"], "NOT_FOUND_REVIEW_REQUIRED")
        self.assertTrue(all(tuple(c[1:3]) in m.READS for c in self.calls))

    def test_old_stream10_response_stops_before_role_reads(self):
        rc, result = self.execute(old_image=True)
        self.assertEqual(rc, 2)
        self.assertEqual(result["stop_reason"], "AMI_IDENTITY_OR_AVAILABILITY_MISMATCH")
        self.assertEqual(len(self.calls), 2)

    def test_receipt_binds_candidate_without_claiming_approval(self):
        rc, result = self.execute()
        self.assertEqual(rc, 0)
        self.assertEqual(result["expected_ami"], "ami-08d855918a18d0cf9")
        self.assertEqual(result["terraform_candidate_sha"], "28ddb32d1dfcde5d2415070dbbc8b2656e8f5bcb")
        self.assertEqual(result["terraform_candidate_status"], "REVIEW_PENDING_NOT_EXECUTION_APPROVAL")
        self.assertEqual(result["plan"], "NOT_RUN")
        self.assertEqual(result["stage_a_ready"], "NO")

    def test_access_denied_is_not_absence(self):
        rc, result = self.execute(denial=True)
        self.assertEqual(rc, 2)
        self.assertEqual(result["stop_reason"], "API_ERROR_REQUIRES_REVIEW")
        self.assertEqual(len(self.calls), 3)

    def test_timeout_preserves_stop_and_no_followup(self):
        rc, result = self.execute(timeout=True)
        self.assertEqual(rc, 2)
        self.assertTrue(result["commands"][0]["timeout"])
        self.assertEqual(len(self.calls), 1)

    def test_write_operation_rejected_before_runner(self):
        with tempfile.TemporaryDirectory() as temp:
            cap = m.Capture(temp, lambda *a, **kw: self.fail("runner invoked"))
            with self.assertRaises(m.Stop):
                cap.call("ec2", "run-instances")

    def test_error_from_other_operation_not_treated_as_absence(self):
        with self.assertRaises(m.Stop):
            m.classify_error("iam", "list-role-policies", "An error occurred (NoSuchEntity)")

    def test_existing_document_is_read_at_pinned_default_version(self):
        self.check_document(drift=False)

    def test_changed_document_stops_capture(self):
        self.check_document(drift=True)

    def check_document(self, drift):
        basic = self.make_runner()
        descriptions = 0
        def runner(cmd, **kwargs):
            nonlocal descriptions
            if cmd[1] != "ssm":
                return basic(cmd, **kwargs)
            self.calls.append(cmd)
            if cmd[2] == "describe-document":
                descriptions += 1
                version = "2" if drift and descriptions == 2 else "1"
                data = {"Document": {"Name": "SSM-SessionManagerRunShell", "DocumentType": "Session",
                        "DefaultVersion": version, "Owner": m.ACCOUNT, "Hash": "SYNTHETIC_ONLY"}}
            else:
                self.assertEqual(cmd[cmd.index("--document-version") + 1], "1")
                data = {"Content": "{}", "DocumentVersion": "1"}
            return subprocess.CompletedProcess(cmd, 0, json.dumps(data).encode(), b"")
        with tempfile.TemporaryDirectory() as temp:
            rc = m.run(Path(temp), runner)
            result = json.loads((next(Path(temp).iterdir()) / "summary.json").read_text())
            self.assertEqual(rc, 2 if drift else 0)
            if drift:
                self.assertEqual(result["stop_reason"], "DOCUMENT_CHANGED_DURING_CAPTURE")
            else:
                self.assertEqual(result["session_document"], "PRESENT_REVIEW_REQUIRED")


if __name__ == "__main__":
    unittest.main()
