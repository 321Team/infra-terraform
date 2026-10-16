# #37 vpn-probe 보충 IAM — 초안 (2026-10-09)

[#37 T3·T6 출발지 계획 6076566043](https://github.com/321Team/fds-project-baseline/issues/37#issuecomment-6076566043)과 [#35 수용·조건 6077187634](https://github.com/321Team/fds-project-baseline/issues/37#issuecomment-6077187634)에 따른 **probe 전용 보충** 입력입니다.
- 이미 승인·부여된 `iam/full-policy-draft-20261009/`의 정책 4개, trust, `SHA256SUMS`는 **바꾸지 않습니다.**
- 이 폴더는 IAM 부여·생성 GO가 아닙니다. 부여·중앙 생성과 회수는 #35 절차를 따릅니다.

## 왜 별도 보충인가 — 승인 정책과 대조

| 항목 | 승인된 정책 | probe 처리 |
|---|---|---|
| 인스턴스 타입 | `FDS-IaC-Vpn` `DenyRunOtherThanT3Medium` **명시적 Deny** | probe도 **`t3.medium`**. Allow를 더해도 Deny는 이길 수 없어 Deny를 고치지 않는 쪽을 택함 |
| AMI | `RunWithExactAdoptedAmi` = Relay AMI만(Deny 없음) | `RunWithExactProbeAmi`: 고정한 AL2023 표준 AMI 1개만 추가 |
| SG 생성·규칙·삭제, 인스턴스 종료, gp3 암호화 ≤40GiB, ENI, 태그 | `FDS-IaC-Vpn`이 `Project=fds-hybrid`·`ManagedBy=terraform` 태그 조건으로 이미 허용 | 추가 없음 |
| 역할 조회·PassRole | `FDS-Relay-SSM`만 | probe 역할·프로파일 조회와 `ec2.amazonaws.com`으로의 PassRole만 |
| state·lock | key 4개만 | `phase2/vpn-probe/terraform.tfstate`와 `.tflock`. state·버전 삭제 Deny는 기존과 같은 형식 |
| 보호 | Relay identity 변경 Deny | probe identity 변경 Deny(조회·PassRole 외) |
| 세션 | Network-Operator Relay 템플릿(Relay instance ID 한정) | `FDS-Network-Operator-Probe.json`: `Purpose=vpn-probe`·`Ticket=P2-VPN-01`·`Project=fds-hybrid`·`ManagedBy=terraform` 태그가 있는 인스턴스만 StartSession, 본인 세션만 Resume·Terminate |

## 파일

| 파일 | 대상 |
|---|---|
| `policies/FDS-IaC-VpnProbe.json` | `FDS-IaC-Operator`에 **probe 시험 기간에만** 붙이는 보충 관리형 정책. 이미지 Allow `RunWithExactProbeAmi`를 **뺀** 모든 Allow는 `aws:PrincipalArn = FDS-IaC-Operator` 조건. 이미지 Allow는 고정 AMI ARN 1개만 자원으로 둔다(시험 `test_every_iac_allow_is_bound_to_operator_except_image`와 같은 기준) |
| `policies/FDS-Network-Operator-Probe.json` | 재환·권욱의 Network-Operator 역할에 붙이는 probe 세션 정책 |
| `trust/trust-FDS-P2-VPN-Probe-SSM.json` | 중앙에서 만드는 probe 역할 trust. Principal `ec2.amazonaws.com`, Action `sts:AssumeRole`만 있고 **Condition 없음** |

## 중앙 생성 (Terraform이 만들지 않음, #35 조건 1)

- 역할 `FDS-P2-VPN-Probe-SSM`: 위 trust를 쓰고, AWS 관리형 `AmazonSSMManagedInstanceCore` 1개만 붙입니다. inline 정책과 boundary는 없습니다.
- trust에 `aws:SourceAccount`·`aws:SourceArn` 조건을 두지 않습니다([PR25 리뷰 B1](https://github.com/321Team/infra-terraform/pull/25#pullrequestreview-5479479869)).
  - EC2가 인스턴스 프로파일 자격증명을 발급하는 AssumeRole 요청에는 이 키가 들어간다는 근거가 없습니다. 키가 없으면 `StringEquals`가 불일치로 평가돼 자격증명 발급·SSM 등록이 막힙니다.
  - 다른 계정 사용은 trust 조건 대신 다음으로 막습니다: 정확한 역할 1개에만 `iam:PassRole`(`iam:PassedToService = ec2.amazonaws.com`, `aws:PrincipalArn = FDS-IaC-Operator`), provider `allowed_account_ids`, probe identity 변경 Deny.
  - 실제 AssumeRole·SSM Online은 생성이 승인된 #35/#37 회차에서 IMDSv2 역할 식별(자격증명 값 출력 금지)과 StartSession으로 확인합니다.
  - 회귀 시험 `test_trust_is_ec2_only_without_source_conditions`가 Principal·Action·조건 부재를 대조합니다.
- 인스턴스 프로파일 `FDS-P2-VPN-Probe-SSM`에 같은 역할 1개를 넣습니다.
- Terraform `terraform/vpn-probe`는 이 둘을 `data` source로 읽습니다. ARN이 다르면 Plan이 실패합니다.
- probe에는 PSK·DB 자격증명을 두지 않습니다. `AmazonSSMManagedInstanceCore`의 Parameter Store 읽기 범위는 #37 6014247521 §2에서 이미 다룬 것과 같고, Parameter Store에는 이 시험용 비밀이 없습니다.

## 수명과 회수 (#35 조건 4)

1. 부여: 승인된 준비 단계부터 보충 정책을 `FDS-IaC-Operator`·`FDS-Network-Operator`에 연결하고 readback합니다(probe 역할과 프로파일은 중앙에서 미리 생성). 준비→시험→결함 재시험→증적 반출·검토 완료까지 유지하며 파일 전송이나 작업창 종료마다 회수하지 않습니다.
2. probe Apply → #37 T3·T6 → probe Destroy → 인스턴스·ENI·SG 부재 readback
3. 검증·증적 검토 완료 후 회수(작업창 종료만으로 자동 회수하지 않음):
   - 보충 정책을 분리하고, 역할의 정책 목록을 readback합니다.
   - probe 역할·프로파일은 삭제하거나, 다음 시험 계획이 확정된 경우에만 남깁니다(#35 판단).
   - state 객체 `phase2/vpn-probe/terraform.tfstate`는 Destroy 뒤 빈 state로 남습니다. 삭제 Deny가 있으므로 지우지 않습니다.

## 남은 확인
- AMI 고정값 `ami-0870825cefcaafcc8`:
  - 2026-10-09 CloudShell(ap-northeast-2)에서 SSM 공개 파라미터 `/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64`를 조회한 값입니다(재환 실행).
  - `describe-images` 결과: 소유자 `137112412989`, 이름 `al2023-ami-2023.12.20260930.0-kernel-6.18-x86_64`, `x86_64`, `ebs`, 생성 `2026-09-29T19:49:01Z`.
  - 정책·Terraform·시험의 세 곳이 같은 ID인지는 `tests/test_vpn_probe_policy.py`가 대조합니다.
  - 생성 직전에는 같은 ID가 `available`인지만 확인합니다(Terraform `data.aws_ami` postcondition). 파라미터가 새 ID로 바뀌었다는 이유만으로 고정값을 바꾸지 않습니다. 바꿀 때는 새 PR로 합니다.
- 중앙 검증·실제 IAM 반영은 [2026-10-16 기록](./VALIDATION-20261016.md)으로 연결합니다. IAM 설정과 실제 probe 생성·SSM 접속 성공은 별개입니다.
- 태그 기반 StartSession: `FDS-IaC-Vpn`의 `MutateOwnedRelayResources`가 소유 인스턴스의 `CreateTags`를 허용합니다. 그래서 IaC 역할은 Relay에도 `Purpose=vpn-probe`를 붙일 수 있습니다. 다만 재환은 이미 Relay 세션 대상자(Network-Operator Relay 템플릿)라 권한이 넓어지지는 않습니다.
- `ssm:SessionDocumentAccessCheck`는 `BoolIfExists=true`입니다. 조건 키가 없으면 이 조건만으로 막지 않고, 명시적 false는 거부합니다. StartSession의 대상 태그·서울 리전 및 허용 shell 문서 범위는 유지합니다. 이 변경이나 합성 조건 시뮬레이션으로 실제 요청의 조건 키 부재를 확정하지 않습니다. 생성 승인 회차에 기본 문서/명시적 문서 정상 및 허용 밖 문서/태그·타인 세션 거부를 확인합니다.
- Resume/Terminate는 `aws:userid`와 세션 소유 태그가 같은 본인 세션으로 제한합니다. 이 statement 자체에 probe instance ID 조건은 없습니다. 현재 역할의 시작 대상은 기존 Relay와 승인 태그 probe이며, 후속 StartSession 범위를 추가할 때 세션 관리 범위도 함께 재검토합니다. 미생성 probe ID를 임의 합성하여 정책에 넣지 않습니다.
