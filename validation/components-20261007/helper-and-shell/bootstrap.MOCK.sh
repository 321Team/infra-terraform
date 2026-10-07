#!/bin/bash
# LOCAL CANDIDATE: contains no tunnel config, PSK, credentials or remote script fetch.
set -euo pipefail
umask 077
test "$(id -u)" = 0
test -f /etc/redhat-release
command -v dnf >/dev/null
test "$(getenforce)" = Enforcing
systemctl is-active --quiet firewalld

# Proposed fail-closed bootstrap boundary: #37 enables forwarding only after
# accepted XFRM/firewall/plaintext-deny rules. Do not declare tunnel readiness.
printf 'net.ipv4.ip_forward = 0\n' > /etc/sysctl.d/90-fds-relay-bootstrap.conf
sysctl -w net.ipv4.ip_forward=0

# EIP association is later than instance launch. Use bounded package retries.
installed=false
for attempt in $(seq 1 20); do
  if dnf -y --setopt=timeout=15 --setopt=retries=1 install 'libreswan-0.0.0-0.TEST_ONLY'; then
    installed=true
    break
  fi
  sleep 15
done
test "$installed" = true
command -v ipsec >/dev/null
rpm -q libreswan
# No unsigned/unpinned Agent installer fallback. Missing Agent is a handoff STOP.
systemctl cat amazon-ssm-agent.service >/dev/null
systemctl enable --now amazon-ssm-agent.service
systemctl is-active --quiet amazon-ssm-agent.service
printf 'FDS_RELAY_BOOTSTRAP=LOCAL_SERVICE_CHECKS_COMPLETE\n'
printf 'AGENT_ONLINE=NOT_VERIFIED; FORWARDING=DISABLED; TUNNEL=NOT_CONFIGURED\n'
