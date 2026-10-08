#!/usr/bin/env bash
# Disposable package-userland test only. No services, AWS, host networking or credentials.
set -euo pipefail
umask 077
export LC_ALL=C
exec > >(tee /evidence/commands.log) 2>&1
trap 'rc=$?; printf "%s\n" "$rc" > /evidence/exit-code.txt; sha256sum /source/terraform/vpn/bootstrap.sh.tftpl /source/terraform/vpn/amazon-ssm-agent.gpg > /evidence/source-sha256.txt' EXIT
cat /etc/os-release
test "$(uname -m)" = x86_64
dnf -y --setopt=*.gpgcheck=1 --setopt=*.sslverify=1 install gnupg2 crypto-policies-scripts python3
policy=$(update-crypto-policies --show)
printf 'CRYPTO_POLICY=%s\n' "$policy"
test "$policy" = DEFAULT
rpm --version
gpg --version
python3 - <<'PY'
from pathlib import Path
source = Path('/source/terraform/vpn/bootstrap.sh.tftpl').read_text()
start = source.index('agent_version=')
end = source.index('systemctl enable --now amazon-ssm-agent.service')
block = source[start:end].replace('${agent_signing_key}', Path('/source/terraform/vpn/amazon-ssm-agent.gpg').read_text()).replace('%%{', '%{')
Path('/evidence/exact-package-block.sh').write_text('set -euo pipefail\numask 077\nexport LC_ALL=C\nretry() { "$@"; }\n' + block)
PY
bash -n /evidence/exact-package-block.sh
# Run the actual version/hash/key/verify/install block, not an independently rewritten installer.
set +e
bash -x /evidence/exact-package-block.sh > /evidence/package-block.log 2>&1
rc=$?
set -e
cat /evidence/package-block.log
printf '%s\n' "$rc" > /evidence/package-block.exit-code.txt
# Always capture the reviewer's original commands; their failures are diagnostic data.
work=$(find /var/tmp -maxdepth 1 -type d -name 'fds-agent-*' | head -1)
if test -n "$work" && test -f "$work/agent.rpm"; then
  set +e
  rpm --import "$work/signer.asc" > /evidence/rpm-import.log 2>&1
  printf '%s\n' "$?" > /evidence/rpm-import.exit-code.txt
  rpm -Kv "$work/agent.rpm" > /evidence/rpm-check.log 2>&1
  printf '%s\n' "$?" > /evidence/rpm-check.exit-code.txt
  dnf install --assumeno --setopt=localpkg_gpgcheck=1 "$work/agent.rpm" > /evidence/original-dnf-assumeno.log 2>&1
  printf '%s\n' "$?" > /evidence/original-dnf-assumeno.exit-code.txt
  set -e
  cat /evidence/rpm-import.log /evidence/rpm-check.log /evidence/original-dnf-assumeno.log
  sha256sum "$work/agent.rpm" "$work/agent.rpm.sig" > /evidence/download-sha256.txt
  cp "$work/signature.status" /evidence/signature.status
fi
test "$rc" -eq 0
test "$(rpm -q --queryformat '%{VERSION}' amazon-ssm-agent)" = 3.3.5390.0
test "$(update-crypto-policies --show)" = DEFAULT
printf 'PACKAGE_USERLAND=PASS; SERVICES_AND_AMI_RUNTIME=NOT_RUN; AWS=NOT_RUN\n'
