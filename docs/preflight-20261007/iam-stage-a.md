# #35 IAM / Stage-A Gate

CODEX_ASSISTED. 판정: **FULL_PERMISSIONS=INCOMPLETE / HUMAN_ROLES=ABSENT / CLOUD_PLAN=NOT_RUN / STAGE_A_READY=NO**. 2026-10-07 23:56 KST 중앙 읽기 조회에서 두 역할의 NoSuchEntity를 직접 수신했다. [실행 접수](central-readonly-receipt.md).

## 기존 완료 근거와 잔여

| 단계 | 확인한 원본 / 현재 범위 | 다음 조건 |
|---|---|---|
| 중앙 bootstrap | [#35 수신6031865288](https://github.com/321Team/fds-project-baseline/issues/35#issuecomment-6031865288): 4자원 CREATE_COMPLETE·설정/manifest PASS_USER_READBACK | CloudFormation 소유 유지. 생성·verify·14시험 반복 안 함. 원본 독립 증적 편입은 별도 |
| trust·개인 AssumeRole | [기존 수집기/결과](https://github.com/321Team/fds-project-baseline/blob/81365568fd0b946ad93e4d82ae8191add5fcacd0/phase2/permissions/20261006-work-role-precheck/README.md): identity-side 22건 PASS_USER_READBACK | 실제 trust/본인 MFA AssumeRole 시험과 구분 |
| backend/PassRole 후보 | [기존 delta 수신](https://github.com/321Team/fds-project-baseline/blob/81365568fd0b946ad93e4d82ae8191add5fcacd0/phase2/permissions/20261007-iac-delta-delivery/central-result-receipt.md): 부분46건+context보완9건 | 전체 EC2 service policy·실효권한의 성공 아님. 동일 시험 반복 안 함 |
| network/vpn 소스 | PR5 HEAD ae39cc6a, merge0eabe8da. STATIC/MOCK와 독립 source 리뷰 완료 | 소스 병합을 IAM/Plan/Apply 승인으로 확대하지 않음 |
| 전체 IAM | [14행 inventory](../../validation/components-20261007/resource-api-inventory.json) `full_permissions_complete=false` | network resource/API coverage부터 보완, 실제 action/ARN/tag/조건·복구까지 완결 |

## 발견한 source 연결 공백

기존 14행 inventory는 주로 vpn을 대상으로 한다. `terraform/network/main.tf`의 **6개 resource block / 15개 resource instance**(VPC1, subnet4, IGW1, route-table4, association4, default route1)와 AZ data source의 개별 coverage 행이 없다. 기존의 “14행은 전체 정책이 아님”이라는 한계를 구체화한 것이며 새 AC가 아니다.

10-08 후속: [network 보완 inventory](network-permission-supplement.json)에 resource6행·15instance와 AZ data3개, shared tag/조건부 정리 경로를 provider6.66.0 원본·SHA와 연결했다. **자료의 network 행 공백은 보완했지만 기존14행 원본과 완결 IAM 정책의 부재는 그대로다.** [중앙 검증 인계](central-validation-handoff.md)의 제출 항목을 #35가 수용·통합한 뒤 검증한다. 모든 후보 action을 자동 Allow하는 파일이 아니다.

| source | 전체 정책 작성 때 빠뜨리지 않을 작업군 |
|---|---|
| aws_vpc.project | VPC 생성/조회/삭제, DNS support/hostname 속성 설정 및 조회 |
| aws_subnet.project | subnet 생성/조회/삭제, public-IP-launch 속성, AZ ID 조회 |
| aws_internet_gateway.transport | IGW 생성/조회/attach/detach/삭제 |
| aws_route_table.subnet | route table 생성/조회/삭제 |
| aws_route_table_association.subnet | association 생성/조회/교체/해제 |
| aws_route.transport_internet | route 생성/조회/교체/삭제 |
| 공통 | create-time tags vs 후속 tag mutation, dependent ARN, 보호 tag 제거/외부 자원 retag 거부 |

이는 작업군 점검표이며 완성 IAM Action JSON이 아니다. AWS provider6.66.0 원본/API와 대조한 뒤 #35가 actual Action/Resource/Condition으로 작성한다. `ec2:*`, `iam:*`, `kms:*`로 빈칸을 메우지 않는다. future ROSA 전체 모듈을 network/vpn의 새 초기 선행조건으로 요구하지 않는다.

정책의 검토 범위: RunInstances의 image/subnet/SG/ENI/volume/instance, 정확 Relay PassRole·PassedToService, 실제 alias/aws/ebs KMS service 경로, 서울·계정·태그, 4개 exact state key/.tflock, state payload 삭제 금지, 중앙 CFn 변경 금지, Network 역할 state 접근 금지. 소스·정책 SHA와 양/음성 simulation을 연결한다.

## 순서와 통과 기준

1. 이하영: 실제 source + 완결 permissions JSON + API/조건 inventory를 제출/검토한다. 기존 trust(권욱/하영 IaC, 권욱/재환 Network), MFA와 본인 RoleSessionName 경계를 재사용한다.
2. 중앙 지원 이권욱: 기존 승인 범위에서 fresh before backup, ValidatePolicy, 변경 delta 양/음성 simulation → 해당 부여 단계 승인 범위 확인 → grant/readback. 아직 부여 명령을 준비·실행하지 않았다. 정책 수용 전 부분 권한만 부착하지 않는다.
3. 권욱·하영: 각 본인 MFA IaC role 세션에서 state/lock 정상·거부·중단복구와 대표 업무 API를 검증. 다른 사람 결과를 본인 시험으로 대체하지 않는다.
4. Plan Gate: 검토 소스·정확 backend/workspace·권한·변수·원본 증적 보존이 준비된 뒤 [network plan](plan-runbook.md). Plan의 state lock 쓰기 가능성을 고려해 순수 읽기 수집과 구분한다.
5. Apply Gate: 위 조건에 더해 #34 Freeze, 검토한 saved plan, $500/자부담0 내부 비용 한도(교육장 리포트 기준 추적), 실행창·복구 조건을 충족해야 함. 이번 작업은 GO가 아니다.
6. 실제 Relay 생성 후 #37에 instance/ENI/EIP/profile/document/Agent/EBS 인계 → Network exact bind/grant → 권욱·재환 각각 U1. actual ID 부재를 생성 전 source 검토의 순환 차단조건으로 삼지 않는다.

## 10-08 새 AMI·소스 소비

PR7의 후보 SHA·AMI와 IAM delta는 [소스 연결표](source-alignment-20261008.md)에 고정했다. 수집기의 AMI는 Stream9로 바뀌었으며 summary에 기대 AMI/owner·후보 SHA를 기록한다. 수집 성공은 후보 metadata 확인일 뿐 코드 승인/Plan GO가 아니다. RunInstances image ARN도 새 AMI와 대조하고 최종 전체 정책을 검토한다. 이전 14행 inventory와 network 보완표의 작성 당시 근거는 보존한다.

## 읽기 전용 추가 수집

대상: 채택 중앙 계정(끝 1866), 서울 CloudShell. 이권욱의 기존 중앙 사전조회 승인 범위에서 실행하며, 이번에는 로그인된 중앙 root identity를 STS로 확인했다. 중앙 사전조회와 이후 본인 MFA 역할 시험을 구분한다. 일반 Terraform Plan/Apply를 root로 수행하는 승인이 아니다. 새 권한 부여는 이 수집 절차에 포함하지 않는다. Python3/AWS CLI가 필요하다. SHA가 고정된 이 PR의 `scripts/collect-phase2-preflight.py` 한 파일을 CloudShell 개인 경로에 업로드한다. 전달 파일의 SHA256을 해당 Git blob에서 산출한 SHA256과 비교한 뒤:

```bash
python3 collect-phase2-preflight.py --output-parent "$HOME"
```

수집기는 STS account 확인 후 exact AMI metadata, IaC/Network role trust·정책 **목록**, 기본 session document metadata/content만 읽는다. 정책 목록은 정책 내용/실효권한 검증이 아니다. state/Secret/Parameter/user-data/토큰은 읽지 않는다. IAM `NoSuchEntity`만 ABSENT, SSM `InvalidDocument`는 NOT_FOUND_REVIEW_REQUIRED, AccessDenied/timeout/기타 오류는 STOP. 문서 부재 결과도 생성·소유 승인으로 쓰지 않는다.

성공: `COLLECTION=COMPLETE`, 명령별 RC/UTC/KST/host/source hash·원본 stdout/stderr·SHA256SUMS 보존. **COLLECTION 성공이어도 STAGE_A_READY=NO**, AMI 내부 패키지·서비스=NOT_VERIFIED. 오류 시 원본을 보존하고 후속 grant/plan/apply로 넘어가지 않는다. AWS 변경이 없으므로 AWS 원복은 없고, 수집 디렉터리를 삭제하지 않는다. 원본은 비공개로 보관하고 공유 전 식별값을 마스킹한 사본을 별도로 만든다. `--debug`, credentials 출력, 일반 계정으로 업무 apply는 사용하지 않는다.

## 10-08 기존 Session document 결정 정합화

[#37 결정6013422735](https://github.com/321Team/fds-project-baseline/issues/37#issuecomment-6013422735)의 무로그/무KMS/RunAs 없음 구성은 이미 결정됐다. 새 선택 요청이 아니라 #35 계정 문서 소유 수용·fresh absence·생성 후 readback이 잔여다. [본인 시험 패킷](gwonuk-u1-plan.md)에 구성/권한/Runtime을 분리했다.
