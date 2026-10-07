# #34 Freeze 입력 정합 검토 — 2026-10-08

CODEX_ASSISTED. 판정: **새 #37 결정은 구현 후보로 소비, 전체 Architecture Freeze는 아직 HOLD.** 기존 본문·AC·상태·담당·일정·정본을 바꾸지 않는다. 비용 리포트 또는 생성 후 actual ID를 기다리는 순환 조건을 만들지 않는다.

기준: baseline main81365568, 발행 docs-v3.1.21/979facb98, infra-terraform main0eabe8da 및 [PR6](https://github.com/321Team/infra-terraform/pull/6)4d1b445. #34/#35/#37/#38/#40/#42/#51 현행 본문과 #34/#35/#37 최신 담당 댓글, #40/#42 기존 수집 기록을 대조했다. 이 검토를 프로젝트 전체 실행 증적 심사로 확대하지 않는다.

| 구분 | 현재 확정/수신값 | 우리 쪽 처리와 잔여 |
|---|---|---|
| 비용 | 지원 이미 제공, 자부담0·상한500·목표400/중단450/예비50. 교육장 리포트 기준 추적 | 별도 지원 승인/자체 Billing·견적 대기 제거. 수신 보고금액별 비교; 미접수를0/PASS로 표시하지 않음 |
| worker 방향 F01 | 사용자 1AZ·m5.xlarge3대, worker1 장애·복구. 새 AZ 전체 장애 P0 없음 | #38 이하영: 실제 subnet key·AZ/machine pool·N-1 platform+app 수용량 계약. node actual IDs는 생성 후 수집 |
| Relay AMI | #37 Stream9 ami-08d855918a18d0cf9 후보 수용 | [구현 검토](relay-stream9-20261008.md)로 기술 판단/소스 후보 완료. #35 IAM AMI 조건 연결·독립 코드 리뷰·Linux first boot/Agent runtime 별도 |
| Relay SG F05 일부 | UDP500/4500 ingress·TCP443 egress·worker private subnet1개 TCP5432, HTTP 조건부, UDP egress 없음 | 확정 tuple을 코드로 제한. worker key·repo 실제 경로 입력 잔여. 이 SG만으로 transaction-api 허용/engine 거부가 해결되는 것은 아님 |
| 세션 문서 | Standard_Stream, 세션 로그/KMS/RunAs 없음 기존 Lead 결정 | 구성 재선택 불필요. #35 공용 소유·fresh absence·생성/readback→Network 결속→본인 U1. 문서 default false/삭제 보호 유지 |
| backend/중앙 identity | bootstrap 생성 기록과 PR4/5에 exact bucket/component keys·Relay profile 소비 구현 존재 | #34 과거 본문의 exact bucket/key PENDING을 현재 미결로 중복 요청하지 않음. human full permissions/grant·본인 MFA/state/lock은 별도 미완료 |
| platform egress F02 | Relay EIP와 ROSA Internet/NAT egress는 별개 | #35/#38: 단일 NAT/대안의 지원·장애·source 경계와 실제 배치 계약 잔여. Relay로 모든 egress를 우회하도록 추론하지 않음 |
| 관리 경로 F03 | Runner source가 기존 selector 밖, bidirectional private DNS 계약 검토 기록 존재 | 실제 Runner/local router/vpn-gw L3·반환·source 보존, 필수 DNS subset·PrivateLink/SG 지원의 수용이 필요. 공개 API/TLS/SNAT 우회 금지 |
| App/DB source F04/F05 | DB 목적지 .55:5432, host FORWARD·DB firewall/pg_hba 및 NP/credential 분담 | #38/#43/#47: worker replacement 후 source-set/egress adapter·전체 NP union·DB 권한, 외부 engine/metrics DENY와 ingress source 보존 계약. SG CIDR 결정을 최종 App source 인수로 확대하지 않음 |
| Registry F06/D22 | #42: Basic Ready 입력 후 단일 Primary/Fallback 결정. Harbor TLS 과거 readback 존재 | 아래 기존 원본 재사용. pre-create에는 옵션별 경로/보안·실패 시 중단 계약 정리; 실제 ROSA cold-pull/최종 D22는 이후 단계. #43/#46 소비 전 mode·endpoint·principal·trust·digest·fallback 완결 필요 |
| Hybrid DNS D23 | #40 P0 기본 IP endpoint 유지, P1 DNS는 Go+capacity일 때만 | P1 미결을 초기 P0/Stage-A 차단으로 새로 추가하지 않음. **필수 private 관리 DNS subset**은 F03과 별도로 계약 수용 필요 |
| Operator D26 | #51 Mirror+capacity 때만 P1 구현, Direct면 승인된 미구현 처리 | 전체 Freeze 준비에서 결정 시점/조건부 범위를 명시하고 P1 구현을 초기 P0 필수로 확대하지 않음 |

## 기존 증적 재사용과 단계별 판단

[#40 5978867156](https://github.com/321Team/fds-project-baseline/issues/40#issuecomment-5978867156)의 zone/source·기존 DNS 검증 연결을 재사용한다. DNS52/53의 과거 반환 경로가 현재 Runner→vpn-gw 전체 접근 PASS는 아니다. 기존 DNS 시험을 통째로 다시 요구하지 않는다.

[#42 5977390034](https://github.com/321Team/fds-project-baseline/issues/42#issuecomment-5977390034)의 Harbor pinned-CA/FQDN TLS `PASS_USER_READBACK`은 유지한다. assistant 원본 재해시/독립 Evidence Review·실제 Robot scope/expiry·HCP trust/cold-pull·최종 승인 digest는 구분한다. D19 TLS 및 #110 공급망의 기존 선택을 다시 승인 대기로 만들지 않는다.

[#42](https://github.com/321Team/fds-project-baseline/issues/42)의 최종 D22는10-15 Basic Ready 입력 뒤이며 [#40](https://github.com/321Team/fds-project-baseline/issues/40)의 P1 Decision은10-16 창이다. 이 후속 actual 시험을 초기 network/Relay 생성 전 완료하라는 새 조건을 만들지 않는다. 생성 전 계약/조건부 경계를 먼저 정리하고 단계별 GO는 기존 Gate 판단자가 기록한다.

## 다음 순서·완료조건

1. #35/#37이 새 코드 exact HEAD를 독립 검토한다. AMI resource/정책·bootstrap·worker read/SG delta를 포함한다. 작성자의 자체 시험을 독립 승인으로 쓰지 않는다.
2. #35/#38 이하영의 worker key/배치·capacity·platform egress 입력, #43/#47의 관리/DB/App source 입력을 받아 F01~F06 미결 계약을 권욱이 취합한다. 담당자에게 같은 기존 자료의 재생산을 요구하지 않는다.
3. #34의 생성 전 필수 계약과 후속 actual readback을 분리해 Freeze를 판단한다. 전체 정책 미수신 상태에서 부분 권한을 먼저 부여하거나 root로 업무 Plan을 우회하지 않는다.
4. full policy 검토/중앙 grant/readback 이후 본인 MFA/lock·거부·복구→network Plan 검토로 이어간다. 이 작업에서 AWS mutation/Plan/Apply/ROSA·VPN Runtime은 미실행이다.

이번 산출물은 구현 후보와 입력 정합표이며 #34 전체 Freeze·G4·AC·정본 publication 완료가 아니다.
