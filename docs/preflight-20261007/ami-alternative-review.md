# Relay AMI 대안 사전조사·실조회

CODEX_ASSISTED. 2026-10-08 00:28:59 KST, 서울 중앙 CloudShell에서 `DescribeImages`만 실행. 생성·AMI 교체·패키지 설치는 미실행이다.

| 항목 | 기존 코드 | 변경 검토 후보 |
|---|---|---|
| AMI |ami-079a2667364cee804|ami-08d855918a18d0cf9|
| OS/name |CentOS Stream 10 x86_64 20260330|CentOS Stream 9 x86_64 20260316|
| owner |125523088429|125523088429|
| 최신 실제 metadata |10-07 23:56 조회|10-08 00:28:59 조회 RC0|
| AWS SSM 지원표 |Stream10 열거 없음|Stream9 열거 있음|
| 패키지/서비스 실측 |미확인|미확인|

[CentOS 공식 AMI 표](https://www.centos.org/download/aws-images/)와 서울 실조회 ID를 대조했다. 후보는 available/x86_64/ebs/hvm, 생성2026-03-17T07:01:11Z이다. 원본 root 매핑 gp2 10GiB/Encrypted=false/DeleteOnTermination=true는 이미지 metadata이며 실제 Relay의 암호화/보존 선택이 아니다.

[AWS 지원 OS 표](https://docs.aws.amazon.com/systems-manager/latest/userguide/operating-systems-and-machine-types.html)는 후보 OS 지원 근거다. [CentOS Agent 설치 안내](https://docs.aws.amazon.com/systems-manager/latest/userguide/agent-install-centos-stream.html)는 기본 미포함을 설명하므로 ID 교체만으로 bootstrap 정상 실행을 보장하지 않는다. 기존 bootstrap은 active firewalld/SELinux Enforcing 및 기존 Agent unit을 요구하며 Agent 설치 기능이 없다.

## 원본·무결성

- 명령: `aws ec2 describe-images --image-ids ami-08d855918a18d0cf9 --owners 125523088429 --region ap-northeast-2 --output json --no-cli-pager --cli-connect-timeout 10 --cli-read-timeout 30`
- 시작/종료 UTC:2026-10-07T15:28:59.157605+00:00 /15:28:59.879896+00:00. RC0, stderr empty.
- stdout SHA256:`95609f7e78e720f99e9695af167da2381f9315b0b3752feccf7b62b8d736d6bd`
- 원본 archive:`fds-ami9-preflight-bf2b6nlm.tar.gz`,1135bytes, SHA256:`29c4420486d1d0410715dec84f394a6da386316d800cc27d04ac85b5e73cee7f`.
- CloudShell의 `/home/cloudshell-user/`에 archive 보존, 로컬 비공개 evidence에 다운로드 후 archive 및 stdout/stderr 2개 재해시 일치. receipt에 명령/시각/RC 포함. SHA는 무결성이고 OS Runtime PASS가 아니다. 같은 중앙 콘솔을 사용했으며 이번 단일 조회에서 STS를 다시 수집하지 않았다(직전 identity는 중앙 root).

## 권고와 필요한 변경

권고: #35/#37이 Stream9 후보를 우선 검토하고 **OS 지원·Agent 공급·firewalld 사전조건을 하나의 변경안**으로 확정한다. 현재 선택된 AMI를 임의 교체하지 않았다. Stream10 유지 시 공식 지원 근거 또는 해당 권위자의 예외 수용이 필요하다.

지원 OS 전환 수용 후 최소 변경 위치는 `terraform/vpn/main.tf`의 exact image-id filter와 `terraform/vpn/tests/vpn.tftest.hcl`의 mock ID, 연관 IAM RunInstances AMI resource/검증 case다. 이 두 ID만 바꾸는 수정은 Agent 문제를 해결하지 않으므로 완성된 수정안으로 제출하지 않는다.

구현 패킷의 입력: exact Agent version/공식 URL/서명 key fingerprint·RPM 서명 검증/sha256, exact Libreswan NEVRA, enabled repo의 HTTPS·redirect·GPG/TLS, firewalld 설치·활성 사전조건, Enforcing, bounded 실패 처리. 공식 `latest` 설치 예제를 그대로 고정된 공급망으로 표시하지 않는다. 실제값이 없으므로 임의 RPM 버전/해시를 만들지 않았다.

검증 순서: 기존 동일 AMI 빌드 manifest 또는 승인된 시험 대상에서 [OS 읽기 수집](sg-ami.md#필요한-원본과-수집-방법) → 공급/소스 변경 STATIC/MOCK 리뷰 → 승인된 격리 bootstrap Runtime → 실제 Relay Agent Online/본인 SSM 접속. HTTPS443만으로 실제 repo 경로가 충족되는지 확인하고 TCP80/SSH/광범위 egress를 자동 개방하지 않는다. AMI 내부 실측은 아직 없으며 실제 테스트 인스턴스 생성도 하지 않았다.

변경 영향/복구: 생성 전이면 source/정책 검토의 갱신, 생성 후면 replacement·EIP/Network exact bind 재결속·본인 U1·터널 재구성 범위를 수용해야 한다. 실패 시 route OFF와 원본 보존, 자동 재생성/보안통제 해제 금지. PSK는 이미지/user_data/state/로그에 넣지 않는다.
