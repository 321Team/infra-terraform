# PR #4 정적 검증 및 network·VPN 구현 인계

AI 사용: CODEX_ASSISTED. 책임: #35 Execution Lead 이하영, 중앙 지원 이권욱. #37 소비·개인 U1은 이재환 담당 범위를 유지한다.

## 검증 대상과 현재 결과

Terraform 입력은 infra-terraform 후보 `d506ffa434257d970eb3781756b25c9a6c41af14`의 12개 파일이다. `validation/stage-a-20261007/source.json`은 해당 원본의 SHA-256을 기록한다. 이 후속 변경은 Terraform 입력·lock·backend bytes를 바꾸지 않고 정적 실행 보조 코드, 시험, 인계 문서만 추가한다. 실제 실행에는 패키지 archive SHA-256과 최종 PR HEAD를 함께 기록한다.

작성 환경에는 Terraform이 없고 공식 release 파일 연결은 proxy timeout이다. 따라서 실제 `fmt/init/validate`는 **NOT_RUN**이다. 보조 코드 unittest는 MOCK 검증이며 Terraform 실행 성공을 대신하지 않는다. 독립 리뷰·merge·AWS 실행·role grant·개인 runtime·Stage-A GO는 각각 별도 상태다. Draft 해제 전 실제 CLI 결과를 받는다.

## CloudShell 격리 실행

CloudShell에서 이전에 검증한 `$HOME/bin/terraform` 1.16.4를 사용한다. 바이너리가 없거나 버전이 다르면 멈추며 자동 설치·버전 교체는 하지 않는다. provider 6.66.0 설치는 새 개인 작업 경로에서 공식 Registry와 lock의 checksum 검증으로 진행된다. 이것은 운영 호스트 패키지 설치·AWS 변경이 아니다. 네트워크 실패 때 lock을 고치거나 대체 mirror로 우회하지 않는다.

전달받은 archive SHA-256을 확인한 후 새 디렉터리에 압축 해제한다. 패키지 안에서 아래 명령을 순서대로 실행하고 실패 시 이후 명령을 실행하지 않는다. 기존 작업 디렉터리, state, `.terraform` cache를 재사용하지 않는다.

```bash
sha256sum -c validation/stage-a-20261007/PACKAGE_SHA256SUMS
python3 -m unittest discover -s tests -p 'test_stage_a_static.py' -v
python3 scripts/validate-stage-a.py --terraform "$HOME/bin/terraform"
printf 'STAGE_A_STATIC_RC=%s\n' "$?"
```

helper는 고정 파일 hash와 clean stage-a 파일 집합을 대조한 뒤 그 파일만 복사한다. 상속 AWS credential/CLI 인자·로그·provider override·사용자 HOME 설정을 전달하지 않는다. 새 HOME·TF_DATA_DIR·CLI config 및 default workspace를 사용한다. 환경 변수 값이나 credential은 출력하지 않는다.

실행 명령은 `version -json`, `fmt -check`, `init -backend=false -lockfile=readonly -input=false`, `validate -json`으로 한정된다. `.example` 5개는 stdin으로 별도 fmt 검사한다. `init`은 최대 180초, 다른 명령은 30초다. 실패·timeout·잘못된 JSON·source/lock 변경은 STOP이며 원본 stdout/stderr를 개인 capture 경로에 보존한다. 자동 재시도·source 수정은 없다.

성공 조건은 전 명령 RC=0, Terraform=1.16.4, 설치 provider=6.66.0, validate `valid=true/error_count=0`, 입력 및 lock 변경 없음이다. 경고는 `WarningCount`와 원본 validate 결과로 별도 확인한다. `.example` fmt는 formatting 검사이며 backend 동작 시험이 아니다. `validate` 역시 실제 입력값·IAM postcondition·서비스 API·remote state를 검증하지 않는다.

보고는 summary JSON, 마지막 RC, capture SHA256SUMS 확인 결과를 제출한다. 원문 state·credential·provider binary를 GitHub에 올리지 않는다. public 인계에는 계정·ARN·개인 경로를 마스킹한다. 이 단계 복구는 실패한 개인 작업 복사본을 보존하고 source를 수정한 새 PR HEAD로 필요한 부분만 재실행하는 것이다. AWS 정리 작업은 없다.

공식 근거: [init/backend=false와 lockfile=readonly](https://developer.hashicorp.com/terraform/cli/commands/init), [validate의 검사 범위·JSON](https://developer.hashicorp.com/terraform/cli/commands/validate), [fmt check와 stdin](https://developer.hashicorp.com/terraform/cli/commands/fmt). 리뷰는 [REVIEW_POLICY](REVIEW_POLICY.md)를 따른다. 이 코드/설정 PR의 정확한 HEAD에 작성자 외 최소 1인 독립 리뷰 후 #35 Lead가 병합을 판단한다. 후보 격리 시험과 운영 반영을 구분한다.

## 확정 근거와 후속 구현 순서

근거는 [backend·EBS·PassRole 채택 6015740112](https://github.com/321Team/fds-project-baseline/issues/35#issuecomment-6015740112), [CloudFormation 4자원 소유권 6031301706](https://github.com/321Team/fds-project-baseline/issues/35#issuecomment-6031301706), [bootstrap readback 수신 6031865288](https://github.com/321Team/fds-project-baseline/issues/35#issuecomment-6031865288), [Lead 후속 리뷰 6032041833](https://github.com/321Team/fds-project-baseline/issues/35#issuecomment-6032041833)다. bootstrap은 재실행하지 않는다. network/VPN을 먼저 구현할 수 있으며 미래 ROSA 전체 구현을 선행조건으로 추가하지 않는다.

| 범위 | 이미 확정된 입력 / 구현 연결 | 실제 source와 함께 남길 항목 |
|---|---|---|
| network root | 서울, VPC `10.20.0.0/16`, stage-a의 4개 subnet/AZ/zone ID | VPC·subnet·IGW·route table·association·SG 등의 최종 resource 주소, owner, route/egress/DNS·SG tuple 근거. 미확정 topology를 임의로 완성하지 않음 |
| vpn root | EC2+EIP Relay, `10.20.110.10`, 고정 AMI/owner·t3.medium, auto IPv4/SSH OFF, source_dest_check OFF | EC2/ENI/EIP owner와 참조, cloud-init/Agent/Libreswan 경계, 삭제·복구·비용 조건 및 network output 계약 |
| Relay profile / EBS | CloudFormation 기존 profile data 참조; encrypted gp3 40GiB, `alias/aws/ebs` | profile exact ARN·role 연결, 실제 EBS KmsKeyId 및 API/dependent action. Terraform으로 bootstrap을 import/create/delete하지 않음 |
| SSM 문서 | [#37 채택 6013422735](https://github.com/321Team/fds-project-baseline/issues/37#issuecomment-6013422735): `SSM-SessionManagerRunShell`, `Standard_Stream`, S3/CloudWatch 세션 로그 OFF, 세션 KMS OFF, Run As OFF. #35 source/default version 소유 | 문서 source와 owner/type/content SHA, 실제 Relay ID·Agent Online·document version·EBS readback을 #37에 인계. 세션 KMS OFF를 EBS 암호화에 확대하지 않으며 PSK/장기 credential은 tfstate에 넣지 않음 |
| state | 별도 network/vpn root, default workspace, 고정 state key 및 `.tflock` | 각 root 소유권과 output 소비, backend+lock+복구 시험; generic scaffold remote init 금지 |
| 사람 역할 | 공통 ReadOnly 유지, 업무 쓰기는 MFA AssumeRole 분리 | 완결된 IaC permissions/trust/identity 연결과 담당자별 허용/거부·복구 시험. 현재 scaffold GetInstanceProfile 1개로 full policy 완료 선언하지 않음 |

작성할 API 목록은 **실제 최종 resource/data source 경로 + 고정 provider 6.66.0 구현 근거 + create/read/update/delete/refresh API + dependent action + ARN/region/tag 조건 + grant 주체 + 시험 case**를 한 행씩 연결한다. 비용 설정·일반 관리자 정책·미래 ROSA IAM 전체 쓰기를 포함하지 않는다. 현 scaffold의 확인된 API는 Relay `iam:GetInstanceProfile`뿐이다.

현재 확정된 최소 privilege 연결은 Relay role 한 개에 대한 `iam:PassRole` + `iam:PassedToService=ec2.amazonaws.com`, 기존 GetRole/GetInstanceProfile 조회, 승인된 backend 부분 정책이다. EC2 `RunInstances`의 여러 resource 유형, tag-on-create, encrypted EBS/KMS, SSM document lifecycle 등은 실제 코드가 선택한 구성과 공식 authorization reference를 대조해 full policy에 채운다. 아직 구현되지 않은 자원의 action을 일괄 허용하지 않는다.

다음 순서는 (1) 이 scaffold 정적 결과·독립 리뷰, (2) #35 담당자의 network/VPN resource source와 API inventory 및 완결 policy PR, (3) 중앙 fresh backup·ValidatePolicy·양/음성 simulation·적용/readback, (4) 본인 MFA AssumeRole·reviewed plan·기존 유료 자원 GO 조건 후 실행, (5) #37 exact ID/document/EBS 인계와 각 본인 runtime 결과다. 기존 14건 bootstrap 시험과 46/9 부분 simulation은 변경 영향이 없으므로 반복하지 않는다.

현재 `AWS_MUTATION=NOT_RUN`, `ROLE_GRANT=NOT_RUN`, `USER_RUNTIME=NOT_TESTED`, `STAGE_A_READINESS=NOT_ASSESSED`다. 이 인계는 현행 담당·AC·Freeze·비용 통제를 바꾸지 않는다.
