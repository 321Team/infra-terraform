# Phase 2 사전 작업 실행 준비 — 2026-10-07

CODEX_ASSISTED. #34 결정 입력 → #35 IAM/Stage-A Gate → #37 SG·AMI → Terraform Plan 준비 순서로 최신 원본을 대조했다. 이 묶음은 준비 자료이며 승인된 Terraform 소스나 AWS 설정을 바꾸지 않는다.

## 현재 판정

- 사전 작업: 결정 입력·Gate 점검·SG/AMI 문서 검증·Plan 절차 준비 수행.
- Architecture Freeze: HOLD. Human Role Grant / Cloud Plan / Apply / Relay·ROSA Runtime: NOT_RUN 또는 실제 완료 증적 미확인.
- 비용: 사용자 2026-10-07 답변으로 **총상한 USD 500, 팀 자부담 USD 0** 확인. 기존 Target ≤400 / Hard Stop 450 / Reserve 50 유지. 지원 범위·기간·누적 Gross·Marketplace 부담 주체는 미확인이다.
- 현행 발행 정본은 docs-v3.1.21. 최신 main/후속 결정과 정본의 이력을 구분하며 AC·담당·일정·종결을 변경하지 않는다.

## 검토 기준

| 원본 | 고정값 / 범위 |
|---|---|
| infra-terraform main | `0eabe8daa75a6b9bf960fe1ea5eeaf6a8818f216` |
| PR5 검토 HEAD | `ae39cc6aed4e5855f710614d01fe6a73682ca6c7`; 21:40:15 KST 병합, source 승인에 한정 |
| baseline main | `81365568fd0b946ad93e4d82ae8191add5fcacd0` |
| 발행 정본 | docs-v3.1.21 / `979facb98de8ca1f1e2ce22f38b27ac3366f3fc3` |
| GitHub 운영 원본 | baseline #33/#34/#35/#37/#38, infra-rosa #3, infra-terraform PR4/PR5 및 리뷰 |
| 조회 시점 | 2026-10-07 23:24~23:34 KST; 이후 상태는 새 조회로 판단 |

PR5의 기존 STATIC/MOCK 증적과 독립 리뷰는 재사용한다. 이 작업의 문서 검증·읽기 전용 수집기 MOCK를 Terraform 재시험/CI/AWS 실제 시험으로 표시하지 않는다. 현재 작성 PC PATH에서 AWS CLI와 Terraform CLI를 찾지 못했고 AWS 실행 세션을 사용하지 않았다. 기존 CloudShell bootstrap 4자원 PASS_USER_READBACK 및 22건/46건/9건 시험을 반복하지 않았다.

## 산출물과 다음 담당

1. [#34 결정 입력](decision-inputs.md): 이권욱이 비용의 새 사용자 입력을 소비하고 N-1/AZ/생명주기 안을 판단. 제안을 확정 사양으로 사용하지 않음.
2. [#35 IAM/Stage-A Gate](iam-stage-a.md): 이하영이 전체 permissions·정책/소스 검토를 완결하고 기존 중앙 부여 경로 및 각 본인 시험을 연결.
3. [#37 SG/AMI 사전검증](sg-ami.md): 이하영·이재환이 AMI 지원/패키지/서비스 근거 및 최종 tuple을 수신. 초기 생성과 route 활성화 조건을 분리.
4. [Plan 실행 준비](plan-runbook.md): network plan → 별도 승인 network apply → 실제 handoff → vpn plan → 별도 승인 vpn apply → #37 증적 후 route plan.
5. [읽기 전용 수집기](../../scripts/collect-phase2-preflight.py): 새 AMI/IAM/document 입력만 수집. 정책 부여/유료 생성/Plan 기능 없음. [사용법](iam-stage-a.md#읽기-전용-추가-수집).

적용 전에는 이 문서의 고정 SHA와 최신 원본의 차이를 확인한다. 문서/수집기 PR 병합은 별도 Lead 판단이며, 이 묶음에 actual tfvars·완결 IAM 정책·유료 실행 승인은 없다. 준비안 원복은 이 PR의 변경만 되돌리는 것으로 충분하고 AWS 복구 작업은 없다.
