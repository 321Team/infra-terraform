# 이권욱 담당 착수·후속 순서

CODEX_ASSISTED. 2026-10-07 사용자 “내가 착수해야 되는 부분 진행” 및 후속 설계 선택에 따른 실제 작업 기록. 기준 baseline main81365568 / infra-terraform main0eabe8da / PR6 원HEAD d8a35b9e. 상세 full SHA는 README에 있다.

## 이번 직접 결정 수신

1. 총상한 USD500, 팀 자부담 USD0. 기존 목표400/중단450/보호예비50 유지.
2. 1 AZ·m5.xlarge worker3대, worker1대 장애·복구 시험 준비. AZ 전체 장애 대응을 새 P0 필수조건으로 추가하지 않음. 제시한 단일 AZ 중단 위험을 포함한 설계 방향 선택이다.
3. 위 결정을 #34 운영 기록과 PR6 준비 자료에 연결한다. Freeze/비용 GO·실행 승인·AC 인수로 확대하지 않는다.

## 중앙 읽기 전용 조회 실행 완료

대상: 서울 중앙 계정 끝1866, 기존 승인 중앙 사전조회/CloudShell, 홈 개인 작업 경로. 사용자 로그인 완료 후 STS로 중앙 root identity를 확인하고 2026-10-07 23:56:33~38 KST에 exact AMI·IaC/Network role·Session document를 [수집 절차](iam-stage-a.md#읽기-전용-추가-수집)로 조회했다. IaC/Network 역할은 모두 ABSENT(NoSuchEntity), document는 NOT_FOUND_REVIEW_REQUIRED(InvalidDocument), AMI metadata는 일치했다. [원본 접수·무결성 결과](central-readonly-receipt.md). 본인 계정으로 먼저 로그인하라는 안내는 순서 오류여서 중앙 조회 → 역할 부여 → 각 본인 MFA 시험으로 정정했다.

수집기 단일 파일 source는 PR6 원HEAD `d8a35b9e0d7077df4ddc12434738c779839f34a6`와 동일하다. 새 문서 선택 반영으로 수집기를 재시험하거나 기존 bootstrap·IAM simulation을 반복할 필요는 없다. 원본 SHA256은 `verification.json`의 `new_source_hashes["scripts/collect-phase2-preflight.py"]`에 있다. 전달 사본 SHA를 검증한 뒤 실행한다. 정상 collection도 role grant/full permissions/OS 내부 검증을 뜻하지 않는다.

## 비용지원 확인에 필요한 최소 입력

- 교육장 제공 AWS 비용지원의 적용기간/만료일.
- 현재 누적 Gross와 조회 KST, 미반영 사용분.
- **ROSA Marketplace가 교육장 지원에 포함되는지**, 제외 요금이 있다면 결제 주체. 팀 자부담을 허용하는 것으로 처리하지 않음.
- 선택한 1AZ3대 기준 잔여 운영시간·Relay/EBS/IPv4/NAT/LB/DNS/전송/정리비용.

기존 조회권한에서 확인 가능한 값만 수신하며 Billing/CE/Budget 권한·설정을 새로 부여하지 않는다. 계정별 지원 약관은 공개 AWS 요금표로 확정할 수 없다. 없는 입력을0으로 기록하지 않는다. 교육장에 메시지를 발송한 것은 아니다.

## 타 담당 입력 수신 후 이어갈 권욱 작업

| 생산 입력 / 책임 | 권욱의 다음 실행 | 완료조건 |
|---|---|---|
| #35 이하영: actual resource/API/완결 permissions와 검토 source | 중앙 fresh before backup·ValidatePolicy·변경 delta 양/음성 검증, 기존 승인 범위에서 grant/readback 준비 | full 정책/소스/권한 경계 일치. 실제 부여의 승인 범위 확인 전 AWS 쓰기 없음 |
| 중앙 grant/readback 완료 | 권욱 본인 MFA IaC 역할 시험, state/lock·거부·복구 | 본인 실행 원본. 하영/재환 결과로 대체하지 않음 |
| #35/#38 이하영: 1AZ3대 actual AZ/subnet·용량·정확 운영창·cost-to-complete; #37 이재환: source/SG/복구; 기존 DNS/Registry/보안 미결 | #34 Freeze와 비용/생명주기 판단 | 선택 방향 충족 + 자부담0 + 기존 필수조건. actual ID는 생성 후 관측 계약으로 분리 |
| 실제 Relay/Agent/document/EBS handoff와 Network exact bind | 권욱 본인 Network U1 | 실제 세션·허용/거부 증적; 팀원 독립 실행을 대체하지 않음 |

권욱에게 남은 일이 없다고 표시하지 않는다. 지금 미완결 정책을 대신 승인하거나 역할을 먼저 만드는 것은 선행조건 역전이다. 준비 문서·결정 기록 변경과 중앙 AWS 읽기 조회를 수행했으며, CloudShell 파일 외 AWS 설정 변경·rollback 대상은 없다. 기존 #35/#37 책임, 일정, AC, 비용 설정 보류는 유지한다.
