# infra-terraform

Phase 2 AWS/ROSA 선행 인프라의 Terraform IaC 저장소. AWS VPC `10.20.0.0/16`·Subnet·Route·Security Group, ROSA 선행 조건, IAM/OIDC 최소권한 Role, Terraform State 통제와 Plan/Apply 추적 기록을 관리한다.

**상태: 저장소 초기 구성 단계.** Terraform 코드·Plan·Apply는 아직 없다. 저장소 생성은 P2-IAC-01 착수·AC 충족·G4 판정을 뜻하지 않는다.

## 책임 티켓

| 티켓 | 이 저장소 범위 | Lead / Support |
|---|---|---|
| [P2-IAC-01](https://github.com/321Team/fds-project-baseline/issues/35) | AWS VPC/Subnet/Route/Security, ROSA Prerequisite, IAM/OIDC, State, Variables/Outputs | 이권욱 / 이하영 |
| [P2-OCI-01](https://github.com/321Team/fds-project-baseline/issues/36) | OCI Relay Go 판정 시 OCI 측 리소스 모듈. No-Go면 Fallback 결정(D21)을 따른다 | 이권욱 / 이하영 |
| [P2-VPN-01](https://github.com/321Team/fds-project-baseline/issues/37) | AWS Site-to-Site VPN·Customer Gateway·Route 전파 리소스. On-Prem vpn-gw01 `.51` 설정은 이 저장소 범위가 아니다 | 이권욱 / 이하영 |
| [DEC-P2-REG-01](https://github.com/321Team/fds-project-baseline/issues/42) | D22가 클라우드 Registry를 선택한 경우에만 해당 리소스 추가 | 이하영 / 이권욱, 이재환 |

Lead·Support는 2026-09-23 Issue 본문 속성표 기준이다. 정확한 Lead·Support·AC는 연결된 Issue와 발행 정본을 따른다.

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
