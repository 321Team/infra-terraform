# 중앙 IAM 검증 착수 자료 — 2026-10-08

CODEX_ASSISTED. 사용자 “후속 절차 착수”에 따라 중앙 검증 직전의 입력을 구체화했다. **PREPARATION=UPDATED / POLICY_INPUT=PENDING / CENTRAL_VALIDATE=NOT_RUN / GRANT=NOT_RUN**. 역할을 먼저 만들거나 부분 정책을 부착하는 절차가 아니다.

## 최신 원본과 실제 진전

2026-10-08 00:07 KST 조회에서 baseline main `81365568fd0b946ad93e4d82ae8191add5fcacd0`, infra-terraform main `0eabe8daa75a6b9bf960fe1ea5eeaf6a8818f216`, infra-rosa main `a37b10628cd59427c45dd28e2f6bd924891e1c54`. 세 저장소 open PR은 infra-terraform PR6만 확인했다. #34/#35/#37에는 직전 결정·수신 코멘트 외 새 입력이 없고 #38 새 코멘트도 없었다. PR6 독립 review는0건이었다. 개인 작업공간·미게시 branch의 작업 상태까지 확인했다는 뜻은 아니다.

직전 [중앙 AWS 실제 조회](central-readonly-receipt.md)의 두 human role ABSENT와 기본 Session document 부재 증적을 재사용한다. 이번에는 AWS API를 반복하지 않고, pinned AWS provider6.66.0 원본을 내려받아 **network6개 resource block/15개 instance + AZ data3개**의 호출 경로를 [별도 보완 inventory](network-permission-supplement.json)에 연결했다. 기존14행 inventory와 승인 Terraform source는 수정하지 않았다. IAM에 붙일 수 있는 `Statement` 정책 파일은 아직 없다.

## 새로 구체화한 권한·복구 검토 사항

| 소스 관측 | 영향·해결 입력 | 완료 확인 |
|---|---|---|
| VPC Read가 default NACL/main route table/default SG와 VPC attributes를 조회 | DescribeNetworkAcls/DescribeRouteTables/DescribeSecurityGroups/DescribeVpcAttribute까지 검토. 일부 실패는 provider가 warning으로 남기므로 command RC만으로 완전 조회 판정 금지 | 변경 policy의 read 범위 및 정상 readback, warning 해석 |
| Subnet Delete는 먼저 DescribeNetworkInterfaces 수행 | 성공 생성 권한만 나열하면 정리 때 권한 누락 가능. 기본 삭제 read와 조건부 service ENI 정리를 분리 | subnet 소유·ENI 의존성·삭제 순서 포함한 복구 검토 |
| Route table Delete가 실제 association 전체를 순회 | 다른 소유자의 association이 연결돼 있으면 계획 밖 연결 해제 위험. 삭제 전 실제 연결 소유를 대조 | foreign association이면 STOP, 담당자의 정리 후 재계획 |
| VPC/subnet DependencyViolation 뒤 GuardDuty 자원 정리 경로 존재 | endpoint/SG 변경·삭제 권한을 정상 구축 정책에 자동 추가하지 않음. 서비스 소유자의 정리 또는 검토된 최소 예외 경로를 명시 | 미수용 경로는 거부 유지. 모니터링 해제·광범위 ENI/endpoint 권한으로 우회 금지 |
| 이후 ENI target route를 읽을 때 DescribeNetworkInterfaces 가능 | 최초15-create와 후속 vpn route 활성화 뒤 refresh 권한을 함께 검토 | route 활성화 후 read 경로에 반영하되 지금 route GO로 보지 않음 |

근거는 inventory의 provider 파일별 URL/행·SHA256에 있다. 이는 기존 “provider transitive reads/cleanup 미검토”를 원본으로 구체화한 것이며 새 AC나 실행 실패 보고가 아니다. 불필요한 provider 지원 분기(IPv6/IPAM/tenancy/VGW)를 이름만 보고 전부 허용하지 않는다.

[AWS EC2 권한 표](https://docs.aws.amazon.com/service-authorization/latest/reference/list_ec2.html)를 기준으로 Action별 Resource/Condition/dependent action을 확인한다. Create의 새 자원 RequestTag와 기존 부모 자원 ResourceTag 조건은 별도로 검토한다. 읽기 API의 ARN 지원 여부를 확인하고 지원하지 않는 조회에 가짜 ARN 제한을 쓰지 않는다. association의 소유 경계는 subnet/route table로 검증한다. 목적지 CIDR·route target이 IAM으로 제한됐다는 가정은 실제 지원 condition 근거 없이는 하지 않는다.

## 이하영이 제출할 최소 묶음

기존 #35 생산 책임을 유지하며 아래를 한 번에 연결한다. **미완결 policy를 중앙이 임의 완성·승인하는 것으로 대신하지 않는다.**

1. 검토할 commit·파일 SHA256·권한 범위 수용 참조. 실제 network/vpn source, 기존14행+이번 network supplement를 합친 coverage와 제외 경로 사유.
2. IaC 전체 identity permissions JSON. network EC2 CRUD/read/tag, vpn RunInstances의 image/subnet/SG/ENI/volume/instance, exact Relay PassRole, 실제 EBS KMS 경계와 state4key/.tflock 정책을 연결. 기존 backend/PassRole 부분안만 제출하면 INCOMPLETE.
3. 각 statement의 Action/Resource/Condition/dependent ARN 표. 생성 시점 ID 미확정을 처리하는 제한과 생성 후 exact bind를 구분. 소유 tag 변경/제거, 외부 자원 retag, 중앙 CFn 자원 변경을 막는 근거.
4. 기존 trust 원본 및 변경 여부·본인 MFA/RoleSessionName·담당자 매핑. Network actual Relay ARN 입력은 생성 후 단계로 분리하며, 부재를 무제한 ARN으로 메우지 않음.
5. 변경분의 simulation 요청 JSON들과 기대 판정표. 각 case ID·policy SHA·action/resource/context·expected decision·근거. 다중 자원 API는 자원별 결과까지 판정. 필요한 context를 비워 implicitDeny만 얻은 음성시험을 PASS로 쓰지 않음.
6. before/readback·부분 실패 복구·소유권 경계. 중앙 bootstrap4자원과 계정 공용 Session document의 소유는 그대로 보존. 문서 actual absence가 확인됐어도 `create_session_document=false`를 자동 해제하지 않음.

권욱은 위 묶음을 수신한 뒤 누락/범위/해시를 확인하고 중앙 검증을 이어간다. 자기 작성 자료를 타인의 독립 리뷰로 표시하지 않는다. 현재는 policy 파일·exact 검토 수용 근거가 없어 중앙 ValidatePolicy/simulation 명령 실행 대상이 확정되지 않았다.

## 중앙 검증 실행 순서와 판정

대상: 서울 중앙 계정 끝1866의 기존 승인 검증 세션. 작업 경로: CloudShell HOME의 새 개인0700 디렉터리. Python3/AWS CLI, 검토된 입력 묶음과 SHA256SUMS, 명령별 stdout/stderr/RC/timeout/UTC·KST 보존이 선행조건이다. 키·토큰을 출력하거나 저장하지 않는다.

1. source/policy SHA와 수용 범위를 대조한다. 예상 밖 파일·상속 endpoint override·계정 불일치면 STOP.
2. 변경 직전 STS와 대상 role/policy/trust의 fresh before를 보존한다. 역할이 여전히 없으면 NoSuchEntity를 그대로 기록한다. 이전 부재 관측은 시간차가 있으므로 쓰기 직전 확인을 생략하는 근거가 아니다. 기존 role이 나타나면 동시 변경으로 보고 원본을 검토한다.
3. identity policy를 아래 **준비 명령**으로 검증한다. `FDS_POLICY`는 검토된 실제 파일 절대경로, `FDS_CAPTURE`는 새 증거 경로다. 값이 미정인 지금은 실행하지 않는다. 외부 timeout과 command/RC 수집을 적용하고 API 오류/timeout이면 중단한다.

```bash
aws accessanalyzer validate-policy \
  --policy-document "file://$FDS_POLICY" \
  --policy-type IDENTITY_POLICY \
  --region ap-northeast-2 --output json --no-cli-pager \
  --cli-connect-timeout 10 --cli-read-timeout 30 \
  > "$FDS_CAPTURE/validate-identity.stdout" \
  2> "$FDS_CAPTURE/validate-identity.stderr"
```

CLI 자동 pagination을 유지한다. RC0만 보지 않고 findings 전체를 심사한다. ERROR/SECURITY_WARNING은 해소 또는 권한 있는 검토자의 처리 근거가 필요하다. WARNING/SUGGESTION은 영향과 수용 사유를 남긴다. trust가 바뀌면 RESOURCE_POLICY와 `AWS::IAM::AssumeRolePolicyDocument` 유형으로 별도 검증한다. trust 불변인데 과거 시험 전부를 반복하지 않는다. [AWS ValidatePolicy 문서](https://docs.aws.amazon.com/cli/latest/reference/accessanalyzer/validate-policy.html).

4. 검토된 변경분 case를 `iam simulate-custom-policy`로 실행한다. 역할이 없는 지금 Principal simulation 성공을 만들기 위해 역할을 선생성하지 않는다. API RC와 각 EvalDecision·ResourceSpecificResults·MissingContextValues를 기대표와 대조한다. 새 network/action/조건·복구 영향은 재검증하며 기존22/46/9건 결과는 해당 SHA·범위에서 재사용한다.
5. 결과 수용과 기존 실제 부여 승인 범위를 확인한 뒤에만 grant/readback 단계로 이동한다. **이 문서에는 부여 명령이 없고 grant 준비 완료도 아니다.** 변경 정책 또는 source가 바뀌면 영향 case와 정책 hash를 갱신한다.

양성/음성 최소 비교축: 서울/타 리전, 올바른/누락·오류 ownership tags, 소유/외부 부모·대상 자원, 허용 tag 수정/보호 tag 제거·retag, 올바른/잘못된 PassRole·서비스, state payload 삭제 거부와 lock 정리 허용, Network 역할 state 접근 거부. source상 불필요한 cleanup 권한은 거부로 남는지 확인한다. 없는 IAM context key를 만들어 범위를 제한했다고 주장하지 않는다.

[AWS simulator 설명](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_testing-policies.html)상 simulation은 실제 서비스 요청이 아니며 live 결과와 다를 수 있다. 현재 입력에 포함되지 않은 session policy·SCP·resource/endpoint policy 등까지 통과했다고 표시하지 않는다. 최종 실효권한은 실제 부여/readback과 **각 본인 MFA 역할 시험**으로 검증한다.

오류 시 원본을 보존하고 다음 단계로 넘어가지 않는다. 읽기/검증만 수행한 회차에는 AWS rollback이 없고, 후속 부여의 부분 실패는 미리 검토한 before 기준으로 해당 변경만 복구한다. 일괄 정책 삭제나 중앙 CFn 재생성은 하지 않는다.

## 단계별 남은 사항

| 단계 | 현재 판정 | 다음 담당·완료조건 |
|---|---|---|
| 중앙 IAM 검증 | 입력 대기 | 이하영: 전체 정책+검토+변경 case. 권욱: 실제 중앙 검증/판정 접수 |
| network Plan | 미실행 | 중앙 grant/readback·본인 MFA/state/lock 시험 후 고정 source/입력으로 [기존 절차](plan-runbook.md) 수행 |
| Relay 생성 | HOLD | #35/#37: Stream10 SSM 지원/정확 Agent·firewalld·repo·Libreswan 근거 및 bootstrap 적합성 |
| Freeze·유료 Apply | HOLD | #34/#35/#38: 선택한1AZ3대 actual AZ/subnet·용량·운영창, 지원은 사용자 확인 완료. 누적/미반영+잔여 견적의 내부 한도 판단과 자부담0; 지원 재확인 차단은 해제 |
| route 활성화 | OFF | #37/#38: 실제 source/inner SG·터널·허용/거부·복구 증적 |

AMI 공백을 network Plan의 새로운 필수조건으로 올리거나, network source에 subnet4개가 있다는 이유로 사용자 ROSA1AZ 선택을3AZ로 바꾸지 않는다. 준비 자료는 PR6에만 반영하며 독립 REVIEW/MERGE/PUBLICATION은 별도다.

## 10-08 후속 정합화

Session document 구성 방향은 [#37 기존 결정6013422735](https://github.com/321Team/fds-project-baseline/issues/37#issuecomment-6013422735)으로 확정되어 있다. 다시 구성값을 결정받지 않는다. #35의 account-wide ownership 수용·fresh absence·실행 Gate·실제 생성/readback이 남으며 default false를 자동 변경하지 않는다. [권욱 본인 U1 패킷](gwonuk-u1-plan.md)의 exact lock fixture/경쟁·정리 및 음성시험 구분도 full policy 검토에 연결한다.
