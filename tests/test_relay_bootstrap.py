"""Execute the rendered shell with command doubles and redirected filesystem paths.

MOCK only: no Linux services/packages/AWS are touched. Set FDS_TEST_BASH to Bash.
Real AWS signer verification is a separate recorded check, not mocked evidence.
"""
import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BASH = os.environ.get("FDS_TEST_BASH")


def shell_path(path):
    value = Path(path).resolve().as_posix()
    return "/" + value[0].lower() + value[2:] if os.name == "nt" else value


DOUBLES = r'''
id() { echo 0; }
uname() { echo x86_64; }
getenforce() { if [ "$CASE" = permissive ]; then echo Permissive; else echo Enforcing; fi; }
sysctl() { if [ "$1" = -n ]; then echo 0; fi; }
sleep() { :; }
dnf() {
  echo "dnf $*" >> "$EVENTS"
  if [ "$CASE" = repo_fail ]; then return 1; fi
}
systemctl() {
  echo "systemctl $*" >> "$EVENTS"
  if [ "$CASE" = firewall_fail ] && [[ "$*" == *firewalld* ]]; then return 1; fi
  if [ "$CASE" = agent_fail ] && [[ "$*" == *amazon-ssm-agent* ]]; then return 1; fi
  return 0
}
ipsec() { :; }
rpm() {
  echo "rpm $*" >> "$EVENTS"
  if [ "$1" = -qp ]; then
    if [ "$CASE" = wrong_package ]; then echo 'other 3.3.5390.0 x86_64'; else echo 'amazon-ssm-agent 3.3.5390.0 x86_64'; fi
  elif [[ "$*" == *queryformat* ]] && [[ "$*" == *libreswan* ]]; then
    if [ "$CASE" = wrong_libreswan ]; then echo libreswan-99.0-1; else echo libreswan-0.0.0-0.TEST_ONLY; fi
  elif [[ "$*" == *queryformat* ]]; then
    if [ "$CASE" = installed_version ]; then echo 0.0.0; else echo 3.3.5390.0; fi
  fi
}
curl() {
  echo "curl $*" >> "$EVENTS"
  if [ "$CASE" = download_fail ]; then return 1; fi
  while [ "$#" -gt 0 ]; do
    if [ "$1" = -o ]; then shift; printf 'MOCK' > "$1"; fi
    shift
  done
}
sha256sum() {
  cat >/dev/null
  echo hash-check >> "$EVENTS"
  [ "$CASE" != hash_fail ]
}
gpg() {
  echo "gpg $*" >> "$EVENTS"
  if [[ "$*" == *--show-keys* ]]; then
    if [ "$CASE" = wrong_key ]; then echo 'fpr:::::::::BAD:'; else echo 'fpr:::::::::1C5B395CBE5E74E2F1CA21592784DBF388D19D46:'; fi
  elif [[ "$*" == *--verify* ]]; then
    if [ "$CASE" = signature_fail ]; then return 1; fi
    if [ "$CASE" = wrong_signer ]; then echo '[GNUPG:] VALIDSIG BAD'; else echo '[GNUPG:] VALIDSIG 1C5B395CBE5E74E2F1CA21592784DBF388D19D46'; fi
  fi
  return 0
}
'''


class BootstrapTests(unittest.TestCase):
    def execute(self, case):
        if not BASH:
            self.fail("FDS_TEST_BASH must name the local Bash executable; not a Runtime test")
        with tempfile.TemporaryDirectory(prefix="fds-bootstrap-mock-") as tmp:
            work = Path(tmp)
            (work / "etc/sysctl.d").mkdir(parents=True)
            (work / "var/tmp").mkdir(parents=True)
            (work / "etc/os-release").write_text("ID=centos\nVERSION_ID=9\n", encoding="utf-8")
            source = (ROOT / "terraform/vpn/bootstrap.sh.tftpl").read_text(encoding="utf-8")
            # Only these two template inputs exist; Terraform's templatefile rendering
            # is also exercised by the separate provider MOCK plans.
            source = source.replace("${libreswan_package_spec}", "libreswan-0.0.0-0.TEST_ONLY")
            source = source.replace("${agent_signing_key}", "MOCK_PUBLIC_KEY_NOT_CRYPTO_EVIDENCE").replace("%%{", "%{")
            source = source.replace("/etc/", shell_path(work / "etc") + "/")
            source = source.replace("/var/tmp/", shell_path(work / "var/tmp") + "/")
            script = work / "bootstrap.mock.sh"
            script.write_bytes(("CASE=" + shlex.quote(case) + "\nEVENTS=" + shlex.quote(shell_path(work / "events")) + "\n" + DOUBLES + source).encode())
            env = {k: v for k, v in os.environ.items() if k.upper() in {"PATH", "SYSTEMROOT", "TEMP", "TMP", "WINDIR"}}
            env.update(HOME=shell_path(work), BASH_ENV="", ENV="")
            result = subprocess.run([BASH, "--noprofile", "--norc", shell_path(script)], env=env, capture_output=True, timeout=15)
            events = (work / "events").read_text() if (work / "events").exists() else ""
            return result, events

    def test_success_orders_verification_before_install_and_start(self):
        result, events = self.execute("success")
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertIn(b"AGENT_ONLINE=NOT_VERIFIED", result.stdout)
        self.assertLess(events.index("hash-check"), events.index("--verify"))
        self.assertLess(events.index("--verify"), events.index("localpkg_gpgcheck=1"))
        self.assertLess(events.index("localpkg_gpgcheck=1"), events.index("enable --now amazon-ssm-agent"))
        self.assertNotIn("ip_forward=1", events)

    def test_failures_stop_before_unverified_agent_install(self):
        for case in ["permissive", "repo_fail", "firewall_fail", "wrong_libreswan", "wrong_key", "download_fail", "hash_fail", "signature_fail", "wrong_signer", "wrong_package"]:
            with self.subTest(case=case):
                result, events = self.execute(case)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("localpkg_gpgcheck=1", events)
                self.assertNotIn("enable --now amazon-ssm-agent", events)
                self.assertNotIn(b"LOCAL_SERVICE_CHECKS_COMPLETE", result.stdout)

    def test_post_install_failures_never_claim_success(self):
        for case in ["installed_version", "agent_fail"]:
            with self.subTest(case=case):
                result, events = self.execute(case)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn(b"LOCAL_SERVICE_CHECKS_COMPLETE", result.stdout)
                self.assertIn("localpkg_gpgcheck=1", events)


if __name__ == "__main__":
    unittest.main()
