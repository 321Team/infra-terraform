# Phase 2 설계 동결·실행 판단표 — 2026-10-10

이권욱 / CODEX_ASSISTED. 조회 기준 03:12–03:18 KST. 정본 `docs-v3.1.21`(979facb98de8ca1f1e2ce22f38b27ac3366f3fc3)과 #34/#35 최신 운영 기록을 연결한 **검토용 현황표**다. 정본 발행·Phase 1 인수·공식 Start·Freeze·Cost GO·Apply GO를 이 문서로 발행하지 않는다.

## 이번 3~5번 산출물과 품질 기준

- 3 증적: 실패2회·PR22 읽기 성공·수동 읽기/I3 성공 원본을 보존하고 별도 증적 PR로 독립 검토 요청. archive hash/manifest 검증은 수신 무결성이며 인수 승인이 아니다.
- 4 절차: [I5 오류 복구 검토안](i5-recovery-review-20261010.md). 실행과 분리하며 강제 종료를 새 필수조건으로 추가하지 않는다.
- 5 판단: 아래 표에 원본·변경결정·생산자·소비자·잔여 조건을 연결한다. 개인 경로/클라우드 ID는 adapter 입력으로 관리, 보안/시험 의미는 이식 시에도 유지한다.

## 기존 결정과 실행 입력

| 항목 | 확인된 현재 근거·상태 | 담당 / 남은 완료조건 | 적용 단계 |
|---|---|---|---|
| Phase 1 및 공식 Start | [#33](https://github.com/321Team/fds-project-baseline/issues/33) OPEN. 기존 Close/Known Issue/Deferred 계약 유지. 이번 작업은 P1 전체 인수를 재심사하지 않음 | 권욱: 기존 승인 기록 소비. 사전 작업을 공식 Start 완료로 바꾸지 않음 | Start 별도 |
| 사양 방향 | [#34 6054304386](https://github.com/321Team/fds-project-baseline/issues/34#issuecomment-6054304386): HCP·1AZ·m5.xlarge3대·worker1대 장애/복구 방향 승인 | 하영 기술 입력 / 권욱 Freeze 판단. AZ 전체 장애를 새 P0로 추가하지 않음 | 방향 승인 완료, 전체 Freeze HOLD |
| Version/Pool·trust/path | [ROSA#3](https://github.com/321Team/infra-rosa/issues/3), [#11](https://github.com/321Team/infra-rosa/issues/11) CLOSED(사전 입력). 4.22.16 후보는 자발적 업그레이드 미계획; 필수 업데이트 정책 별도 | 생성 시 지원 목록·실제 control-plane/worker 버전·pool 읽기. 생성 뒤 minor downgrade를 복구안으로 사용 금지 | 사전 입력 완료 / Runtime 별도 |
| CIDR/AZ/route | #34/#35 확정 설계: 서울, On-Prem10.1.93.0/24↔VPC10.20.0.0/16; private a/b/c 및 public-transport-a | 하영: source81162467/실제 Plan 대조, 생성 후 actual ID/Zone ID handoff | 설계/Plan 확인, Apply 미실행 |
| D21 transport | #34 권위표: aws_ec2_eip_relay, OCI primary NO-GO. managed VGW/TGW 미채택 | 재환/하영: Relay actual 인계 후 VPN Runtime. S2S VPN quota를 미채택 경로의 Stage-A blocker로 복원하지 않음 | 확정 adapter / Runtime 별도 |
| NAT/On-Prem 경로 | network Plan20개 생성 예정, NAT1·NAT EIP1. 인터넷 NAT와 DB/Harbor Relay 경로 분리 | 하영/재환: On-Prem route 초기 OFF, VPN 확인 후 별도 route Plan. NAT EIP를 DB source로 대체 금지 | 소스/Plan 완료, 유료 생성 미실행 |
| IAM·backend | [#35 실제 부여 6077294756](https://github.com/321Team/fds-project-baseline/issues/35#issuecomment-6077294756), 개인 역할/정책 readback. bucket fds-tfstate-774055931866-ap-northeast-2; network key phase2/network/terraform.tfstate, native lock | 각 본인 역할 및 미검증 U1 추적. Network 역할은 Relay/SSM 실제 결속 후. #9 전체 PASS 아님 | IaC 역할 부여/일부 Runtime 완료 |
| 권욱 I3 | [#9 6086432328](https://github.com/321Team/infra-terraform/issues/9#issuecomment-6086432328): 02:52:12–02:52:57 RUNTIME PASS, collision rc1→If-Match 정리→retry20/0/0→lock 부재 | 권욱 원본 제출 / 독립 리뷰어 편입 심사. I5·타인 계정 검증으로 확대 금지 | I3 Runtime 완료 / 독립 편입 대기 |
| IAM 잔여 | [#9 6078433685](https://github.com/321Team/infra-terraform/issues/9#issuecomment-6078433685): noMFA RUNTIME NOT_RUN, N5 없는 객체404 UNDETERMINED; STATIC/SIMULATION과 분리 | 권욱·하영 및 #35 Lead: 기존 AC별 근거/미검증 범위를 판정. 장기키·MFA 해제를 시험용으로 추가하지 않음 | Apply 전 기존 조건 판단 |
| I5 | 기존 오류 종료·해제·재계획 기준의 절차 후보 작성, 실제 시험 미실행 | 독립 절차 리뷰 → 별도 I5-A 실행 범위/새 작업창 확정 → 원본 검증 | 준비 가능 / 실행 보류 |
| 전체 network Plan 독립 검토 | [#10 6084258507](https://github.com/321Team/infra-terraform/issues/10#issuecomment-6084258507): 사용자 공유 제공 보고, 하영 수신/재해시/전체 검토 회신 미확인. 원본 Plan18b65922… | 하영: 수신시각·원본 해시·전체20개·UNKNOWN·보안/비용 기술 입력 판정. I3 retry Plan은 별도 파일이며 기존 Plan 승인으로 대체 금지 | Apply 선행 잔여 |
| 중앙 bootstrap 검증 | evidence [PR200](https://github.com/321Team/fds-project-evidence/pull/200) HEAD5892765a… CHANGES_REQUESTED, 변경 없음 | 하영: Audit role simulation 한계·S10 Retain/R6 범위 정정, 원본 불변·해시 갱신 후 리뷰 | 증적 판정 정정 대기; 중앙 설정 실패로 단정 금지 |
| 하영 I2/I3 증적 | evidence [PR201](https://github.com/321Team/fds-project-evidence/pull/201) HEADd6872ba5… OPEN. 승인122c4ab9 이후 대장 통합본 확인 대기 | 재환 exact HEAD 확인, 기존 승인/원본 불변과 구분 | 편입 후속, 권욱 I3와 별개 |
| ROSA IAM/OIDC | [Terraform PR21](https://github.com/321Team/infra-terraform/pull/21) HEAD0d18e754… CHANGES_REQUESTED, 변경 없음 | 하영: 임의 trust/정책 생성·연결 경로 통제, 실패 시 증적 기록 후 비정상 종료. 독립 코드 검토 후 별도 권한 적용 | ROSA 사전 정책 수정; 일반 network I3 재실행 조건 아님 |
| Registry/DB/관리 경로 | ROSA#11 정적 입력 CLOSED, [#10](https://github.com/321Team/infra-rosa/issues/10) OPEN. #34 F03~F09의 계약 추적 유지 | 하영/재환: 기존 증적으로 actual443 allowlist·P2 Runner 후속 책임, worker DB source-set/NP·credential·관리 계약 연결. 이미 수용한 입력 재승인 금지 | 생성 전 계약 vs 생성 후 cold-pull 구분 |
| 비용 | [#34 6073631202](https://github.com/321Team/fds-project-baseline/issues/34#issuecomment-6073631202): 교육장 지원·자부담0, 목표400/중단450/상한USD500 | **권욱만** 교육장 리포트의 금액/기준시각/범위로 판정. 현재 새 금액·Cost GO 미수신. 구현자는 수량·운영/정리 입력만 제공 | 사전 산출물 반려 사유 아님; 유료 실행 전 판단 |
| 생성/삭제 일정 | [ROSA#4](https://github.com/321Team/infra-rosa/issues/4): 10/15생성·10/16Basic Ready·10/19복구 여유는 Lead 미확정 일정안 | 권욱/하영: G4·별도 Create GO 뒤 실제창 확정. 증적 반출/보존→승인 teardown→잔존 과금 확인. 10/23·10/26 자동삭제 아님 | 별도 실행창 미확정 |

## 과거 상태와 충돌하는 문구의 소비 기준

1. #35의 10/02 `WORK_ROLES=NOT_ASSIGNED / PLAN=NOT_RUN / BACKEND_STATE=PENDING` 및 #34의 exact backend PENDING은 **당시 이력**이다. 이후 실제 부여/Plan/readback/I3 기록으로 해당 범위만 갱신한다. 과거 원문은 삭제하지 않는다.
2. #35 초기 S2S quota/attachment 조건은 이후 D21 self-managed handoff에서 selected path 비차단으로 정정됐다. 미채택 VGW/TGW를 새 선행조건으로 넣지 않는다.
3. #34 과거 비용 산식보다 사용자 결정6073631202의 교육장 리포트·권욱 중앙 판정이 우선한다. 예상 총비용에 누적액을 중복 합산하지 않는다.
4. 사전조사 #3/#11 종결, 코드 승인/병합, 증적 편입은 Freeze/Create GO와 다르다. 실제 IDs를 생성 전 Freeze 입력으로 요구해 순환 차단하지 않고 생성 후 수집 계약을 고정한다.

## 실행 판단 경로

1. 지금 완료할 범위: 증적 제출·독립 리뷰 요청, I5 절차 초안과 이 판단표 제출.
2. 다음 유료 실행 판단: #34 Freeze/기존 Start 경계, #35 해당 단계 Hard Gate, 독립 full Plan, 본인 권한·backend/복구 근거, 권욱 Cost GO, 새 실행창·정리 조건을 확인한다. 충족하지 않은 항목을 임의 체크하지 않는다.
3. network Apply 후에만 실제 network handoff → 검토된 vpn Plan/Relay·SSM 문서 → Network 역할 actual 결속/본인 접속 → VPN Runtime 순서로 소비한다.
4. G4와 별도 ROSA Create GO 이후 생성 → 최소 pull 경로/cold-pull → Basic Ready → D22 Final. 실제 P1 Harbor/방화벽/Robot 변경은 해당 소관 승인 없이 끼우지 않는다.

각 Gate 기록 필드: `단계 / 대상source·plan hash / 충족 근거 링크 / 미충족 항목 / 생산자 / 소비·검토자 / 비용결정 링크 / 작업창 / 복구·잔존 자원 / 판단자·시각 / GO|HOLD`. 현재 **Freeze/Apply/Create는 HOLD(이번 GO 발행 없음)**. I5-A는 별도 검토·실행 확인 필요. 담당자·AC·정본·기존 일정 필드는 이번 제출로 변경하지 않는다.
