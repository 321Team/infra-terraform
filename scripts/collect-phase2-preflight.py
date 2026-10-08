#!/usr/bin/env python3
"""One-shot, read-only AWS inventory. Never grants readiness or runs Terraform."""
import argparse
from datetime import datetime, timezone, timedelta
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import tempfile

ACCOUNT = "774055931866"
REGION = "ap-northeast-2"
AMI = "ami-08d855918a18d0cf9"
OWNER = "125523088429"
# Candidate binding is provenance, never a merge, permission or execution grant.
TERRAFORM_CANDIDATE = "127921559e41f9667ccaf855bf6a3d3c2876fd5d"
READS = {
    ("sts", "get-caller-identity"), ("ec2", "describe-images"),
    ("iam", "get-role"), ("iam", "list-attached-role-policies"),
    ("iam", "list-role-policies"), ("ssm", "describe-document"),
    ("ssm", "get-document"),
}


def now():
    return datetime.now(timezone.utc).isoformat()


class Stop(RuntimeError):
    pass


def classify_error(service, operation, stderr):
    # Absence is never inferred from AccessDenied or a generic failure.
    match = re.search(r"An error occurred \(([^)]+)\)", stderr)
    code = match.group(1) if match else None
    if (service, operation, code) == ("iam", "get-role", "NoSuchEntity"):
        return "ABSENT"
    if (service, operation, code) == ("ssm", "describe-document", "InvalidDocument"):
        return "NOT_FOUND_REVIEW_REQUIRED"
    raise Stop("API_ERROR_REQUIRES_REVIEW")


class Capture:
    def __init__(self, parent, runner=subprocess.run):
        self.root = Path(tempfile.mkdtemp(prefix="fds-phase2-preflight-", dir=parent))
        self.root.chmod(0o700)
        self.runner = runner
        self.calls = []
        self.sequence = 0

    def write(self, name, value):
        path = self.root / name
        data = value if isinstance(value, bytes) else value.encode("utf-8")
        path.write_bytes(data)
        path.chmod(0o600)

    def call(self, service, operation, *args):
        if (service, operation) not in READS:
            raise Stop("NON_ALLOWLISTED_OPERATION")
        self.sequence += 1
        label = f"{self.sequence:02d}-{service}-{operation}"
        cmd = ["aws", service, operation, *args, "--region", REGION,
               "--output", "json", "--no-cli-pager", "--cli-connect-timeout", "10",
               "--cli-read-timeout", "30"]
        record = {"label": label, "command": cmd, "started_utc": now()}
        self.calls.append(record)
        try:
            result = self.runner(cmd, capture_output=True, timeout=90, check=False)
            stdout, stderr = result.stdout, result.stderr
            record.update(returncode=result.returncode, timeout=False)
        except subprocess.TimeoutExpired as exc:
            stdout, stderr = exc.stdout or b"", exc.stderr or b""
            record.update(returncode=None, timeout=True)
        except OSError as exc:
            stdout, stderr = b"", str(exc).encode("utf-8")
            record.update(returncode=None, timeout=False)
        record["finished_utc"] = now()
        self.write(label + ".stdout", stdout)
        self.write(label + ".stderr", stderr)
        if record["timeout"] or record["returncode"] is None:
            raise Stop("TIMEOUT_OR_LAUNCH_FAILURE")
        if record["returncode"] != 0:
            status = classify_error(service, operation, stderr.decode("utf-8", "replace"))
            return {"capture_status": status}
        try:
            data = json.loads(stdout)
            if not isinstance(data, dict):
                raise Stop("UNEXPECTED_JSON_SHAPE")
            return data
        except (ValueError, UnicodeError) as exc:
            raise Stop("INVALID_JSON") from exc

    def finish(self, summary):
        summary["commands"] = self.calls
        summary["finished_utc"] = now()
        self.write("summary.json", json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
        lines = [f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n"
                 for p in sorted(self.root.iterdir()) if p.is_file()]
        self.write("SHA256SUMS", "".join(lines))


def collect(capture):
    identity = capture.call("sts", "get-caller-identity")
    if identity.get("Account") != ACCOUNT:
        raise Stop("WRONG_ACCOUNT")
    images = capture.call("ec2", "describe-images", "--image-ids", AMI, "--owners", OWNER)
    selected = images.get("Images", [])
    if len(selected) != 1 or any(selected[0].get(key) != expected for key, expected in {
        "ImageId": AMI, "OwnerId": OWNER, "State": "available",
        "Architecture": "x86_64", "RootDeviceType": "ebs",
    }.items()):
        raise Stop("AMI_IDENTITY_OR_AVAILABILITY_MISMATCH")
    role_states = {}
    for name in ("FDS-IaC-Operator", "FDS-Network-Operator"):
        role = capture.call("iam", "get-role", "--role-name", name)
        if role.get("capture_status") == "ABSENT":
            role_states[name] = "ABSENT"
            continue
        expected_arn = f"arn:aws:iam::{ACCOUNT}:role/{name}"
        if role.get("Role", {}).get("Arn") != expected_arn:
            raise Stop("ROLE_IDENTITY_MISMATCH")
        capture.call("iam", "list-attached-role-policies", "--role-name", name)
        capture.call("iam", "list-role-policies", "--role-name", name)
        role_states[name] = "PRESENT_METADATA_ONLY"
    document = capture.call("ssm", "describe-document", "--name", "SSM-SessionManagerRunShell")
    doc_state = document.get("capture_status", "PRESENT_REVIEW_REQUIRED")
    if doc_state == "PRESENT_REVIEW_REQUIRED":
        info = document.get("Document", {})
        if info.get("Name") != "SSM-SessionManagerRunShell" or info.get("DocumentType") != "Session":
            raise Stop("DOCUMENT_IDENTITY_OR_TYPE_MISMATCH")
        version = info.get("DefaultVersion")
        if not isinstance(version, str) or not re.fullmatch(r"[0-9]+", version):
            raise Stop("DOCUMENT_DEFAULT_VERSION_MISSING")
        capture.call("ssm", "get-document", "--name", "SSM-SessionManagerRunShell",
                     "--document-version", version, "--document-format", "JSON")
        again = capture.call("ssm", "describe-document", "--name", "SSM-SessionManagerRunShell")
        if any(again.get("Document", {}).get(k) != info.get(k)
               for k in ("Owner", "DefaultVersion", "Hash", "DocumentType")):
            raise Stop("DOCUMENT_CHANGED_DURING_CAPTURE")
    return {"roles": role_states, "session_document": doc_state}


def run(parent, runner=subprocess.run):
    cap = Capture(parent, runner)
    summary = {"collection": "STOP", "started_utc": now(),
               "started_kst": datetime.now(timezone(timedelta(hours=9))).isoformat(),
               "host": platform.node(), "platform": platform.platform(),
               "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               "expected_ami": AMI, "expected_ami_owner": OWNER,
               "terraform_candidate_sha": TERRAFORM_CANDIDATE,
               "terraform_candidate_status": "REVIEW_PENDING_NOT_EXECUTION_APPROVAL",
               "aws_mutation": "NOT_RUN", "plan": "NOT_RUN", "stage_a_ready": "NO",
               "ami_os_packages_services": "NOT_VERIFIED",
               "effective_permissions": "NOT_TESTED", "grant": "NOT_RUN"}
    rc = 2
    try:
        summary.update(collect(cap))
        summary["collection"] = "COMPLETE"
        rc = 0
    except (Stop, KeyError, TypeError, ValueError) as exc:
        summary["stop_reason"] = str(exc)
    finally:
        cap.finish(summary)
    print(f"COLLECTION={summary['collection']}; STAGE_A_READY=NO; AWS_MUTATION=NOT_RUN")
    print(f"CAPTURE={cap.root}")
    return rc


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-parent", type=Path, required=True)
    opts = parser.parse_args()
    if platform.system() != "Linux":
        parser.error("Run on approved Linux CloudShell; offline tests may use other platforms.")
    if not opts.output_parent.is_dir():
        parser.error("output-parent must already exist")
    if any(k.startswith("AWS_ENDPOINT_URL") and v for k, v in os.environ.items()):
        parser.error("Endpoint overrides are not accepted")
    os.umask(0o077)
    raise SystemExit(run(opts.output_parent))
