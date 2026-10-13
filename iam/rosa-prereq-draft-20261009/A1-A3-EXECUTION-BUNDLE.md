# #12 ROSA 계정 준비 A1~A3 실행 묶음 — 절차와 승인 요청 (하영, 2026-10-12)

대상: [infra-terraform#12](https://github.com/321Team/infra-terraform/issues/12) (#35 Sub-task 5/6) · G4 입력 5(ROSA 생성 준비)
상태: **문서 / 실행 승인 요청. 이 문서 자체로는 아무것도 실행하지 않는다.**
개정: 2026-10-13 — PR28 리뷰([6141088957](https://github.com/321Team/infra-terraform/pull/28#issuecomment-6141088957)) 반영. 초기 설치와 재개 경로를 분리하고(§3-1), 권한 유지·회수 기준을 최신 결정으로 바꿨다(§4-1).

## 0. 한눈에 보기

| 묶음 | 하는 일 | 쉬운 뜻 |
|---|---|---|
| A1 활성화 | AWS Marketplace에서 ROSA 구독 | ROSA를 쓰겠다고 가입 |
| A2 연결 | AWS 계정 ↔ 이하영 Red Hat 조직 청구 연결 | 가입 정보를 Red Hat에 등록 |
| A3 역할·OIDC | 기본 ocm-role(CLI, user-role 제외), account role 3 + managed OIDC + OIDC provider(Terraform 단계 1), operator role 8(Terraform 단계 2) | Red Hat이 우리 AWS에서 쓸 출입증과 신분 확인 창구 |

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
| D1 | **중앙 실행 주체(IAM 쓰기 identity)** | 교육장 중앙 관리 경로의 기승인 한정 사용(§1-1) | 실행 때마다 caller ARN 확인·기록 |
| D2 | 작업창 | 단계별 승인과 실제 준비·비중첩 조건으로 판단. A1/A2는 10-13(화) 17:30~18:30 KST 한정 승인([6141012088](https://github.com/321Team/infra-terraform/issues/12#issuecomment-6141012088), [6141247655](https://github.com/321Team/infra-terraform/issues/12#issuecomment-6141247655)) | D7 초대 미완료는 A1 차단 사유가 아님 |
| D3 | Guardrails v1 → v2 전환 | 기승인([6120545216](https://github.com/321Team/infra-terraform/issues/12#issuecomment-6120545216)) · **실행 완료** 10-12 18:47 VERIFIED([6122063075](https://github.com/321Team/infra-terraform/issues/12#issuecomment-6122063075)) | 재개 때 다시 실행하지 않음 |
| D4 | 정책 2개 생성·부착 | 기승인 · **실행 완료** 10-12: Subscribe 생성 후 미부착 보관, RosaPrereq 생성·부착([6122063075](https://github.com/321Team/infra-terraform/issues/12#issuecomment-6122063075)) | 재개 때는 Subscribe attach만(§3-1) |
| D5 | A1 활성화, A2 연결 실행 | 기승인([6120545216](https://github.com/321Team/infra-terraform/issues/12#issuecomment-6120545216)) · 10-12 실제 준비 완료 · 10-13 재개 작업창 승인. **A1/A2 실제 성공은 아직 미확인** | 하영 실행 |
| D6 | A3를 4개로 나눠 판정 | **OCM basic**: 기승인(#12 6121083000, 역할1+정책1+부착1+연결1, 직전 확인 조건부) / **user-role**: 미요청, 필요·범위 별도 검토 전 실행 안 함 / **A3-1(단계 1)**: Plan 기승인, Apply는 saved Plan 독립 검토·명시 GO 후 / **A3-2(단계 2)**: 같은 방식 | 대조기 PASS는 기계 검사이며 실행 GO가 아님. 별도 티켓·중복 Plan은 만들지 않음 |
| D7 | 이권욱·이재환 Red Hat 조직 초대 | A2 직후 | v3 §3 ② |

### 1-1. D1 — 중앙 실행 주체

- 설계상 IAM 쓰기(정책 생성·부착, Guardrails 버전 변경, A3 역할·OIDC 생성)는 **위임 역할 `FDS-IaC-Operator`가 하지 않는다**(PR21 rev2, 리뷰 차단 1 대응).
- 결정: 교육장 **중앙 관리 경로의 이미 승인된 한정 사용**으로 IAM 쓰기를 수행한다. 10-12 권한 준비 6쓰기가 이 경로로 수행됐다([6122063075](https://github.com/321Team/infra-terraform/issues/12#issuecomment-6122063075)).
- 실행 때마다 caller ARN을 확인해 `rosa_grant.py --expected-caller`와 ledger에 고정한다.
- 이 결정은 A1~A3 권한 준비 단계에 한정한다. **A3 Terraform Apply를 root로 포괄 승인하는 것이 아니다.** A3 Apply는 saved Plan 독립 검토·명시 GO를 따로 받는다(D6).

## 2. 선행 조건 (실행 당일 시작 전 전부 확인)

| # | 조건 | 확인 방법 | 상태 |
|---|---|---|---|
| P1 | PR21·PR24 병합본 = 실행 SHA | `git rev-parse HEAD`, `sha256sum -c iam/rosa-prereq-draft-20261009/SHA256SUMS` | 실행일 |
| P2 | D1~D7 승인 | #35 댓글 | 대기 |
| P3 | `FDS-IaC-Operator` 존재. **초기:** 기본 부착 4개·inline 0 / **재개:** §3-1 기대값 | `rosa_grant.py status` | 실행일 |
| P4 | **초기:** live Guardrails = v1 원문 / **재개:** v2 원문(되돌리지 않음) | `rosa_grant.py status` | 실행일 |
| P5 | 도구 고정 | Terraform 1.16.4·ROSA CLI 1.2.53 바이너리 SHA-256(README 표), provider lock | 실행일 |
| P6 | 하영 Red Hat 로그인 가능, Org Admin | `rosa login --use-device-code`, `rosa whoami`(조직 `2042****`) | 실행일 |
| P7 | 비공개 tfvars(`rh_support_principal_arn`) 준비 | CLI `sts_support_trust_policy.json` 값과 동일 | 실행일 |
| P8 | ledger 폴더(0700, 저장소 밖) | `rosa_grant.py`가 검사 | 실행일 |

## 3. 실행 순서

공통 규칙: **한 단계 = 쓰기 1건 → readback → 다음.** readback이 실패하거나 도구가 STOP하면 다음 단계로 가지 않는다. `rosa_grant.py`는 기본 dry-run이며, 각 단계는 dry-run 출력 확인 후 `--execute`를 붙인다.

`G="python3 tools/rosa_grant.py --expected-caller <D1 ARN> --ledger-dir <비공개 0700 경로>"`

| 순서 | 묶음 | 누가 | 명령 / 동작 | readback (통과 기준) | 실패 시 |
|---|---|---|---|---|---|
| 0 | 사전(초기 설치 전용, 재개는 §3-1) | 중앙 | `$G status` | guardrails_default=v1, role 기본 4·inline 0, 미확정 회차 0 | 시작 안 함 |
| 1 | 준비 | 중앙 | `$G guardrails-v2` → `--execute` | `result=VERIFIED`, 기본 버전=v2 원문 | STOP → `reconcile` |
| 2 | A1 | 중앙 | `$G subscribe-create` → `--execute` | VERIFIED, 미부착 | STOP |
| 3 | A1 | 중앙 | `$G subscribe-attach` → `--execute` | VERIFIED, FDS-IaC-Operator에만 부착 | STOP |
| 4 | **A1** | 하영 | 콘솔에서 `FDS-IaC-Operator`(본인 MFA)로 전환 → ROSA 콘솔 "ROSA HCP 활성화" | 콘솔에 활성화 완료 표시(계정·시각 캡처)와 실제 활성 상태 readback. 추가 권한 거부가 나오면 그 Action만 기록하고 STOP. 응답이 불명확하면 버튼을 다시 누르지 않고 실제 활성 상태부터 조회 | STOP. Subscribe 처리는 §4-1 |
| 5 | A1 | 중앙 | **A1 성공 readback + 이권욱 검증 종료·재시험 불필요 판정 후에만** `$G subscribe-detach` → `--execute` | VERIFIED, 역할/사용자/그룹 연결 0. 정책 객체는 기존 PolicyId로 미부착 보관 | STOP. 판정 전에는 §4-1에 따라 유지 |
| 6 | **A2** | 하영 | 같은 콘솔에서 "Red Hat으로 계속" → 이하영 Red Hat 로그인 → 연결 | console.redhat.com에 AWS `774055931866` 청구 연결 표시 + AWS 콘솔 연결 상태(캡처) | STOP |
| 7 | A2 후속 | 하영 | 이권욱·이재환 조직 초대(최소 역할) | 각자 본인 로그인으로 `rosa whoami` | 초대만 보류, 다음 진행 가능 |
| 8 | A3 준비 | 중앙 | `$G prereq-create` → `--execute`, `$G prereq-attach` → `--execute` | 각 VERIFIED, RosaPrereq(조회 전용) 부착 | STOP |
| 9 | **A3** OCM basic | 중앙(IAM 3쓰기) → 하영(link) | **기승인 basic ocm-role만** 수행한다. 직전에 고정본 3파일(trust·permission·manual 명령) 재해시, 같은 계정 1866·Red Hat production 조직·로그인 fresh 확인, exact role/policy·조직 연결 상태 조회(NoSuchEntity와 조회 실패 구분, 이미 있으면 재생성하지 않고 대조·보고), OrgAdmin unlink 담당·접근 확인. 중앙: manual 출력의 aws 명령 3개만 실행(`--mode auto` 금지). 하영: 본인 Red Hat 로그인으로 `rosa link ocm-role --role-arn ...`. **user-role은 필요·범위 별도 검토 전 실행하지 않는다.** | trust·policy 원문 구조가 고정본과 일치, attached 1·inline 0·boundary 0, admin 권한 없음, RoleId/PolicyId/default version, `rosa list ocm-role` Linked | STOP. 연결 이후 원복은 unlink → 연결 부재 readback → 정책 분리/역할·정책 정리 |
| 10 | **A3** 단계 1 | 중앙 | `terraform/rosa-prereq`: `init -backend-config=backend.hcl` → `plan -var execution_enabled=true -var-file=<비공개> -out=stage1.plan` → `terraform show -json stage1.plan > stage1.plan.json` → `python3 tools/rosa_prereq_check.py plan --stage 1 --support-principal <값> stage1.plan.json` | saved Plan(`stage1.plan`)·plan JSON·해시·source/lock/입력·state 기준을 제출한다. **대조기 PASS + 이 saved Plan의 독립 검토·명시 GO + 작업창**이 모두 충족될 때만 정확히 그 Plan을 apply한다 | apply 안 함 |
| 11 | A3 단계 1 확인 | 중앙(또는 하영 조회) | `python3 tools/rosa_prereq_check.py readback --stage 1 --support-principal <값>`, `rosa list account-roles`, `rosa list oidc-config` | PASS, `oidc_host` 기록(=`oidc.op1.openshiftapps.com/<id>`) | 단계 2 금지 |
| 12 | A3 단계 2 전 대조 | 하영 | `rosa create operator-roles --hosted-cp --prefix fds-rosa --oidc-config-id <id> --installer-role-arn <installer arn> --mode manual` | 이름·namespace·service account·정책이 `main.tf` `operator_roles`와 같음 | 다르면 코드 수정 → 리뷰 → 재승인 |
| 13 | **A3** 단계 2 | 중앙 | `plan -var execution_enabled=true -var create_operator_roles=true ...` → show -json → `rosa_prereq_check.py plan --stage 2 --oidc-host <11번 값> ...` | 단계 2 saved Plan·plan JSON·해시·source/lock/입력·state 기준을 제출한다. **대조기 PASS(생성 8+8, 단계 1 no-op, 변경·삭제 0) + 이 saved Plan의 독립 검토·명시 GO + 작업창**이 모두 충족될 때만 정확히 그 Plan을 apply한다 | apply 안 함 |
| 14 | A3 단계 2 확인 | 중앙(또는 하영 조회) | `rosa_prereq_check.py readback --stage 2 ...`, `rosa list operator-roles` | PASS | 보고 |
| 15 | 정리 | 하영 | 증적 정리(§5) → 증적 PR | — | — |

예상 소요: 0~8번 약 1시간, 9~14번 약 1~2시간(IAM 반영 대기 포함). 위 표의 0·1·2·8번은 **초기 상태 전용**이다. 같은 작업창에서 끝내지 못하면 완료된 단계까지만 유지하고, 다음 작업창은 §3-1 재개 경로로 시작한다.

### 3-1. 재개 경로 (이미 일부 단계를 수행한 뒤)

기준: 마지막 승인 receipt [6122063075](https://github.com/321Team/infra-terraform/issues/12#issuecomment-6122063075) — Guardrails v2 / 기본 4 + RosaPrereq 1 / inline 0 / Subscribe 객체 존재·미부착 / 미확정 회차 0. 이 값은 그때의 결과이며 **당일 상태를 대신하지 않는다.**

| 위치 | 재개 경로에서 하는 일 |
|---|---|
| P3/P4·순서 0 | 당일 `$G status`로 위 기대값을 확인한다. **rc 0만으로 PASS 처리하지 않는다**(UNRESOLVED가 있어도 rc 0) — 출력의 미확정 회차 0을 확인한다. 다르면 원인을 확인하고 멈춘다. 과거 기록으로 현재 PASS를 대신하지 않는다 |
| 순서 1·2·8 | 이미 끝난 Guardrails 전환·정책 생성·RosaPrereq 부착은 원문·PolicyId·ledger·현재 연결을 대조해 **재사용**한다. 다시 실행하지 않는다. 문서에 맞추려고 v1으로 되돌리거나 검증 중인 권한을 지우지 않는다 |
| 순서 3 | 기존 ledger의 Subscribe(고정 해시 `d3dca1500541ff3b12ccf0bcd69c31e8174a5e5978a554124e09090d5b052644`)가 **미부착일 때만** dry-run/precheck → attach → VERIFIED. 승인된 역할에 이미 정확히 붙어 있으면 PolicyId·원문·다른 연결 부재를 확인하고 재사용한다. 원문·소유 불일치나 미확정이면 STOP. 새 ledger로 이름만 같은 정책을 채택하지 않는다 |
| 순서 4~7 | 위 표와 같다. 중앙 VERIFIED 알림 뒤 승인 작업창 안에서만 시작한다 |


## 4. 멈춤·되돌림

- **공통 STOP**: 도구 exit≠0, readback 불일치, 예상 밖 권한 거부, 승인 표에 없는 자원·principal·정책, 미확정 회차, 비용 Hard Stop 신호(판정 이권욱).
- **미확정 회차**: `$G reconcile --run-id <id>`. 결과가 AMBIGUOUS면 그대로 두고 보고한다. "반영 안 됨"은 CloudTrail 등 증거를 검토자가 확인한 뒤에만 `confirm-not-applied --evidence ... --reviewer ...`로 기록한다(PR24 B3).
- **되돌림 순서**(필요할 때만, 각각 별도 판단): Terraform 단계 2 → 단계 1 destroy(중앙) → ocm-role 연결 해제(unlink)·연결 부재 확인·정책 분리·삭제 → `$G prereq-detach` → `prereq-delete` → `subscribe-detach` → 연결 0 readback → `subscribe-delete` → `guardrails-v1`. Subscribe가 이미 미부착이면 detach를 다시 실행하지 않고 조회 결과를 쓴다. 정상 회수는 미부착 보관까지이며 객체 삭제·Guardrails v1 전환을 자동 실행하지 않는다. 다른 승인된 검증이 쓰는 RosaPrereq/v2는 A1 완료만으로 함께 회수하지 않는다. 클러스터가 없을 때만 IAM·OIDC를 회수한다(실행 자료 §2). Marketplace 구독 해지는 이 묶음 범위가 아니다.
### 4-1. 권한 유지·회수 기준 (B2, 최신 결정 적용)

[검증기간 권한 유지 결정](https://github.com/321Team/infra-terraform/issues/12#issuecomment-6122519296)을 적용한다. 새 포괄 권한 허용이 아니다.

- A1 성공을 readback하고 이권욱이 검증 종료·재시험 불필요를 판정하면 Subscribe를 분리하고 모든 연결 부재를 확인한다.
- 실패·미완료·단순 대기·일과/작업창 종료만으로는 승인된 재시험에 필요한 최소 권한을 반복 회수·재부여하지 않는다. 실제 부착 상태·사용 목적·잔여와 종료 판정자(이권욱)를 ledger/작업 기록에 남긴다.
- 작업창 종료 뒤 새 쓰기는 멈춘다. 권한 유지가 다음 실행 GO를 뜻하지 않는다.
- 응답이 불명확하면 활성화 실제 상태를 먼저 조회하고 재실행하지 않는다. IAM 미확정 회차는 별도로 reconcile한다. 활성화 UI의 불명확을 IAM ledger reconcile만으로 해소했다고 하지 않는다.
- 오부여·보안 사고가 확인되거나 검증 중단/종료로 판정되면 회수한다.
- 실패가 곧 검증 종료는 아니다. 반대로 성공 버튼 응답만으로 실제 상태 확인과 종료 판정을 생략하지 않는다.

| 경로 | Subscribe 처리 |
|---|---|
| 성공 + 실제 활성 확인 + 종료 판정 | detach → 연결 0 readback, 객체는 미부착 보관 |
| 재시험 대기(실패·미완료) | 최소 권한 유지, 목적·잔여·판정자 기록, 새 쓰기는 다음 승인 창까지 중지 |
| 응답 불명확 | 재실행 금지, 활성 상태 조회 → IAM 미확정은 reconcile |
| 작업창 종료 | 신규 쓰기 착수 중지, 진행 중 결과 확인·증적 보존. 시각만으로 자동 회수·자동 재개하지 않음 |

- **하지 않는 것**: 기존 역할 덮어쓰기, 일괄 삭제, `--mode auto`, 승인 밖 권한 임시 부여, 실패 후 무조건 재실행.

## 5. 증적

| 항목 | 내용 |
|---|---|
| 도구 ledger | `rosa_grant.py` ledger(INTENT/WRITE_RETURNED/READBACK, argv·RC·UTC·PolicyId) |
| plan·대조 | `stage1/2.plan.json` 해시, `rosa_prereq_check.py` 출력(조직 ID 마스킹) |
| CLI | `--mode manual` 출력 원문, 실행한 aws 명령·RC, `rosa list ...` 출력 |
| 콘솔 | A1 활성화, A2 연결 화면(계정·시각 포함) |
| 역할 대응표 | account/operator role ARN, OIDC config ID, OIDC provider ARN, ocm-role ARN(user-role은 생성 시에만) |
| 제외 | 토큰·비밀키·이메일·Red Hat 사용자명·조직 External ID 원문 |
| 편입 | `321Team/fds-project-evidence` `evidence/P2-IAC-01/` 증적 PR, 독립 리뷰 |

#12 완료 조건 대응: ① A1~A3 실행 묶음 리뷰 승인 = 이 문서 승인과 D6의 4개 판정(OCM basic / user-role / A3-1 / A3-2)을 각각 해당 단계 조건으로 충족 ② role·OIDC readback = 9·11·14번 PASS(각 단계는 자기 GO가 난 범위만) ③ 증적 = §5 증적 PR.

## 6. 실행 경계

Apply 전 Hard Gate(원티켓 2026-10-02 v2)를 따른다. 이 묶음은 IAM·구독·연결만 다루며 VPC/VPN/ROSA 클러스터 생성은 포함하지 않는다. state·tfvars·자격증명은 저장소에 커밋하지 않는다. 실행 결과 수용·G4 판정은 별도다.
