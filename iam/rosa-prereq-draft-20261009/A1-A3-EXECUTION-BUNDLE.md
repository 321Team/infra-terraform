# #12 ROSA 계정 준비 A1~A3 실행 묶음 — 절차와 승인 요청 (하영, 2026-10-12)

대상: [infra-terraform#12](https://github.com/321Team/infra-terraform/issues/12) (#35 Sub-task 5/6) · G4 입력 5(ROSA 생성 준비)
상태: **문서 / 실행 승인 요청. 이 문서 자체로는 아무것도 실행하지 않는다.**

## 0. 한눈에 보기

| 묶음 | 하는 일 | 쉬운 뜻 |
|---|---|---|
| A1 활성화 | AWS Marketplace에서 ROSA 구독 | ROSA를 쓰겠다고 가입 |
| A2 연결 | AWS 계정 ↔ 이하영 Red Hat 조직 청구 연결 | 가입 정보를 Red Hat에 등록 |
| A3 역할·OIDC | ocm-role·user-role(CLI), account role 3 + managed OIDC + OIDC provider(Terraform 단계 1), operator role 8(Terraform 단계 2) | Red Hat이 우리 AWS에서 쓸 출입증과 신분 확인 창구 |

**기준 소스(모두 main 병합·독립 승인 완료)**

| 항목 | 위치 | 승인 |
|---|---|---|
| A1·A3 정책, Guardrails v2 후보, 시뮬레이션 35/35 | `iam/rosa-prereq-draft-20261009/` | PR21 — 이권욱 APPROVED·병합 10-10 |
| Terraform `rosa-prereq` + lock | `terraform/rosa-prereq/` | PR21 |
| 부여 실행기 `rosa_grant.py`, plan/readback 대조기 `rosa_prereq_check.py` | `tools/` | PR24 — 이권욱 APPROVED·병합 10-11 (CloudShell 70/70) |
| 실행 시 고정할 main SHA | `<실행 직전 기록>` | — |

**비용:** managed OIDC라 S3·Secrets Manager를 만들지 않는다. 이 묶음이 만드는 것은 IAM 역할·정책, Marketplace 구독, Red Hat 연결뿐이다. 클러스터 요금은 infra-rosa#4 생성부터다. **금액 판정은 이권욱(#34 교육장 리포트 기준)에게 맡긴다.**

## 1. 승인 요청 항목 (이권욱)

| # | 결정할 것 | 제안 | 비고 |
|---|---|---|---|
| D1 | **중앙 실행 주체(IAM 쓰기 identity)** | 아래 §1-1 참고 | ⚠️ 핵심 미결 |
| D2 | 작업창 | 10-13(월) 중 1회, 하영·중앙 실행자 동시 접속 | G4 10-14 전 |
| D3 | Guardrails v1 → v2 전환 | 승인 요청 (NotAction +11, IAM 쓰기 없음) | `rosa_grant.py guardrails-v2` |
| D4 | 정책 2개 생성·부착 | Subscribe(A1 동안만), RosaPrereq(조회 전용) | `rosa_grant.py` |
| D5 | A1 활성화, A2 연결 실행 | 승인 요청 | 하영 실행 |
| D6 | A3 중앙 apply(ocm-role/user-role, 단계 1, 단계 2) | 승인 요청 | plan 대조기 PASS일 때만 |
| D7 | 이권욱·이재환 Red Hat 조직 초대 | A2 직후 | v3 §3 ② |

### 1-1. D1 — 중앙 실행 주체 (결정 필요)

- 설계상 IAM 쓰기(정책 생성·부착, Guardrails 버전 변경, A3 역할·OIDC 생성)는 **위임 역할 `FDS-IaC-Operator`가 하지 않는다**(PR21 rev2, 리뷰 차단 1 대응).
- `phase2/rosa-prereq` state 쓰기는 bucket policy상 `FDS-IaC-Operator`와 root만 허용된다.
- 그런데 10-09 이권욱 확인에 따르면 **root는 IaC IAM 초기 설정에만 쓰고 이후 사용하지 않는다.**
- 따라서 지금 문서들만으로는 **A3를 실제로 누가 어떤 identity로 실행할지가 비어 있다.** 선택지:

| 안 | 내용 | 장단점 |
|---|---|---|
| ① root 1회 예외 | 교육장 root로 이 묶음의 IAM 쓰기만 1회 수행, 이후 미사용 | 가장 간단. "root 미사용" 원칙에 명시적 예외 승인 필요 |
| ② 임시 중앙 역할 | root로 최소권한 임시 역할 1개를 만들고 그 역할로 실행, 끝나면 회수 | 원칙에 더 맞음. 역할·정책·state 접근 설계와 리뷰가 추가로 필요해 일정 부담 |
| ③ 교육장 지정 경로 | 교육장이 제공하는 다른 관리 경로 | 존재·조건 확인 필요 |

→ **이권욱 판단 요청.** 정해지면 그 ARN을 `rosa_grant.py --expected-caller`와 plan 대조 기록에 고정한다.

## 2. 선행 조건 (실행 당일 시작 전 전부 확인)

| # | 조건 | 확인 방법 | 상태 |
|---|---|---|---|
| P1 | PR21·PR24 병합본 = 실행 SHA | `git rev-parse HEAD`, `sha256sum -c iam/rosa-prereq-draft-20261009/SHA256SUMS` | 실행일 |
| P2 | D1~D7 승인 | #35 댓글 | 대기 |
| P3 | `FDS-IaC-Operator` 존재, 기본 부착 4개·inline 0 | `rosa_grant.py status` | 실행일 |
| P4 | live Guardrails = v1 원문 | `rosa_grant.py status`(guardrails_default=v1) | 실행일 |
| P5 | 도구 고정 | Terraform 1.16.4·ROSA CLI 1.2.53 바이너리 SHA-256(README 표), provider lock | 실행일 |
| P6 | 하영 Red Hat 로그인 가능, Org Admin | `rosa login --use-device-code`, `rosa whoami`(조직 `2042****`) | 실행일 |
| P7 | 비공개 tfvars(`rh_support_principal_arn`) 준비 | CLI `sts_support_trust_policy.json` 값과 동일 | 실행일 |
| P8 | ledger 폴더(0700, 저장소 밖) | `rosa_grant.py`가 검사 | 실행일 |

## 3. 실행 순서

공통 규칙: **한 단계 = 쓰기 1건 → readback → 다음.** readback이 실패하거나 도구가 STOP하면 다음 단계로 가지 않는다. `rosa_grant.py`는 기본 dry-run이며, 각 단계는 dry-run 출력 확인 후 `--execute`를 붙인다.

`G="python3 tools/rosa_grant.py --expected-caller <D1 ARN> --ledger-dir <비공개 0700 경로>"`

| 순서 | 묶음 | 누가 | 명령 / 동작 | readback (통과 기준) | 실패 시 |
|---|---|---|---|---|---|
| 0 | 사전 | 중앙 | `$G status` | guardrails_default=v1, role 기본 4·inline 0, 미확정 회차 0 | 시작 안 함 |
| 1 | 준비 | 중앙 | `$G guardrails-v2` → `--execute` | `result=VERIFIED`, 기본 버전=v2 원문 | STOP → `reconcile` |
| 2 | A1 | 중앙 | `$G subscribe-create` → `--execute` | VERIFIED, 미부착 | STOP |
| 3 | A1 | 중앙 | `$G subscribe-attach` → `--execute` | VERIFIED, FDS-IaC-Operator에만 부착 | STOP |
| 4 | **A1** | 하영 | 콘솔에서 `FDS-IaC-Operator`(본인 MFA)로 전환 → ROSA 콘솔 "ROSA HCP 활성화" | 콘솔에 활성화 완료 표시(계정·시각 캡처). 추가 권한 거부가 나오면 그 Action만 기록하고 STOP | STOP, 3번까지 유지한 채 보고 |
| 5 | A1 | 중앙 | `$G subscribe-detach` → `--execute` | VERIFIED, 분리됨 | STOP |
| 6 | **A2** | 하영 | 같은 콘솔에서 "Red Hat으로 계속" → 이하영 Red Hat 로그인 → 연결 | console.redhat.com에 AWS `774055931866` 청구 연결 표시 + AWS 콘솔 연결 상태(캡처) | STOP |
| 7 | A2 후속 | 하영 | 이권욱·이재환 조직 초대(최소 역할) | 각자 본인 로그인으로 `rosa whoami` | 초대만 보류, 다음 진행 가능 |
| 8 | A3 준비 | 중앙 | `$G prereq-create` → `--execute`, `$G prereq-attach` → `--execute` | 각 VERIFIED, RosaPrereq(조회 전용) 부착 | STOP |
| 9 | **A3** CLI | 하영 → 중앙 | 하영: `rosa create ocm-role --prefix fds-rosa --mode manual`, `rosa create user-role --prefix fds-rosa --mode manual` 출력 저장. 중앙: 10-09 확인본과 이름·정책·trust가 같은지 대조 후 **출력된 aws 명령만** 실행(`--mode auto` 금지). 하영: `rosa link ocm-role/user-role --role-arn ...` | `rosa list ocm-role`·`user-role` Linked, `aws iam get-role` trust ExternalId 일치 | STOP |
| 10 | **A3** 단계 1 | 중앙 | `terraform/rosa-prereq`: `init -backend-config=backend.hcl` → `plan -var execution_enabled=true -var-file=<비공개> -out=stage1.plan` → `terraform show -json stage1.plan > stage1.plan.json` → `python3 tools/rosa_prereq_check.py plan --stage 1 --support-principal <값> stage1.plan.json` | **대조기 `result=PASS`(exit 0)일 때만** `apply stage1.plan` | apply 안 함 |
| 11 | A3 단계 1 확인 | 중앙(또는 하영 조회) | `python3 tools/rosa_prereq_check.py readback --stage 1 --support-principal <값>`, `rosa list account-roles`, `rosa list oidc-config` | PASS, `oidc_host` 기록(=`oidc.op1.openshiftapps.com/<id>`) | 단계 2 금지 |
| 12 | A3 단계 2 전 대조 | 하영 | `rosa create operator-roles --hosted-cp --prefix fds-rosa --oidc-config-id <id> --installer-role-arn <installer arn> --mode manual` | 이름·namespace·service account·정책이 `main.tf` `operator_roles`와 같음 | 다르면 코드 수정 → 리뷰 → 재승인 |
| 13 | **A3** 단계 2 | 중앙 | `plan -var execution_enabled=true -var create_operator_roles=true ...` → show -json → `rosa_prereq_check.py plan --stage 2 --oidc-host <11번 값> ...` | PASS(생성 8+8, 단계 1 no-op, 변경·삭제 0)일 때만 apply | apply 안 함 |
| 14 | A3 단계 2 확인 | 중앙(또는 하영 조회) | `rosa_prereq_check.py readback --stage 2 ...`, `rosa list operator-roles` | PASS | 보고 |
| 15 | 정리 | 하영 | 증적 정리(§5) → 증적 PR | — | — |

예상 소요: 0~8번 약 1시간, 9~14번 약 1~2시간(IAM 반영 대기 포함). 같은 작업창에서 끝내지 못하면 **완료된 단계까지만 유지**하고 다음 작업창에서 0번(status)부터 다시 시작한다.

## 4. 멈춤·되돌림

- **공통 STOP**: 도구 exit≠0, readback 불일치, 예상 밖 권한 거부, 승인 표에 없는 자원·principal·정책, 미확정 회차, 비용 Hard Stop 신호(판정 이권욱).
- **미확정 회차**: `$G reconcile --run-id <id>`. 결과가 AMBIGUOUS면 그대로 두고 보고한다. "반영 안 됨"은 CloudTrail 등 증거를 검토자가 확인한 뒤에만 `confirm-not-applied --evidence ... --reviewer ...`로 기록한다(PR24 B3).
- **되돌림 순서**(필요할 때만, 각각 별도 판단): Terraform 단계 2 → 단계 1 destroy(중앙) → ocm-role·user-role 연결 해제·삭제 → `$G prereq-detach` → `prereq-delete` → `subscribe-delete` → `guardrails-v1`. 클러스터가 없을 때만 IAM·OIDC를 회수한다(실행 자료 §2). Marketplace 구독 해지는 이 묶음 범위가 아니다.
- **하지 않는 것**: 기존 역할 덮어쓰기, 일괄 삭제, `--mode auto`, 승인 밖 권한 임시 부여, 실패 후 무조건 재실행.

## 5. 증적

| 항목 | 내용 |
|---|---|
| 도구 ledger | `rosa_grant.py` ledger(INTENT/WRITE_RETURNED/READBACK, argv·RC·UTC·PolicyId) |
| plan·대조 | `stage1/2.plan.json` 해시, `rosa_prereq_check.py` 출력(조직 ID 마스킹) |
| CLI | `--mode manual` 출력 원문, 실행한 aws 명령·RC, `rosa list ...` 출력 |
| 콘솔 | A1 활성화, A2 연결 화면(계정·시각 포함) |
| 역할 대응표 | account/operator role ARN, OIDC config ID, OIDC provider ARN, ocm-role/user-role ARN |
| 제외 | 토큰·비밀키·이메일·Red Hat 사용자명·조직 External ID 원문 |
| 편입 | `321Team/fds-project-evidence` `evidence/P2-IAC-01/` 증적 PR, 독립 리뷰 |

#12 완료 조건 대응: ① A1~A3 실행 묶음 리뷰 승인 = 이 문서 승인(D1~D7) ② role·OIDC readback = 11·14번 PASS ③ 증적 = §5 증적 PR.

## 6. 실행 경계

Apply 전 Hard Gate(원티켓 2026-10-02 v2)를 따른다. 이 묶음은 IAM·구독·연결만 다루며 VPC/VPN/ROSA 클러스터 생성은 포함하지 않는다. state·tfvars·자격증명은 저장소에 커밋하지 않는다. 실행 결과 수용·G4 판정은 별도다.
