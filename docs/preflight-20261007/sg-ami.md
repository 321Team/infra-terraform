# #37 SG·AMI 사전검증

CODEX_ASSISTED. Terraform 기준 `0eabe8daa75a6b9bf960fe1ea5eeaf6a8818f216`. STATIC 문서·소스 대조에 더해 2026-10-07 23:56 KST 중앙 DescribeImages를 실제 수행했다. exact AMI/owner와 available/x86_64/ebs, 이름 CentOS Stream 10 x86_64 20260330을 재확인했다. [원본 접수](central-readonly-receipt.md). OS/Agent/터널 Runtime은 미실행이다.

## SG 입력 정리

권위 입력: [#37 Lead6037284573](https://github.com/321Team/fds-project-baseline/issues/37#issuecomment-6037284573). 최종 tuple 확정은 source/AMI 확인 후 #37에서 한다.

| 방향 | 후보/기존 값 | 단계·판정 |
|---|---|---|
| outer ingress | UDP500/4500, 0.0.0.0/0 | D21 기존 채택·코드 구현. 동적 공인 source이므로 임의 /32 축소 안 함 |
| outer egress | TCP443, 0.0.0.0/0 | #37 Agent/repository 입력. SSM과 모든 실제 repo/redirect가 HTTPS로 가능한지 확인 후 소비 |
| outer UDP egress | 초기 미개방 후보 | On-Prem initiator/Relay auto=add, rekey 주체·NAT-T/DPD/conntrack 실측 전 동작 PASS로 표시 안 함. Relay 시작이 필요하면 별도 tuple 리뷰 |
| TCP80 | 초기 미개방 | 실제 repo가 HTTP를 요구할 때만 별도 수용. mirrorlist/metalink/redirect 포함, 단순 문자열 한 줄로 전체 목적지 판단 안 함 |
| inner ingress | worker source + TCP5432 | source 미확정, 코드 미구현, route OFF 유지. 목적지 .55 제한은 host FORWARD·db01 방화벽/pg_hba. engine 거부는 NP/DB 인증·음성시험 |
| Harbor .54:443 | 미개방 | D22가 On-Prem Harbor를 선택하기 전 추론 금지 |
| 관리 DNS/API | 별도 계약 | inner DB 규칙에 섞지 않음 |

PR5 리뷰의 “VPC resolver DNS53 egress 필수” 의견은 **AmazonProvidedDNS에는 적용되지 않는다**. AWS 공식 [SG 규칙](https://docs.aws.amazon.com/vpc/latest/userguide/security-group-rules.html)은 Route53 Resolver/AmazonProvidedDNS를 SG로 차단할 수 없다고 명시한다. custom DNS/Resolver endpoint/On-Prem DNS는 별도 경로 규칙을 검토한다. DNS가 동작했다거나 host firewall도 예외라는 뜻은 아니다.

worker SG reference는 #37의 우선 후보지만 모든 라우팅 경로의 허용을 보장하지 않는다. 같은 AWS 문서는 middlebox를 경유하는 종단 SG에서 peer SG reference만으로 통과하지 않는 제한을 설명한다. **Relay 자체 ingress와 종단 SG, 실제 node SNAT source를 분리해** #38/#37이 확인해야 한다. SG 방식이 해당 경로에 맞지 않으면 Lead가 이미 제시한 실제 worker subnet CIDR 대안을 사용한다. 아직 SG ID·1AZ subnet·규칙을 임의 확정하지 않았다.

이 단계에서 inner 규칙 부재는 **초기 Relay 생성의 새 차단조건이 아니라 route 활성화 전 필수 조건**이다. TCP443 후보만으로 “터널 준비 완료”가 되지 않는다.

## AMI: 생성 전 해소할 두 공백

기존 [#35 AMI metadata readback](https://github.com/321Team/fds-project-baseline/issues/35#issuecomment-5967245694), [이름 기록](https://github.com/321Team/fds-project-baseline/issues/35#issuecomment-5964612301): `ami-079a2667364cee804`, owner `125523088429`, CentOS Stream 10 x86_64 20260330, available/ebs. 과거 metadata가 실제 패키지·서비스의 증거는 아니다.

1. **지원성 확인 필요 / Relay 생성 Gate 미충족.** 2026-10-07 조회 [AWS Systems Manager 지원표](https://docs.aws.amazon.com/systems-manager/latest/userguide/operating-systems-and-machine-types.html)는 CentOS Stream 9를 열거하고 10은 열거하지 않는다. 해당 AMI가 반드시 실패한다고 단정하지 않지만, Stream10에서 지원된다고 판정할 근거가 없다. #35/#37이 공식 지원 근거 또는 관련 권위자의 예외 수용을 확인하거나 지원 OS/AMI 대안을 별도 변경검토한다. AMI를 이 작업에서 교체하지 않음.
2. **Agent/firewalld 실제 상태 미확인 / Relay 생성 Gate 미충족.** [AWS CentOS Stream 설치 안내](https://docs.aws.amazon.com/systems-manager/latest/userguide/agent-install-centos-stream.html)는 SSM Agent 기본 미포함을 설명한다. exact AMI의 패키지 부재를 직접 확인한 것은 아니다. 현 [bootstrap](../../terraform/vpn/bootstrap.sh.tftpl)은 `getenforce=Enforcing`, `firewalld active`를 요구하고, Libreswan 설치 뒤 기존 Agent unit을 활성화할 뿐 Agent를 설치하지 않는다. Agent가 없거나 firewalld inactive이면 STOP하며 public SSH/보안통제 해제로 우회하지 않는다.

이번에 확인한 공식 지원표는 새 외부 근거이며 PR5 이후 코드 변경에서 생긴 결함이 아니다. AMI 내부 상태와 Agent 미포함 위험은 기존 리뷰의 미확인 사항을 유지한다.

## 필요한 원본과 수집 방법

읽기 전용 CloudShell 수집기로 exact AMI ImageId/Owner/Name/State/Architecture/RootDeviceType/CreationDate를 갱신한다. **DescribeImages는 RPM 목록·서비스 활성 상태를 반환하지 않는다.** 기존 동일 AMI에서 생성된 검증 인스턴스나 빌드 manifest가 있으면 AMI→build/instance→원본의 연결을 먼저 확인한다. 없으면 실제 내용 확인은 별도 승인된 격리 인스턴스 시험 또는 공급자 build manifest가 필요하며, 무승인 RunInstances로 빈칸을 채우지 않는다.

이미 승인된 대상 OS 접근에서 수집할 명령(인스턴스 ID/AMI·실행 계정/시각/SHA/RC와 함께 비공개 보관):

```bash
cat /etc/os-release
uname -m
rpm -q amazon-ssm-agent firewalld libreswan
systemctl is-enabled amazon-ssm-agent firewalld
systemctl is-active amazon-ssm-agent firewalld
getenforce
sysctl net.ipv4.ip_forward
```

이는 설치/enable/restart를 수행하지 않는다. 미설치 패키지/비활성 서비스의 RC도 그대로 남긴다. repo 파일은 승인 대상에서 검토하되 URL 내 credential을 출력/게시하지 않고 enabled repo의 baseurl/metalink/mirrorlist scheme·GPG/TLS 설정을 정리한다. exact Libreswan NEVRA 및 서명된 Agent RPM version/hash/signature 근거가 필요하다. 공식 문서의 `latest` 설치 명령을 그대로 user_data로 복사하지 않는다.

Agent 공급/서비스 준비를 구현하면 bootstrap 소스 변경으로 분류해 exact HEAD 리뷰·STATIC/MOCK 후 승인된 격리 Runtime을 거친다. user_data 변경은 Relay 교체·EIP 재연결·Network ARN 재결속·본인 U1·PSK 재입력을 유발할 수 있다. 실패 시 cloud-init 원본을 제한 경로에 보존하고 route OFF, 추가 생성 중단. PSK/credentials는 로그·AMI·tfvars·plan/state에 넣지 않는다.

성공 조건: OS 지원 근거 + exact AMI/패키지·GPG/TLS·Enforcing·firewalld 사전조건 + bootstrap 실행 결과 + SSM Agent Online + 본인 세션. 마지막 두 항목은 실제 생성 후 Runtime이며 생성 전 actual instance ID를 요구하는 순환 Gate를 만들지 않는다.
