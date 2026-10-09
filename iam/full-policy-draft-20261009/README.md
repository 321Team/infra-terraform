# #9 전체 IAM 정책 초안 (Hard Gate 2) — 2026-10-09

상태: **DRAFT / 로컬 정적검사 PASS / AWS 미실행 / 부여 아님**
대상 이슈: [infra-terraform#9](https://github.com/321Team/infra-terraform/issues/9) · 원티켓 [#35](https://github.com/321Team/fds-project-baseline/issues/35)
비용: 파일 작성·로컬 검사만 — **비용 없음**

기준 소스
- infra-terraform main `93d71500e3e881c55f1814cd144ca41f43e77f3d` (`terraform/network`, `terraform/vpn`), AWS provider 6.66.0
- 14행 inventory `validation/components-20261007/resource-api-inventory.json`
- network 보완표 `docs/preflight-20261007/network-permission-supplement.json`
- 기존 후보: [fds-project-baseline `c02831d7` `phase2/permissions/20261006-*`](https://github.com/321Team/fds-project-baseline/tree/c02831d7e4060813bd36637f180ba40e11f55f8f/phase2/permissions) — State-PassRole·Relay template·trust는 원문 복사

## 한눈에 보기

| 역할 | 누가 | 붙일 정책 | 상태 |
|---|---|---|---|
| `FDS-IaC-Operator` | 권욱·하영 | `FDS-IaC-State-PassRole` + `FDS-IaC-Network` + `FDS-IaC-Vpn` + `FDS-IaC-Guardrails` | State-PassRole은 **기존 후보 그대로**(46+9건 시험분), 나머지 3개 **신규** |
| `FDS-Network-Operator` | 권욱·재환 | `FDS-Network-Operator-Relay.template` + `FDS-Network-Operator-StateDeny` | template은 **기존 그대로**(Relay 생성 후 instance ID 채움), StateDeny **신규** |
| `FDS-ReadOnly-Audit` | 3명 | AWS 관리형 `job-function/ViewOnlyAccess` + `FDS-ReadOnly-Audit-StateDeny` | **신규 제안 — Lead 확인 필요** |

trust: IaC·Network는 기존 후보 그대로(MFA=true, 본인 RoleSessionName), ReadOnly-Audit 신규. 사용자별 assume 정책은 ReadOnly-Audit을 추가한 버전(`trust/assume-*.json`).

## 설계 원칙 (쉽게)

1. **"우리 태그 붙은 것만 만진다."** 만들 때는 `Project=fds-hybrid`, `ManagedBy=terraform` 태그를 꼭 달아야 하고(`aws:RequestTag`), 고치거나 지울 때는 그 태그가 있는 자원만 가능하다(`aws:ResourceTag`). Terraform `default_tags`가 두 스택 모두 이 태그를 자동으로 단다.
2. **서울만.** 모든 쓰기에 `aws:RequestedRegion=ap-northeast-2`, Guardrails에서 다른 리전을 명시 거부.
3. **만능 권한 없음.** `ec2:*`, `iam:*`, `kms:*` 없음 (검사 스크립트가 확인).
4. **Relay EC2는 정해진 모양만.** AMI `ami-08d855918a18d0cf9` 하나, `t3.medium`만, IMDSv2 필수, 루트 디스크 gp3·암호화·40GiB 이하.
5. **보호 대상은 명시 거부.** 소유 태그 삭제/변경, 세션 문서 수정·삭제·SendCommand, CloudFormation 스택 변경, state 파일 삭제(기존 후보).

## 왜 state(Terraform 장부)를 역할별로 막나

state는 Terraform이 "무엇을 만들었는지" 적어 두는 장부다(S3 `fds-tfstate-774055931866-ap-northeast-2`, `phase2/` 아래 4개 key).

**팀원을 못 믿어서 막는 것이 아니다. 막는 대상은 사람이 아니라 역할(작업 세션)이다.** 같은 사람이라도 어떤 역할로 들어왔는지에 따라 할 수 있는 일이 달라진다.

| 이유 | 설명 |
|---|---|
| 실수 방지 | VPN·Relay 작업 중 잘못된 명령으로 state를 덮어쓰거나 지우면 Terraform이 기존 자원을 "없음"으로 보고 다시 만들거나 지울 수 있다. 그 작업에 필요 없는 권한은 처음부터 없게 한다. |
| 세션·자격증명 유출 대비 | 한 역할 세션이 노출되어도 피해 범위가 그 역할 권한으로 한정된다. Network 세션이 노출돼도 state와 인프라 생성 권한은 따라가지 않는다. |
| 민감값 노출 최소화 | state에는 자원 ID·IP·설정값이 평문으로 남을 수 있다. 보기 전용(Audit) 역할은 인벤토리 조회만 하고 state 내용은 읽지 않는다. |
| 추적성 | state 변경이 항상 `FDS-IaC-Operator/<본인>` 세션으로만 남아 CloudTrail에서 누가 Terraform을 돌렸는지 바로 구분된다. |
| 기존 결정·Gate 정합 | #35 결정에 "Network 역할 state 접근 금지", #9 완료 조건에 "Work Role 최소권한 리뷰"가 있다. 역할 권한을 넓히면 이 두 기준과 충돌한다. |

역할별 state 접근:

| 역할 | state | 이유 |
|---|---|---|
| FDS-IaC-Operator | 읽기·쓰기, `.tflock` 정리 허용, **state 삭제 거부** | Terraform 실행에 필수 |
| FDS-Network-Operator | **전체 거부** | Relay 접속·재시작 업무에 불필요 |
| FDS-ReadOnly-Audit | **내용 읽기 거부** | 조회·감사에 state 원문 불필요 |

사람 기준으로는 권욱(IaC·Network·Audit), 하영(IaC·Audit)은 이미 IaC 역할로 state에 접근할 수 있고, 재환(Network·Audit)만 접근하지 못한다.

**선택안 (Lead 결정 필요):** 재환도 state 접근이 필요하면 Network 역할을 넓히지 않고, `trust-FDS-IaC-Operator`와 `assume-321team-jaehwan`에 IaC 역할을 추가한다. "VPN 작업 세션은 state 불가, Terraform 실행 세션만 state 가능"이라는 원칙을 유지한 채 3명 모두 접근할 수 있다. IaC trust 대상(현재 권욱·하영)은 #35 결정 사항이라 이 초안에는 반영하지 않았다.

## 파일별 statement 표

### FDS-IaC-Network.json (신규)
| Sid | 하는 일 | 범위 |
|---|---|---|
| ReadSeoulNetworkMetadata | VPC/subnet/IGW/RT/NACL/SG/ENI/AZ/Tag 조회 | `*` + 서울 (Describe는 자원 단위 제한 미지원) |
| CreateTaggedVpcIgwRouteTableSubnet | VPC·IGW·RT·Subnet 생성 | 새 자원에 소유 태그 필수 |
| UseOwnedVpcAsParent | Subnet·RT를 만들 부모 VPC | 소유 태그 VPC만 |
| TagOnlyAtCreate | 생성 순간 태그 달기 | `ec2:CreateAction` 4종만 |
| MutateOwnedNetworkResources | 속성 변경·IGW attach/detach·RT 연결·route·삭제·태그 | 소유 태그 자원만 |

### FDS-IaC-Vpn.json (신규)
| Sid | 하는 일 | 범위 |
|---|---|---|
| ReadSeoulRelayMetadata | AMI/인스턴스/볼륨/EIP/SG rule 조회 | `*` + 서울 |
| CreateTaggedSgInstanceEip | SG·인스턴스·EIP 생성 | 소유 태그 필수 |
| DenyRunOtherThanT3Medium / DenyRunWithoutImdsv2 | 다른 타입·IMDSv1 거부 | 명시 Deny 2개(조건 AND 함정 피하려고 분리) |
| RunWithEncryptedGp3UpTo40GiB | 루트 볼륨 | 암호화·gp3·≤40 |
| RunWithExactAdoptedAmi | AMI | 정확히 1개 |
| RunCreatesPrimaryEni | 기본 ENI 생성·EIP 연결 | 서울 (아래 한계 1) |
| UseOwnedVpcSubnetSgAsParent | 부모 VPC/subnet/SG | 소유 태그만 |
| TagOnlyAtCreate | 생성 순간 태그 | `CreateAction` 5종 |
| MutateOwnedRelayResources | SG rule·인스턴스 수정/시작/중지/종료·EIP·On-Prem route·태그 | 소유 태그만 |
| SgRulesUnderOwnedSg | SG rule 자원 자체 | 서울 (부모 SG가 소유 태그여야 함) |
| ResolveAwsManagedEbsKey | `alias/aws/ebs` 조회 | `kms:RequestAlias` 고정. 암호화 사용은 AWS 관리형 키 정책(EC2 경유)이 허용 |
| SessionDocumentCreateAndReadOnly | `SSM-SessionManagerRunShell` 생성·조회 | 문서 1개. `create_session_document=false` 기본값 유지 |

### FDS-IaC-Guardrails.json (신규, 전부 Deny)
서울 밖 거부(IAM 조회·PassRole·GetCallerIdentity 예외), `Project`/`ManagedBy` 태그 삭제 거부, 두 태그를 다른 값으로 바꾸기 거부, 세션 문서 수정·삭제·권한변경·SendCommand 거부, CloudFormation 스택 변경 거부.

### FDS-IaC-State-PassRole.json (기존 후보 그대로)
4개 state key 읽기/쓰기, `.tflock` 읽기/쓰기/삭제, state 삭제·버전 삭제 거부, `FDS-Relay-SSM` 조회 + EC2에만 PassRole, 보호 버킷/Relay identity 변경 거부. **이미 중앙 시험(46+9건)을 받은 내용이라 한 글자도 바꾸지 않음.**

## 일부러 안 넣은 것 (제외 사유)

| API | 이유 |
|---|---|
| `ec2:DetachNetworkInterface`, `DeleteNetworkInterface` | subnet 삭제 시 남은 서비스 ENI 정리용. 소유자 확인 후 별도 예외로만 |
| `ec2:DescribeVpcEndpoints`, `ModifyVpcEndpoint`, `DeleteVpcEndpoints` | GuardDuty endpoint 정리 예외 경로. 모니터링 해제로 우회 금지 |
| `ssm:RemoveTagsFromResource` | 세션 문서는 `prevent_destroy`, 태그 제거 불필요 |
| IPv6/IPAM/tenancy/VGW propagation | 현재 소스에 없음 |

inventory 밖에 추가한 것: `ec2:DescribeInstanceCreditSpecifications` (t3 `credit_specification` 읽기 — provider 원본 대조 필요). s3/iam:GetRole은 기존 State-PassRole 후보분.

## 아직 남은 한계 (리뷰어가 꼭 볼 것)

1. **ENI는 태그로 못 묶음.** 생성 시점 ENI에 태그가 없어 `RunCreatesPrimaryEni`가 서울 전체 ENI 대상. 인스턴스·subnet·SG·EIP가 소유 태그로 묶여 있어 실제 영향은 "우리 EIP를 다른 ENI에 연결" 정도. 음성시험 N7로 확인.
2. **route 목적지 CIDR·target은 IAM으로 제한 불가.** `0.0.0.0/0`, `10.1.93.0/24`는 소스·plan 리뷰로 통제.
3. **소유 태그 VPC를 하나 더 만드는 것은 막지 못함.** 비용·plan 리뷰로 통제.
4. `ec2:MetadataHttpTokens`, `ec2:VolumeSize/VolumeType` 조건키가 RunInstances 해당 자원에서 평가되는지 **simulation으로 확인 필요**.
5. `FDS-ReadOnly-Audit`은 기존 #35 결정에 "최소 후보 역할"로만 있었고 trust 후보가 없었음 → **Lead 확인 후** 채택.
6. Network-Operator template의 `__RELAY_INSTANCE_ID__`는 Relay 생성 후 채움(기존 결정 유지). 그 전에는 부여 안 함.

## 시뮬레이션 기대표 (권욱 중앙 검증용)

`iam simulate-custom-policy`에 IaC 정책 4개를 함께 넣는다. context(태그·리전·CreateAction 등)를 비워서 나온 implicitDeny는 음성 PASS로 쓰지 않는다.

| ID | Action | Resource / context | 기대 |
|---|---|---|---|
| P1 | ec2:CreateVpc | vpc/* , RequestTag Project=fds-hybrid, ManagedBy=terraform, 서울 | allowed |
| P2 | ec2:CreateSubnet | subnet/* RequestTag + vpc/* ResourceTag 소유 | allowed |
| P3 | ec2:CreateTags | vpc/*, CreateAction=CreateVpc, RequestTag 소유 | allowed |
| P4 | ec2:CreateRoute | route-table/* ResourceTag 소유 | allowed |
| P5 | ec2:RunInstances | instance(t3.medium, IMDS required, RequestTag)·volume(gp3, enc, 40)·image(exact)·subnet/SG(소유)·ENI | 자원별 모두 allowed |
| P6 | iam:PassRole | role/FDS-Relay-SSM, PassedToService=ec2 | allowed |
| P7 | s3:PutObject | phase2/network/terraform.tfstate | allowed |
| P8 | s3:DeleteObject | phase2/network/terraform.tfstate.tflock | allowed |
| P9 | kms:DescribeKey | key/*, RequestAlias=alias/aws/ebs | allowed |
| N1 | ec2:CreateVpc | RequestTag Project 없음 | implicitDeny |
| N2 | ec2:CreateVpc | RequestedRegion=us-east-1 | explicitDeny |
| N3 | ec2:DeleteVpc | ResourceTag Project 없음(default VPC) | implicitDeny |
| N4 | ec2:DeleteTags | 소유 VPC, TagKeys=[Project] | explicitDeny |
| N5 | ec2:CreateTags | 외부 자원(ResourceTag 없음), CreateAction 없음 | implicitDeny |
| N6 | ec2:CreateTags | 소유 자원, RequestTag Project=other | explicitDeny |
| N7 | ec2:AssociateAddress | 외부 EIP(ResourceTag 없음) | implicitDeny |
| N8 | ec2:RunInstances | instance, InstanceType=t3.large | explicitDeny |
| N9 | ec2:RunInstances | instance, MetadataHttpTokens=optional | explicitDeny |
| N10 | ec2:RunInstances | image/다른 AMI | implicitDeny |
| N11 | ec2:RunInstances | volume, Encrypted=false 또는 VolumeSize=100 | implicitDeny |
| N12 | iam:PassRole | role/다른 role 또는 PassedToService=lambda | implicitDeny |
| N13 | s3:DeleteObject | phase2/network/terraform.tfstate | explicitDeny |
| N14 | s3:PutObject | phase2/other/terraform.tfstate | implicitDeny |
| N15 | ssm:UpdateDocument / ssm:SendCommand | document/SSM-SessionManagerRunShell | explicitDeny |
| N16 | cloudformation:UpdateStack | 중앙 bootstrap stack | explicitDeny |
| N17 | ec2:DeleteNetworkInterface | 임의 ENI | implicitDeny |
| N18 | (Network 정책) s3:GetObject | state 버킷 | explicitDeny |
| N19 | (Audit 정책) s3:GetObject | state 버킷 | explicitDeny |

## 실제 본인 시험 (#9 완료 조건, 부여 후)

각자 본인 MFA로 `aws sts assume-role --role-session-name 321team-<본인>` →
- 성공: `sts get-caller-identity`가 `assumed-role/FDS-IaC-Operator/321team-<본인>`, `ec2 describe-vpcs`(서울) RC0, state 정상 init/lock
- 거부: 다른 RoleSessionName으로 assume → AccessDenied, MFA 없이 assume → AccessDenied, `ec2 describe-vpcs --region us-east-1` → AccessDenied, state 삭제 → AccessDenied
- 다른 사람 결과로 본인 시험을 대신하지 않음

## 로컬 검사

```bash
py -3 -I iam/full-policy-draft-20261009/check_draft.py   # 저장소 루트에서 실행
```
JSON 유효성, 정책 크기(6,144자 이하), Sid 중복, inventory 대비 누락/제외/추가, 와일드카드 Action 여부를 확인한다. 2026-10-09 결과: **PASS** (누락 0, 제외 6, 추가 7).

## 다음 순서

1. 하영: 이 PR로 #9에 제출 (이권욱 Lead 리뷰·병합 판단)
2. 권욱: fresh before → `accessanalyzer validate-policy` → 위 기대표 simulation → 부여·readback (central-validation-handoff.md 절차)
3. 권욱·하영(IaC), 권욱·재환(Network), 3명(Audit): 본인 AssumeRole 성공·거부 시험 → 증적 `fds-project-evidence/evidence/P2-IAC-01/`
