# #12 ROSA 계정 준비 A1·A3 full policy 초안 — 2026-10-09

상태: **DRAFT / 부여 아님 / 실행 아님**
대상 이슈: [infra-terraform#12](https://github.com/321Team/infra-terraform/issues/12) · 원티켓 [#35](https://github.com/321Team/fds-project-baseline/issues/35)
근거: [v3 보완판](https://github.com/321Team/fds-project-baseline/issues/35#issuecomment-6074050926), [이권욱 실행 자료 요청](https://github.com/321Team/fds-project-baseline/issues/35#issuecomment-6074663186), 실행 자료 [EXECUTION-PACK.md](EXECUTION-PACK.md)
비용: 파일 작성·로컬 문법 검사만 — **비용 없음**

## 한눈에 보기

| 정책 파일 | 단계 | 붙일 곳 | 붙이는 기간 |
|---|---|---|---|
| `FDS-RosaBootstrap-Subscribe.json` | A1 ROSA 활성화 | `FDS-IaC-Operator` (하영 세션) | **A1 1회만.** 활성화 readback 후 바로 떼어냄 |
| `FDS-IaC-RosaPrereq.json` | A3 역할·OIDC 생성·조회 | `FDS-IaC-Operator` | A3 기간. ROSA 운영 중 Terraform plan readback에도 필요 |
| `FDS-IaC-RosaPrereq-Cleanup.json` | 정리(회수) | `FDS-IaC-Operator` | **정리 단계에만.** 클러스터 삭제·공유 참조 확인 후 별도 승인으로 부착 |

- A2(Red Hat 청구 연결)는 AWS 쪽 추가 권한이 필요 없다고 **가정**한다. 실행 직전 화면 흐름에서 거부가 나오면 그 Action만 추가해 리뷰를 받는다.
- 새 실행 역할은 만들지 않는다. `FDS-IaC-Operator`는 이미 `phase2/rosa-prereq/terraform.tfstate` 읽기·쓰기 권한(`FDS-IaC-State-PassRole`)과 MFA·본인 RoleSessionName trust를 갖고 있다.
- 이 정책들에는 `iam:PassRole`이 없다. 클러스터 생성(#4)은 이 범위가 아니다.

## 설계 원칙 (쉽게)

1. **`fds-rosa`로 시작하는 이름만.** 역할·정책·OIDC provider 쓰기는 모두 이름 prefix나 정확한 ARN으로 제한한다.
2. **Terraform이 만드는 것은 우리 태그 필수.** account/operator role과 OIDC provider는 생성 시 `Project=fds-hybrid`, `ManagedBy=terraform` 태그가 없으면 거부된다(기존 IaC 규칙과 같음).
3. **CLI가 만드는 것은 이름으로만 제한.** `ocm-role`·`user-role`은 ROSA CLI가 자체 태그를 붙여서 우리 태그를 강제할 수 없다. 대신 이름 패턴을 좁게 둔다.
4. **ROSA 정책만 붙일 수 있다.** `AttachRolePolicy`는 AWS 관리형 `service-role/ROSA*` 정책, Worker 역할용 `AmazonEC2ContainerRegistryReadOnly`(정확한 ARN 1개), `fds-rosa-*` 정책만 허용한다. 관리자 권한(AdministratorAccess 등)은 붙일 수 없다.
5. **만들기와 지우기는 분리한다.** 삭제 권한은 Cleanup 정책에만 두고 평소에는 붙이지 않는다. 기존 역할의 trust 덮어쓰기(`iam:UpdateAssumeRolePolicy`)는 어느 정책에도 없다.
6. **Unsubscribe는 없다.** A1에는 `Subscribe`·`ViewSubscriptions`만 두고, `ROSAManageSubscription` 관리형 정책은 붙이지 않는다.

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
| CreateTerraformOwnedRosaRoles | `iam:CreateRole`·`TagRole` | Terraform이 account role(Installer·Support·Worker)과 operator role 생성 | `role/fds-rosa-HCP-ROSA-*`, `role/fds-rosa-openshift-*`, `role/fds-rosa-kube-system-*` + 우리 태그 필수 |
| CreateCliOwnedOrgLinkRoles | `iam:CreateRole`·`TagRole` | ROSA CLI가 `ocm-role`·`user-role` 생성 | `role/fds-rosa-OCM-Role-*`, `role/fds-rosa-User-*` |
| CreateCliOwnedRolePolicy | `iam:CreatePolicy`·`TagPolicy` | CLI가 `ocm-role`용 고객 관리형 정책을 만들 때 | `policy/fds-rosa-*` |
| AttachOnlyRosaPolicies | `iam:AttachRolePolicy` | account/operator role에 AWS 관리형 ROSA 정책, Worker 역할에 ECR 읽기 정책, ocm-role에 그 정책 부착 | `role/fds-rosa-*` + 붙일 정책을 `ROSA*`·ECR ReadOnly 1개·`fds-rosa-*`로 제한 |
| CreateTerraformOwnedOidcProvider | `iam:CreateOpenIDConnectProvider`·`TagOpenIDConnectProvider` | Terraform이 managed OIDC config에 대응하는 IAM OIDC provider 생성 | `oidc-provider/oidc.op1.openshiftapps.com/*` + 우리 태그 필수 |

### FDS-IaC-RosaPrereq-Cleanup (정리 단계만)

| Sid | Action | 용도 | Resource 범위 |
|---|---|---|---|
| DetachOnlyRosaPolicies | `iam:DetachRolePolicy` | 역할 삭제 전 ROSA 정책 떼기 | `role/fds-rosa-*` + `ROSA*`·ECR ReadOnly 1개·`fds-rosa-*` 정책만 |
| DeleteRosaRoles | `iam:ListInstanceProfilesForRole`·`DeleteRole` | Terraform destroy·CLI 역할 삭제 | `role/fds-rosa-*` |
| DeleteCliOwnedRolePolicy | `iam:DeletePolicy` | ocm-role용 정책 삭제 | `policy/fds-rosa-*` |
| DeleteRosaOidcProvider | `iam:DeleteOpenIDConnectProvider` | OIDC provider 삭제 | `oidc-provider/oidc.op1.openshiftapps.com/*` |

## ⚠️ 기존 정책과의 충돌 — Guardrails 리전 거부

`FDS-IaC-Guardrails`의 `DenyOutsideSeoul`은 `aws:RequestedRegion != ap-northeast-2`인 요청을 거부한다. 예외(NotAction)는 `iam:GetRole`·`GetInstanceProfile`·`PassRole`·`sts:GetCallerIdentity` 4개뿐이다.

- IAM과 Marketplace는 글로벌 서비스라 요청 리전이 **us-east-1**로 평가되는 것으로 알고 있다. 그러면 위 A1·A3 Action 대부분이 Guardrails의 명시적 거부에 막혀 **허용 정책을 붙여도 실행되지 않는다.**
- 제안: `DenyOutsideSeoul` NotAction에 이 초안의 IAM·Marketplace Action을 **정확한 이름으로** 추가한다(`iam:*` 와일드카드는 쓰지 않음). Guardrails는 이권욱 IaC Grant 준비안([PR18](https://github.com/321Team/infra-terraform/pull/18)) 범위이므로 그쪽 판단으로 반영한다.
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
| 4 | managed OIDC issuer 호스트(`oidc.op1.openshiftapps.com`) | `rosa create oidc-config --managed --mode manual` 출력 또는 Red Hat 문서로 확인 | 없음 |
| 5 | account/operator role trust 내용 | Terraform rhcs data source(`rhcs_hcp_policies` 등)가 주는 Red Hat principal·OIDC 조건. `terraform plan` 출력으로 확인 후 첨부 | 없음 |
| 6 | 콘솔 A1 흐름에서 추가 Action 필요 여부 | 실행 직전 화면 확인. 거부 시 그 Action만 추가 리뷰 | 없음 |
| 7 | 도구 pin | Terraform 1.16.4 바이너리 SHA-256, `.terraform.lock.hcl`(AWS 6.66.0·rhcs 1.7.9). **ROSA CLI 확인 완료**(아래) | 없음 |

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

| CLI 명령 | 출력된 aws 호출 | 생성 이름 | 이 초안 Sid |
|---|---|---|---|
| `create ocm-role` (admin 질문 없음 = basic) | `iam create-role`(tags), `iam create-policy`(tags), `iam attach-role-policy` → `rosa link ocm-role` | 역할 `fds-rosa-OCM-Role-<조직 External ID>`, 정책 `fds-rosa-OCM-Role-<조직 External ID>-Policy` | CreateCliOwnedOrgLinkRoles, CreateCliOwnedRolePolicy, AttachOnlyRosaPolicies |
| `create user-role` | `iam create-role`(tags, 정책 부착 없음) → `rosa link user-role` | `fds-rosa-User-<Red Hat 사용자명>-Role` | CreateCliOwnedOrgLinkRoles |
| `create account-roles --hosted-cp` (Terraform으로 만들 대상, 이름·정책 대조용) | `iam create-role` ×3, `iam attach-role-policy` ×4 | `fds-rosa-HCP-ROSA-Installer/Support/Worker-Role` | CreateTerraformOwnedRosaRoles, AttachOnlyRosaPolicies |

- Worker 역할에는 `ROSAWorkerInstancePolicy` 외에 **`arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly`**도 붙는다. 처음 초안의 부착 조건(`ROSA*`만)은 이를 막았으므로 정확한 ARN 1개를 추가했다.
- CLI가 붙이는 태그: `red-hat-managed=true`, `rosa_role_prefix=fds-rosa`, `rosa_role_type`, `rosa_openshift_version=4.22` 등. Terraform 생성분은 여기에 `Project`·`ManagedBy`가 더해진다.
- user-role 이름에 Red Hat 사용자명이 들어가므로 공개 문서에서는 마스킹한다.
- `iam:CreateRole`·`CreatePolicy`에 tag가 함께 전달되므로 `iam:TagRole`·`iam:TagPolicy`가 필요하다(초안에 포함).

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
- 이 정책은 CLI가 `fds-rosa-OCM-Role-<조직 External ID>-Policy`로 만들며, 그 생성·부착은 이 초안의 CreateCliOwnedRolePolicy·AttachOnlyRosaPolicies가 허용한다.

- 3·4는 `rosa login`(하영 Red Hat 토큰, 비공유)이 필요하다. 출력에 토큰은 없지만 증적에 넣기 전에 확인한다.
- 위 확인 결과로 이 JSON의 이름 패턴·Action을 고치면 SHA256SUMS를 다시 만든다.

## 알려진 위험과 대응

| 위험 | 대응 |
|---|---|
| `iam:CreateRole`은 trust 내용을 제한할 수 없어, `fds-rosa-*` 이름으로 아무 principal을 믿는 역할을 만들 수 있다 | 붙일 수 있는 정책이 ROSA 관리형·`fds-rosa-*`로 제한되고 PassRole이 없다. 생성 후 trust readback을 rhcs data source 값과 대조한다 |
| CLI 역할(`ocm-role`·`user-role`)은 우리 태그를 강제할 수 없다 | 이름 패턴을 좁게 두고 §inventory(실행 자료 §2)에 ARN을 기록한다 |
| `iam:TagRole`에 태그 조건이 있어 Terraform이 다른 태그만 바꾸는 갱신은 거부될 수 있다 | 의도된 동작. 필요하면 그때 리뷰를 받는다 |

## Guardrails 조합 시뮬레이션 결과 — 2026-10-09 22:58 KST (#35 6078438929 요청 대응)

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

후보 Guardrails: `guardrails-candidate/FDS-IaC-Guardrails.v2-candidate.json` — v1 대비 `DenyOutsideSeoul.NotAction`에 A1/A3 Action 18개를 정확한 이름으로 추가한 것 외 변경 없음. `iam:*`·`aws-marketplace:*` 없음. Cleanup Action은 미포함(정리 단계에서 별도 변경안).

한계: 시뮬레이션은 identity 정책 평가만이며 실제 API 호출·trust·SCP·리소스 정책은 포함하지 않는다. 실제 동작은 승인 후 부착·실행 단계에서 readback으로 확인한다.
