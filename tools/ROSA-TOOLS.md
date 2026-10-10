# ROSA 중앙 실행 도구 (#12)

PR21(정책·시뮬레이션·Terraform source)에서 분리한 실행 도구 2개의 설명이다. 내용은 PR21 `b49bfef`의 README 두 절을 그대로 옮겼다.
**이 PR이 독립 리뷰를 통과해 병합되기 전에는 중앙 실행을 하지 않는다.** 실행 승인이 아니다. 실제 AWS에서 실행한 적 없다.

- 정책·중앙 실행 경로 계약: [`iam/rosa-prereq-draft-20261009/README.md`](../iam/rosa-prereq-draft-20261009/README.md)
- Terraform 실행 순서: [`terraform/rosa-prereq/README.md`](../terraform/rosa-prereq/README.md)

## 1. 위임 역할 정책 부여 실행기 `tools/rosa_grant.py`

`FDS-IaC-Operator`에 이 폴더의 정책을 붙이고 Guardrails를 v2로 바꾸는 IAM 쓰기를 **한 번 실행에 한 건씩** 한다. 중앙 실행 주체가 실행 승인 뒤에 돌린다. 역할·OIDC 생성(Terraform)과 trust 변경은 하지 않는다.

| 순서 | step | 쓰기 1건 | 실행 전 조건(아니면 STOP) | 실행 후 readback |
|---|---|---|---|---|
| 1 | `guardrails-v2` | `create-policy-version --set-as-default` | live 기본 버전 = v1 원문, 버전 5개 미만, Guardrails가 이 역할에만 부착, 역할 부착 = 기본 4개, inline 0 | 기본 버전 = v2 후보 원문 |
| 2 | `subscribe-create` | `create-policy` FDS-RosaBootstrap-Subscribe | Guardrails v2, 같은 이름 정책 없음(기존 정책 채택 안 함) | 원문 일치, 버전 1개, 미부착 |
| 3 | `subscribe-attach` | `attach-role-policy` | 이 ledger가 만든 PolicyId, 원문 일치, 미부착 | 이 역할에만 부착 |
| — | (A1 활성화와 readback) | 실행기 밖 | | |
| 4 | `subscribe-detach` | `detach-role-policy` | 부착 상태 | 어디에도 미부착 |
| 5 | `prereq-create` | `create-policy` FDS-IaC-RosaPrereq | 2와 같음 | 2와 같음 |
| 6 | `prereq-attach` | `attach-role-policy` | 3과 같음 | 3과 같음 |
| 되돌림 | `prereq-detach`·`subscribe-delete`·`prereq-delete`·`guardrails-v1` | 분리·삭제·기본 버전 v1 복귀 | 삭제는 **이 ledger가 만든 PolicyId**·미부착·버전 1개일 때만. v1 복귀는 ROSA 정책이 모두 분리된 뒤에만 | 각 결과 |

- 기본은 dry-run이다. 조건 확인 뒤 실행할 aws 명령만 출력한다. 실제 쓰기는 `--execute`를 붙일 때만 한다.
- 매번 `SHA256SUMS`로 정책 파일을 확인하고, 호출 주체 ARN이 `--expected-caller`와 정확히 같은지 확인한다.
- 쓰기 뒤에는 IAM 반영 지연을 고려해 readback을 최대 12회(5초 간격) 반복한다. 조회 오류(거부·손상 JSON·시간초과)도 재시도 대상이며, 끝내 맞지 않으면 "미검증"으로 기록하고 STOP한다. AWS CLI 호출은 120초 제한.
- **ledger = 실행 기록 일지**(`--ledger-dir`, 디렉터리 0700·파일 0600, 저장소 밖). 쓰기 1건마다 `run_id`를 붙여 단계별로 한 줄씩 추가하고 즉시 디스크에 반영(fsync)한다. 자격 증명은 기록하지 않는다(PR21 리뷰 B1).
  | 단계 | 언제 | 남기는 것 |
  |---|---|---|
  | `INTENT` | **쓰기 전** | step·argv·호출 주체·정책 파일 SHA-256. 이 기록을 못 남기면 쓰지 않는다 |
  | `WRITE_RETURNED` | 쓰기 응답 직후, 조회 전 | RC·stdout SHA-256·stderr 앞부분·**응답의 PolicyId/Arn/VersionId** |
  | `OUTCOME_UNKNOWN` | 쓰기 호출 자체가 예외(시간초과·중단) | 예외 종류 |
  | `READBACK` | 조회 반복 후 | verified·실패 사유·검증된 ID |
  | `RECONCILED` | `reconcile` 실행 후 | APPLIED(실제 반영됨) 또는 NOT_APPLIED(반영 안 됨)·ID |
- **결과가 확정되지 않은 회차가 하나라도 있으면 모든 step을 STOP한다**(되돌림 포함). 확정 = `READBACK` verified 또는 `RECONCILED`. 프로세스가 중간에 죽어도 `INTENT`가 남아 다음 실행이 막힌다.
- `reconcile --run-id <id>`: 그 회차 step의 실행 전 조건·실행 후 조건을 live IAM과 다시 맞춰 본다. 실행 후 조건만 맞으면 APPLIED(쓰기 응답의 PolicyId와 다르면 STOP), 실행 전 조건만 맞으면 NOT_APPLIED, 둘 다 아니면 **AMBIGUOUS로 STOP하고 미확정으로 남긴다**(사람이 확인). 기본은 dry-run이고 `--execute`일 때만 ledger에 기록한다. AWS 쓰기는 하지 않는다. 자동 재쓰기·자동 삭제는 없다.
- 동시 실행 방지: 실행 중 ledger 폴더에 `rosa-grant.lock`(O_EXCL)을 둔다. 있으면 STOP. 비정상 종료로 남은 lock은 ledger·live IAM을 확인한 뒤 사람이 지운다.
- ledger 줄이 JSON이 아니거나 `run_id`/`phase`가 없으면(이전 형식 포함) 입력 오류로 멈춘다.
- **지원 환경: POSIX만(Linux, AWS CloudShell), Python 3.9+, AWS CLI v2.** Windows는 시작 시 거부한다(비공개 ledger가 POSIX 파일 권한에 의존). 권한 검사는 빼지 않는다.
- Guardrails의 남은 v2 버전은 삭제하지 않는다. 기본 버전이 아니면 효과가 없다.
- 사용 예: `python3 tools/rosa_grant.py --expected-caller <승인된 ARN> --ledger-dir <비공개 경로> status`, 이어서 `... guardrails-v2`(dry-run) → `... guardrails-v2 --execute`. 미확정 회차가 나오면 `... reconcile --run-id <id>`(dry-run) → 확인 후 `... reconcile --run-id <id> --execute`.
- 오프라인 테스트(POSIX): `python3 tests/test_rosa_grant.py` (31건: 정방향 6단계·되돌림 4단계, dry-run 무쓰기, 1회 1쓰기, 호출 주체 불일치, 순서 위반, 동명 정책 채택·삭제 거부, live v1 drift, 다른 주체에 Guardrails 공유, 버전 한도, 예상 외 부착·inline, 쓰기 실패 기록→reconcile NOT_APPLIED, 반영 지연 재시도·미수렴, 원문 hash 불일치, v2 = v1 + NotAction 11개. **B1 추가**: 생성 후 조회 거부·손상 JSON·시간초과 각각에서 PolicyId 보존·후속 실행 차단·reconcile APPLIED 후 삭제 가능, 일시 조회 오류 회복, 쓰기 호출 예외(반영 전/후), INTENT 기록 실패 시 무쓰기, READBACK 기록 실패 시 미확정 유지, lock 동시 실행 차단, AMBIGUOUS 유지, reconcile 입력 오류, 손상·이전 형식 ledger 거부, 공개 ledger 파일 거부, Windows 거부).

## 2. 중앙 실행 대조 스크립트 `tools/rosa_prereq_check.py`

승인 표(ROSA CLI 1.2.53 manual 출력 기준)를 스크립트 안에 `main.tf`와 **따로** 적어 두고 비교한다. 둘 중 하나를 바꾸면 같은 PR에서 둘 다 바꾼다.

| 모드 | 하는 일 | AWS 호출 | STOP 조건 |
|---|---|---|---|
| `plan` | `terraform show -json` 결과 대조 | 없음 | Terraform 버전 불일치, 승인 목록 밖 자원, create(단계 2의 단계 1 자원은 no-op) 외 동작, 역할 이름·trust(Statement·Principal·Action·Condition)·부착 정책 ARN 불일치, inline 정책·permissions boundary, plan 시점 trust 미확정 |
| `readback` | apply 뒤 실제 IAM 대조 | 조회만(`get-role`·`list-attached-role-policies`·`list-role-policies`·OIDC provider 조회). `FDS-IaC-RosaPrereq.json`으로 가능 | 계정 불일치, 역할 없음, trust·부착 정책 불일치, inline 정책 1개 이상, `oidc.op1` provider가 1개가 아님, client ID 불일치 |

- 결과: exit 0 PASS, 1 STOP, 2 입력 오류. 출력에서 Red Hat 조직 External ID는 `<masked>`로 가린다. plan 모드는 plan JSON SHA-256을 출력한다.
- **미확정 값 처리(PR21 리뷰 B2)**: plan JSON에서 apply 뒤에야 정해지는 값은 `after`가 null, `after_unknown`이 true다. 미확정을 "승인됨"이나 "없음"으로 보지 않는다. 역할 이름·trust·permissions boundary·path, 부착의 role·policy_arn, OIDC 설정은 plan 시점에 확정돼야 하며 아니면 STOP. 부착 대상 역할을 주소 문자열로 추측하지 않는다. provider가 채우는 `inline_policy`·`managed_policy_arns`만 예외로, plan의 `configuration`에 그 항목이 설정되지 않은 경우에 한해 `DEFERRED`로 표시하고 readback에서 확인한다(inline 0, 부착 정확히 일치). 단계 2에서도 단계 1 OIDC(managed, URL = 단계 1 readback 값, client ID)를 다시 대조한다.
- 실제 `terraform show -json` 출력으로는 아직 확인하지 않았다(이 환경에 terraform 없음). 테스트의 plan 예시는 `main.tf` 구조를 본떠 만든 것이며, 첫 실제 plan에서 `DEFERRED` 항목이 위 2개 필드에 한정되는지 확인한다.
- `--support-principal`은 CLI `sts_support_trust_policy.json` 값을 넣는다. 커밋하지 않는다.
- `ocm-role`·`user-role`(CLI 소유)은 대상이 아니다. manual 출력 원문과 실행 명령을 검토해 따로 대조한다.
- 오프라인 테스트: `python3 tests/test_rosa_prereq_check.py` (28건: 정상 단계 1·2와 DEFERRED 표시, trust principal 추가, statement 추가, 조건 연산자 변경, AdministratorAccess 부착, 승인 밖 자원, update·delete·replace, inline 정책, trust 미확정, 버전 불일치, 입력 오류, 출력 마스킹. **B2 추가**: 부착 role·policy_arn 미확정, configuration에 inline_policy 설정됨, configuration 없음, permissions boundary 미확정, managed_policy_arns 추가 정책, 단계 2 OIDC client ID·URL·managed 변경).
