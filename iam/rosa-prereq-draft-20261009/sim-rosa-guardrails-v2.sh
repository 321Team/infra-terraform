#!/usr/bin/env bash
# #12 ROSA A1/A3 IaC 정책 + FDS-IaC-Guardrails 조합 시뮬레이션 (infra-terraform#12, PR21 rev2 2026-10-10)
# rev2: A3 IAM 쓰기(역할·정책·OIDC 생성/부착)를 IaC 역할에서 제거하고 중앙 실행으로 이관한 정책 기준.
#       실행자·계정 확인, live Guardrails MATCH, 호출 RC, case 수·고유 ID·MissingContextValues 계약을 성공 조건에 결속.
# 실행 위치: AWS CloudShell(서울). 기본 실행자 321team-hayeoung. 다른 승인 실행자는 EXPECTED_ARN 환경변수로 지정하고 기록에 남긴다.
# 필요 권한: sts:GetCallerIdentity, iam:SimulateCustomPolicy, iam:GetPolicy, iam:GetPolicyVersion
# 비용: 없음. 모의 계산과 정책 조회만. AWS 자원 생성/수정/삭제 0, 실제 Subscribe 0
# 종료코드: 0=전 case PASS / 1=case FAIL·도구·입력·identity 오류 / 2=live Guardrails가 승인 v1과 MATCH가 아님(읽기 실패 포함)
set -u -o pipefail
ACC=774055931866
EXPECTED_ARN="${EXPECTED_ARN:-arn:aws:iam::$ACC:user/321team-hayeoung}"
EXPECTED_CASES=35
EXPECTED_IDS="A01-v1-list-attached A02-v1-get-rosa-policy A03-v1-subscribe-rosa A04-v1-get-oidc S01-region-only B01-v2-get-role B02-v2-list-role-policies B03-v2-list-attached B04-v2-list-role-tags B05-v2-list-roles B06-v2-get-rosa-policy B07-v2-get-ecr-policy-version B08-v2-list-cli-policy-versions B09-v2-get-oidc B10-v2-list-oidc B11-v2-subscribe-rosa B12-v2-view-subscriptions W01-create-account-role W02-create-cli-role W03-create-prefixed-policy W04-attach-rosa-policy W05-attach-prefixed-cross W06-attach-admin W07-create-oidc W08-update-trust W09-delete-role W10-tag-role W11-pass-rosa-role N01-v2-create-account-role N02-v2-attach-rosa-policy N03-v2-unsubscribe-rosa N04-v2-subscribe-other N05-v2-ec2-us-east-1 N06-v2-read-other-role N07-v2-get-admin-policy"
OUT=$(mktemp -d "$HOME/sim-rosa-gr-$(date +%Y%m%d-%H%M%S)-XXXX") && chmod 700 "$OUT" && cd "$OUT" || { echo "STOP: cannot create result folder under $HOME" >&2; exit 1; }
kst(){ TZ=Asia/Seoul date '+%Y-%m-%dT%H:%M:%S%z'; }
finish(){ # $1=result $2=exit code
  echo "result=$1" >> meta.txt; echo "end_kst=$(kst)" >> meta.txt
  sha256sum -- * > SHA256SUMS 2>/dev/null || echo "WARN: SHA256SUMS write failed" >&2
  echo "result=$1 (exit $2) 결과 폴더: $OUT"; exit "$2"; }
stop(){ echo "STOP: $1" | tee -a meta.txt >&2; finish "STOP($1)" "${2:-1}"; }
echo "start_kst=$(kst)" > meta.txt || { echo "STOP: meta write failed" >&2; exit 1; }
for t in aws jq sha256sum awk cmp; do command -v "$t" >/dev/null || stop "missing_tool_$t"; done
echo "aws_cli=$(aws --version 2>&1)" >> meta.txt

# 1. 실행자·계정 확인 — 실패하면 계산하지 않는다
aws sts get-caller-identity --output json > 00-identity.json 2> 00-identity.err; rc=$?
echo "identity_rc=$rc" >> meta.txt
[ "$rc" -eq 0 ] || stop identity_call_failed
ACT_ACC=$(jq -er .Account 00-identity.json) || stop identity_parse
ACT_ARN=$(jq -er .Arn 00-identity.json) || stop identity_parse
echo "identity_account=$ACT_ACC identity_arn=$ACT_ARN expected_arn=$EXPECTED_ARN" >> meta.txt
[ "$ACT_ACC" = "$ACC" ] || stop identity_account_mismatch
[ "$ACT_ARN" = "$EXPECTED_ARN" ] || stop identity_arn_mismatch

# 2. 정책 원문 (PR21 rev2 파일과 같은 내용의 압축 JSON)
cat > gr-v1.json <<'J'
{"Version":"2012-10-17","Statement":[{"Sid":"DenyOutsideSeoul","Effect":"Deny","NotAction":["iam:GetRole","iam:GetInstanceProfile","iam:PassRole","sts:GetCallerIdentity"],"Resource":"*","Condition":{"StringNotEquals":{"aws:RequestedRegion":"ap-northeast-2"}}},{"Sid":"DenyRemovingOwnershipTags","Effect":"Deny","Action":"ec2:DeleteTags","Resource":"*","Condition":{"ForAnyValue:StringEquals":{"aws:TagKeys":["Project","ManagedBy"]}}},{"Sid":"DenyRetagProjectToOtherValue","Effect":"Deny","Action":"ec2:CreateTags","Resource":"*","Condition":{"Null":{"aws:RequestTag/Project":"false"},"StringNotEquals":{"aws:RequestTag/Project":"fds-hybrid"}}},{"Sid":"DenyRetagManagedByToOtherValue","Effect":"Deny","Action":"ec2:CreateTags","Resource":"*","Condition":{"Null":{"aws:RequestTag/ManagedBy":"false"},"StringNotEquals":{"aws:RequestTag/ManagedBy":"terraform"}}},{"Sid":"DenySessionDocumentChangeOrDelete","Effect":"Deny","Action":["ssm:UpdateDocument","ssm:UpdateDocumentDefaultVersion","ssm:DeleteDocument","ssm:ModifyDocumentPermission","ssm:SendCommand"],"Resource":"*"},{"Sid":"DenyCentralBootstrapStackChange","Effect":"Deny","NotAction":["cloudformation:Describe*","cloudformation:Get*","cloudformation:List*"],"Resource":"arn:aws:cloudformation:*:774055931866:stack/*"}]}
J
cat > gr-v2-file.json <<'J'
{"Version":"2012-10-17","Statement":[{"Sid":"DenyOutsideSeoul","Effect":"Deny","NotAction":["iam:GetRole","iam:GetInstanceProfile","iam:PassRole","sts:GetCallerIdentity","aws-marketplace:ViewSubscriptions","aws-marketplace:Subscribe","iam:ListRolePolicies","iam:ListAttachedRolePolicies","iam:ListRoleTags","iam:ListRoles","iam:GetPolicy","iam:GetPolicyVersion","iam:ListPolicyVersions","iam:GetOpenIDConnectProvider","iam:ListOpenIDConnectProviders"],"Resource":"*","Condition":{"StringNotEquals":{"aws:RequestedRegion":"ap-northeast-2"}}},{"Sid":"DenyRemovingOwnershipTags","Effect":"Deny","Action":"ec2:DeleteTags","Resource":"*","Condition":{"ForAnyValue:StringEquals":{"aws:TagKeys":["Project","ManagedBy"]}}},{"Sid":"DenyRetagProjectToOtherValue","Effect":"Deny","Action":"ec2:CreateTags","Resource":"*","Condition":{"Null":{"aws:RequestTag/Project":"false"},"StringNotEquals":{"aws:RequestTag/Project":"fds-hybrid"}}},{"Sid":"DenyRetagManagedByToOtherValue","Effect":"Deny","Action":"ec2:CreateTags","Resource":"*","Condition":{"Null":{"aws:RequestTag/ManagedBy":"false"},"StringNotEquals":{"aws:RequestTag/ManagedBy":"terraform"}}},{"Sid":"DenySessionDocumentChangeOrDelete","Effect":"Deny","Action":["ssm:UpdateDocument","ssm:UpdateDocumentDefaultVersion","ssm:DeleteDocument","ssm:ModifyDocumentPermission","ssm:SendCommand"],"Resource":"*"},{"Sid":"DenyCentralBootstrapStackChange","Effect":"Deny","NotAction":["cloudformation:Describe*","cloudformation:Get*","cloudformation:List*"],"Resource":"arn:aws:cloudformation:*:774055931866:stack/*"}]}
J
cat > rosa.json <<'J'
{"Version":"2012-10-17","Statement":[{"Sid":"ReadCallerIdentity","Effect":"Allow","Action":"sts:GetCallerIdentity","Resource":"*"},{"Sid":"ReadRosaRoles","Effect":"Allow","Action":["iam:GetRole","iam:ListRolePolicies","iam:ListAttachedRolePolicies","iam:ListRoleTags"],"Resource":"arn:aws:iam::774055931866:role/fds-rosa-*"},{"Sid":"ListRolesNoResourceLevel","Effect":"Allow","Action":"iam:ListRoles","Resource":"*"},{"Sid":"ReadRosaPolicies","Effect":"Allow","Action":["iam:GetPolicy","iam:GetPolicyVersion","iam:ListPolicyVersions"],"Resource":["arn:aws:iam::aws:policy/service-role/ROSA*","arn:aws:iam::774055931866:policy/fds-rosa-*","arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"]},{"Sid":"ReadRosaOidcProvider","Effect":"Allow","Action":"iam:GetOpenIDConnectProvider","Resource":"arn:aws:iam::774055931866:oidc-provider/oidc.op1.openshiftapps.com/*"},{"Sid":"ListOidcProvidersNoResourceLevel","Effect":"Allow","Action":"iam:ListOpenIDConnectProviders","Resource":"*"}]}
J
cat > sub.json <<'J'
{"Version":"2012-10-17","Statement":[{"Sid":"ViewMarketplaceSubscriptions","Effect":"Allow","Action":"aws-marketplace:ViewSubscriptions","Resource":"*"},{"Sid":"SubscribeRosaOnly","Effect":"Allow","Action":"aws-marketplace:Subscribe","Resource":"*","Condition":{"ForAnyValue:StringEquals":{"aws-marketplace:ProductId":["34850061-abaf-402d-92df-94325c9e947f","bfdca560-2c78-4e64-8193-794c159e6d30"]}}}]}
J
for f in gr-v1.json gr-v2-file.json rosa.json sub.json; do
  jq -e . "$f" > /dev/null || stop "embedded_policy_parse_$f"
  echo "policy_sha256 $f $(jq -S -c . "$f" | sha256sum | cut -d' ' -f1)" >> meta.txt || stop meta_write
done

# 후보 v2 = v1의 DenyOutsideSeoul NotAction에 A1/A3 조회·Subscribe Action 11개만 정확한 이름으로 추가
ADD='["aws-marketplace:ViewSubscriptions","aws-marketplace:Subscribe","iam:ListRolePolicies","iam:ListAttachedRolePolicies","iam:ListRoleTags","iam:ListRoles","iam:GetPolicy","iam:GetPolicyVersion","iam:ListPolicyVersions","iam:GetOpenIDConnectProvider","iam:ListOpenIDConnectProviders"]'
jq -c --argjson add "$ADD" '.Statement |= map(if .Sid=="DenyOutsideSeoul" then .NotAction = (.NotAction + $add) else . end)' gr-v1.json > gr-v2-candidate.json || stop v2_build
cmp -s <(jq -S -c . gr-v2-candidate.json) <(jq -S -c . gr-v2-file.json) || stop v2_candidate_file_mismatch
jq -c '.Statement |= map(select(.Sid=="DenyOutsideSeoul"))' gr-v1.json > gr-region-only.json || stop region_only_build

# 3. 실제 부착된 Guardrails가 승인 v1과 같아야 현재 조합 판정을 낸다
aws iam get-policy --policy-arn "arn:aws:iam::$ACC:policy/FDS-IaC-Guardrails" --query Policy.DefaultVersionId --output text > live-version.txt 2> live.err; rc=$?
echo "live_get_policy_rc=$rc" >> meta.txt
[ "$rc" -eq 0 ] || { echo "live_guardrails=UNREADABLE" >> meta.txt; stop live_guardrails_unreadable 2; }
V=$(tr -d '[:space:]' < live-version.txt)
[ -n "$V" ] || { echo "live_guardrails=UNREADABLE" >> meta.txt; stop live_guardrails_unreadable 2; }
aws iam get-policy-version --policy-arn "arn:aws:iam::$ACC:policy/FDS-IaC-Guardrails" --version-id "$V" --query PolicyVersion.Document --output json > gr-live.json 2>> live.err; rc=$?
echo "live_get_policy_version_rc=$rc" >> meta.txt
[ "$rc" -eq 0 ] || { echo "live_guardrails=UNREADABLE($V)" >> meta.txt; stop live_guardrails_unreadable 2; }
jq -e . gr-live.json > /dev/null || { echo "live_guardrails=UNREADABLE($V)" >> meta.txt; stop live_guardrails_parse 2; }
if cmp -s <(jq -S -c . gr-live.json) <(jq -S -c . gr-v1.json); then LIVE="MATCH($V)"; else LIVE="DIFF($V)"; fi
echo "live_guardrails=$LIVE" | tee -a meta.txt
[ "$LIVE" = "MATCH($V)" ] || stop live_guardrails_not_match 2

# 4. case 실행 — 호출 실패도 행으로 남기고 계속한다(마지막에 전체 판정)
printf 'case\taction\texpect\tactual\tresult\tmissing_context\n' > summary.tsv || stop summary_write
ctx(){ printf '{"ContextKeyName":"%s","ContextKeyValues":["%s"],"ContextKeyType":"%s"}' "$1" "$2" "${3:-string}"; }
R=$(ctx aws:RequestedRegion us-east-1)
OWN="$(ctx aws:RequestTag/Project fds-hybrid),$(ctx aws:RequestTag/ManagedBy terraform)"
PID="$(ctx aws-marketplace:ProductId 34850061-abaf-402d-92df-94325c9e947f stringList)"
ROLE=arn:aws:iam::$ACC:role; POL=arn:aws:iam::$ACC:policy; AWSPOL=arn:aws:iam::aws:policy
OIDC=arn:aws:iam::$ACC:oidc-provider/oidc.op1.openshiftapps.com/EXAMPLE
CUR="rosa.json sub.json gr-v1.json"; CAND="rosa.json sub.json gr-v2-candidate.json"; ONLY="rosa.json sub.json"

# MissingContextValues 계약: 모든 case는 판정에 필요한 context를 제공한다. rev2 정책에는 case와 무관한 조건 키가
# 남아 있지 않으므로 기대값은 case 전부 "빈 목록"이다. 하나라도 보고되면 그 case를 FAIL로 기록한다.
sim(){
  local c=$1 files=$2 a=$3 r=$4 exp=$5 cx=$6 pl rc act miss res
  if ! pl=$(for f in $files; do jq -c . "$f" | jq -Rs . || exit 1; done | jq -s .); then
    printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$c" "$a" "$exp" INPUT_ERROR FAIL - >> summary.tsv; echo "[FAIL] $c input"; return; fi
  if ! jq -n --arg a "$a" --arg r "$r" --argjson cx "[$cx]" --argjson pl "$pl" \
      '{PolicyInputList:$pl,ActionNames:[$a],ResourceArns:[$r],ContextEntries:$cx}' > "$c.input.json"; then
    printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$c" "$a" "$exp" INPUT_ERROR FAIL - >> summary.tsv; echo "[FAIL] $c input"; return; fi
  aws iam simulate-custom-policy --cli-input-json "file://$c.input.json" --output json > "$c.out.json" 2> "$c.err"; rc=$?
  if [ "$rc" -eq 0 ]; then
    act=$(jq -er '.EvaluationResults | if length==1 then .[0].EvalDecision else error("results") end' "$c.out.json") || act=PARSE_ERROR
    miss=$(jq -er '[.EvaluationResults[0].MissingContextValues[]?] | join(",")' "$c.out.json") || miss=PARSE_ERROR
  else act="RC$rc"; miss="-"; fi
  res=FAIL; [ "$act" = "$exp" ] && [ -z "$miss" ] && res=PASS
  printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$c" "$a" "$exp" "$act" "$res" "${miss:--}" >> summary.tsv || stop summary_write
  echo "[$res] $c expect=$exp actual=$act missing=${miss:--}"
}
# A. 현재 Guardrails v1에서 ROSA 조회·Subscribe가 리전 Deny에 막히는지(충돌 확인)
sim A01-v1-list-attached     "$CUR"  iam:ListAttachedRolePolicies "$ROLE/fds-rosa-HCP-ROSA-Installer-Role" explicitDeny "$R"
sim A02-v1-get-rosa-policy   "$CUR"  iam:GetPolicy "$AWSPOL/service-role/ROSAInstallerPolicy" explicitDeny "$R"
sim A03-v1-subscribe-rosa    "$CUR"  aws-marketplace:Subscribe '*' explicitDeny "$R,$PID"
sim A04-v1-get-oidc          "$CUR"  iam:GetOpenIDConnectProvider "$OIDC" explicitDeny "$R"
# S. 막는 Statement가 DenyOutsideSeoul인지 단독 확인
sim S01-region-only          "rosa.json gr-region-only.json" iam:ListAttachedRolePolicies "$ROLE/fds-rosa-HCP-ROSA-Installer-Role" explicitDeny "$R"
# B. 후보 v2에서 IaC 역할의 조회·Subscribe가 통과하는지
sim B01-v2-get-role          "$CAND" iam:GetRole "$ROLE/fds-rosa-HCP-ROSA-Installer-Role" allowed "$R"
sim B02-v2-list-role-policies "$CAND" iam:ListRolePolicies "$ROLE/fds-rosa-OCM-Role-EXAMPLE" allowed "$R"
sim B03-v2-list-attached     "$CAND" iam:ListAttachedRolePolicies "$ROLE/fds-rosa-HCP-ROSA-Worker-Role" allowed "$R"
sim B04-v2-list-role-tags    "$CAND" iam:ListRoleTags "$ROLE/fds-rosa-kube-system-kms-provider" allowed "$R"
sim B05-v2-list-roles        "$CAND" iam:ListRoles '*' allowed "$R"
sim B06-v2-get-rosa-policy   "$CAND" iam:GetPolicy "$AWSPOL/service-role/ROSAInstallerPolicy" allowed "$R"
sim B07-v2-get-ecr-policy-version "$CAND" iam:GetPolicyVersion "$AWSPOL/AmazonEC2ContainerRegistryReadOnly" allowed "$R"
sim B08-v2-list-cli-policy-versions "$CAND" iam:ListPolicyVersions "$POL/fds-rosa-OCM-Role-EXAMPLE-Policy" allowed "$R"
sim B09-v2-get-oidc          "$CAND" iam:GetOpenIDConnectProvider "$OIDC" allowed "$R"
sim B10-v2-list-oidc         "$CAND" iam:ListOpenIDConnectProviders '*' allowed "$R"
sim B11-v2-subscribe-rosa    "$CAND" aws-marketplace:Subscribe '*' allowed "$R,$PID"
sim B12-v2-view-subscriptions "$CAND" aws-marketplace:ViewSubscriptions '*' allowed "$R"
# W. IaC 역할 허용 정책 자체에 IAM 쓰기가 없는지(Guardrails 없이 평가 — 리전 Deny에 가려지지 않게)
#    리뷰 지적: 허용 prefix 내 임의 정책·승인 외 principal·역할 간 정책 교차 연결 → 생성·부착 권한 자체가 없음
sim W01-create-account-role  "$ONLY" iam:CreateRole "$ROLE/fds-rosa-HCP-ROSA-Installer-Role" implicitDeny "$R,$OWN"
sim W02-create-cli-role      "$ONLY" iam:CreateRole "$ROLE/fds-rosa-OCM-Role-EXAMPLE" implicitDeny "$R"
sim W03-create-prefixed-policy "$ONLY" iam:CreatePolicy "$POL/fds-rosa-EXAMPLE-Admin" implicitDeny "$R"
sim W04-attach-rosa-policy   "$ONLY" iam:AttachRolePolicy "$ROLE/fds-rosa-HCP-ROSA-Installer-Role" implicitDeny "$R,$(ctx iam:PolicyARN "$AWSPOL/service-role/ROSAInstallerPolicy")"
sim W05-attach-prefixed-cross "$ONLY" iam:AttachRolePolicy "$ROLE/fds-rosa-HCP-ROSA-Worker-Role" implicitDeny "$R,$(ctx iam:PolicyARN "$POL/fds-rosa-EXAMPLE-Admin")"
sim W06-attach-admin         "$ONLY" iam:AttachRolePolicy "$ROLE/fds-rosa-HCP-ROSA-Installer-Role" implicitDeny "$R,$(ctx iam:PolicyARN "$AWSPOL/AdministratorAccess")"
sim W07-create-oidc          "$ONLY" iam:CreateOpenIDConnectProvider "$OIDC" implicitDeny "$R,$OWN"
sim W08-update-trust         "$ONLY" iam:UpdateAssumeRolePolicy "$ROLE/fds-rosa-HCP-ROSA-Installer-Role" implicitDeny "$R"
sim W09-delete-role          "$ONLY" iam:DeleteRole "$ROLE/fds-rosa-HCP-ROSA-Installer-Role" implicitDeny "$R"
sim W10-tag-role             "$ONLY" iam:TagRole "$ROLE/fds-rosa-HCP-ROSA-Installer-Role" implicitDeny "$R,$OWN"
sim W11-pass-rosa-role       "$ONLY" iam:PassRole "$ROLE/fds-rosa-HCP-ROSA-Installer-Role" implicitDeny "$R"
# N. 후보 v2에서도 계속 막혀야 하는 것
sim N01-v2-create-account-role "$CAND" iam:CreateRole "$ROLE/fds-rosa-HCP-ROSA-Installer-Role" explicitDeny "$R,$OWN"
sim N02-v2-attach-rosa-policy "$CAND" iam:AttachRolePolicy "$ROLE/fds-rosa-HCP-ROSA-Installer-Role" explicitDeny "$R,$(ctx iam:PolicyARN "$AWSPOL/service-role/ROSAInstallerPolicy")"
sim N03-v2-unsubscribe-rosa  "$CAND" aws-marketplace:Unsubscribe '*' explicitDeny "$R,$PID"
sim N04-v2-subscribe-other   "$CAND" aws-marketplace:Subscribe '*' implicitDeny "$R,$(ctx aws-marketplace:ProductId 00000000-0000-0000-0000-000000000000 stringList)"
sim N05-v2-ec2-us-east-1     "$CAND" ec2:DescribeVpcs '*' explicitDeny "$R"
sim N06-v2-read-other-role   "$CAND" iam:ListAttachedRolePolicies "$ROLE/other-admin-role" implicitDeny "$R"
sim N07-v2-get-admin-policy  "$CAND" iam:GetPolicy "$AWSPOL/AdministratorAccess" implicitDeny "$R"

# 5. 전체 판정 — 행 형식·고유 ID·기대 ID 집합·case 수·전부 PASS
echo; column -t -s $'\t' summary.tsv
diff <(tail -n +2 summary.tsv | cut -f1 | sort) <(tr ' ' '\n' <<< "$EXPECTED_IDS" | sort) > case-id-diff.txt; idrc=$?
awk -F '\t' -v n="$EXPECTED_CASES" 'NR==1 { if (NF!=6) bad=1; next } { c++; if (NF!=6 || $5!="PASS" || seen[$1]++) bad=1 } END { exit (c!=n || bad) }' summary.tsv; arc=$?
echo "case_id_set_rc=$idrc summary_check_rc=$arc expected_cases=$EXPECTED_CASES live_guardrails=$LIVE" >> meta.txt
if [ "$idrc" -eq 0 ] && [ "$arc" -eq 0 ]; then finish "PASS($EXPECTED_CASES/$EXPECTED_CASES)" 0; else finish FAIL 1; fi
