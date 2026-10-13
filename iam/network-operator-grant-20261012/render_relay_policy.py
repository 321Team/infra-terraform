#!/usr/bin/env python3
"""FDS-Network-Operator Relay 정책 렌더러 — 템플릿의 __RELAY_INSTANCE_ID__를 실제 Relay ID로 채운다.

AWS를 호출하지 않는다. 입력 ID가 실제 Relay인지는 README "채우기 전 readback"으로 따로 확인한다.

사용: python3 render_relay_policy.py i-0123456789abcdef0 [--out DIR]
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TEMPLATE = REPO / "iam/full-policy-draft-20261009/policies/FDS-Network-Operator-Relay.template.json"
TEMPLATE_SHA256 = "bf6bb817c15633253023f449134331ddf6d8d8e430b0cea8aab9997649f62122"
PLACEHOLDER = "__RELAY_INSTANCE_ID__"
PLACEHOLDER_COUNT = 5
INSTANCE_ID = re.compile(r"^i-[0-9a-f]{17}$")
MANAGED_POLICY_LIMIT = 6144  # AWS 관리형 정책 크기(공백 제외)


class Stop(Exception):
    pass


def render(instance_id: str) -> bytes:
    if not INSTANCE_ID.fullmatch(instance_id):
        raise Stop(f"instance ID 형식 아님: {instance_id!r} (i- + 소문자 hex 17자리)")
    raw = TEMPLATE.read_bytes()
    if hashlib.sha256(raw).hexdigest() != TEMPLATE_SHA256:
        raise Stop("템플릿 SHA256 불일치 — 리뷰된 템플릿이 아님")
    text = raw.decode("utf-8")
    if text.count(PLACEHOLDER) != PLACEHOLDER_COUNT:
        raise Stop(f"자리표시자 개수 {text.count(PLACEHOLDER)} != {PLACEHOLDER_COUNT}")
    out = text.replace(PLACEHOLDER, instance_id)
    if "__" in out:
        raise Stop("채워지지 않은 자리표시자가 남음")
    doc = json.loads(out)
    arn = f"arn:aws:ec2:ap-northeast-2:774055931866:instance/{instance_id}"
    used = json.dumps(doc)
    if used.count(arn) != 4:
        raise Stop(f"Relay instance ARN 사용 횟수 {used.count(arn)} != 4")
    if "instance/*" in used:
        raise Stop("instance 와일드카드가 있음")
    if len(re.sub(r"\s", "", out)) > MANAGED_POLICY_LIMIT:
        raise Stop("관리형 정책 크기 초과")
    return out.encode("utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("instance_id")
    ap.add_argument("--out", type=Path, default=Path("."))
    a = ap.parse_args(argv)
    try:
        body = render(a.instance_id)
    except Stop as e:
        print("STOP:", e, file=sys.stderr)
        return 1
    a.out.mkdir(parents=True, exist_ok=True)
    p = a.out / f"FDS-Network-Operator-Relay.{a.instance_id}.json"
    p.write_bytes(body)
    print(f"{hashlib.sha256(body).hexdigest()}  {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
