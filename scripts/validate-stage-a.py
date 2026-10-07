#!/usr/bin/env python3
"""Validate the pinned scaffold in a private copy; never run AWS/plan/apply."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = "validation/stage-a-20261007/source.json"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_source(root, manifest):
    files = manifest["Files"]
    stage = {p.name for p in (root / "terraform/stage-a").iterdir()}
    expected = {Path(p).name for p in files if p.startswith("terraform/stage-a/")}
    if stage != expected:
        raise ValueError("stage-a contains missing or unexpected files; use the clean package")
    for name, sha in files.items():
        p = root / name
        if p.is_symlink() or not p.is_file() or digest(p) != sha:
            raise ValueError("pinned source mismatch: " + name)


def child_environment(capture, inherited):
    # No AWS credentials, CLI arguments, plugin overrides, logs or user config.
    env = {key: inherited[key] for key in (
        "PATH", "LANG", "LC_ALL", "HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY",
        "http_proxy", "https_proxy", "no_proxy", "SSL_CERT_FILE", "SSL_CERT_DIR",
    ) if key in inherited}
    home = capture / "isolated-home"
    home.mkdir(mode=0o700)
    config = capture / "terraform.rc"
    config.write_text("disable_checkpoint = true\n")
    env.update(HOME=str(home), TF_CLI_CONFIG_FILE=str(config),
               TF_DATA_DIR=str(capture / "terraform-data"), TF_WORKSPACE="default",
               TF_INPUT="0", TF_IN_AUTOMATION="1", CHECKPOINT_DISABLE="1",
               AWS_EC2_METADATA_DISABLED="true")
    return env


def run_validation(root, binary, output_parent, inherited=None, runner=subprocess.run):
    os.umask(0o077)
    capture = Path(tempfile.mkdtemp(prefix="fds-stage-a-static-", dir=output_parent)).resolve()
    summary = {"UTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
               "Scope": "ISOLATED_SCAFFOLD_STATIC_ONLY", "Status": "STOP",
               "TerraformStatic": "NOT_RUN", "AWS_MUTATION": "NOT_RUN",
               "ROLE_GRANT": "NOT_RUN", "PLAN": "NOT_RUN", "APPLY": "NOT_RUN",
               "USER_RUNTIME": "NOT_TESTED", "STAGE_A_READINESS": "NOT_ASSESSED",
               "Steps": []}
    rc = 1
    try:
        manifest = json.loads((root / MANIFEST).read_text())
        summary["CandidateHead"] = manifest["CandidateHead"]
        summary["SourceManifestSHA256"] = digest(root / MANIFEST)
        summary["HelperSHA256"] = digest(Path(__file__))
        verify_source(root, manifest)
        copy_root = capture / "source"
        for name in manifest["Files"]:
            target = copy_root / name
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            shutil.copy2(root / name, target)
        shutil.copy2(root / MANIFEST, capture / "source.json")
        shutil.copy2(Path(__file__), capture / "validator.py")
        verify_source(copy_root, manifest)
        executable = Path(binary).expanduser().resolve(strict=True)
        if not executable.is_file() or not os.access(executable, os.X_OK):
            raise ValueError("Terraform executable is unavailable")
        summary["TerraformBinarySHA256"] = digest(executable)
        env = child_environment(capture, inherited if inherited is not None else os.environ)
        stage = copy_root / "terraform/stage-a"

        def step(label, args, stdin=None, timeout=30):
            n = len(summary["Steps"]) + 1
            record = {"Label": label, "Args": args, "RC": None, "Timeout": False}
            summary["Steps"].append(record)
            stdout = capture / f"{n:02d}-{label}.stdout"
            stderr = capture / f"{n:02d}-{label}.stderr"
            with stdout.open("wb") as out, stderr.open("wb") as err:
                try:
                    result = runner([str(executable), *args], cwd=stage, env=env,
                                    input=stdin, stdout=out, stderr=err, timeout=timeout,
                                    check=False)
                    record["RC"] = result.returncode
                except subprocess.TimeoutExpired:
                    record["Timeout"] = True
                    raise ValueError(label + " timed out; partial logs preserved")
            verify_source(root, manifest)
            verify_source(copy_root, manifest)
            if record["RC"] != 0:
                raise ValueError(label + " failed; inspect private logs")
            return stdout

        version = json.loads(step("version", ["version", "-json"]).read_text())
        if version.get("terraform_version") != "1.16.4":
            raise ValueError("Terraform version must be exactly 1.16.4")
        summary["TerraformVersion"] = version["terraform_version"]
        summary["TerraformPlatform"] = version.get("platform")
        step("fmt", ["fmt", "-check", "-recursive", "-no-color"])
        # Directory fmt does not cover .example files. Check their literal HCL via stdin.
        examples = ["terraform/stage-a/terraform.tfvars.example"] + sorted(
            p for p in manifest["Files"] if p.startswith("terraform/backends/"))
        for index, name in enumerate(examples, 1):
            step(f"fmt-example-{index}", ["fmt", "-check", "-no-color", "-"],
                 stdin=(copy_root / name).read_bytes())
        step("init", ["init", "-backend=false", "-lockfile=readonly", "-input=false",
                      "-no-color"], timeout=180)
        selected = json.loads(step("provider-version", ["version", "-json"]).read_text())
        if selected.get("provider_selections", {}).get("registry.terraform.io/hashicorp/aws") != "6.66.0":
            raise ValueError("AWS provider selection must be exactly 6.66.0")
        result = json.loads(step("validate", ["validate", "-json"]).read_text())
        if (result.get("valid") is not True
                or type(result.get("error_count")) is not int or result["error_count"] != 0
                or type(result.get("warning_count")) is not int or result["warning_count"] < 0
                or not isinstance(result.get("diagnostics"), list)
                or any(not isinstance(d, dict) or d.get("severity") == "error"
                       for d in result["diagnostics"])):
            raise ValueError("validate JSON does not confirm valid=true and zero errors")
        summary["WarningCount"] = result.get("warning_count")
        summary["ProviderVersion"] = "6.66.0"
        summary["LockAndSourceUnchanged"] = "PASS"
        summary["TerraformStatic"] = "PASS"
        summary["Status"] = "COMPLETE"
        rc = 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        summary["StopReason"] = str(exc)
        if summary["Steps"]:
            summary["TerraformStatic"] = "INCOMPLETE"
    finally:
        (capture / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        # Capture only source/provenance and logs, not downloaded provider binaries.
        evidence = [capture / "summary.json", capture / "terraform.rc",
                    capture / "source.json", capture / "validator.py"]
        evidence += list(capture.glob("*.stdout")) + list(capture.glob("*.stderr"))
        evidence += list((capture / "source").rglob("*")) if (capture / "source").exists() else []
        lines = [f"{digest(p)}  ./{p.relative_to(capture)}\n"
                 for p in sorted(evidence) if p.is_file()]
        (capture / "SHA256SUMS").write_text("".join(lines))
    return rc, capture, summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--terraform", default=str(Path.home() / "bin/terraform"))
    args = parser.parse_args()
    rc, capture, summary = run_validation(ROOT, args.terraform, Path.home())
    print("CAPTURE_DIR=" + str(capture))
    print(json.dumps(summary))
    print("STATIC_VALIDATION_RC=" + str(rc))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
