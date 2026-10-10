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
- 쓰기 뒤에는 IAM 반영 지연을 고려해 readback을 최대 12회(5초 간격) 반복한다. 그래도 조건이 맞지 않으면 STOP한다.
- ledger(`--ledger-dir`, 0700, 저장소 밖)에는 argv·RC·UTC·stdout SHA-256·PolicyId·정책 파일 SHA-256을 남긴다. 자격 증명은 기록하지 않는다.
- Guardrails의 남은 v2 버전은 삭제하지 않는다. 기본 버전이 아니면 효과가 없다.
- 사용 예: `python3 tools/rosa_grant.py --expected-caller <승인된 ARN> --ledger-dir <비공개 경로> status`, 이어서 `... guardrails-v2`(dry-run) → `... guardrails-v2 --execute`.
- 오프라인 테스트: `python3 -m unittest tests/test_rosa_grant.py` (18건: 정방향 6단계와 되돌림 4단계, dry-run 무쓰기, 1회 1쓰기, 호출 주체 불일치, 순서 위반, 동명 정책 채택·삭제 거부, live v1 drift, 다른 주체에 Guardrails 공유, 버전 한도, 예상 외 부착·inline, 쓰기 실패 기록, 반영 지연 재시도·미수렴, 원문 hash 불일치, v2 = v1 + NotAction 11개).

## 2. 중앙 실행 대조 스크립트 `tools/rosa_prereq_check.py`

승인 표(ROSA CLI 1.2.53 manual 출력 기준)를 스크립트 안에 `main.tf`와 **따로** 적어 두고 비교한다. 둘 중 하나를 바꾸면 같은 PR에서 둘 다 바꾼다.

| 모드 | 하는 일 | AWS 호출 | STOP 조건 |
|---|---|---|---|
| `plan` | `terraform show -json` 결과 대조 | 없음 | Terraform 버전 불일치, 승인 목록 밖 자원, create(단계 2의 단계 1 자원은 no-op) 외 동작, 역할 이름·trust(Statement·Principal·Action·Condition)·부착 정책 ARN 불일치, inline 정책·permissions boundary, plan 시점 trust 미확정 |
| `readback` | apply 뒤 실제 IAM 대조 | 조회만(`get-role`·`list-attached-role-policies`·`list-role-policies`·OIDC provider 조회). `FDS-IaC-RosaPrereq.json`으로 가능 | 계정 불일치, 역할 없음, trust·부착 정책 불일치, inline 정책 1개 이상, `oidc.op1` provider가 1개가 아님, client ID 불일치 |

- 결과: exit 0 PASS, 1 STOP, 2 입력 오류. 출력에서 Red Hat 조직 External ID는 `<masked>`로 가린다. plan 모드는 plan JSON SHA-256을 출력한다.
- `--support-principal`은 CLI `sts_support_trust_policy.json` 값을 넣는다. 커밋하지 않는다.
- `ocm-role`·`user-role`(CLI 소유)은 대상이 아니다. manual 출력 원문과 실행 명령을 검토해 따로 대조한다.
- 오프라인 테스트: `python3 -m unittest tests/test_rosa_prereq_check.py` (정상 단계 1·2, trust principal 추가, statement 추가, 조건 연산자 변경, AdministratorAccess 부착, 승인 밖 자원, update·delete·replace, inline 정책, trust 미확정, 버전 불일치, 입력 오류, 출력 마스킹 등 18건).
