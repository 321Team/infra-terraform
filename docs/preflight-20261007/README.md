# Phase 2 사전 작업 실행 준비 — 2026-10-07

CODEX_ASSISTED. #34 결정 입력 → #35 IAM/Stage-A Gate → #37 SG·AMI → Terraform Plan 준비 순서로 최신 원본을 대조했다. 이 묶음은 준비 자료이며 승인된 Terraform 소스나 AWS 설정을 바꾸지 않는다.

## 현재 판정

- 사전 작업: 결정 입력·Gate 점검·SG/AMI 문서 검증·Plan 절차 준비 수행.
- Architecture Freeze: HOLD. Human Role Grant / Cloud Plan / Apply / Relay·ROSA Runtime: NOT_RUN 또는 실제 완료 증적 미확인.
- 비용: 사용자 2026-10-07 답변으로 **총상한 USD 500, 팀 자부담 USD 0** 확인. 기존 Target ≤400 / Hard Stop 450 / Reserve 50 유지. 2026-10-08 사용자 정정으로 교육장 지원은 이미 제공 중임을 확정했다. 사용액·예상 총비용은 교육장 리포트 금액으로 추적한다. 최신 금액은 이 작업에 미접수이며 자체 조회/견적 확보는 선행조건이 아니다. 지원 자체의 재확인은 요구하지 않는다.
- 설계 방향: 후속 사용자 선택으로 **1 AZ·m5.xlarge 3대, worker 1대 장애·복구 시험 준비** 수신. AZ 전체 장애 대응을 새 P0 필수조건으로 추가하지 않음. actual AZ/subnet·용량·비용·생성 GO는 별도 잔여다.
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

PR5의 기존 STATIC/MOCK 증적과 독립 리뷰는 재사용한다. 최초 준비 시 작성 PC PATH에서 AWS/Terraform CLI를 찾지 못해 AWS 실행을 수행하지 않았다. 후속 사용자 로그인 뒤 **23:56:33~38 KST 중앙 CloudShell 읽기 조회를 실제 수행**했다. IaC/Network 역할 ABSENT, 기본 Session document NOT_FOUND_REVIEW_REQUIRED, AMI metadata 일치이며 원본 11개 해시를 로컬에서 재검증했다. 이 조회는 Terraform/Agent/터널 Runtime 시험이 아니다. 기존 bootstrap 4자원 및 22건/46건/9건 시험은 반복하지 않았다.

## 산출물과 다음 담당

1. [#34 결정 입력](decision-inputs.md): 이권욱의 비용·N-1/AZ 방향 선택을 기록. exact 생명주기와 실행 Gate 잔여를 구분함.
2. [#35 IAM/Stage-A Gate](iam-stage-a.md): 이하영이 전체 permissions·정책/소스 검토를 완결하고 기존 중앙 부여 경로 및 각 본인 시험을 연결.
3. [#37 SG/AMI 사전검증](sg-ami.md): 이하영·이재환이 AMI 지원/패키지/서비스 근거 및 최종 tuple을 수신. 초기 생성과 route 활성화 조건을 분리.
4. [Plan 실행 준비](plan-runbook.md): network plan → 별도 승인 network apply → 실제 handoff → vpn plan → 별도 승인 vpn apply → #37 증적 후 route plan.
5. [읽기 전용 수집기](../../scripts/collect-phase2-preflight.py): 새 AMI/IAM/document 입력만 수집. 정책 부여/유료 생성/Plan 기능 없음. [사용법](iam-stage-a.md#읽기-전용-추가-수집).
6. [권욱 담당 실행 순서](gwonuk-next-actions.md): 직접 결정 완료 항목, 지금 가능한 조회, 타 담당 입력 이후의 중앙 실행을 구분.
7. [중앙 읽기 조회 접수](central-readonly-receipt.md): 실제 명령별 RC·부재 판정·원본 보존/재해시와 실행 한계.
8. [중앙 검증 착수·인계](central-validation-handoff.md): 10-08 후속 요청에 따른 전체 정책 제출 항목·변경분 시험·단계별 완료조건. [network 권한 보완표](network-permission-supplement.json)는 provider6.66.0 원본으로6block/15instance와 조건부 복구 경로를 연결한 검토 자료이며 부여 정책이 아니다.

적용 전에는 이 문서의 고정 SHA와 최신 원본의 차이를 확인한다. 문서/수집기 PR 병합은 별도 Lead 판단이며, 이 묶음에 actual tfvars·완결 IAM 정책·유료 실행 승인은 없다. 준비안 원복은 이 PR의 변경만 되돌리는 것으로 충분하고 AWS 복구 작업은 없다.

## 2026-10-08 권욱 선행 작업 전체 착수

[사용액·한도 관리 입력표](cost-support-request.md), [운영창/정리안](operating-teardown-plan.md), [지원 AMI 대안 실조회](ami-alternative-review.md), [본인 U1·lock/거부/복구 준비](gwonuk-u1-plan.md)를 추가했다. 지원 및 교육장 리포트 기준 추적은 확정, 최신 보고금액은 이 작업에 미접수, AMI 후보 metadata는 실제 RC0/원본 재해시 완료. 설정 방향이 이미 결정된 Session document는 다시 결정받지 않고 actual ownership/readback만 잔여로 둔다. 실제 Grant/Plan/Apply/Runtime은 미실행이다.
