# Phase 2 network/VPN 검토 후보 — 2026-10-07

PR #4의 Stage-A 정적 검증 기반이 main에 병합된 뒤, 별도 `terraform/network`와 `terraform/vpn` root를 추가한다. 기존 Stage-A 불변 증적은 당시 기록으로 보존한다. 이번 후보는 정적·모의 검토용이며 실제 plan/apply, AWS 생성, 정책 부여, Runtime 인수는 미실행이다.

## 기준·추적

- 선행 [PR #4](https://github.com/321Team/infra-terraform/pull/4): 2026-10-07 19:49:15 KST 병합, `da452938714a770b43ad44641be0b80123c73f8d`. 병합 직전 HEAD `0168220efa6bd141efaa8e52f6104a7cf77e0858`의 독립 APPROVED와 사용자 조건부 병합 요청을 확인했다. CI 검사 0건은 NOT_RUN이다. 사용자 제출 Linux Stage-A 수신 결과와 로컬 무결성 검토를 구분하며, 제출한 원본 capture 전체를 독립 재해시했다고 주장하지 않는다.
- 중앙 기준 조회 SHA: `bbae7d7b52d3084187b328b97a70b59e5980ffe4`, [PR #137](https://github.com/321Team/fds-project-baseline/pull/137) 병합 반영. 이 중앙 문서의 제안 항목을 승인된 실행값으로 승격하지 않는다.
- 책임: [#35 AWS/ROSA IaC](https://github.com/321Team/fds-project-baseline/issues/35) 이하영, 지원 이권욱; [#37 Hybrid VPN](https://github.com/321Team/fds-project-baseline/issues/37) 이재환. 담당·일정·AC는 변경하지 않는다.
- [source.json](../validation/components-20261007/source.json)은 로컬 v1.2 후보와 동일한 15개 파일의 SHA256, 원본 ZIP hash, 버전과 테스트 수를 고정한다. SHA 일치는 무결성이며 승인이나 Runtime 성공이 아니다.

## 범위와 구현 선택

| 대상 | 이번 소스 | 남은 판단 |
|---|---|---|
| network | VPC `10.20.0.0/16`, 채택된 4개 subnet/CIDR·AZ ID, 명시적 route table/association, transport IGW 경로, 비밀 없는 handoff | DNS flags·태그·route 소유 방식 등 새 구현 선택의 리뷰, 실제 AZ 매핑·권한·비용 확인 |
| vpn | 기존 profile 참조, Relay EC2/SG/EIP, IMDSv2, 암호화 gp3, 별도 On-Prem route 활성화 | egress, AMI/Agent/패키지, EBS 삭제/보존, CPU credit mode, 유료 생성 GO |
| backend | `phase2/network/terraform.tfstate`, `phase2/vpn/terraform.tfstate`, S3 native `.tflock`, default workspace | 실제 backend 접근·locking·복구는 미검증. 기존 CFn 중앙 bucket/role/profile 소유권 유지 |
| 세션 문서 | 기존 결정의 내용만 소스화, 생성 기본 OFF, 부재 증적과 소유 수용 후 opt-in | account/regional 기본 문서의 실제 owner/default version/content 확인. `vpn` state 소유는 새 제안 |

`execution_enabled=false`는 실수 방지 장치다. 승인·최소권한·sandbox를 대신하지 않으며 직접 실행하면 provider/data 조회가 가능하다. 로컬 검증은 아래 격리 helper만 사용한다. Terraform test의 `command=plan`은 mock provider 계획이다. 합성 ID·TEST-NET egress·패키지·근거 문자열을 실제 입력으로 복사하지 않는다.

network 6개 resource block은 계획상 15개 instance다. vpn은 SG ingress를 채택된 UDP 500/4500으로 제한하고 egress를 임의 확정하지 않는다. outer SG 설정만으로 inner 경로 동작을 보장하지 않는다. 이 후보는 ROSA 전체 모듈·Runner selector 확장·Phase 1 DNS Runtime 변경을 포함하지 않는다.

## 로컬 재현

일반 작성 PC, Python 3.10 이상, 공식 Terraform **1.16.4**, registry의 AWS Provider **6.66.0** 다운로드 연결이 필요하다. 관리자/AWS 권한은 필요하지 않다. 정확한 PR commit을 checkout한 깨끗한 저장소 루트에서 실행한다. CLI를 공식 checksum과 대조한 뒤 해당 환경의 절대경로를 지정한다.

```text
python -m unittest discover -s tests -p test_validate_components.py -v
python scripts/validate-components.py --component network --terraform /absolute/path/to/terraform
python scripts/validate-components.py --component vpn --terraform /absolute/path/to/terraform
```

Windows도 같은 인자를 쓰되 Python/terraform.exe의 실제 경로를 사용한다. helper는 source.json의 파일 집합·해시와 일치해야 시작하며, 새 임시 디렉터리로 복사한다. 상속 AWS/TF 설정·자격증명·proxy를 제거하고 빈 HOME/config와 독립 TF_DATA_DIR를 쓴다. 버전 → 본문 fmt → backend 예제 fmt → init(`-backend=false -lockfile=readonly`) → validate → mock test 순서다. registry 다운로드는 발생하지만 실제 AWS provider 구성·cloud backend·AWS CLI는 실행하지 않는다. 이는 현재 hash로 검토된 코드의 절차이며 임의 코드의 보안 sandbox가 아니다.

성공 기준은 6단계 RC0, 정확 버전, validate error/warning 0, network **3건**, vpn **13건** 모의 시험 성공, 소스/lock 전후 불변이다. 시작 시 표시되는 evidence 디렉터리에 호스트·UTC·명령·RC·timeout·stdout/stderr·source hash와 capture-manifest가 남는다. 저장소 [검증 증적](../validation/components-20261007/)의 실제 결과와 구분한다.

실패/timeout/hash 차이 시 즉시 중단하고 원본을 보존한다. lock을 자동 갱신하거나 AWS credential/backend로 우회하지 않는다. 복구는 원인을 수정한 별도 SHA와 검토 후 새 임시 디렉터리에서 재실행한다. 임시 source/home/provider cache는 로컬 산출물로 남으며 별도 확인 후 정리한다. 저장소 원본은 변경하지 않는다.

## 실제 실행 전 차단·확인

| 항목 | 근거·영향 | 해결 및 재검증 |
|---|---|---|
| 권한 | [14행 API inventory](../validation/components-20261007/resource-api-inventory.json)는 **전체 IAM 정책이 아니다** | #35가 dependent action·ARN·tag·조건부 update/cleanup·EBS key 경로를 완결하고 정책 검증/음성·양성 시험 및 실제 role readback 수행. PassRole fragment만 부여하지 않음 |
| egress/패키지 | 빈 egress와 근거로 SG 생성 차단, 정확 Libreswan version-release 필수 | #35/#37이 Agent/repository/NAT-T 목적지·port·DNS 경로 수용. 실제 AMI의 RHEL/SELinux Enforcing/firewalld active/기존 Agent unit·패키지 metadata와 설치 NEVRA 확인 |
| EBS/T3 | 삭제/보존과 standard/unlimited 기본값 미지정 | #35가 복구·잔존 비용·성능 판단 후 입력. mock의 false/standard는 결정 아님 |
| 세션 문서 | opt-in OFF. 과거 `ABSENT_OR_UNAVAILABLE`는 부재 증거 아님 | 실제 이름·owner·default version·content 조회 후 부재/소유 수용 시만 생성. 존재·AccessDenied·불명확이면 STOP. 자동 import/overwrite 금지 |
| 비용/실행창 | 교육장 한도·기간·전체 누적액 미확인; 기존 Relay 생성 창은 10/12~14 직전 GO | 기존 책임자가 실행창/비용 정합화. 제공된 6개 서비스의 USD 0.0을 전체 계정 무료로 해석하지 않음. 추가 Billing/CE/Budget 권한을 요구하지 않음 |
| tunnel/route | route 활성화 기본 OFF, readiness 문자열 자체는 검증 증거 아님 | #37 실제 Agent Online·본인 세션·XFRM/SA·승인/미승인 흐름·반환/source·SA-down plaintext deny 증적 → #35 정확 대상/association 검토 → 별도 route plan |

Root MFA 교육장 소유 미조치 이력은 기존 외부 위험으로 유지하며 새 로컬 검증 차단조건으로 확대하지 않는다. ROSA 방식의 미결을 초기 network/VPN 후보 전체의 신규 선행 AC로 만들지 않는다.

## Runtime 인계·중단·복구

실제 대상은 서울 리전의 채택 계정, #35의 기존 업무 역할이며 root 일상 사용은 없다. 리뷰한 SHA/입력·적용 plan·계정·실행 시각·비용/Freeze·권한·rollback을 고정한 뒤 승인 범위에서만 실행한다. 이 PR에는 live tfvars나 실제 cloud plan이 없다. 기존 중앙 CFn 4자원을 재생성·import하지 않는다.

bootstrap은 root/RHEL/Enforcing/firewalld를 확인하고 정확 Libreswan 패키지를 제한 횟수로 설치한다. EIP 연결 지연으로 실패할 수 있으며 실제 타이밍은 미시험이다. 미설치 Agent의 임의 installer fallback은 없다. 로컬 서비스 active는 Agent Online이 아니다. 실패 시 cloud-init 원본/패키지·서비스 상태를 보존하고 유료 자원 추가와 route 활성화를 중단한다. 통제 해제나 비밀 로그 출력으로 복구하지 않는다.

forwarding=0을 `/etc/sysctl.d/90-fds-relay-bootstrap.conf`에 영구 기록하는 것은 **새 구현 제안**이다. #37의 conn/PSK·XFRM/firewall·SA-down 차단 준비 후 같은 파일을 수용된 최종 forwarding 설정으로 변경하고 재부팅 유지까지 확인해야 한다. 단발성 sysctl 변경만으로 완료 처리하지 않는다. tunnel secret은 세션의 기존 안전 절차로만 입력한다.

user_data 변경은 instance 교체를 유발한다. 고정 IP 때문에 create-before-destroy를 추가하지 않았다. 교체 시 새 instance/profile/Agent readback → exact Network ARN 재결속·구 ARN 거부 → 각 본인 U1 → conn/PSK 재적용이 필요하다. EIP 재연결도 변경/장애창 검토 대상이다. 경로 복구는 승인된 route의 이전 next-hop/부재 상태부터 검토하며 전체 state 일괄 destroy로 처리하지 않는다. 보존 EBS/EIP·중앙 자원과 account/regional 세션 문서는 별도 소유·비용·복구 대상이다. `prevent_destroy`를 지워 문서 삭제를 우회하지 않는다.

공식 근거: [고정 provider 코드](https://github.com/hashicorp/terraform-provider-aws/tree/v6.66.0/internal/service), [EC2 권한·dependent actions](https://docs.aws.amazon.com/service-authorization/latest/reference/list_ec2.html), [기본 세션 문서](https://docs.aws.amazon.com/systems-manager/latest/userguide/getting-started-create-preferences-cli.html), [SG middlebox 경로](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/security-group-rules-reference.html).

이 PR은 IaC 포함 혼합 PR이다. 자체 점검은 독립 승인과 구분한다. 새 정확 HEAD 독립 리뷰와 Lead 판단이 필요하며 PR #4의 승인을 승계하지 않는다. STATIC/MOCK 결과는 CI/RUNTIME/AC 인수 또는 유료 실행 GO가 아니다.
