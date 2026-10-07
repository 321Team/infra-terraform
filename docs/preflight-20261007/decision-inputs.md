# #34 결정 입력 — 확정값과 제안 분리

CODEX_ASSISTED. Architecture Freeze HOLD. 이 문서는 이권욱의 결정을 준비하며 자체 승인이나 새 AC가 아니다.

## 비용 입력 반영

사용자 직접 답변(2026-10-07 KST): “일단 $ 500이 상한이지만 우리의 자부담 금액은 없음”. **총상한 USD 500 / 팀 자부담 USD 0**으로 수신한다. 비용지원이 모든 서비스에 적용된다는 뜻은 아니다.

기존 [DEC-P2-COST-01](https://github.com/321Team/fds-project-baseline/blob/81365568fd0b946ad93e4d82ae8191add5fcacd0/audit/phase2-cost-policy-20260930/decision-record.md)의 Target ≤400, Hard Stop 450, 보호 Reserve 50을 유지한다. 기존 [미입력 표](https://github.com/321Team/fds-project-baseline/blob/81365568fd0b946ad93e4d82ae8191add5fcacd0/phase2/inputs/cost-intake.pending.json)의 전 항목을 0으로 채우지 않는다.

| 값 | 상태 |
|---|---|
| 총상한 USD 500 / 팀 자부담 USD 0 | USER_CONFIRMED |
| 지원 기간·만료일, 실제 계정 누적 Gross와 조회 시각 | PENDING |
| ROSA Marketplace 청구 지원·교육장 결제 주체·지원 제외 요금 | PENDING |
| Relay/EBS/IPv4/NAT/LB/DNS/전송 및 정리 지연을 포함한 Cost-to-Complete | PENDING |

Cost GO는 누적액+미반영액+잔여 운영/삭제/잔존 비용을 같은 기간·통화로 비교하고, 팀 자부담이 발생하지 않는 결제 근거를 확인한 뒤 판단한다. 지원 범위가 미확인이면 생성 HOLD, 지원 밖 요금이 있으면 별도 지원 확인 또는 사양 재검토가 필요하다. Reserve를 정상 운영시간에 배정하지 않는다. Billing/CE/Budget 설정 권한을 추가하지 않는다.

## 나머지 세 결정의 검토안

근거: [#38 Lead 입력](https://github.com/321Team/fds-project-baseline/issues/34#issuecomment-6019747268), [비용 비교](https://github.com/321Team/infra-rosa/issues/3#issuecomment-6019744131), [계정 사전조회](https://github.com/321Team/infra-rosa/issues/3#issuecomment-6035898024), #38 현행 AC 및 일정.

| 결정 | 권고 후보 | 수용 전 남은 조건 / 영향 |
|---|---|---|
| N-1 worker 시험 | **1 AZ × m5.xlarge 3대**를 우선 비교하고 worker 1대 중단·복구를 시험 설계에 포함 | 현재 #38 AC에 새 필수 N-1을 추가하는 결정은 아님. 승인 P0 시험의 실제 HA 범위, 남은 2대의 platform+app requests/용량, 비용을 확인. 3대라는 수만으로 N-1 PASS가 아님 |
| AZ 장애 대응 | P0의 새 필수 AC로 추가하지 않고, **단일 AZ 위험 수용 후보**로 제시 | 현행 승인 HA 요구와 충돌하면 변경결정 필요. 단일 AZ 장애 동안 서비스 중단 가능. 기존 필수 시험을 삭제하지 않음 |
| 생성·삭제 | #38 기록의 **10-14 G4 승인 후 10-15 착수/Basic Ready**에 맞춘 최소 연속 실행창, 필요한 증적 확보 후 조기 삭제. 기존 전체 teardown 목표 10-23 유지 | exact 생성/삭제 시각과 재생성 소요는 이하영 입력 후 결정. 10-13~23 250h는 비교용 가정이며 현행 실행 일정으로 채택하지 않음. 밤마다 삭제·재생성은 검증/비용 없이 기본화하지 않음 |

대안 1 AZ ×2대는 N-1을 요구하지 않는 경우의 비용 비교안이다. 플랫폼 여유·workload requests를 확인하기 전 2대를 충분한 용량으로 확정하지 않는다. 3 AZ ×1대는 AZ 요구가 생기면 비교하되 AZ별 subnet/pool·NAT·DNS·source·PVC 복구와 비용을 함께 검토한다. 최신 ROSA 조회는 지원/최소 quota 결과이며 실제 topology 선택·전체 quota·생성 조직 확정이 아니다.

기존 비교의 $537/$426(250h) 등은 Relay/LB/전송 등 누락이 있는 과거 추정이며 새 총액으로 사용하지 않는다. 가동 가능시간은 `(사용 가능한 운영예산 - 누적/미반영 - 잔여 고정/변동/정리 비용) / 검증된 시간당 비용`으로 계산하되 미확인 값이 있으면 결과를 내지 않는다. 총상한과 별개로 모든 비용의 지원 적격성을 확인한다.

## Freeze 소비 경계

MachinePool/AZ/subnet이 결정되면 #37의 worker source 후보를 좁힐 수 있다. 실제 worker SG ID는 생성 후 관측 대상이며 Freeze 전 필수 actual ID로 요구하지 않는다. DNS/관리 경로, D22 Registry, source/DB 경계 등 기존 미결은 관련 담당 결정에 연결하며 네 값만으로 전체 Freeze를 선언하지 않는다.

책임: #34 이권욱 / #35·#38 입력 이하영 / #37 tuple·복구 이재환. 기존 담당·기한을 변경하거나 상시 이중 승인 단계를 만들지 않는다.
