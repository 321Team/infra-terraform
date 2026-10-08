# Relay Stream9·SG 변경 검토 및 구현 후보

현재 Agent 설치 경로의 후속 수정·검증 범위·남은 Stream9 userland 확인은 [RPM 리뷰 후속](relay-agent-rpm-review-20261008.md)을 따른다. 현재 source manifest는 `validation/relay-agent-rpm-20261008/source.json`이며 아래 기존 검증 기록은 변경 전 소스에 대한 이력이다.

CODEX_ASSISTED. 2026-10-08. 기반 main `0eabe8daa75a6b9bf960fe1ea5eeaf6a8818f216`. #35 Lead 이하영 / #37 Lead 이재환 / PMO·QA 검토 이권욱. 이 변경은 **실행 코드 혼합 PR**으로 작성자 자체 점검과 독립 리뷰를 구분한다. 생성·부여·Apply·운영 승인은 아니다.

## 입력과 기술 판단

- [#37 tuple 확정6041369929](https://github.com/321Team/fds-project-baseline/issues/37#issuecomment-6041369929): UDP500/4500 ingress, TCP443 egress, TCP80은 repo 확인 후 조건부, TCP5432 ingress는 실제 worker 서브넷 CIDR1개. UDP egress·SSH·ESP·Harbor·관리용 DNS/API를 추가하지 않는다.
- [#37 Stream9 후보 수용6041388694](https://github.com/321Team/fds-project-baseline/issues/37#issuecomment-6041388694): exact AMI 변경과 Agent 설치·firewalld 활성·Enforcing·Libreswan 버전·first boot readback 요구.
- [AMI 실조회6041330684](https://github.com/321Team/fds-project-baseline/issues/37#issuecomment-6041330684): 서울 `ami-08d855918a18d0cf9`, owner125523088429, CentOS Stream9 x86_64 20260316, available/ebs. 이 원본을 재사용하며 새 인스턴스를 만들지 않았다.

**기술 검토: Stream9 후보와 확정 tuple을 source 변경안으로 수용 가능.** 기존 CentOS 계열/dnf/SELinux 경계와 공식 지원 OS를 만족시키는 방향이다. D21의 AMI 고정값 변경을 이 PR에 명시하고 IAM의 old AMI resource·simulation 입력도 새 ID로 함께 검토해야 한다. 코드 독립 APPROVED나 D21 정본 발행으로 표시하지 않는다. IKEv2/NAT-T 표준이 같다는 사실만으로 서로 다른 Libreswan의 실제 연결·재협상·복구 PASS를 선언하지 않는다.

## 실제 구현

1. `main.tf`의 AMI filter를 Stream9 exact ID로 변경했다. profile·계정·t3.medium·IMDSv2·gp3 40GiB·암호화/aws-ebs·EIP 소유는 유지한다.
2. bootstrap은 Stream9/x86_64/Enforcing 확인 → forwarding0 → 서명/TLS 검증을 유지한 DNF prerequisite 설치 → firewalld enabled/active → 고정 Agent payload/서명 검증 → 설치/서비스 확인 순서다. Libreswan exact version-release 입력은 계속 필수이며 설치 후 일치 여부도 확인한다. Agent가 없어서 무조건 멈추던 이전 경로를 해결한다.
3. Agent `3.3.5390.0`을 서울 공식 version URL에서 수집했다. payload SHA256 `85369679511b67f8f01824043ae17a679b6f21edd78229ccd1d5acd6c347f82f`, key fingerprint `1C5B395CBE5E74E2F1CA21592784DBF388D19D46` 고정. key는 [AWS 서명 문서](https://docs.aws.amazon.com/systems-manager/latest/userguide/verify-agent-signature.html)에서 가져와 source에 보존했다. key 유효기간은 문서상2027-11-25이며 GPG 검증 실패/만료는 STOP한다. HTTPS redirect만 허용하고 `latest`, 임의 URL/key, `--nogpgcheck`, TLS 비검증 우회를 쓰지 않는다. SHA 일치만으로 서명을 대신하지 않는다.
4. egress map은 TCP443 world1개 + 근거가 있는 TCP80 world1개만 허용한다. 기존 빈 기본값은 유지한다. 실제 repo/mirror 경로 확인 전 TCP80을 넣지 않으며, 전송 실패만으로 추가하지 않는다.
5. `worker_subnet_key`는 기본 빈값이다. 실제 private key1개와 `worker_source_reference` 수신 후 live subnet VPC/CIDR/AZ-ID/public-IP 설정을 대조해 TCP5432 규칙1개를 만든다. 직접 CIDR/전체VPC/노드32/worker SG를 입력받지 않는다. route는 별도 readiness 및 동일 worker key1개일 때만 활성화한다. 목적지 `.55`/engine 거부는 host FORWARD·DB/NetworkPolicy의 책임이다.

## 실행 전 남은 입력과 실행 순서

대상은 서울 중앙 계정의 새 Relay이며, 실행자는 검토·부여된 본인 MFA IaC 역할이다. 기존 [PR6 준비 절차](https://github.com/321Team/infra-terraform/pull/6)의 개인 작업 경로·backend·증적 경계를 따른다.

- #35 full permissions/API 목록에 새 AMI ARN, worker subnet read, 선택적 ingress create/read/delete를 연결한다. 이미 존재하는 action 이름과 실제 resource/조건 delta를 구분하며 grant는 여기서 수행하지 않는다.
- exact Libreswan package, root volume 삭제/보존, CPU credit mode, 실제 network handoff, worker key(필요 단계), repo 경로 및 egress 수용 입력 필요. 예제·MOCK 값을 live tfvars로 쓰지 않는다.
- 코드 독립 리뷰→Lead 병합 판단→기존 IAM/Freeze/실행 조건→본인 검증 및 saved plan 검토→범위별 실행 순서다. 비용은 교육장 리포트의 사용액·예상 총비용으로 추적한다. 자체 견적/조회 조건을 새로 만들지 않는다.
- 초기 worker/문서/route OFF + TCP4431개이면7create 예상. 문서 opt-in이면+1, worker 선택이면+1. plan의 실제 전체 diff가 판단 기준이다. worker 선택은 ROSA actual ID 생성을 Freeze 전에 요구하는 뜻이 아니며 생성 전 배치/source 계약으로 먼저 고정할 수 있다.

## 검증과 한계

### #35 IAM 검토에 넘길 차이

| 코드 소비 | 전체 정책에서 확인할 사항 |
|---|---|
| 새 AMI / RunInstances | 기존 Stream10 image resource를 `arn:aws:ec2:ap-northeast-2::image/ami-08d855918a18d0cf9`로 대조한다. instance/volume/subnet/SG/ENI 등 RunInstances의 다른 resource와 조건은 기존 전체 정책 검토를 유지한다. AMI에는 계정 필드를 넣지 않는다. |
| DescribeImages / DescribeSubnets | 기존 AMI·transport subnet 조회에 이미 필요한 action이다. worker 조회가 생긴다고 새 광범위 EC2 권한을 부여하지 않는다. 조회는 IAM Resource 지원 범위와 region 조건, 코드의 owner/ID 및 subnet postcondition을 함께 검토한다. |
| worker ingress | `ec2:AuthorizeSecurityGroupIngress`, readback의 `DescribeSecurityGroupRules`/`DescribeSecurityGroups`, 정리의 `RevokeSecurityGroupIngress` 등은 기존 IKE 규칙과 공통이다. 새 worker 규칙의 실제 SG/규칙 resource·tag 조건이 허용 범위에 드는지 검토한다. 전체 action 목록을 대신하는 표는 아니다. |
| Agent 공급 | EC2 내부에서 공개 HTTPS RPM을 수집한다. IAM instance profile에 S3 전체 권한을 추가하지 않는다. Agent 통신 권한은 기존 Relay profile 검토 범위다. |

권한 simulation은 **최종 전체 정책과 exact source**를 대상으로 해야 한다. 이 delta 표만으로 grant/Plan 권한이 충분하다고 판정하지 않는다. 기존 PR6의 old AMI·source manifest를 실제 실행 입력으로 그대로 소비하지 말고, 최종 병합 SHA/manifest 및 AMI에 맞춘 사전조회·Plan 입력을 실행 직전에 고정한다.

`validation/relay-stream9-20261008/`에 해당 source manifest와 명령별 원본을 보존한다. `scripts/validate-components.py --manifest validation/relay-stream9-20261008/source.json --component vpn --terraform <고정1.16.4 실행파일>`은 새 개인 복사본·격리된 자격증명/설정·backend=false·lockfile readonly로 validate/MOCK만 수행한다. 이전 validation manifest와 증적을 새 PASS로 덮어쓰지 않는다.

실제 Agent RPM/서명에 대한 로컬 GPG 검증과 RPM header metadata 확인을 수행한다. 이는 Linux 설치/AMI Runtime이 아니다. bootstrap shell은 명령 대역·임시 경로로 성공 및 실패 시 설치/성공선언 차단을 시험한다. provider MOCK도 AWS API를 호출하지 않는다. 전체 시험 결과/플랫폼 제한은 `summary.json`을 따른다.

실제 first boot에서 확인할 것: Fleet Manager/SSM `PingStatus=Online`·Agent version/platform, firewalld enabled/active·Enforcing·forwarding0, Libreswan version, root volume gp3/40/encrypted/KMS readback, 본인 세션. package repository의 실제 HTTPS/HTTP mirror 동작, Agent RPM 설치 의존성, 재부팅·터널 Runtime은 미검증이다.

실패/복구: cloud-init/로컬 임시 evidence와 실제 자원 상태를 보존하고 route OFF·추가 생성 중단. SSH/UDP egress/SELinux 해제로 우회하지 않는다. source 또는 user_data 변경은 `user_data_replace_on_change=true` 때문에 이미 존재하는 Relay를 교체할 수 있어 EIP·Network exact bind·세션·터널 재설정 영향이 있다. 자동 replacement/destroy를 실행하지 않으며 reviewed plan과 #35/#37 복구 범위로 처리한다. PSK/conn/비밀은 user_data/state에 넣지 않는다.

## 공급자 원본

- [AWS CentOS Agent 설치](https://docs.aws.amazon.com/systems-manager/latest/userguide/agent-install-centos-stream.html)
- [AWS 서명·fingerprint](https://docs.aws.amazon.com/systems-manager/latest/userguide/verify-agent-signature.html)
- [서울 고정 RPM](https://s3.ap-northeast-2.amazonaws.com/amazon-ssm-ap-northeast-2/3.3.5390.0/linux_amd64/amazon-ssm-agent.rpm), [detached signature](https://s3.ap-northeast-2.amazonaws.com/amazon-ssm-ap-northeast-2/3.3.5390.0/linux_amd64/amazon-ssm-agent.rpm.sig)

원본 다운로드 URL/hash/size는 `agent-download.json`, 서명 원본은 `signature.stdout`/`signature.stderr`에 있다. 실제 RPM 바이너리는 이 저장소에 커밋하지 않는다.
