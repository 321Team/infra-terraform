#!/usr/bin/env python3
"""Check the reviewed, hash-pinned roots in a new credential-isolated copy.

This is a reproducibility helper, not a sandbox for arbitrary Terraform code.
Changes to source.json AND source require renewed review of mock-only tests.
No cloud plan/apply, backend initialization, lock update or AWS CLI call.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile

REPO = Path(__file__).resolve().parents[1]
MANIFEST = REPO / "validation/components-20261007/source.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def snapshot(root):
    result = {}
    if root.is_symlink():
        raise ValueError("Source root must not be a symlink")
    for path in sorted(root.rglob("*")):
        if path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction()):
            raise ValueError("Source must not contain links: " + str(path))
        if path.is_file():
            result[path.relative_to(root).as_posix()] = sha(path)
    return result


def isolated_env(home, data):
    # Do not inherit AWS_*, TF_*, proxies, credentials, profiles or CLI overrides.
    keep = {"SYSTEMROOT", "WINDIR", "PATH", "PATHEXT", "TEMP", "TMP", "COMSPEC"}
    env = {k: v for k, v in os.environ.items() if k.upper() in keep}
    env.update({
        "HOME": str(home), "USERPROFILE": str(home),
        "APPDATA": str(home), "LOCALAPPDATA": str(home),
        "AWS_SHARED_CREDENTIALS_FILE": str(home / "credentials"),
        "AWS_CONFIG_FILE": str(home / "config"),
        "AWS_EC2_METADATA_DISABLED": "true", "CHECKPOINT_DISABLE": "1",
        "TF_CLI_CONFIG_FILE": str(home / "terraform.tfrc"),
        "TF_DATA_DIR": str(data), "TF_IN_AUTOMATION": "1", "TF_INPUT": "0",
    })
    return env


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--terraform", required=True, type=Path)
    parser.add_argument("--component", required=True, choices=["network", "vpn", "vpn-probe"])
    parser.add_argument("--manifest", type=Path, default=MANIFEST, help="Reviewed source/hash manifest; historical default is unchanged")
    args = parser.parse_args()
    binary = args.terraform.resolve(strict=True)
    root = REPO / "terraform" / args.component
    manifest_path = args.manifest.resolve(strict=True)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = manifest["components"][args.component]["files"]
    # Exact set rejects unexpected auto.tfvars, override files, state and tests.
    if snapshot(root) != expected:
        raise ValueError("Source set/hash differs from source.json; stop and review")
    out = Path(tempfile.mkdtemp(prefix="fds-static-" + args.component + "-"))
    work, home, data = out / "source", out / "home", out / "terraform-data"
    shutil.copytree(root, work)
    home.mkdir()
    for name in ("credentials", "config", "terraform.tfrc"):
        (home / name).write_text("", encoding="utf-8")
    env = isolated_env(home, data)
    summary = {
        "started_at_utc": now(), "host": socket.gethostname(),
        "source_root": str(root), "isolated_cwd": str(work),
        "component": args.component, "terraform_sha256": sha(binary),
        "source_manifest_sha256": sha(manifest_path), "source_before": expected,
        "credentials_inherited": False, "backend_initialized": False,
        "cloud_plan": "NOT_RUN", "cloud_apply": "NOT_RUN", "CI": "NOT_RUN",
        "test_type": "MOCK_PROVIDER_PLAN_ONLY", "records": [], "pass": False,
    }
    steps = [
        ("version", ["version", "-json"], None),
        ("fmt", ["fmt", "-check", "-recursive", "-diff"], None),
        ("backend-example-fmt", ["fmt", "-check", "-"], (work / "backend.hcl.example").read_bytes()),
        ("init", ["init", "-backend=false", "-input=false", "-lockfile=readonly", "-no-color"], None),
        ("validate", ["validate", "-json"], None),
        ("mock-test", ["test", "-no-color"], None),
    ]
    print("Evidence: " + str(out), flush=True)
    try:
        for name, argv, stdin in steps:
            if snapshot(root) != expected or snapshot(work) != expected:
                raise ValueError("Source changed before " + name)
            started = now()
            timeout = False
            try:
                proc = subprocess.run([str(binary), *argv], cwd=work, env=env,
                                      input=stdin, capture_output=True, timeout=300)
                rc, stdout, stderr = proc.returncode, proc.stdout, proc.stderr
            except subprocess.TimeoutExpired as exc:
                rc, stdout, stderr = None, exc.stdout or b"", exc.stderr or b""
                timeout = True
            (out / (name + ".stdout")).write_bytes(stdout)
            (out / (name + ".stderr")).write_bytes(stderr)
            record = {
                "name": name, "argv": [str(binary), *argv], "exit_code": rc,
                "started_at_utc": started, "finished_at_utc": now(), "timeout": timeout,
                "stdout_sha256": sha(out / (name + ".stdout")),
                "stderr_sha256": sha(out / (name + ".stderr")),
            }
            summary["records"].append(record)
            print(json.dumps({"step": name, "exit_code": rc}), flush=True)
            if rc != 0:
                raise ValueError(name + " failed; preserve stdout/stderr")
            if snapshot(root) != expected or snapshot(work) != expected:
                raise ValueError("Source changed after " + name)
            if name == "version":
                version = json.loads(stdout)
                if (version["terraform_version"] != "1.16.4" or
                        version["provider_selections"].get("registry.terraform.io/hashicorp/aws") != "6.66.0"):
                    raise ValueError("Unexpected CLI/provider version")
            if name == "validate":
                validation = json.loads(stdout)
                if not validation["valid"] or validation["error_count"] or validation["warning_count"]:
                    raise ValueError("Validation is not valid with zero errors/warnings")
            if name == "mock-test":
                count = manifest["components"][args.component]["mock_tests"]
                if f"{count} passed, 0 failed." not in stdout.decode("utf-8"):
                    raise ValueError("Unexpected mock test result/count")
        summary["pass"] = True
    except Exception as exc:
        summary["failure"] = str(exc)
    finally:
        summary["finished_at_utc"] = now()
        try:
            summary["source_after"] = snapshot(root)
            summary["copy_after"] = snapshot(work)
            summary["source_unchanged"] = summary["source_after"] == expected == summary["copy_after"]
        except Exception as exc:
            summary["source_unchanged"] = False
            summary["integrity_error"] = str(exc)
        summary["pass"] = summary["pass"] and summary["source_unchanged"]
        (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        logs = {p.name: sha(p) for p in sorted(out.iterdir()) if p.is_file()}
        (out / "capture-manifest.json").write_text(json.dumps(logs, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"pass": summary["pass"], "summary": str(out / "summary.json")}), flush=True)
    return 0 if summary["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
