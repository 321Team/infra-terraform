# infra-terraform

Phase 2 AWS/ROSA 선행 인프라의 Terraform IaC 저장소. AWS VPC `10.20.0.0/16`·Subnet·Route·Security Group, ROSA 선행 조건, IAM/OIDC 최소권한 Role, Terraform State 통제와 Plan/Apply 추적 기록을 관리한다.

**상태: Stage-A 계약 scaffold와 bootstrap 소비 사전 작업.** 관리 리소스 구현·Terraform Plan/Apply는 아직 없다. 소스 준비는 P2-IAC-01 AC 충족·G4 판정을 뜻하지 않는다.

## 책임 티켓

| 티켓 | 이 저장소 범위 | Lead / Support |
|---|---|---|
| [P2-IAC-01](https://github.com/321Team/fds-project-baseline/issues/35) | AWS VPC/Subnet/Route/Security, ROSA Prerequisite, IAM/OIDC, State, Variables/Outputs | 이하영 / 이권욱 |
| [P2-OCI-01](https://github.com/321Team/fds-project-baseline/issues/36) | OCI Relay Go 판정 시 OCI 측 리소스 모듈. No-Go면 Fallback 결정(D21)을 따른다 | 이권욱 / 이하영 |
| [P2-VPN-01](https://github.com/321Team/fds-project-baseline/issues/37) | D21 AWS EC2+EIP Relay/ENI·명시적 Route·SG Transport Adapter 리소스. On-Prem vpn-gw01 `.51` 설정은 이 저장소 범위가 아니다 | 이재환 / 이권욱 |
| [DEC-P2-REG-01](https://github.com/321Team/fds-project-baseline/issues/42) | D22가 클라우드 Registry를 선택한 경우에만 해당 리소스 추가 | 이권욱 / 이하영, 이재환 |

Lead·Support는 2026-09-30 승인된 Phase 2 담당 리밸런싱과 현재 Issue 속성표를 따른다. 정확한 Lead·Support·AC는 연결된 Issue와 현행 승인 기록을 따른다.

Stage-A W0 입력은 [`docs/P2-IAC-01_STAGE_A_W0_20261002.md`](docs/P2-IAC-01_STAGE_A_W0_20261002.md)에 기록한다.

## 다른 저장소와의 경계

| 저장소 | 범위 |
|---|---|
| [fds-project-baseline](https://github.com/321Team/fds-project-baseline) | 요구사항·AC·Interface(IF-17~IF-20)·Decision(D21~D23·D26) 정본 |
| [infra-rosa](https://github.com/321Team/infra-rosa) | ROSA 클러스터 내부 구성(Namespace·RBAC·NetworkPolicy·OADP·Operator). 이 저장소의 Output을 입력으로 쓴다 |
| [infra-ansible](https://github.com/321Team/infra-ansible) | On-Prem vpn-gw01 등 VM 구성 자동화 |
| [infra-cicd](https://github.com/321Team/infra-cicd) | Runner·Delivery. ROSA 배포 경로(P2-CICD-01) |
| [fds-project-evidence](https://github.com/321Team/fds-project-evidence) | 실행 증적 원본. 경로 `evidence/<Record ID>/` |

## 비밀정보와 State

- Access Key·Secret·토큰·`*.tfvars`·State 파일을 커밋하지 않는다. `.gitignore`가 기본 차단하지만 커밋 전 확인 책임은 작성자에게 있다.
- 공유 가능한 입력 예시는 `*.tfvars.example`로만 둔다.
- Remote State의 위치·잠금·접근 권한은 P2-IAC-01에서 결정하고 README에 기록한다. 결정 전에는 Apply하지 않는다.
- Plan은 검토 후 Apply한다. Plan·Apply 원본 로그는 민감정보를 제거해 증적 저장소에 편입한다.

## 변경 절차

리뷰·병합과 Lead 판단은 [리뷰 정책](docs/REVIEW_POLICY.md)을 따른다. Terraform 코드·변수·모듈은 **코드 변경**이므로 작성자 외 적격 검토자의 독립 리뷰 후 Lead가 병합을 결정한다. 문서만 변경한 PR은 책임 Lead가 판단한다. 사전 검증(Pre-check) 코드는 담당 Lead 권한으로 바로 병합할 수 있으나, 실제 AWS/OCI 계정에 Apply하기 전에는 해당 SHA의 코드 리뷰가 필수다. main 직접 push·force push·자동 병합을 하지 않는다.

이 문서는 운영 통제이며, GitHub branch protection/ruleset이 활성화됐다는 뜻이 아니다.

## 2026-10-03 Current Phase 2 boundary

D21=`aws_ec2_eip_relay`; managed S2S/CGW/VGW-TGW는 selected path 아님. Historical W0와 current contract를 [Stage-A 기록](docs/P2-IAC-01_STAGE_A_W0_20261002.md)에서 분리한다. 현재 code/static scaffold는 PR #3, architecture contract는 [private baseline PR #137](https://github.com/321Team/fds-project-baseline/pull/137)이다. Topology/access/egress/DNS/backend/source contract 미결로 Freeze HOLD. AWS resource create/apply 미실행.

이전 공개 architecture PR #8은 종료된 역사 출처이며 현행 상세 후보는 비공개 baseline PR #137에서 관리한다. 후보 링크 갱신은 Freeze/승인/Apply 완료를 뜻하지 않는다. 적용할 입력은 검토된 exact SHA로 고정한다.

## 2026-10-07 Bootstrap 이후 소스 준비

[중앙 4자원 생성·설정 수신 기록](https://github.com/321Team/fds-project-baseline/issues/35#issuecomment-6031865288)과 [Lead 리뷰](https://github.com/321Team/fds-project-baseline/issues/35#issuecomment-6032041833)를 소비하는 [Stage-A 사전 작업](terraform/stage-a/README.md)을 추가한다. Provider 계정 제한, 채택된 component backend 예시 4개, 기존 Relay profile의 읽기 전용 참조를 제안한다. CloudFormation이 bootstrap 4자원을 계속 소유한다.

완결된 관리 리소스 구현/API·permissions JSON은 이하영 Lead의 후속 입력이다. 이번 변경은 후보 소스이며 role grant·MFA 본인 Runtime·유료 생성·Stage-A GO·전체 AC 인수가 아니다. 담당·일정·기존 Freeze/비용 조건은 유지한다. 계정·ARN·backend 설정 원문은 비공개 구현 입력으로 보존하고, 외부 요약은 식별 값을 마스킹한다.
