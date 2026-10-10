# #12 ROSA 계정 준비 A1·A3 full policy 초안 — 2026-10-09

상태: **DRAFT rev2 (2026-10-10) / 부여 아님 / 실행 아님**

> **rev2 변경 요약:** [PR21 리뷰](https://github.com/321Team/infra-terraform/pull/21#pullrequestreview-5471849615) 차단 1(임의 trust·정책 생성/연결 경로)에 따라 **A3의 IAM 쓰기(역할·고객 정책·OIDC provider 생성·부착·삭제)를 `FDS-IaC-Operator`에서 제거하고 중앙 실행 경로로 옮겼다.** IaC 역할에는 조회 권한만 남는다. 차단 2(시뮬레이션 성공 종료 조건)는 스크립트를 다시 작성해 반영했다. 아래 [중앙 실행 경로](#중앙-실행-경로-rev2)와 [rev2 시뮬레이션](#rev2-시뮬레이션)을 본다.
대상 이슈: [infra-terraform#12](https://github.com/321Team/infra-terraform/issues/12) · 원티켓 [#35](https://github.com/321Team/fds-project-baseline/issues/35)
근거: [v3 보완판](https://github.com/321Team/fds-project-baseline/issues/35#issuecomment-6074050926), [이권욱 실행 자료 요청](https://github.com/321Team/fds-project-baseline/issues/35#issuecomment-6074663186), 실행 자료 [EXECUTION-PACK.md](EXECUTION-PACK.md)
비용: 파일 작성·로컬 문법 검사만 — **비용 없음**

## 한눈에 보기

| 정책 파일 / 경로 | 단계 | 붙일 곳 | 붙이는 기간 |
|---|---|---|---|
| `FDS-RosaBootstrap-Subscribe.json` | A1 ROSA 활성화 | `FDS-IaC-Operator` (하영 세션) | **A1 1회만.** 활성화 readback 후 바로 떼어냄 |
| `FDS-IaC-RosaPrereq.json` | A3 **조회만**(생성 후 readback, Terraform plan refresh, `rosa list`) | `FDS-IaC-Operator` | A3 기간과 ROSA 운영 중 readback |
| 중앙 실행 경로 (정책 파일 없음) | A3 **생성·부착·정리** — account/operator role, IAM OIDC provider, CLI `ocm-role`·`user-role`과 그 고객 정책 | 승인된 중앙 주체 1회 실행 | 단계별 별도 실행 승인. 위임 역할에 IAM 쓰기를 붙이지 않음 |

- 위 두 정책의 생성·부착·분리와 Guardrails v2 전환은 중앙 주체가 부여 도구로 한 단계씩 실행한다. **실행 도구는 별도 PR로 분리했다**(대조 `tools/rosa_prereq_check.py`, 부여 `tools/rosa_grant.py`, 브랜치 `tools/rosa-grant-check-12`). 그 PR이 독립 리뷰를 통과해 병합되기 전에는 중앙 실행(정책 부여·Guardrails 전환·plan/apply)을 하지 않는다. 눈으로 하는 대조로 대신하지 않는다.
- rev1의 `FDS-IaC-RosaPrereq-Cleanup.json`은 삭제했다. IaC 역할이 만들지 않으므로 정리(회수)도 중앙 실행 경로에서 한다.

- A2(Red Hat 청구 연결)는 AWS 쪽 추가 권한이 필요 없다고 **가정**한다. 실행 직전 화면 흐름에서 거부가 나오면 그 Action만 추가해 리뷰를 받는다.
- 새 위임 역할은 만들지 않는다. `FDS-IaC-Operator`는 `phase2/rosa-prereq/terraform.tfstate` 읽기 권한으로 생성 후 readback·plan refresh에 쓴다. state 쓰기를 동반하는 apply는 중앙 실행 경로에서 한다(state bucket policy의 허용 주체는 `FDS-IaC-Operator`와 root뿐이다).
- 이 정책들에는 `iam:PassRole`이 없다. 클러스터 생성(#4)은 이 범위가 아니다.

## 설계 원칙 (쉽게)

1. **위임 역할에는 IAM 쓰기가 없다(rev2).** `iam:CreateRole`은 trust 내용을, `iam:CreatePolicy`는 정책 내용을 조건으로 제한할 수 없다. 이름 prefix·태그·부착 대상 제한만으로는 "허용 이름의 역할을 임의 trust로 만들고, 같은 prefix의 임의 내용 정책을 붙이는" 경로를 막지 못한다(rev1 리뷰 차단 1). 그래서 생성·부착·삭제는 위임 역할에서 뺀다.
2. **IAM 쓰기는 중앙 실행 경로에서 검토된 내용으로 1회.** trust·부착 정책은 검토된 Terraform source와 ROSA CLI `--mode manual` 출력으로 고정하고, 실행 전 plan JSON 대조 → 실행 후 readback으로 확인한다. 이 대조는 IAM simulation이 아니라 소스·실행 전후 대조다.
3. **조회 범위는 `fds-rosa` 이름과 정확한 ARN.** 역할·정책·OIDC provider 조회는 prefix나 정확한 ARN으로 제한한다. 리소스 단위 제한을 지원하지 않는 `ListRoles`·`ListOpenIDConnectProviders`만 `*`이다.
4. **Unsubscribe는 없다.** A1에는 `Subscribe`·`ViewSubscriptions`만 두고, `ROSAManageSubscription` 관리형 정책은 붙이지 않는다.
5. **PassRole·UpdateAssumeRolePolicy는 어디에도 없다.**

## Action별 한 줄 용도

### FDS-RosaBootstrap-Subscribe (A1)

| Sid | Action | 용도 | Resource 범위 |
|---|---|---|---|
| ViewMarketplaceSubscriptions | `aws-marketplace:ViewSubscriptions` | 활성화 전후 구독 상태 readback | `*` — 리소스 단위 제한 미지원(실행 전 Service Authorization Reference로 확인) |
| SubscribeRosaOnly | `aws-marketplace:Subscribe` | ROSA 구독(활성화) 1회 | `*` + `ForAnyValue:StringEquals aws-marketplace:ProductId`로 ROSA 제품 2개만. 값과 연산자는 AWS 관리형 `arn:aws:iam::aws:policy/ROSAManageSubscription` v2 원본과 같다(`ForAllValues`는 키가 없을 때도 통과하므로 쓰지 않음) |

### FDS-IaC-RosaPrereq (A3)

| Sid | Action | 용도 | Resource 범위 |
|---|---|---|---|
| ReadCallerIdentity | `sts:GetCallerIdentity` | 실행 identity·계정 guard 확인(Terraform·ROSA CLI 공통) | `*` — 리소스 단위 제한 미지원 |
| ReadRosaRoles | `iam:GetRole`·`ListRolePolicies`·`ListAttachedRolePolicies`·`ListRoleTags` | Terraform refresh·plan과 생성 후 readback | `role/fds-rosa-*` |
| ListRolesNoResourceLevel | `iam:ListRoles` | `rosa list account-roles`·`ocm-role`·`user-role`이 계정의 역할 목록에서 ROSA 역할을 찾을 때 | `*` — 2026-10-09 시뮬레이션에서 `role/*`는 implicitDeny, `*`만 allowed(리소스 단위 제한 미지원). **사유 검토 대상** |
| ReadRosaPolicies | `iam:GetPolicy`·`GetPolicyVersion`·`ListPolicyVersions` | AWS 관리형 ROSA 정책·ECR 읽기 정책 내용 확인, CLI가 만든 정책 readback | `aws:policy/service-role/ROSA*`, `aws:policy/AmazonEC2ContainerRegistryReadOnly`, `policy/fds-rosa-*` |
| ReadRosaOidcProvider | `iam:GetOpenIDConnectProvider` | OIDC provider readback | `oidc-provider/oidc.op1.openshiftapps.com/*` |
| ListOidcProvidersNoResourceLevel | `iam:ListOpenIDConnectProviders` | Terraform·CLI의 OIDC provider 존재 확인 | `*` — 리소스 단위 제한 미지원. **사유 검토 대상** |

rev1에 있던 생성·부착 Sid 5개(`CreateTerraformOwnedRosaRoles`, `CreateCliOwnedOrgLinkRoles`, `CreateCliOwnedRolePolicy`, `AttachOnlyRosaPolicies`, `CreateTerraformOwnedOidcProvider`)와 Cleanup 정책은 **rev2에서 제거했다.** 해당 동작은 [중앙 실행 경로](#중앙-실행-경로-rev2)에서 한다.

## ⚠️ 기존 정책과의 충돌 — Guardrails 리전 거부

`FDS-IaC-Guardrails`의 `DenyOutsideSeoul`은 `aws:RequestedRegion != ap-northeast-2`인 요청을 거부한다. 예외(NotAction)는 `iam:GetRole`·`GetInstanceProfile`·`PassRole`·`sts:GetCallerIdentity` 4개뿐이다.

- IAM과 Marketplace는 글로벌 서비스라 요청 리전이 **us-east-1**로 평가되는 것으로 알고 있다. 그러면 위 A1·A3 Action 대부분이 Guardrails의 명시적 거부에 막혀 **허용 정책을 붙여도 실행되지 않는다.**
- 제안(rev2): `DenyOutsideSeoul` NotAction에 이 초안의 **IAM 조회·Marketplace Action 11개**만 **정확한 이름으로** 추가한다(`iam:*` 와일드카드 없음, IAM 쓰기 Action 없음). Guardrails는 이권욱 IaC Grant 준비안([PR18](https://github.com/321Team/infra-terraform/pull/18)) 범위이므로 그쪽 판단으로 반영한다.
- 실행 전 중앙 simulation에서 Guardrails와 함께 평가해 실제로 거부되는지 확인한다.

**실제 런타임 근거 (2026-10-09 U1 자체 시험 N6, `~/u1-hayeoung-20261009-090652/N6-iam-list-users.stderr`)**

- `FDS-IaC-Operator/321team-hayeoung` 역할 세션의 `iam:ListUsers` → `AccessDenied ... with an explicit deny in an identity-based policy: arn:aws:iam::774055931866:policy/FDS-IaC-Guardrails`
- Guardrails v1에서 `iam:ListUsers`에 걸릴 수 있는 Deny는 `DenyOutsideSeoul`뿐이다(나머지는 ec2 태그·ssm 문서·cloudformation 대상). → **IAM 요청이 `ap-northeast-2`가 아닌 리전으로 평가되어 이 Deny에 걸린 것으로 판단**한다.
- 한계: 오류 메시지는 Sid를 알려 주지 않으므로 소거법 추론이다. 시뮬레이션(`MatchedStatements`)으로 Sid를 확정한다. 이 기록은 ROSA Action 자체의 거부를 입증하지 않는다.

## 실행 전 확정할 것 (빈칸·가정)

| # | 항목 | 확정 방법 | 비용 |
|---|---|---|---|
| 1 | ROSA 제품 ID(A1 조건) | ✅ **확인 완료** — `arn:aws:iam::aws:policy/ROSAManageSubscription` v2(경로는 `service-role/` 아님): `34850061-abaf-402d-92df-94325c9e947f`, `bfdca560-2c78-4e64-8193-794c159e6d30`, 연산자 `ForAnyValue:StringEquals` | 없음 |
| 2 | ROSA 관리형 정책 ARN 경로(`service-role/ROSA*`) | ✅ **확인 완료** — `service-role/ROSAInstallerPolicy`(v10) 조회 성공, CLI 출력의 `ROSASRESupportPolicy`·`ROSAWorkerInstancePolicy`도 같은 경로 | 없음 |
| 3 | CLI가 만드는 역할·정책 이름과 실제 호출 API | ✅ **확인 완료**(아래 표) — `rosa create ocm-role`·`user-role`·`account-roles --hosted-cp`를 `--mode manual`로 실행. AWS 변경 없음 | 없음 |
| 4 | managed OIDC issuer 호스트(`oidc.op1.openshiftapps.com`) | `terraform/rosa-prereq`의 OIDC provider precondition이 이 호스트가 아니면 apply를 멈춘다. 단계 1 readback(`rosa list oidc-config`)으로 실제 값 확인. `rosa create oidc-config`는 managed일 때 실제 생성할 수 있어 실행하지 않음 | 없음 |
| 5 | account/operator role trust 내용 | Terraform rhcs data source(`rhcs_hcp_policies` 등)가 주는 Red Hat principal·OIDC 조건. `terraform plan` 출력으로 확인 후 첨부 | 없음 |
| 6 | 콘솔 A1 흐름에서 추가 Action 필요 여부 | 실행 직전 화면 확인. 거부 시 그 Action만 추가 리뷰 | 없음 |
| 7 | 도구 pin | ✅ **확인 완료** — ROSA CLI(아래), Terraform 1.16.4(`terraform_1.16.4_windows_amd64.zip` HashiCorp SHA256SUMS 검증 OK, 로컬 검사용), provider lock `terraform/rosa-prereq/.terraform.lock.hcl`(AWS 6.66.0·rhcs 1.7.9, linux_amd64·windows_amd64 해시). CloudShell 실행 시 linux 바이너리를 같은 방식으로 SHA256SUMS 검증 | 없음 |

**ROSA CLI 고정값 (2026-10-09 18:10 KST CloudShell 서울, 321team-hayeoung)**

| 항목 | 값 |
|---|---|
| 버전 | `rosa version` → 1.2.53 (`latest`로 받았을 때 해석된 값) |
| 재현용 URL | `https://mirror.openshift.com/pub/openshift-v4/clients/rosa/1.2.53/rosa-linux.tar.gz` |
| tar.gz SHA-256 | `a513d437adc174a6bf6e02a7936f81ded3a4b15714b121c030b7b2304eb70aee` |
| 바이너리 SHA-256 | `a3a57d6adb9a39f7ec8363951999cecde98aa403675c52ef7d7e74e169e7a9e1` |
| 로그인 | `rosa login --use-device-code` 성공. `rosa whoami` 조직 External ID = 콘솔 Org ID(`2042****`) 일치 |
| 원본 | CloudShell `~/fds-rosa-prereq-check-20261009-091045/` (01-rosa-sha256.txt, 01-rosa-version.txt, 02-whoami.txt) |

**ROSA CLI 1.2.53 `--mode manual` 출력 대조 (03-*.txt)**

| CLI 명령 | 출력된 aws 호출 | 생성 이름 | rev1 Sid → rev2 실행 주체 |
|---|---|---|---|
| `create ocm-role` (admin 질문 없음 = basic) | `iam create-role`(tags), `iam create-policy`(tags), `iam attach-role-policy` → `rosa link ocm-role` | 역할 `fds-rosa-OCM-Role-<조직 External ID>`, 정책 `fds-rosa-OCM-Role-<조직 External ID>-Policy` | 중앙 실행(manual 출력의 aws 명령을 검토 후 그대로 실행) |
| `create user-role` | `iam create-role`(tags, 정책 부착 없음) → `rosa link user-role` | `fds-rosa-User-<Red Hat 사용자명>-Role` | 중앙 실행(필요할 때만, 실행 자료 §1-2) |
| `create account-roles --hosted-cp` (Terraform으로 만들 대상, 이름·정책 대조용) | `iam create-role` ×3, `iam attach-role-policy` ×4 | `fds-rosa-HCP-ROSA-Installer/Support/Worker-Role` | 중앙 실행(Terraform `rosa-prereq` 단계 1) |

- Worker 역할에는 `ROSAWorkerInstancePolicy` 외에 **`arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly`**도 붙는다. 처음 초안의 부착 조건(`ROSA*`만)은 이를 막았으므로 정확한 ARN 1개를 추가했다.
- CLI가 붙이는 태그: `red-hat-managed=true`, `rosa_role_prefix=fds-rosa`, `rosa_role_type`, `rosa_openshift_version=4.22` 등. Terraform 생성분은 여기에 `Project`·`ManagedBy`가 더해진다.
- user-role 이름에 Red Hat 사용자명이 들어가므로 공개 문서에서는 마스킹한다.
- `iam:CreateRole`·`CreatePolicy`에 tag가 함께 전달되므로 실행 주체에게 `iam:TagRole`·`iam:TagPolicy`도 필요하다(rev2에서는 중앙 실행 주체의 권한이며 위임 정책에는 없음).

**trust 내용 (같은 manual 실행이 만든 `sts_*_trust_policy.json`, 05-trust-files.txt)**

| 역할 | 믿는 대상(Principal) | 조건 | 비고 |
|---|---|---|---|
| Installer | `arn:aws:iam::710019948333:role/RH-Managed-OpenShift-Installer` (Red Hat 계정) | 없음 | |
| Support | `arn:aws:iam::469112722088:role/RH-Technical-Support-<조직 External ID>` (Red Hat 계정) | 없음 | 조직별 지원 역할 |
| Worker | `Service: ec2.amazonaws.com` | 없음 | |
| ocm-role | `710019948333:role/RH-Managed-OpenShift-Installer` | `sts:ExternalId` = OCM Organization ID | 다른 조직이 이 역할을 쓰지 못하게 막는 값 |
| user-role | `710019948333:role/RH-Managed-OpenShift-Installer` | `sts:ExternalId` = OCM Account ID | 사용자별 값 |

- Terraform이 만드는 account role trust(rhcs data source 값)를 `terraform plan`에서 위 값과 대조한다. 다르면 apply 전에 중단한다.
- ExternalId는 OCM 조직·계정 ID라 공개 문서에서는 마스킹한다. 원본은 CloudShell 폴더에만 있다.

**ocm-role 권한 = basic 확인 (`sts_ocm_permission_policy.json`, 05-ocm-permission-policy.txt)**

- Allow 1개, Resource `*`, Action 10개 모두 조회: `ec2:DescribeSubnets`·`DescribeVpcs`·`DescribeRegions`·`DescribeRouteTables`·`DescribeInstanceTypeOfferings`, `iam:GetRole`·`ListRoles`·`ListRoleTags`·`GetOpenIDConnectProvider`·`GetPolicy`
- `iam:Create*`·`Attach*`·`Delete*` 없음 → Red Hat이 ocm-role로 operator role·OIDC를 자동 생성할 수 없다. **Terraform 소유 자원과 겹치지 않음**(v3 §4-3 근거).
- 이 정책은 CLI가 `fds-rosa-OCM-Role-<조직 External ID>-Policy`로 만들며, rev2에서는 manual 출력의 정책 원문(위 Action 10개)을 검토한 뒤 중앙 실행 경로에서 생성·부착한다.

- 3·4는 `rosa login`(하영 Red Hat 토큰, 비공유)이 필요하다. 출력에 토큰은 없지만 증적에 넣기 전에 확인한다.
- 위 확인 결과로 이 JSON의 이름 패턴·Action을 고치면 SHA256SUMS를 다시 만든다.

## 알려진 위험과 대응

| 위험 | 대응 |
|---|---|
| `iam:CreateRole`은 trust 내용을, `iam:CreatePolicy`는 정책 내용을 제한할 수 없다(rev1 차단 1) | **rev2: 위임 역할에서 IAM 쓰기를 제거.** 생성은 중앙 실행 경로에서 검토된 source·manual 출력으로만 하고, plan JSON 대조와 apply 후 readback으로 trust·부착 정책을 확인한다. permissions boundary만으로는 외부 계정 principal을 trust에 넣는 경로를 막지 못하므로 채택하지 않았다 |
| 중앙 실행 주체는 강한 권한을 가진다 | 실행 단위·입력·대조 기준을 이 문서와 실행 승인에 고정하고, 실행 기록(명령·RC·plan/readback 원본)을 증적으로 남긴다. 대상 외 IAM 변경이 plan에 나오면 STOP |
| CLI 역할(`ocm-role`·`user-role`)은 우리 태그를 강제할 수 없다 | 이름과 manual 출력 원문을 고정하고 §inventory(실행 자료 §2)에 ARN을 기록한다 |
| 생성된 역할의 trust가 나중에 바뀔 수 있다 | 위임 역할에는 `UpdateAssumeRolePolicy`가 없다. ROSA 운영 중 IaC 역할의 조회 권한으로 trust readback을 주기적으로 대조할 수 있다 |

## 중앙 실행 경로 (rev2)

위임 역할이 하지 않는 A3 IAM 쓰기를 어떻게 하는지에 대한 계약이다. **실행 승인 요청이 아니다.**

| 항목 | 내용 |
|---|---|
| 대상 | Terraform `terraform/rosa-prereq` 단계 1(account role 3 + 부착 4 + managed OIDC config + IAM OIDC provider)·단계 2(operator role 8 + 부착 8), CLI `ocm-role`(역할 1 + 고객 정책 1 + 부착 1), 필요할 때만 `user-role`, 정리 단계의 역순 삭제 |
| 실행 주체 | 승인된 중앙 주체. 기존 10-07 중앙 bootstrap과 같은 경로를 기본안으로 한다. state bucket policy상 `phase2/rosa-prereq` state 쓰기 허용 주체는 `FDS-IaC-Operator`와 root뿐이다. **실제 실행자·작업창은 이권욱과 협의해 실행 승인에서 정한다(미정).** |
| 고정 입력 | source commit SHA, `.terraform.lock.hcl`, Terraform 1.16.4·ROSA CLI 1.2.53 바이너리 SHA-256, 비공개 tfvars(조직 External ID 포함), CLI manual 출력 원문(`sts_*_trust_policy.json`, `sts_ocm_permission_policy.json`) |
| 실행 전 대조 | 대조 도구(별도 PR) `plan` 모드로 자동 대조(exit 0이 아니면 STOP). `terraform show -json` plan에서 역할별 `assume_role_policy`의 Principal·조건과 부착 정책 ARN을 위 trust 표·CLI 출력 표와 1:1 대조한다. 승인 표에 없는 principal·조건·정책, 대상 외 IAM 자원, 변경·삭제가 하나라도 있으면 STOP. CLI 역할은 manual 출력의 aws 명령과 정책 원문을 검토한 뒤 그 명령을 그대로 실행한다(`--mode auto` 사용 안 함) |
| 실행 후 readback | 대조 도구(별도 PR) `readback` 모드로 자동 대조. `aws iam get-role`(trust 원문 SHA)·`list-attached-role-policies`·`list-role-policies`(inline 0)·`get-open-id-connect-provider`, `rosa list account-roles / oidc-config / operator-roles / ocm-role`. readback은 IaC 역할의 조회 권한(이 문서의 `FDS-IaC-RosaPrereq`)으로도 할 수 있다 |
| 증적 | 명령·시각·RC·plan JSON·readback 원본을 비공개 보관하고, 마스킹된 대조표를 증적 PR로 독립 리뷰 |
| 실행 도구 | **실행 도구는 별도 PR로 분리했다**(대조 `tools/rosa_prereq_check.py`, 부여 `tools/rosa_grant.py`, 브랜치 `tools/rosa-grant-check-12`). 그 PR이 독립 리뷰를 통과해 병합되기 전에는 중앙 실행(정책 부여·Guardrails 전환·plan/apply)을 하지 않는다. 눈으로 하는 대조로 대신하지 않는다. |
| 하지 않는 것 | 위임 역할에 IAM 쓰기 부착, permissions boundary만으로의 대체, IAM simulation으로 trust 내용을 검증했다고 표시하기 |

## rev2 시뮬레이션

- 스크립트: `sim-rosa-guardrails-v2.sh` rev2(SHA는 `SHA256SUMS`). rev1 결과(아래)는 이전 정책 기준이며 rev2 정책에는 적용하지 않는다.
- 성공 조건(리뷰 차단 2 반영): ① `sts get-caller-identity` 성공 + 계정 `774055931866` + 실행자 ARN이 `EXPECTED_ARN`(기본 `321team-hayeoung`)과 일치 ② live `FDS-IaC-Guardrails` 기본 버전이 내장 v1과 정규화 비교 MATCH(DIFF·읽기 실패는 exit 2) ③ 내장 후보 v2 = v1 + 조회·Subscribe 11개와 파일 원문 일치 ④ 각 API 호출 RC와 결과 파싱 성공 ⑤ case 35개, 고유 ID, 기대 ID 집합 일치, 모두 PASS ⑥ MissingContextValues **case별 기대값**(rev2.1): allowed·explicitDeny는 빈 목록, implicitDeny는 "입력 정책들의 Condition 키 집합 − 그 case에 준 context 키 집합"과 정확히 같아야 한다. 다르면 그 case를 FAIL로 기록한다.
- 호출 실패는 `set -e`로 즉시 끝내지 않고 case 행(`RC<n>`/FAIL)과 오류 파일을 남긴 뒤 최종 판정에서 실패한다.
- case 묶음: A(4) v1 충돌 / S(1) 거부 Statement 확정 / B(12) v2에서 조회·Subscribe 허용 / **W(11) Guardrails 없이 IaC 허용 정책만으로 IAM 쓰기 전부 implicitDeny**(허용 prefix 내 임의 정책 생성, ROSA·임의·Admin 정책 부착, 역할·OIDC 생성, trust 변경, 삭제, 태그, PassRole) / N(7) v2에서도 거부 유지.
- 로컬 확인(2026-10-10, AWS 미접속): `bash -n` 통과. 가짜 `aws` 명령으로 정상(PASS 35/35, exit 0), live DIFF(exit 2), 읽기 거부(exit 2), 다른 실행자(exit 1), 판정 불일치·MissingContext 보고·API 실패(각 해당 case FAIL, exit 1)의 종료 경로를 확인했다. 실제 AWS 평가 결과가 아니다.
- **1차 실제 실행(rev2 스크립트 SHA-256 `613983133f8e…`, 2026-10-10 16:00 KST, CloudShell 서울, `321team-hayeoung`)**: `live_guardrails=MATCH(v1)`. **판정(EvalDecision)은 35/35 모두 기대값과 일치**했다. 그러나 결과는 `FAIL(exit 1)`이었다. 원인은 정책이 아니라 rev2의 MissingContextValues 계약("전부 빈 목록")이 틀렸기 때문이다. AWS는 implicitDeny일 때 입력 정책 전체의 조건 키 중 context로 주지 않은 키를 모두 보고한다.
  - W01~W11(Guardrails 없이 평가): `aws-marketplace:ProductId` — Subscribe 문장의 키
  - N04: Guardrails 태그 키 3개(`aws:RequestTag/ManagedBy`·`aws:RequestTag/Project`·`aws:TagKeys`) — ProductId는 제공됨
  - N06·N07: 위 4개 모두
  - allowed·explicitDeny 21건: 빈 목록
  - 원본: CloudShell `~/sim-rosa-gr-20261010-070006-JLXV/`. 이 실행 결과는 FAIL로 그대로 보존한다.
- **rev2.1**: 계약을 case별 기대값으로 정정했다(정책·case·기대 판정은 그대로). 1차 실행의 관측값 35건을 재생한 가짜 `aws` 시험에서 PASS 35/35였고, 키 하나만 달라도 FAIL로 잡히는 것을 확인했다.
- **rev2.1 실제 실행 — PASS 35/35 (exit 0).** 스크립트 SHA-256 `7240f17f6e8dd63423bc450a0a960d386c65a2bd5fae93e91f5312f8ac0cb2c0`(CloudShell `sha256sum` 출력 일치), 2026-10-10 16:04 KST, CloudShell 서울, `321team-hayeoung`, `live_guardrails=MATCH(v1)`. 원본은 `~/sim-rosa-gr-20261010-070419-xmFM/`.

| 묶음 | 결과 |
|---|---|
| A(4)·S(1) 현재 v1 충돌 | explicitDeny 5/5 — 조회·Subscribe도 v1 리전 Deny에 막힘, 거부 Statement는 `DenyOutsideSeoul` |
| B(12) 후보 v2 | allowed 12/12 — 역할·정책·OIDC 조회, ListRoles·ListOpenIDConnectProviders, ROSA Subscribe·ViewSubscriptions |
| **W(11) IaC 허용 정책만(Guardrails 없이)** | **implicitDeny 11/11** — 역할 생성(account·CLI), prefix 정책 생성, ROSA·prefix·Admin 정책 부착, OIDC 생성, trust 변경, 삭제, 태그, PassRole. 위임 역할에는 IAM 쓰기 권한이 없다 |
| N(7) 후보 v2에서도 거부 | 7/7 — 생성·부착 explicitDeny, Unsubscribe explicitDeny, 다른 제품 Subscribe implicitDeny, us-east-1 EC2 explicitDeny, 다른 역할·Admin 정책 조회 implicitDeny |

- **rev2.2(PR21 리뷰 B3)**: `finish()`만 바꿨다. 종료 기록(`meta.txt`)·manifest(`SHA256SUMS`) 생성·대조 중 하나라도 실패하면 PASS로 끝나지 않는다(원래 code가 0이면 1, 0이 아니면 원래 code 유지). 원래 결과는 stderr에 남긴다. 각 단계 RC는 명령 직후 직접 받는다(`if ! ( … ) > file` 형태는 리다이렉트 실패를 놓쳐 쓰지 않음, bash 5.3에서 확인). 정책·case·기대 판정·MissingContextValues 계약은 rev2.1과 같다. 스크립트 SHA-256은 `SHA256SUMS`.
  - 로컬 고장 주입(2026-10-10, Git Bash 5.3, AWS 미접속, `finish()`만 떼어 실행): 정상 exit 0 / meta 쓰기 실패 1 / manifest 쓰기 실패 1 / 해시 계산 실패 1 / manifest 대조 실패 1 / 원래 FAIL 1 / 원래 DIFF(2)+manifest 실패 2 / 원래 DIFF(2) 2. 실제 AWS 실행이 아니다.
  - 위 rev2.1 PASS 35/35는 rev2.1 스크립트(`7240f17f…`) 결과다. rev2.2로 다시 실행하지 않았다.
| MissingContextValues | 35/35 case별 기대값과 일치(implicitDeny 14건은 조건 키 − 제공 키, 나머지 21건은 빈 목록) |

  - 제출 범위: 사용자 화면 출력(case 행·summary 표·result 줄)이다. 원격 폴더의 `meta.txt`·`SHA256SUMS`·case별 input/out JSON은 CloudShell 다운로드 권한이 없어 받지 못했으며, 원격 원본을 재해시했다고 주장하지 않는다.
  - 이 결과는 identity 정책 평가다. 실제 부착·Guardrails 변경·Subscribe·중앙 실행의 Runtime 결과가 아니다.

## rev1 Guardrails 조합 시뮬레이션 결과 (이전 정책 기준) — 2026-10-09 22:58 KST (#35 6078438929 요청 대응)

> 아래는 rev1 정책(IAM 쓰기 포함)과 rev1 스크립트(SHA-256 `4cc90b82…`)의 결과다. rev2에서 정책·스크립트가 바뀌었으므로 현재 판정 근거로 쓰지 않고 이력으로만 남긴다.

- 실행: CloudShell 서울, `321team-hayeoung`, `sim-rosa-guardrails-v2.sh`(SHA-256 `4cc90b82b846fbe5650ec35697f67e04d281192d07337c79b7296b36bb19e22a`). `iam simulate-custom-policy`와 정책 조회만. AWS 변경·Subscribe 0. 비용 없음.
- 원본: CloudShell `~/sim-rosa-gr-20261009-135843/` (case별 input/out/err JSON, summary.tsv, SHA256SUMS). 1차 실행 `~/sim-rosa-gr-20261009-134758/`(B10 FAIL → `ListRoles` Resource `*`로 수정)도 보존.
- 실제 부착 Guardrails: `live_guardrails=MATCH(v1)` — AWS 기본 버전 v1이 PR18 승인 원문(SHA-256 `58c5774c…92fd`)과 정규화 비교상 동일.
- context: `aws:RequestedRegion=us-east-1`(U1 N6 explicit deny 근거), Terraform 생성분은 `Project=fds-hybrid`·`ManagedBy=terraform` 요청 태그.

| 묶음 | 내용 | 결과 |
|---|---|---|
| A (4) | 현재 Guardrails v1 + ROSA 정책: CreateRole(account·ocm)·Subscribe·CreateOpenIDConnectProvider | 4/4 **explicitDeny** — 충돌 실재 |
| S (1) | `DenyOutsideSeoul` 단독 + ROSA 정책 | explicitDeny — 거부 Statement 확정 |
| B (11) | 후보 v2 + ROSA 정책: account/operator/ocm/user role 생성, ocm 정책 생성, ROSA·ECR 정책 부착, OIDC 생성, ROSA Subscribe, ListRoles, ListOpenIDConnectProviders | 11/11 **allowed** |
| N (9) | 후보 v2에서도 거부 유지: 다른 이름 역할, 태그 없음/ManagedBy 불일치, AdministratorAccess 부착, 다른 제품 Subscribe, Unsubscribe, us-east-1 EC2, DeleteRole, UpdateAssumeRolePolicy | 9/9 거부(implicit 5 / explicit 4) |
| K (1) | Cleanup 정책 + 후보 v2: DeleteRole | explicitDeny — 정리 단계에 별도 Guardrails 변경 필요 |

**합계 26/26 PASS.** N01·N02·N03·N04·N09의 MissingContextValues는 해당 case와 무관한 다른 Statement의 조건 키(또는 N02의 의도적 태그 생략)이며 판정에 영향 없음.

후보 Guardrails(rev2): `guardrails-candidate/FDS-IaC-Guardrails.v2-candidate.json` — v1 대비 `DenyOutsideSeoul.NotAction`에 A1 Marketplace 2개와 A3 IAM **조회** 9개, 모두 11개를 정확한 이름으로 추가한 것 외 변경 없음. rev1의 IAM 쓰기 7개(`CreateRole`·`TagRole`·`CreatePolicy`·`TagPolicy`·`AttachRolePolicy`·`CreateOpenIDConnectProvider`·`TagOpenIDConnectProvider`)는 제거했다. `iam:*`·`aws-marketplace:*` 없음.

한계: 시뮬레이션은 identity 정책 평가만이며 실제 API 호출·trust·SCP·리소스 정책은 포함하지 않는다. 실제 동작은 승인 후 부착·실행 단계에서 readback으로 확인한다.
