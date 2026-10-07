# PR6 기존 승인 이후 변경분과 Phase 2 실행 준비

CODEX_ASSISTED. 2026-10-08. Phase 1 작업은 이번 후속 범위에서 제외한다.

기존 이재환 APPROVED 대상은 `73ed0e1c0aa808c9db8f9435d14de43c0ffa3777`이다. 후속 후보 `c0f9ae7cdd14b7220eb1a945e48169595812daea`와 이번 문서 정정까지의 차이를 검토 입력으로 제공한다. 기존 승인을 최신 HEAD의 독립 승인으로 복제하지 않는다. 전체 PR의 기존 검토를 이유 없이 처음부터 반복하지 않는다.

| 변경 | 영향과 자체 검증 | 남은 확인 |
|---|---|---|
| collector AMI Stream10→Stream9, 기대 owner/후보 source metadata | READS·계정/리전 guard·쓰기 없음은 유지. 기존 검증에서 MOCK11건 PASS, 이전 AMI 응답 STOP 확인 | AMI 방향/PR7 candidate와 결속. 후보 SHA는 실행 승인 아님 |
| 비용 문서/JSON | 교육장 지원 확정, 사용액·예상 총비용은 교육장 리포트. 기존400/450/500·자부담0 유지 | 새 Billing/지원 승인/자체 견적 Gate 없음 |
| source binding·Plan 안내 | PR6 Terraform은 구 main, PR7은 Stream9 candidate. accepted execution SHA=null 유지 | 최종 수용 SHA와 manifest가 정해질 때 실행 입력 갱신 |
| .gitattributes / 수집기 시험 / validation | LF 유지 및 source/test 증적 연결. 실제 정책 부여·AWS Plan 아님 | 과거 실제 원본/접수와 신규 MOCK 구분 |
| 이번 운영·정리 문서 | G4 10-14 결정 근거를 연결해 오래된 미결 표현 해소 | 작업 시간은 제안 상태, 생성/삭제 GO 아님 |

이번 회차 Terraform·collector·시험 코드는 변경하지 않았다. 이전11건과 Terraform22 MOCK을 반복하지 않고, 문서 링크/JSON/공백/민감정보와 코드 불변만 확인한다.

## IAM/Plan 접수 조건

기존 [중앙 검증 인계](central-validation-handoff.md) 및 [network 보완표](network-permission-supplement.json)를 사용한다. 이하영 생산 입력은 full permissions JSON·trust와 source/policy SHA·Action/Resource/Condition·의존 ARN·소유 tag·새 AMI·회수/복구 및 변경 simulation 요청/기대값이다. 문서 준비가 완결 정책의 제출이나 수용은 아니다.

수신 후 중앙 fresh before → ValidatePolicy findings 검토 → 변경분 양/음성 simulation → 해당 부여 범위 판단 → grant/readback → 각 본인 MFA/권한/state-lock/거부·복구 시험 → 정확한 source의 network Plan 순서다. 실제 network handoff 후 vpn Plan을 진행한다. [본인 시험안](gwonuk-u1-plan.md)과 [Plan Runbook](plan-runbook.md)을 재사용한다.

Phase 2 준비는 계속 가능하지만 권한 부여/Plan/Apply는 각각 기존 조건 충족 후다. root 업무 Plan 우회·부분 권한 선부여·actual ID 합성 없음. Session document는 기존 무로그/무KMS/RunAs 없음 방향을 재결정하지 않고 #35의 계정 공용 소유·생성/readback·보존 조건을 수신한다.

이 문서와 운영일 정정은 자체 검토 기록이다. 타인의 독립 리뷰·Lead 병합·실제 권한 완료·Freeze로 표시하지 않는다.
