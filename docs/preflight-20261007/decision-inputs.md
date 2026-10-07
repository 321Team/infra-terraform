# #34 결정 입력 — 확정값과 제안 분리

CODEX_ASSISTED. Architecture Freeze HOLD. 2026-10-07 이권욱의 직접 응답으로 비용 경계와 아래 설계 방향을 수신했다. 설계 선택·실행 승인·AC 인수를 구분한다.

## 비용 입력 반영

사용자 직접 답변(2026-10-07 KST): “일단 $ 500이 상한이지만 우리의 자부담 금액은 없음”. **총상한 USD 500 / 팀 자부담 USD 0**으로 수신한다. 2026-10-08 후속 사용자 설명으로 교육장 비용지원은 이미 제공 중임을 확정했다. 내부 한도 초과 여부에 따라 후속 절차를 진행하며 지원 재확인은 선행조건이 아니다.

기존 [DEC-P2-COST-01](https://github.com/321Team/fds-project-baseline/blob/81365568fd0b946ad93e4d82ae8191add5fcacd0/audit/phase2-cost-policy-20260930/decision-record.md)의 Target ≤400, Hard Stop 450, 보호 Reserve 50을 유지한다. 기존 [미입력 표](https://github.com/321Team/fds-project-baseline/blob/81365568fd0b946ad93e4d82ae8191add5fcacd0/phase2/inputs/cost-intake.pending.json)의 전 항목을 0으로 채우지 않는다.

| 값 | 상태 |
|---|---|
| 총상한 USD 500 / 팀 자부담 USD 0 | USER_CONFIRMED |
| 교육장 비용지원 | USER_CONFIRMED_ALREADY_PROVIDED — 재승인 불필요 |
| 사용액·예상 총비용의 기준 | USER_CONFIRMED — 교육장 리포트 금액 |
| 최신 리포트 금액 | 이 작업에 미접수. 수신 시 원본·기준시점과 한도 비교 기록 |

한도 판단은 교육장 리포트의 사용액과 예상 총비용을 각각 기존 기준과 비교한다. 예상 총비용에 사용액을 다시 더하지 않는다. 자체 Billing 조회/독립 견적 확보를 선행조건으로 두지 않는다. 지원기간/Marketplace 적격성 회신을 별도 포괄 차단조건으로 둔 이전 해석은 철회한다. 목표/중단선/상한 초과 예상 또는 실제 초과 시 기존 비용 정책의 후속 절차로 연결한다. 금액 미확인은 한도 판정 미완료이며 독립 선행 작업을 중단하는 사유가 아니다. Reserve를 정상 운영시간에 배정하지 않는다. Billing/CE/Budget 설정 권한을 추가하지 않는다.

## 설계 방향 결정 수신 — 2026-10-07 23:48 KST

사용자에게 1 AZ·m5.xlarge 3대/worker 1대 장애·복구 시험, AZ 전체 장애 대응을 새 필수조건으로 추가하지 않는 범위와 단일 AZ 중단 위험을 제시했다. 사용자 답변: **“권고안: 1 AZ·3대, worker 장애·복구 시험”**.

- **USER_SELECTED_DESIGN_DIRECTION:** 1 AZ, m5.xlarge worker 3대, worker 1대 장애·복구 시험을 준비한다.
- **AZ 범위:** AZ 전체 장애 대응은 새 P0 필수조건으로 추가하지 않는다. 제시된 단일 AZ 중단 위험을 포함한 설계 방향 선택이며 기존 승인 요구를 삭제하지 않는다.
- **소비할 입력:** 이하영은 실제 AZ/subnet·machine pool·남은 2대의 platform/app 수용 용량 및 cost-to-complete를 이 방향으로 구체화한다. 선택과 다른 대수/AZ로 자동 대체하지 않는다.
- **경계:** 새 #38 AC 체크/인수, 장애 주입 실행, topology/version 최종 Freeze, 한도 내 비용 판단, 유료 생성 GO는 아직 아니다. N-1 성공은 실제 workload/복구 증적으로 판단한다.

## 결정별 현재 상태

근거: [#38 Lead 입력](https://github.com/321Team/fds-project-baseline/issues/34#issuecomment-6019747268), [비용 비교](https://github.com/321Team/infra-rosa/issues/3#issuecomment-6019744131), [계정 사전조회](https://github.com/321Team/infra-rosa/issues/3#issuecomment-6035898024), #38 현행 AC 및 일정.

| 결정 | 권고 후보 | 수용 전 남은 조건 / 영향 |
|---|---|---|
| N-1 worker 시험 | **USER_SELECTED: 1 AZ × m5.xlarge 3대**, worker 1대 장애·복구 시험 준비 | 승인 P0 시험의 실제 HA 범위, 남은 2대의 platform+app requests/용량, 비용을 확인. 3대라는 수만으로 N-1 PASS가 아님 |
| AZ 장애 대응 | **USER_SELECTED: 단일 AZ 방향**, AZ 전체 장애 대응은 새 P0 필수조건으로 추가하지 않음 | 현행 승인 HA 요구와 충돌하면 변경결정 필요. 단일 AZ 장애 동안 서비스 중단 가능. 기존 필수 시험을 삭제하지 않음 |
| 생성·삭제 | #38 기록의 **10-14 G4 승인 후 10-15 착수/Basic Ready**에 맞춘 최소 연속 실행창, 필요한 증적 확보 후 조기 삭제. 기존 전체 teardown 목표 10-23 유지 | exact 생성/삭제 시각과 재생성 소요는 이하영 입력 후 결정. 10-13~23 250h는 비교용 가정이며 현행 실행 일정으로 채택하지 않음. 밤마다 삭제·재생성은 검증/비용 없이 기본화하지 않음 |

1 AZ ×2대와 3 AZ ×1대는 이번 사용자가 선택하지 않은 대안이다. 비용/용량 조건을 충족하지 못하면 변경 영향을 설명하고 재결정하며 자동 전환하지 않는다. 최신 ROSA 조회는 지원/최소 quota 결과이며 전체 quota·생성 조직 확정이 아니다.

기존 비교의 $537/$426(250h) 등은 과거 참고 추정이며 교육장 리포트의 예상 총비용을 대체하지 않는다. 자체 잔여시간/비용 재산출을 필수조건으로 두지 않는다. 교육장 지원 자체를 다시 확인하지 않으며 초과 전망이 있으면 운영창/정리 대안과 필요한 후속 절차를 제시한다.

## Freeze 소비 경계

MachinePool/AZ/subnet이 결정되면 #37의 worker source 후보를 좁힐 수 있다. 실제 worker SG ID는 생성 후 관측 대상이며 Freeze 전 필수 actual ID로 요구하지 않는다. DNS/관리 경로, D22 Registry, source/DB 경계 등 기존 미결은 관련 담당 결정에 연결하며 네 값만으로 전체 Freeze를 선언하지 않는다.

책임: #34 이권욱 / #35·#38 입력 이하영 / #37 tuple·복구 이재환. 기존 담당·기한을 변경하거나 상시 이중 승인 단계를 만들지 않는다.
