# 운영창·정리 실행 준비안

CODEX_ASSISTED. 2026-10-08. **운영/삭제 창 제안이며 일정 확정·생성·삭제 승인이 아니다.** 담당 이권욱(비용/QA), 이하영(인프라/ROSA), 이재환(Relay/업무 시험). 기존 담당 배정의 소비 관계만 정리한다.

## 원본 일정과 차이

- [#39](https://github.com/321Team/fds-project-baseline/issues/39): 상단 운영 기록은 G4 목표10-13, 발행 Description은10-14로 표시되어 있다. 정본과 운영 기록의 날짜 차이를 유지하고 임의로 한쪽을 고치지 않는다. 실제 G4 PASS가 ROSA 실행 선행조건이다.
- [#38](https://github.com/321Team/fds-project-baseline/issues/38):10-15 Basic Ready,10-19 Full. Full 이후에도 [#50](https://github.com/321Team/fds-project-baseline/issues/50)의10-22 Final Regression이 남는다. 따라서10-19 즉시 전체 삭제를 기본안으로 삼을 수 없다.
- [#48](https://github.com/321Team/fds-project-baseline/issues/48), [#51](https://github.com/321Team/fds-project-baseline/issues/51)은 P1 조건부이며 이를 위해 P0 가동기간을 자동 연장하지 않는다.

## 견적 비교용 구체 창 (모두 KST)

| 범위 | 제안 창 | 계산용 가동시간 | 실행 전 조건 |
|---|---|---|---|
| Relay/network 준비 |10-12 09:00 시작 후보 →10-23 18:00 잔여확인 목표|273시간(연속 유지 시)|Freeze/비용/IAM/saved plan 및 #35/#37 실행 수용. G4 실제 인수창은 별도 확정|
| ROSA 1AZ3worker |10-15 09:00 시작 후보 →10-23 18:00 잔여확인 목표|201 cluster시간,603 worker시간(3대 고정 시)|G4 PASS와 #38 생성 조건, 지원 비용 확보|
| Final Regression |10-22, 시간은 #47 handoff 후 확정|원본 기준 당일 시험|실제 Hybrid handoff, 정상/음성/복구 결과|
| 정리·잔여확인 |10-23 09:00~18:00 제안|삭제 시작 뒤에도 완료까지 비용 계상|증적 수신·소유 inventory·백업/보존 분류·담당 수용|

273/201은 총비용이 아니라 비교용 달력시간이다. 생성 전 대기·삭제 지연·중간 replacement가 있으면 실제 service별 시간을 다시 계산한다. 기존 정본 일정 변경이나10-23 최종 종결을 뜻하지 않는다. 비용이 충족되지 않으면 실행 시작을 보류하고 필수시험 창을 재계획한다. worker를2대로 줄이거나 ROSA를 밤마다 정지/재생성하는 방안을 자동 채택하지 않는다.

## 일일 통제와 중단

이권욱이 매 실행 전과 일일 작업 종료 시 교육장 비용자료(조회시각/미반영 포함)와 실제 inventory를 대조한다. 현재+잔여시험+삭제비가 목표400을 초과하는 전망이면 실행 범위/시간을 재검토하고, 기존450 중단선과 자부담0 조건에 해당하면 새 유료 생성·확장을 중단한다. 50 예비를 정상 운영 예산에 먼저 사용하지 않는다. 자료가 없어도 무료라고 간주하지 않는다. 자동 Budget Action/비용 설정을 이번에 만들지 않는다.

## 실행 가능한 정리 인계 순서

1. 담당자가 실제 cluster ID, component state 주소, Project/ManagedBy/Phase 태그, EBS/PVC/EIP/ENI/LB/NAT/endpoint 등 inventory와 보존/삭제 분류를 제출한다. 다른 프로젝트/공유/소유 불명 자원은 STOP 목록으로 분리한다.
2. 회귀 결과·Known Issue·원본 hash·필요 데이터 백업과 복구 가능성을 먼저 확인한다. PSK·token·state/plan 원문은 비공개 보존한다. 미수신 증적을 삭제 완료로 대체하지 않는다.
3. #38 담당이 승인된 ROSA 정상 삭제 절차를 수행하고 완료/남은 ROSA 의존 자원을 확인한다. worker EC2를 임의 terminate하지 않는다.
4. IaC 담당이 실제 state/source 기반 component별 삭제 plan을 검토한다. vpn의 `session_preferences`는 계정 문서 + `prevent_destroy=true`이므로 일괄 destroy를 실행하면 안 된다. 문서의 중앙 보존/관리이관 절차와 state 소유를 별도로 수용해야 한다. `prevent_destroy`를 임의 해제하거나 `state rm`, `-target`로 우회하지 않는다.
5. 승인된 vpn 정리 후 network 의존성이 해소됐는지 확인하고 network 정리한다. EIP·보존 EBS·snapshot·endpoint·LB·NAT의 잔여 및 비용을 확인한다. 중앙 CFn bootstrap, backend/state/evidence, 공용 IAM/SLR은 기본 삭제 대상이 아니다.
6. 실패 시 실제 API/state와 잔여를 먼저 보존하고 신규 생성/일괄 삭제를 멈춘다. 동일 작업 재실행 안전성을 확인한 뒤 소유 자원만 복구/정리한다. 자격증명/보안통제를 완화하지 않는다.

완료조건: 서비스별 실제 삭제 완료시각 + 잔여 inventory 사유/소유자 + 교육장 후행 비용 확인. 명령을 지금 실행할 actual ID/state/삭제 수용이 없으므로 파괴 명령을 채워 넣지 않았다. 본 준비 문서 원복은 PR 변경만 되돌리면 되며 AWS 복구 대상은 없다.
