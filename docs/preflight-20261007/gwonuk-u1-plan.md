# 권욱 본인 역할·state/lock·세션 시험 준비

CODEX_ASSISTED. 2026-10-08. **시험 설계/실행 자료 준비이며 U1 NOT_RUN.** 중앙 사전조회에서 IaC/Network 역할이 ABSENT이므로 지금 본인 전환을 반복해도 새 권한 성공을 증명할 수 없다.

기준: baseline main81365568의 [팀 계약](https://github.com/321Team/fds-project-baseline/blob/81365568fd0b946ad93e4d82ae8191add5fcacd0/phase2/permissions/20261006-team-build-test/README.md), [IaC trust 후보](https://github.com/321Team/fds-project-baseline/blob/81365568fd0b946ad93e4d82ae8191add5fcacd0/phase2/permissions/20261006-work-role-precheck/candidates/trust-FDS-IaC-Operator.candidate.json), [Network 최종 후보](https://github.com/321Team/fds-project-baseline/blob/81365568fd0b946ad93e4d82ae8191add5fcacd0/phase2/permissions/20261006-network-final-candidate/README.md). actual grant/readback가 시험 입력이며 후보만으로 실행하지 않는다.

## 준비된 대상/선행조건

- 중앙 계정774055931866, 서울. 권욱 사용자 `321team-gwonuk`, 본인 MFA, session name `321team-gwonuk`. root를 본인 업무 역할 시험으로 대체하지 않는다. MFA 코드/장기키를 채팅·로그·파일에 넣지 않는다.
- grant 후 승인된 본인 CLI/MFA 절차로 전환하고 `aws sts get-caller-identity --region ap-northeast-2 --output json --no-cli-pager`로 actual role/session/account를 대조한다. ARN은 MFA 증명 자체가 아니므로 실제 AssumeRole의 수용/거부 결과와 함께 보존한다. AssumeRole 자격증명 stdout을 공개 로그에 덤프하지 않는다.
- 소스/작업경로: CloudShell HOME 개인0700 경로, reviewed checkout. Terraform1.16.4/provider6.66.0 lock, backend bucket `fds-tfstate-774055931866-ap-northeast-2`, default workspace, component `phase2/network/terraform.tfstate` 및 `phase2/vpn/terraform.tfstate`, native `.tflock`.
- 실행할 실제 command/RC/stdout/stderr, 시작/종료, host·identity, source/policy/input hash, 예상/실제 판정, 정리 결과를 개인 evidence 회차에 기록한다. 토큰·state payload·plan 전체는 GitHub 게시하지 않는다.

## 순차 시험표

| case | 단계·실행 내용 | 성공/중단 및 복구 |
|---|---|---|
| U1-I1 |본인 MFA→IaC 역할, 정확 session 이름 확인|배정 principal+MFA trust 실측. 타 role/user로 성공 대체 금지|
| U1-I2 |[network Plan 절차](plan-runbook.md#1-network-plan)로 init/validate/reviewed plan|기존 승인 범위/Gate 충족 후. state 접근·lock 생성/정상해제 원본 필요. 아직 cloud plan NOT_RUN|
| U1-I3 |동일 network component에서 본인 시험 lock과 Terraform plan 경쟁|아래 조건부 lock fixture 절차로 고유 ID/ETag 결속. B의 lock 거부→자기 fixture 정리→B 재시도. 실제 경쟁 API가 없으면 NOT_RUN|
| U1-I4 |거부 시험: noMFA·잘못된 session/미배정role, 서울 밖·타 Project·타state·state삭제/권한상승 경계|중앙 simulation과 실제시험을 분리. noMFA/잘못된 session은 자신의 identity만 사용. 타 Project 생성/실제 state DeleteObject/타인 자원 변경으로 거부를 시험하지 않음. 파괴 API 거부는 정책 simulation 증적이며 Runtime PASS로 표시하지 않음|
| U1-I5 |오류 종료·정상 lock 해제·동일 source 재계획|잔여 lock이면 writer·Lock ID·소유·프로세스 상태부터 확인. 자동 force-unlock/state삭제 금지. 계획되지 않은 drift/쓰기 발생 시 STOP|
| U1-N1 |실제 Relay/Agent Online, Network exact bind와 문서 readback 수신 후 본인 Network 역할·CLI plugin으로 Standard_Stream StartSession|정확 Relay/문서, 실제 본인 접속과 CloudTrail/세션 내 script 기록. 명령 기록의 credential/PSK 제외|
| U1-N2 |본인 세션 Resume/Terminate 정상 + 타 문서/대상 경계|타인의 활성 세션을 실제 종료하여 deny를 시험하지 않음. 자신의 session만 정리. Bool/context 실제 제공 여부 불일치면 STOP, 조건 삭제로 우회 금지|

## I3 재현 절차 (grant 후 검토된 시험 회차)

일반 plan은 빠르게 끝나므로 두 번 실행만으로 lock 경쟁 성공이라고 판정하지 않는다. native S3 lockfile의 API 경계는 [HashiCorp S3 backend](https://developer.hashicorp.com/terraform/language/backend/s3), 조건부 연산은 AWS [PutObject](https://docs.aws.amazon.com/cli/latest/reference/s3api/put-object.html) / [DeleteObject](https://docs.aws.amazon.com/cli/latest/reference/s3api/delete-object.html)를 따른다. 이 fixture는 실제 Terraform 프로세스 장애가 아닌 **잠금 충돌·정리 API 시험**이며 그 한계를 기록한다.

1. 역할·계정·backend와 테스트 창을 고정하고 live writer가 없음을 담당자와 확인한다. exact 시험 key는 `phase2/network/terraform.tfstate.tflock` 하나다. state 본문에 Put/Delete하지 않는다. CLI가 아래 조건부 옵션을 지원하지 않으면 중단한다.
2. HOME 개인 경로에 Terraform LockInfo 구조 JSON을 만든다: `ID`=이번 UUID, `Operation`=`OperationTypePlan`, `Info`=`U1-I3 owned test fixture`, `Who`=actual 본인 session, `Version`=actual Terraform 버전, `Created`=actual UTC RFC3339, `Path`=exact bucket/state key. 비밀과 실제 state 내용은 포함하지 않는다. local SHA를 기록한다.
3. `aws s3api put-object`에 exact bucket/key, `--body` 위 파일, `--if-none-match '*'`, `--server-side-encryption AES256`, `--expected-bucket-owner 774055931866`, 서울/JSON/no-cli-pager를 지정한다. **412/409/AccessDenied/timeout 모두 STOP**, 반복 덮어쓰기 없음. 응답 ETag를 보존하고 GetObject로 자기 UUID와 원본 바이트/hash가 일치하는지 확인한다. timeout이면 fresh readback으로 자기 생성 여부부터 판정한다.
4. B가 이미 초기화된 같은 reviewed network root에서 `plan -input=false -var=execution_enabled=true -lock-timeout=5s`를 수행한다. RC1과 lock-acquisition 오류·자기 fixture Lock ID가 함께 있어야 충돌 성공이다. 권한 오류/다른 원인의 RC1은 PASS가 아니다.
5. 자기 UUID·hash·ETag를 다시 대조한 뒤에만 `aws s3api delete-object`의 exact `.tflock` key와 `--if-match` 원래 ETag, expected owner/region을 사용한다. version ID 삭제·state DeleteObject·외부 lock 삭제 금지. 412/timeout/내용 변경이면 소유 상태부터 재조회하고 자동 재시도하지 않는다. versioned bucket의 이 정상 삭제는 과거 version 영구삭제가 아니다.
6. 현재 lock 부재를 권한 있는 readback의404로 확인한다(403을 부재로 해석 금지). B의 새 plan이 정상 lock 획득/해제를 하는지 별도 원본으로 판정한다. 실제 writer 장애 후 정상 해제는 I5에서 확인하며 fixture 성공으로 대체하지 않는다.

실행/정리 기록과 fixture는 비공개 evidence에 보존한다. 준비 단계에는 lock 객체조차 생성하지 않았다. full policy에 exact lock Get/Put/Delete·bucket encryption 조건이 맞는지 #35 검토에 포함하며 실제 grant 없는 중앙 root 실행으로 대체하지 않는다.

## Session document에서 이미 결정된 것

[#37 Lead 결정6013422735](https://github.com/321Team/fds-project-baseline/issues/37#issuecomment-6013422735): Standard_Stream, S3/CloudWatch session logging 없음, session-data KMS 없음, RunAs 없음, 기본 ssm-user. 명령 증적은 세션 내 script, 접속 주체/시각은 CloudTrail. **설정 방향을 사용자에게 다시 선택받지 않는다.** 현재 [session-document.tf](../../terraform/vpn/session-document.tf)의 소스는 이 방향과 일치한다.

잔여는 #35의 계정 공용 문서 소유 수용·fresh actual absence·권한/실행 Gate·Terraform 생성 후 owner/type/default version/content SHA readback 및 #37 정책 exact bind다. 10-07 InvalidDocument 수집은 부재 검토 자료이며 무조건 생성 허가가 아니다. create_session_document=true 입력은 이 조건 수용 후 계획 회차에만 사용하며 기본false를 이번 작업에서 변경하지 않는다. 문서 포함 최초 vpn plan은 기존 문서OFF 7create에 문서1개를 더하는 **8create 예상**이나 실제 saved plan 전체로 검토한다.

완료 회신: case별 STATIC/SIMULATION/RUNTIME/NOT_RUN을 구분해 #35 및 #37에 본인 원본과 결과를 인계한다. 타 팀원의 본인 시험과 독립 Evidence Review를 대신하지 않는다.
