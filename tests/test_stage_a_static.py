import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("static_check", ROOT / "scripts/validate-stage-a.py")
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)


class StaticTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.parent = Path(self.tmp.name)
        self.root = self.parent / "repo"
        shutil.copytree(ROOT / "terraform", self.root / "terraform")
        (self.root / check.MANIFEST).parent.mkdir(parents=True)
        shutil.copy2(ROOT / check.MANIFEST, self.root / check.MANIFEST)
        self.binary = self.parent / "terraform"
        self.binary.write_text("test-double\n")
        self.binary.chmod(0o700)
        self.calls = []

    def runner(self, argv, **kwargs):
        self.calls.append((argv[1:], kwargs))
        args = argv[1:]
        if args[0] == "version":
            value = {"terraform_version": "1.16.4", "platform": "linux_amd64",
                     "provider_selections": {"registry.terraform.io/hashicorp/aws": "6.66.0"}}
        elif args[0] == "validate":
            value = {"valid": True, "error_count": 0, "warning_count": 0, "diagnostics": []}
        else:
            value = None
        if value is not None:
            kwargs["stdout"].write(json.dumps(value).encode())
        return subprocess.CompletedProcess(argv, 0)

    def execute(self, runner=None):
        return check.run_validation(self.root, self.binary, self.parent,
                                    inherited={"PATH": os.environ["PATH"],
                                               "AWS_SECRET_ACCESS_KEY": "must-not-leak",
                                               "TF_CLI_ARGS_init": "-migrate-state",
                                               "TF_LOG": "TRACE",
                                               "TF_PLUGIN_CACHE_DIR": "/external"},
                                    runner=runner or self.runner)

    def test_static_flow_is_isolated_exact_commands_and_no_credentials(self):
        rc, capture, report = self.execute()
        self.assertEqual(rc, 0)
        self.assertEqual(report["TerraformStatic"], "PASS")
        commands = [args for args, _ in self.calls]
        self.assertEqual(commands[0], ["version", "-json"])
        self.assertIn(["init", "-backend=false", "-lockfile=readonly", "-input=false", "-no-color"], commands)
        self.assertEqual(commands[-1], ["validate", "-json"])
        self.assertEqual(sum(args[0] == "fmt" for args in commands), 6)
        self.assertTrue(all(args[0] in {"version", "fmt", "init", "validate"} for args in commands))
        for _, kwargs in self.calls:
            self.assertEqual(kwargs["cwd"], capture / "source/terraform/stage-a")
            self.assertNotIn("AWS_SECRET_ACCESS_KEY", kwargs["env"])
            self.assertNotIn("TF_CLI_ARGS_init", kwargs["env"])
            self.assertNotIn("TF_LOG", kwargs["env"])
            self.assertNotIn("TF_PLUGIN_CACHE_DIR", kwargs["env"])
            self.assertEqual(kwargs["env"]["TF_WORKSPACE"], "default")
        self.assertNotIn("must-not-leak", (capture / "summary.json").read_text())
        self.assertEqual(capture.stat().st_mode & 0o777, 0o700)
        self.assertTrue((capture / "SHA256SUMS").is_file())

    def test_tamper_or_unclean_source_never_calls_terraform(self):
        target = self.root / "terraform/stage-a/providers.tf"
        target.write_text(target.read_text() + "# drift\n")
        self.assertEqual(self.execute()[0], 1)
        self.assertFalse(self.calls)

    def test_unexpected_state_and_symlink_stop_before_commands(self):
        (self.root / "terraform/stage-a/terraform.tfstate").write_text("private")
        self.assertEqual(self.execute()[0], 1)
        self.assertFalse(self.calls)
        (self.root / "terraform/stage-a/terraform.tfstate").unlink()
        file = self.root / "terraform/stage-a/providers.tf"
        external = self.parent / "external"
        file.rename(external)
        file.symlink_to(external)
        self.assertEqual(self.execute()[0], 1)
        self.assertFalse(self.calls)

    def test_wrong_cli_version_stops_before_fmt_or_init(self):
        def runner(argv, **kwargs):
            self.calls.append(argv)
            kwargs["stdout"].write(b'{"terraform_version":"1.15.0"}')
            return subprocess.CompletedProcess(argv, 0)
        self.assertEqual(self.execute(runner)[0], 1)
        self.assertEqual(len(self.calls), 1)

    def test_init_error_and_timeout_preserve_logs_and_no_validate(self):
        for timeout in (False, True):
            self.calls = []
            def runner(argv, **kwargs):
                if argv[1] == "init":
                    self.calls.append((argv[1:], kwargs))
                    kwargs["stderr"].write(b"partial failure")
                    if timeout:
                        raise subprocess.TimeoutExpired(argv, 180)
                    return subprocess.CompletedProcess(argv, 1)
                return self.runner(argv, **kwargs)
            rc, capture, report = self.execute(runner)
            self.assertEqual(rc, 1)
            self.assertNotIn("validate", [args[0] for args, _ in self.calls])
            self.assertEqual(report["TerraformStatic"], "INCOMPLETE")
            self.assertTrue(any(p.read_bytes() == b"partial failure" for p in capture.glob("*.stderr")))

    def test_lock_drift_stops_even_when_init_returns_zero(self):
        def runner(argv, **kwargs):
            if argv[1] == "init":
                (kwargs["cwd"] / ".terraform.lock.hcl").write_text("changed")
            return self.runner(argv, **kwargs)
        self.assertEqual(self.execute(runner)[0], 1)
        self.assertNotIn("validate", [args[0] for args, _ in self.calls])

    def test_provider_version_and_invalid_json_cannot_be_pass(self):
        for kind in ("provider", "json", "invalid"):
            self.calls = []
            def runner(argv, **kwargs):
                if kind == "provider" and argv[1] == "version" and len(self.calls) > 0:
                    self.calls.append((argv[1:], kwargs))
                    kwargs["stdout"].write(b'{"terraform_version":"1.16.4","provider_selections":{}}')
                    return subprocess.CompletedProcess(argv, 0)
                if kind in {"json", "invalid"} and argv[1] == "validate":
                    self.calls.append((argv[1:], kwargs))
                    kwargs["stdout"].write(b"truncated" if kind == "json" else b'{"valid":false,"error_count":1,"diagnostics":[]}')
                    return subprocess.CompletedProcess(argv, 0)
                return self.runner(argv, **kwargs)
            self.assertEqual(self.execute(runner)[0], 1)

    def test_missing_binary_is_not_run_with_report(self):
        self.binary.unlink()
        rc, capture, report = self.execute()
        self.assertEqual(rc, 1)
        self.assertEqual(report["TerraformStatic"], "NOT_RUN")
        self.assertTrue((capture / "summary.json").is_file())


if __name__ == "__main__":
    unittest.main()
