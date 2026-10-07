"""Offline checks for the credential and unreviewed-input boundaries."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/validate-components.py"
spec = importlib.util.spec_from_file_location("components", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class IsolationTests(unittest.TestCase):
    def test_parent_credentials_and_cli_overrides_are_not_inherited(self):
        contaminated = {
            "AWS_ACCESS_KEY_ID": "TEST_ONLY", "AWS_SECRET_ACCESS_KEY": "TEST_ONLY",
            "AWS_SESSION_TOKEN": "TEST_ONLY", "AWS_PROFILE": "TEST_ONLY",
            "AWS_WEB_IDENTITY_TOKEN_FILE": "/not-used", "AWS_CONTAINER_CREDENTIALS_FULL_URI": "https://invalid.invalid",
            "TF_CLI_ARGS": "-var-file=not-reviewed.tfvars", "TF_VAR_execution_enabled": "true",
            "TF_PLUGIN_CACHE_DIR": "/not-used", "HTTPS_PROXY": "https://invalid.invalid",
        }
        with patch.dict(os.environ, contaminated, clear=True):
            env = module.isolated_env(Path("isolated-home"), Path("isolated-data"))
        self.assertFalse(set(contaminated) & set(env))
        self.assertEqual(env["AWS_EC2_METADATA_DISABLED"], "true")
        self.assertEqual(env["AWS_CONFIG_FILE"], str(Path("isolated-home/config")))

    def rejected_before_binary_launch(self, modification):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            (repo / "scripts").mkdir()
            shutil.copyfile(SCRIPT, repo / "scripts/validate-components.py")
            root = repo / "terraform/network"
            root.mkdir(parents=True)
            original = b'# TEST ONLY\n'
            (root / "main.tf").write_bytes(original)
            manifest = repo / "validation/components-20261007/source.json"
            manifest.parent.mkdir(parents=True)
            manifest.write_text(json.dumps({"components": {"network": {"files": {
                "main.tf": hashlib.sha256(original).hexdigest()}}}}), encoding="utf-8")
            modification(root)
            # Non-executable sentinel: any attempt to launch it would be a different failure.
            sentinel = repo / "never-launch"
            sentinel.write_text("TEST ONLY", encoding="utf-8")
            proc = subprocess.run([sys.executable, str(repo / "scripts/validate-components.py"),
                                   "--component", "network", "--terraform", str(sentinel)],
                                  capture_output=True, timeout=15)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn(b"Source set/hash differs", proc.stderr)
            self.assertNotIn(b"Evidence:", proc.stdout)

    def test_extra_auto_tfvars_is_rejected_before_launch(self):
        self.rejected_before_binary_launch(lambda root: (root / "override.auto.tfvars").write_text("execution_enabled = true\n"))

    def test_changed_test_or_source_is_rejected_before_launch(self):
        self.rejected_before_binary_launch(lambda root: (root / "main.tf").write_text("# modified\n"))


if __name__ == "__main__":
    unittest.main()
