"""Local static check for the #9 IAM draft. No AWS call.

usage: py -3 -I check_draft.py [infra-terraform root]  (default: this repo)
"""
import hashlib
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
MANAGED_POLICY_LIMIT = 6144  # AWS managed policy size, whitespace excluded

# Inventory APIs deliberately not granted; reason is printed in the report.
EXCLUDED = {
    "ec2:DetachNetworkInterface": "cleanup exception (service ENI) - owner path first",
    "ec2:DeleteNetworkInterface": "cleanup exception (service ENI) - owner path first",
    "ec2:DescribeVpcEndpoints": "GuardDuty endpoint cleanup exception only",
    "ec2:ModifyVpcEndpoint": "GuardDuty endpoint cleanup exception only",
    "ec2:DeleteVpcEndpoints": "GuardDuty endpoint cleanup exception only",
    "ssm:RemoveTagsFromResource": "session document tags kept; prevent_destroy",
}


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def actions_of(stmt):
    a = stmt.get("Action", [])
    return [a] if isinstance(a, str) else a


def granted(policies):
    out = set()
    for doc in policies.values():
        for s in doc["Statement"]:
            if s["Effect"] == "Allow":
                out.update(actions_of(s))
    return out


def main():
    infra = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else HERE.parents[1]
    inv = load(infra / "validation/components-20261007/resource-api-inventory.json")
    sup = load(infra / "docs/preflight-20261007/network-permission-supplement.json")

    needed = set()
    for r in inv["rows"]:
        needed.update(r["api_candidates"])
    for r in sup["rows"]:
        for k in ("create", "read", "update", "delete"):
            needed.update(r.get(k, []))
    for d in sup["data_sources"]:
        needed.update(d["actions"])
    needed.update(sup["shared_tag_lifecycle"]["actions"])
    for c in sup["conditional_paths_not_default_grants"]:
        needed.update(c["actions"])
    nat = load(HERE / "nat-permission-supplement.json")
    for r in nat["rows"]:
        for k in ("create", "read", "update", "delete"):
            needed.update(r.get(k, []))

    iac_files = ["FDS-IaC-State-PassRole", "FDS-IaC-Network", "FDS-IaC-Vpn", "FDS-IaC-Guardrails"]
    iac = {n: load(HERE / "policies" / f"{n}.json") for n in iac_files}
    have = granted(iac)

    fail = False
    print("== size (whitespace excluded, limit %d) ==" % MANAGED_POLICY_LIMIT)
    for p in sorted((HERE / "policies").glob("*.json")) + sorted((HERE / "trust").glob("*.json")):
        doc = load(p)
        size = len(re.sub(r"\s", "", p.read_text(encoding="utf-8")))
        sids = [s.get("Sid") for s in doc["Statement"]]
        dup = len(sids) != len(set(sids))
        bad = size > MANAGED_POLICY_LIMIT or dup
        fail |= bad
        print(f"{'FAIL' if bad else 'ok  '} {p.parent.name}/{p.name} size={size} stmts={len(sids)}"
              f" sha256={hashlib.sha256(p.read_bytes()).hexdigest()[:12]}")

    print("== inventory coverage (IaC role) ==")
    for a in sorted(needed):
        if a in have:
            continue
        if a in EXCLUDED:
            print(f"excluded  {a}: {EXCLUDED[a]}")
        else:
            print(f"MISSING   {a}")
            fail = True
    extra = sorted(have - needed)
    print("== granted beyond inventory (review reason in README) ==")
    for a in extra:
        print(f"extra     {a}")
    wildcard = [a for a in have if a.endswith(":*") or a == "*"]
    if wildcard:
        print("FAIL wildcard actions:", wildcard)
        fail = True
    print("RESULT", "FAIL" if fail else "PASS")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
