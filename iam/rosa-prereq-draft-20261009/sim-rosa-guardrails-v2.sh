#!/usr/bin/env bash
# #12 ROSA A1/A3 정책 + FDS-IaC-Guardrails 조합 시뮬레이션 (infra-terraform#12, #35 6078438929 요청)
# 실행 위치: AWS CloudShell(서울), 321team-hayeoung. 필요 권한: iam:SimulateCustomPolicy, iam:GetPolicy(Version)
# 비용: 없음. simulate-custom-policy(모의 계산)와 정책 조회만. AWS 자원 생성/수정/삭제 0, 실제 Subscribe 0
# 기준 context: aws:RequestedRegion=us-east-1 (U1 N6 explicit deny 근거). 조직/사용자 값은 EXAMPLE로 대체
set -u
ACC=774055931866
OUT="$HOME/sim-rosa-gr-$(date +%Y%m%d-%H%M%S)"; mkdir "$OUT" && chmod 700 "$OUT" && cd "$OUT" || exit 1
kst(){ TZ=Asia/Seoul date '+%Y-%m-%dT%H:%M:%S%z'; }
echo "start_kst=$(kst)" > meta.txt
aws sts get-caller-identity --output json > 00-identity.json; echo "identity_rc=$?" >> meta.txt

cat > gr-v1.json <<'J'
{"Version":"2012-10-17","Statement":[{"Sid":"DenyOutsideSeoul","Effect":"Deny","NotAction":["iam:GetRole","iam:GetInstanceProfile","iam:PassRole","sts:GetCallerIdentity"],"Resource":"*","Condition":{"StringNotEquals":{"aws:RequestedRegion":"ap-northeast-2"}}},{"Sid":"DenyRemovingOwnershipTags","Effect":"Deny","Action":"ec2:DeleteTags","Resource":"*","Condition":{"ForAnyValue:StringEquals":{"aws:TagKeys":["Project","ManagedBy"]}}},{"Sid":"DenyRetagProjectToOtherValue","Effect":"Deny","Action":"ec2:CreateTags","Resource":"*","Condition":{"Null":{"aws:RequestTag/Project":"false"},"StringNotEquals":{"aws:RequestTag/Project":"fds-hybrid"}}},{"Sid":"DenyRetagManagedByToOtherValue","Effect":"Deny","Action":"ec2:CreateTags","Resource":"*","Condition":{"Null":{"aws:RequestTag/ManagedBy":"false"},"StringNotEquals":{"aws:RequestTag/ManagedBy":"terraform"}}},{"Sid":"DenySessionDocumentChangeOrDelete","Effect":"Deny","Action":["ssm:UpdateDocument","ssm:UpdateDocumentDefaultVersion","ssm:DeleteDocument","ssm:ModifyDocumentPermission","ssm:SendCommand"],"Resource":"*"},{"Sid":"DenyCentralBootstrapStackChange","Effect":"Deny","NotAction":["cloudformation:Describe*","cloudformation:Get*","cloudformation:List*"],"Resource":"arn:aws:cloudformation:*:774055931866:stack/*"}]}
J
cat > rosa.json <<'J'
{"Version":"2012-10-17","Statement":[{"Sid":"ReadCallerIdentity","Effect":"Allow","Action":"sts:GetCallerIdentity","Resource":"*"},{"Sid":"ReadRosaRoles","Effect":"Allow","Action":["iam:GetRole","iam:ListRolePolicies","iam:ListAttachedRolePolicies","iam:ListRoleTags"],"Resource":"arn:aws:iam::774055931866:role/fds-rosa-*"},{"Sid":"ListRolesNoResourceLevel","Effect":"Allow","Action":"iam:ListRoles","Resource":"*"},{"Sid":"ReadRosaPolicies","Effect":"Allow","Action":["iam:GetPolicy","iam:GetPolicyVersion","iam:ListPolicyVersions"],"Resource":["arn:aws:iam::aws:policy/service-role/ROSA*","arn:aws:iam::774055931866:policy/fds-rosa-*","arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"]},{"Sid":"ReadRosaOidcProvider","Effect":"Allow","Action":"iam:GetOpenIDConnectProvider","Resource":"arn:aws:iam::774055931866:oidc-provider/oidc.op1.openshiftapps.com/*"},{"Sid":"ListOidcProvidersNoResourceLevel","Effect":"Allow","Action":"iam:ListOpenIDConnectProviders","Resource":"*"},{"Sid":"CreateTerraformOwnedRosaRoles","Effect":"Allow","Action":["iam:CreateRole","iam:TagRole"],"Resource":["arn:aws:iam::774055931866:role/fds-rosa-HCP-ROSA-*","arn:aws:iam::774055931866:role/fds-rosa-openshift-*","arn:aws:iam::774055931866:role/fds-rosa-kube-system-*"],"Condition":{"StringEquals":{"aws:RequestTag/Project":"fds-hybrid","aws:RequestTag/ManagedBy":"terraform"}}},{"Sid":"CreateCliOwnedOrgLinkRoles","Effect":"Allow","Action":["iam:CreateRole","iam:TagRole"],"Resource":["arn:aws:iam::774055931866:role/fds-rosa-OCM-Role-*","arn:aws:iam::774055931866:role/fds-rosa-User-*"]},{"Sid":"CreateCliOwnedRolePolicy","Effect":"Allow","Action":["iam:CreatePolicy","iam:TagPolicy"],"Resource":"arn:aws:iam::774055931866:policy/fds-rosa-*"},{"Sid":"AttachOnlyRosaPolicies","Effect":"Allow","Action":"iam:AttachRolePolicy","Resource":"arn:aws:iam::774055931866:role/fds-rosa-*","Condition":{"ArnLike":{"iam:PolicyARN":["arn:aws:iam::aws:policy/service-role/ROSA*","arn:aws:iam::774055931866:policy/fds-rosa-*","arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"]}}},{"Sid":"CreateTerraformOwnedOidcProvider","Effect":"Allow","Action":["iam:CreateOpenIDConnectProvider","iam:TagOpenIDConnectProvider"],"Resource":"arn:aws:iam::774055931866:oidc-provider/oidc.op1.openshiftapps.com/*","Condition":{"StringEquals":{"aws:RequestTag/Project":"fds-hybrid","aws:RequestTag/ManagedBy":"terraform"}}}]}
J
cat > sub.json <<'J'
{"Version":"2012-10-17","Statement":[{"Sid":"ViewMarketplaceSubscriptions","Effect":"Allow","Action":"aws-marketplace:ViewSubscriptions","Resource":"*"},{"Sid":"SubscribeRosaOnly","Effect":"Allow","Action":"aws-marketplace:Subscribe","Resource":"*","Condition":{"ForAnyValue:StringEquals":{"aws-marketplace:ProductId":["34850061-abaf-402d-92df-94325c9e947f","bfdca560-2c78-4e64-8193-794c159e6d30"]}}}]}
J
cat > cleanup.json <<'J'
{"Version":"2012-10-17","Statement":[{"Sid":"DetachOnlyRosaPolicies","Effect":"Allow","Action":"iam:DetachRolePolicy","Resource":"arn:aws:iam::774055931866:role/fds-rosa-*","Condition":{"ArnLike":{"iam:PolicyARN":["arn:aws:iam::aws:policy/service-role/ROSA*","arn:aws:iam::774055931866:policy/fds-rosa-*","arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"]}}},{"Sid":"DeleteRosaRoles","Effect":"Allow","Action":["iam:ListInstanceProfilesForRole","iam:DeleteRole"],"Resource":"arn:aws:iam::774055931866:role/fds-rosa-*"},{"Sid":"DeleteCliOwnedRolePolicy","Effect":"Allow","Action":"iam:DeletePolicy","Resource":"arn:aws:iam::774055931866:policy/fds-rosa-*"},{"Sid":"DeleteRosaOidcProvider","Effect":"Allow","Action":"iam:DeleteOpenIDConnectProvider","Resource":"arn:aws:iam::774055931866:oidc-provider/oidc.op1.openshiftapps.com/*"}]}
J

# 후보 v2: DenyOutsideSeoul NotAction에 A1/A3 Action만 정확한 이름으로 추가 (Cleanup Action 미포함)
ADD='["aws-marketplace:ViewSubscriptions","aws-marketplace:Subscribe","iam:ListRolePolicies","iam:ListAttachedRolePolicies","iam:ListRoleTags","iam:ListRoles","iam:GetPolicy","iam:GetPolicyVersion","iam:ListPolicyVersions","iam:GetOpenIDConnectProvider","iam:ListOpenIDConnectProviders","iam:CreateRole","iam:TagRole","iam:CreatePolicy","iam:TagPolicy","iam:AttachRolePolicy","iam:CreateOpenIDConnectProvider","iam:TagOpenIDConnectProvider"]'
jq -c --argjson add "$ADD" '.Statement |= map(if .Sid=="DenyOutsideSeoul" then .NotAction = (.NotAction + $add) else . end)' gr-v1.json > gr-v2-candidate.json
jq -c '.Statement |= map(select(.Sid=="DenyOutsideSeoul"))' gr-v1.json > gr-region-only.json

# 실제 부착된 Guardrails와 원문 비교 (조회만)
V=$(aws iam get-policy --policy-arn "arn:aws:iam::$ACC:policy/FDS-IaC-Guardrails" --query Policy.DefaultVersionId --output text 2>live.err)
if [ -n "$V" ] && aws iam get-policy-version --policy-arn "arn:aws:iam::$ACC:policy/FDS-IaC-Guardrails" --version-id "$V" --query PolicyVersion.Document --output json > gr-live.json 2>>live.err; then
  if [ "$(jq -S -c . gr-live.json)" = "$(jq -S -c . gr-v1.json)" ]; then LIVE="MATCH($V)"; else LIVE="DIFF($V)"; fi
else LIVE="UNREADABLE"; fi
echo "live_guardrails=$LIVE" | tee -a meta.txt

printf 'case\taction\texpect\tactual\tresult\tmissing_context\n' > summary.tsv
ctx(){ printf '{"ContextKeyName":"%s","ContextKeyValues":["%s"],"ContextKeyType":"%s"}' "$1" "$2" "${3:-string}"; }
R=$(ctx aws:RequestedRegion us-east-1)
OWN="$(ctx aws:RequestTag/Project fds-hybrid),$(ctx aws:RequestTag/ManagedBy terraform)"

# sim CASE "정책파일들" ACTION RESOURCE EXPECT CONTEXT
sim(){
  local c=$1 files=$2 a=$3 r=$4 exp=$5 cx=$6
  jq -n --arg a "$a" --arg r "$r" --argjson cx "[$cx]" \
    --argjson pl "$(for f in $files; do jq -c . "$f" | jq -Rs .; done | jq -s .)" \
    '{PolicyInputList:$pl,ActionNames:[$a],ResourceArns:[$r],ContextEntries:$cx}' > "$c.input.json"
  aws iam simulate-custom-policy --cli-input-json "file://$c.input.json" --output json > "$c.out.json" 2> "$c.err"
  local rc=$? act miss
  if [ $rc -eq 0 ]; then
    act=$(jq -r '.EvaluationResults[0].EvalDecision' "$c.out.json")
    miss=$(jq -r '[.EvaluationResults[0].MissingContextValues[]?]|join(",")' "$c.out.json")
  else act="RC$rc"; miss="-"; fi
  local res=FAIL; [ "$act" = "$exp" ] && res=PASS
  printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$c" "$a" "$exp" "$act" "$res" "${miss:--}" >> summary.tsv
  echo "[$res] $c expect=$exp actual=$act"
}
CUR="rosa.json sub.json gr-v1.json"; CAND="rosa.json sub.json gr-v2-candidate.json"
ROLE=arn:aws:iam::$ACC:role; POL=arn:aws:iam::$ACC:policy; OIDC=arn:aws:iam::$ACC:oidc-provider/oidc.op1.openshiftapps.com/EXAMPLE
PID="$(ctx aws-marketplace:ProductId 34850061-abaf-402d-92df-94325c9e947f stringList)"

# A. 현재 Guardrails v1에서 ROSA 동작이 막히는지
sim A01-v1-create-account-role "$CUR" iam:CreateRole $ROLE/fds-rosa-HCP-ROSA-Installer-Role explicitDeny "$R,$OWN"
sim A02-v1-create-ocm-role     "$CUR" iam:CreateRole $ROLE/fds-rosa-OCM-Role-EXAMPLE explicitDeny "$R"
sim A03-v1-subscribe-rosa      "$CUR" aws-marketplace:Subscribe '*' explicitDeny "$R,$PID"
sim A04-v1-create-oidc         "$CUR" iam:CreateOpenIDConnectProvider $OIDC explicitDeny "$R,$OWN"
# S. 막는 Statement가 DenyOutsideSeoul인지 단독 확인
sim S01-region-only            "rosa.json gr-region-only.json" iam:CreateRole $ROLE/fds-rosa-HCP-ROSA-Installer-Role explicitDeny "$R,$OWN"
# B. 후보 v2에서 필요한 ROSA 동작이 통과하는지
sim B01-v2-create-account-role "$CAND" iam:CreateRole $ROLE/fds-rosa-HCP-ROSA-Installer-Role allowed "$R,$OWN"
sim B02-v2-create-operator-role "$CAND" iam:CreateRole $ROLE/fds-rosa-kube-system-kms-provider allowed "$R,$OWN"
sim B03-v2-create-ocm-role     "$CAND" iam:CreateRole $ROLE/fds-rosa-OCM-Role-EXAMPLE allowed "$R"
sim B04-v2-create-user-role    "$CAND" iam:CreateRole $ROLE/fds-rosa-User-EXAMPLE-Role allowed "$R"
sim B05-v2-create-ocm-policy   "$CAND" iam:CreatePolicy $POL/fds-rosa-OCM-Role-EXAMPLE-Policy allowed "$R"
sim B06-v2-attach-installer    "$CAND" iam:AttachRolePolicy $ROLE/fds-rosa-HCP-ROSA-Installer-Role allowed "$R,$(ctx iam:PolicyARN arn:aws:iam::aws:policy/service-role/ROSAInstallerPolicy)"
sim B07-v2-attach-worker-ecr   "$CAND" iam:AttachRolePolicy $ROLE/fds-rosa-HCP-ROSA-Worker-Role allowed "$R,$(ctx iam:PolicyARN arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly)"
sim B08-v2-create-oidc         "$CAND" iam:CreateOpenIDConnectProvider $OIDC allowed "$R,$OWN"
sim B09-v2-subscribe-rosa      "$CAND" aws-marketplace:Subscribe '*' allowed "$R,$PID"
sim B10-v2-list-roles          "$CAND" iam:ListRoles "*" allowed "$R"
sim B11-v2-list-oidc           "$CAND" iam:ListOpenIDConnectProviders '*' allowed "$R"
# N. 후보 v2에서도 계속 막혀야 하는 것
sim N01-v2-create-other-role   "$CAND" iam:CreateRole $ROLE/other-admin-role implicitDeny "$R,$OWN"
sim N02-v2-account-role-no-tag "$CAND" iam:CreateRole $ROLE/fds-rosa-HCP-ROSA-Installer-Role implicitDeny "$R"
sim N03-v2-attach-admin        "$CAND" iam:AttachRolePolicy $ROLE/fds-rosa-HCP-ROSA-Installer-Role implicitDeny "$R,$(ctx iam:PolicyARN arn:aws:iam::aws:policy/AdministratorAccess)"
sim N04-v2-subscribe-other     "$CAND" aws-marketplace:Subscribe '*' implicitDeny "$R,$(ctx aws-marketplace:ProductId 00000000-0000-0000-0000-000000000000 stringList)"
sim N05-v2-unsubscribe-rosa    "$CAND" aws-marketplace:Unsubscribe '*' explicitDeny "$R,$PID"
sim N06-v2-ec2-us-east-1       "$CAND" ec2:DescribeVpcs '*' explicitDeny "$R"
sim N07-v2-delete-rosa-role    "$CAND" iam:DeleteRole $ROLE/fds-rosa-HCP-ROSA-Installer-Role explicitDeny "$R"
sim N08-v2-update-trust        "$CAND" iam:UpdateAssumeRolePolicy $ROLE/fds-rosa-HCP-ROSA-Installer-Role explicitDeny "$R"
sim N09-v2-wrong-managedby     "$CAND" iam:CreateRole $ROLE/fds-rosa-HCP-ROSA-Installer-Role implicitDeny "$R,$(ctx aws:RequestTag/Project fds-hybrid),$(ctx aws:RequestTag/ManagedBy manual)"
# K. 정리 정책은 v2에서도 리전 Deny에 막힘 → 정리 단계에 별도 변경 필요
sim K01-v2-cleanup-delete-role "cleanup.json gr-v2-candidate.json" iam:DeleteRole $ROLE/fds-rosa-HCP-ROSA-Installer-Role explicitDeny "$R"

echo "end_kst=$(kst)" >> meta.txt
sha256sum -- * > SHA256SUMS
echo; column -t -s $'\t' summary.tsv
echo; echo "live_guardrails=$LIVE"; echo "결과 폴더: $OUT"
grep -q $'\tFAIL\t' summary.tsv && exit 1 || exit 0
