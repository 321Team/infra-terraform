# PR6 준비값과 PR7 구현 후보 연결

CODEX_ASSISTED. 2026-10-08. PR7 HEAD `e4ee0bff2d6aba92a0b147b86e1f4759f315eded`에 대한 독립 리뷰 대기 중에 수행한 준비 작업이다. 검토 대상 코드 변경 없이 PR6의 수집·안내 값을 맞췄다. 승인 SHA나 실제 실행값을 임의 확정하지 않았다.

## 소스·증적 경계

| 항목 | 이번 준비값 | 소비 조건 |
|---|---|---|
| 새 Relay 소스 | [PR7 e4ee0bf](https://github.com/321Team/infra-terraform/pull/7), Stream9 `ami-08d855918a18d0cf9` / owner125523088429 | 독립 exact-HEAD 리뷰·Lead 병합 판단 별도 |
| PR6의 Terraform | 이전 main `0eabe8daa75a6b9bf960fe1ea5eeaf6a8818f216` 유지 | **새 Relay Plan을 이 checkout에서 실행하지 않음** |
| 후보 manifest | [PR7 source.json](https://github.com/321Team/infra-terraform/blob/e4ee0bff2d6aba92a0b147b86e1f4759f315eded/validation/relay-stream9-20261008/source.json), network6/vpn10파일 | SHA256은 [참조 JSON](source-binding-20261008.json)에 고정. 과거15파일 manifest는 과거 소스용 |
| 읽기 수집기 | Stream9 exact AMI 조회, summary에 AMI/owner/후보 SHA/미승인 상태 기록 | 기존 승인된 중앙 조회 범위만. CloudShell 실행은 이번에 하지 않음 |
| 실제 실행 source | 아직 미확정(null) | 최종 병합 SHA·manifest·정책·명시 입력과 해당 단계 수용 근거를 실행 전 기록 |
| 과거 AWS 증적 | 23:56 Stream10 및00:28:59 Stream9 실제 조회 기록 | 변경·재해석·새 Runtime PASS로 재사용하지 않음 |

PR7은 merge 전 후보다. 리뷰로 HEAD가 바뀌면 AMI/bootstrap/변수/manifest 변화와 관련 입력을 재대조한다. merge commit을 실행 SHA로 쓰는 경우 그 tree와 manifest를 확인한다. PR6 또는 PR7이 병합됐다는 사실만으로 execution_enabled를 켜지 않는다. 수집기 summary의 후보 SHA는 Terraform을 실행한 SHA가 아니다.

## 지금 취합할 입력과 완료조건

| 주체 | 남은 입력 | 우리 쪽 완료조건 |
|---|---|---|
| #35 이하영 | 전체 IAM 정책 JSON·source SHA, API/resource/condition 목록, 새 AMI 조건 및 회수/복구 | 기존 network 보완표와 PR7 delta를 전체 정책에 대조한 뒤 중앙 검증·부여 단계 판단. 부분 정책 선부여 없음 |
| #35/#38 이하영 | worker private subnet key/AZ·machine pool, N-1 platform+app 수용량, ROSA platform egress | 기존1AZ·m5.xlarge3대 방향과 source/장애 범위가 맞는지 #34에 취합. 생성 전 계약에 actual node ID 요구하지 않음 |
| #35/#37 | exact Libreswan version-release, 실제 repo/mirror 경로, root volume 보존/삭제·CPU credit mode | 임의 기본값·MOCK 값 없이 vpn 입력표 완결. HTTP 필요 근거와 수용 없으면80 추가 안 함 |
| #43/#47 및 인프라 연결 | Runner 관리 경로·반환/source 보존·필수 private DNS subset, App/DB source-set·NP/credential 경계 | #34 생성 전 계약과 이후 실제 허용/거부 시험을 분리하여 취합 |
| 이권욱 | 위 입력·독립 리뷰 결과 접수, 후보/최종 source 차이 확인 | Freeze/단계별 Gate 판정 기록과 본인 역할 시험 준비. 타인 결과를 본인 MFA/U1 증적으로 대체하지 않음 |

요청 항목은 기존 미결의 접수 목록이며 담당·AC·일정 변경이나 새 상시 승인 단계가 아니다. full IAM 정책/담당 입력을 대신 작성·수용한 것으로 표시하지 않는다.

## 후속 단계와 중단 기준

1. source 리뷰 의견을 수정·재검증하고 최종 HEAD에 대한 Lead 판단을 받는다. 새 source와 기존 PR6 준비값의 차이를 다시 반영한다.
2. 해당 단계의 기존 Freeze/권한/실행 조건 충족 후 중앙 grant/readback, 각 본인 MFA/state-lock·거부·복구 시험으로 진행한다. 본인 IAM/Network 역할이 마지막 조회에서 없었으며 지금도 없다고 재조회 없이 단정하지 않는다.
3. [Plan 절차](plan-runbook.md)는 수용된 실행 SHA와 깨끗한 checkout 확인 이후에만 진행한다. network Plan→별도 Apply 판단→actual network handoff→vpn Plan이며 합성 ID를 사용하지 않는다.
4. 초기 worker/문서/route OFF·TCP4431개이면 vpn7create 예상. worker 선택+1, 문서 선택+1, 별도 수용 HTTP+1. 실제 saved plan 전체가 판단 기준이다.
5. 실제 생성 후 Agent Online/OS·EBS readback, Network exact bind/U1, 터널/DB 허용·거부·복구, ROSA Runtime을 각각 수행한다. Basic Ready 후 최종 D22/cold-pull·조건부 P1 DNS/Operator를 초기 생성 전 actual 조건으로 당기지 않는다.

소스/권한/입력 불일치·예상 밖 변경·검증 오류이면 해당 단계 STOP하고 원본을 보존한다. Plan을 root로 우회하거나 SSH/SELinux/서명 검증을 해제하지 않는다. 실제 Apply/교체·삭제에는 기존 승인 대상·영향·복구 범위를 적용한다. 이번 준비 변경의 복구는 PR6 변경 되돌리기이며 AWS 원복 대상은 없다.

교육장 지원 확정·팀 자부담0, 사용액/예상 총비용은 교육장 리포트 기준이다. 기존400/450/상한USD500·예비50을 유지하며 자체 Billing/별도 견적·지원 재승인을 요구하지 않는다.
