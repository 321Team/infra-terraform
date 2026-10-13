# FDS-Network-Operator 부여 명세 — Relay 전용 세션 역할 (재환·권욱)

2026-10-12 / 이하영(#9 실행 Lead) / CLAUDE_ASSISTED. **명세·준비 자료이며 IAM 부여·생성 GO가 아닙니다.**

- 관련 티켓: [infra-terraform#9](https://github.com/321Team/infra-terraform/issues/9)(처분: Network 역할은 Relay 생성 후 부여, [6108456609](https://github.com/321Team/infra-terraform/issues/9#issuecomment-6108456609)·[수용 6109083724](https://github.com/321Team/infra-terraform/issues/9#issuecomment-6109083724)) · 원티켓 [baseline#35](https://github.com/321Team/fds-project-baseline/issues/35) · VPN [baseline#37](https://github.com/321Team/fds-project-baseline/issues/37)
- 목적: vpn Apply로 Relay가 생기면 **바로 부여**해서 재환 님 VPN 1단계(Relay 접속)가 기다리지 않게 합니다.

## 1. 역할이 하는 일 (쉽게)

| 할 수 있음 | 할 수 없음 |
|---|---|
| **Relay 1대에만** Session Manager로 접속(기본 셸 문서만) | 다른 EC2 접속, 인프라 생성·변경·삭제 |
| 본인이 연 세션만 재개·종료 | 남의 세션 종료 |
| Relay만 재부팅·중지·시작, 부팅 로그·SSM 연결 상태 조회 | Terraform state 버킷 접근(전부 Deny) |
| 서울 리전 조회(인스턴스·주소·ENI·라우트·SG·SSM 세션·지표) | 서울 밖 모든 동작(Deny) |

## 2. 정책·trust 세트 — 새로 쓰지 않고 리뷰된 원본 사용

| 파일 | 역할 | SHA256 | 출처 |
|---|---|---|---|
| `iam/full-policy-draft-20261009/policies/FDS-Network-Operator-Relay.template.json` | Relay 한정 세션·복구·진단. **Relay ID 자리표시자 `__RELAY_INSTANCE_ID__` 5곳** | `bf6bb817c15633253023f449134331ddf6d8d8e430b0cea8aab9997649f62122` (2026-10-13 `Bool`→`BoolIfExists` 후보, 5-1절. 이전 `d4c94fc9…62ba45bd6ebba2f6`) | PR15 병합, baseline `20261006-network-final-candidate` 원문 + 5-1절 변경 |
| `iam/full-policy-draft-20261009/policies/FDS-Network-Operator-StateDeny.json` | state 버킷 전체 Deny + 서울 밖 Deny | `e222cddb82a388be6f7c565f3e670ee761575a3cbd994cdbf56a6a29fb4a6e77` | PR15 병합 |
| `iam/full-policy-draft-20261009/trust/trust-FDS-Network-Operator.json` | 권욱·재환 사용자만, **MFA=true + 본인 RoleSessionName** | `13e134a09d309e58ad6e6c7d04a5ca14605b629caf5d7feff8eb2305e2c11e10` | PR15 병합(baseline 20261006 work-role-precheck 원문) |
| `iam/vpn-probe-20261009/policies/FDS-Network-Operator-Probe.json` | (선택) #37 probe 시험 인스턴스 세션 | `33053efe4e9ab326b3dcffe2541442ffd71faa7af371b6a9b3ebb004de5e2dcd` | PR25 병합. **probe 시험창에만 붙이고 끝나면 분리** |
| `iam/grant-plan-20261009/trust-closed.json` | 생성 직후 잠긴 trust(전부 거부) | — | PR18 병합. 같은 패턴 재사용 |

`tests/test_network_operator_render.py`가 위 4개 원본의 해시가 그대로인지 확인합니다.

## 3. Relay ID 채우기 — `render_relay_policy.py`

vpn Apply 뒤에만 실행합니다. AWS를 호출하지 않습니다.

```bash
python3 iam/network-operator-grant-20261012/render_relay_policy.py <RELAY_INSTANCE_ID> --out <비공개 작업 폴더>
```

- 템플릿 해시가 리뷰본과 다르면 STOP
- ID 형식(`i-` + 소문자 hex 17자리)이 아니면 STOP. `*`, 공백, 대문자도 거부
- 자리표시자 5곳이 모두 채워졌는지, Relay ARN 4회·`instance/*` 0회인지, 관리형 정책 크기 한도 안인지 확인
- 출력: 채워진 정책 파일과 SHA256

### 채우기 전 readback (ID가 진짜 Relay인지)
입력 ID는 vpn state 출력 `relay_handoff.instance_id`에서 가져옵니다. 아래가 **모두 맞을 때만** 씁니다(읽기, 비용 없음).
- `ec2 describe-instances --instance-ids <ID>` (서울): state `running`/`stopped`, 태그 `Name=fds-relay`·`Project=fds-hybrid`·`ManagedBy=terraform`·`Component=vpn`
- 서브넷이 `relay_handoff.subnet_id`(public_transport_a), 프로파일이 `FDS-Relay-SSM`, ENI가 `relay_handoff.primary_eni_id`
- 하나라도 다르면 STOP하고 #37·#9에 보고합니다. 다른 인스턴스 ID로 대체하지 않습니다.

## 4. 부여 순서 (PR18 방식 그대로)

| 단계 | 내용 | 확인 |
|---|---|---|
| 0 | fresh before: 역할·정책 2개가 **없음**(NoSuchEntity) 확인. 있으면 STOP(덮어쓰지 않음) | before 원본 보존 |
| 1 | 중앙 검증: 채운 Relay 정책·StateDeny에 `accessanalyzer validate-policy`, 아래 5절 시뮬레이션 | ERROR·SECURITY_WARNING 0, 기대표 일치 |
| 2 | `create-policy` ×2 (Relay·StateDeny) | 응답 PolicyId·DefaultVersionId |
| 3 | `create-role FDS-Network-Operator` **closed trust로** | RoleId |
| 4 | `attach-role-policy` ×2 | attached 2 / inline 0 / boundary 0 |
| 5 | readback: 정책 원문 해시 = 채운 파일·StateDeny 원본 | 불일치면 trust 닫힌 채 STOP |
| 6 | `update-assume-role-policy` → 최종 trust(권욱·재환, MFA) | trust readback = 원본 |
| 7 | #9·#37에 결과 기록, 원본 비공개 보관 → evidence 편입(독립 리뷰) | |

**실패·회수:** trust를 closed로 되돌림 → 정책 분리 → 역할·정책 삭제 → 부재 readback. 기존 IaC 역할·사용자·그룹은 건드리지 않습니다.

## 5. 시뮬레이션 기대표 (부여 전 중앙 검증용)

| ID | Action | Resource / context | 기대 |
|---|---|---|---|
| P1a | ssm:StartSession | `instance/<RELAY>`, SessionDocumentAccessCheck=true | allowed |
| P1b | ssm:StartSession | `instance/<RELAY>`, SessionDocumentAccessCheck **부재** | allowed (후보 `BoolIfExists`. 현행 `Bool`은 implicitDeny) |
| P2 | ssm:StartSession | `document/SSM-SessionManagerRunShell` | allowed |
| P3 | ssm:TerminateSession | `session/*`, tag session-id=`${aws:userid}`, target-id=`<RELAY>` | allowed |
| P4 | ec2:RebootInstances / StopInstances / StartInstances | `instance/<RELAY>` | allowed |
| P5 | ec2:DescribeInstances | `*`, 서울 | allowed |
| N1 | ssm:StartSession | `instance/<다른 ID>` | implicitDeny |
| N2 | ssm:StartSession | 다른 문서(예: `AWS-StartPortForwardingSession`) | implicitDeny |
| N3 | ssm:TerminateSession | 다른 사용자 session-id | implicitDeny |
| N4 | ec2:TerminateInstances | `instance/<RELAY>` | implicitDeny |
| N5 | s3:GetObject / ListBucket | state 버킷 | explicitDeny |
| N6 | ec2:DescribeInstances | us-east-1 | explicitDeny |
| N1b | ssm:StartSession | `instance/<RELAY>`, SessionDocumentAccessCheck=**false** | implicitDeny (현행·후보 같음) |
| N7-IAM | iam:ListRoles | `*`, IAM 글로벌 endpoint (`aws:RequestedRegion=us-east-1`) | **explicitDeny** (StateDeny `DenyOutsideSeoul`) |
| N7-EC2 | ec2:CreateVpc | `*`, 서울, **시뮬레이션만** | implicitDeny |

### 5-1. `Bool` → `BoolIfExists` 변경 후보 (2026-10-13)

[권욱 #11 6139933906](https://github.com/321Team/infra-terraform/issues/11#issuecomment-6139933906) 지시에 따른 **수정 후보**입니다. 병합만으로 IAM 반영·Runtime GO가 되지 않습니다.

**바꾼 것:** Relay 템플릿 `StartSessionOnExactRelayWithDocumentCheck`(instance 대상 StartSession)의 조건 연산자 1개만 `Bool` → `BoolIfExists`. 값(`"true"`), 리전 조건, Resource(Relay 1대), 다른 statement는 그대로입니다.

**왜:** 부여 뒤 권욱(문서 명시)·재환(문서 생략) 두 계정의 StartSession이 같은 instance ARN에서 거부됐습니다([재환 6124959403](https://github.com/321Team/infra-terraform/issues/11#issuecomment-6124959403)). `Bool`은 조건 키가 요청에 없으면 불일치로 평가되고, `...IfExists`는 키가 없을 때 그 조건을 통과시킵니다([IAM 조건 연산자](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_elements_condition_operators.html)). **실제 요청의 키 부재는 관측하지 않았습니다.** `Bool`은 유력 원인 후보이며, 수정 전후 실제 시험으로 개선 효과와 제한 범위를 확인합니다([권욱 R1 6126405407](https://github.com/321Team/infra-terraform/issues/11#issuecomment-6126405407)). 시뮬레이션은 입력한 조건에서의 정책 평가일 뿐입니다.

**조건 키 비교표** (instance statement 기준, 서울 요청. `tests/test_network_operator_condition_matrix.py` 단순 모형)

| `ssm:SessionDocumentAccessCheck` | 현행 `Bool` | 후보 `BoolIfExists` |
|---|---|---|
| `true` | 일치 → allowed | 일치 → allowed |
| `false` | 불일치 → implicitDeny | 불일치 → implicitDeny |
| 부재 | 불일치 → implicitDeny | **일치 → allowed** |
| (모든 경우) 서울 밖 요청 | 불일치 | 불일치 |

**그대로 유지되는 제한** (이번 변경으로 넓어지지 않음)
| 제한 | 근거 statement | 확인 |
|---|---|---|
| 대상 = Relay 1대 | instance Resource 고정 ARN, `instance/*` 0 | N1 |
| 문서 = `SSM-SessionManagerRunShell`만 | `StartOnlyApprovedDefaultShellDocument` (다른 문서 Allow 없음) | N2 |
| 본인 세션만 재개·종료 | `ManageOnlyOwnSessionsOnExactRelay` session-id=`${aws:userid}`·target-id=Relay | N3 |
| 서울만 | 각 Allow의 `aws:RequestedRegion` + StateDeny `DenyOutsideSeoul` | N6, N7-IAM |
| state 버킷 접근 불가 | StateDeny explicit Deny | N5 |

**중앙 시뮬레이션 기대표 추가분:** P1a·P1b·N1b(위 5절). 나머지 P2~P5·N1~N6 기대는 변경 없음. N7은 N7-IAM / N7-EC2로 분리(IAM Allow 확대·서울 외 거부 해제 없음, 실제 EC2 생성 시험 없음).

**IAM 반영 후 실제 시험안** (권욱·재환 각자, 비용 없음. 정확한 명령·RC·`aws --version`·`session-manager-plugin --version`·정책 `DefaultVersionId` 보존)
| # | 시험 | 기대 |
|---|---|---|
| T4a | `aws ssm start-session --target <RELAY>` (문서 생략) → `exit` | 셸 연결 성공 |
| T4b | `--document-name SSM-SessionManagerRunShell` 명시 | 셸 연결 성공 |
| T5 | 본인 세션 `resume-session`·`terminate-session` | 성공 |
| N1 | 다른 instance ID 대상 start-session | AccessDenied (대상 부재 오류면 판정 불가로 기록) |
| N2 | `--document-name AWS-StartPortForwardingSession` | AccessDenied |
| N3 | 상대방(권욱↔재환) 세션 terminate | AccessDenied |
| N6 | `--region us-east-1` start-session | AccessDenied |
| T6 | state 버킷 `s3api list-objects-v2` | AccessDenied |
- 기존 통과 결과(T1·T2·T3·state·리전·IAM 거부)는 재사용하고 반복하지 않습니다.
- 첫 셸에서는 기존 계획대로 NEVRA·firewalld·SELinux·`ip_forward=0`·bootstrap 상태를 **읽기로만** 확인합니다.

**한정 반영 범위(제안, 판단은 권욱):** 대상 `FDS-Network-Operator-Relay` 관리형 정책만, `create-policy-version --set-as-default`로 새 버전 1개. 변경 전 기본 버전 원문·버전 ID 보존, 실패 시 `set-default-policy-version`으로 이전 버전 복귀. trust·StateDeny·역할·다른 정책 변경 없음.

**이번 PR에서 바꾸지 않은 것**
- `iam/vpn-probe-20261009/policies/FDS-Network-Operator-Probe.json`에도 같은 `Bool` 패턴이 있습니다. 현재 미부착 정책이므로 수정·부착하지 않았고, probe 시험창 전 같은 판단이 필요합니다.
- 관찰: AWS 예시는 본인 세션 조건에 `StringLike` + `${aws:userid}*`를 씁니다. 현행 `StringEquals` + `${aws:userid}`가 AssumedRole 세션 태그와 맞는지는 T5 실제 시험으로 확인합니다(이번 PR 미변경).

## 6. 부여 후 본인 시험 (재환·권욱 각자)

비용 없음. Relay 접속만 합니다.
1. 본인 MFA로 `sts assume-role --role-arn ...:role/FDS-Network-Operator --role-session-name 321team-<본인>` → identity 확인
2. 다른 RoleSessionName → AccessDenied
3. `aws ssm start-session --target <RELAY>` 접속 → `exit`
4. 다른 인스턴스(있다면) `start-session` → AccessDenied
5. state 버킷 `s3api list-objects-v2` → AccessDenied

## 7. 결정 필요 (부여 전)

| # | 사안 | 하영 의견 |
|---|---|---|
| D1 | **IAM 쓰기 실행 주체.** 현재 사람 계정·IaC 역할 모두 IAM 생성 권한이 없습니다. PR18 때는 교육장 root를 "초기 설정 1회 예외"로 썼습니다([6077299965](https://github.com/321Team/infra-terraform/issues/9#issuecomment-6077299965)). | root 재사용이면 "특수 상황 제한 수정"으로 **이 4절 순서만** 별도 승인합니다(같은 4조건: 범위 한정·즉시 종료·전후 기록·본인 시험 전 사용 금지). 판단은 권욱 |
| D2 | probe 정책(PR25) 부착 시점 | Relay 부여 때 함께 붙이지 않고, #37 probe 시험창에만 붙였다가 분리 |
| D3 | `SSM-SessionManagerRunShell` 문서 존재 | StartSession 기본 문서입니다. 계정에 없으면 vpn `create_session_document` 경로(#37 결정)로 먼저 정리. 부여 전 `ssm describe-document` 읽기로 확인 |
| D4 | Relay 중지·재부팅 권한 | 재환 님 VPN 복구에 필요하다고 보고 템플릿대로 유지. 사용 시 #37에 기록 |

## 8. 이 문서가 뜻하지 않는 것
- Relay 생성(vpn Apply) GO, IAM 부여 GO가 아닙니다.
- 템플릿·trust·StateDeny 원본은 바꾸지 않았습니다. 채운 정책 파일은 부여 회차의 비공개 증적으로만 남깁니다.
- 중앙 validate-policy·시뮬레이션: **NOT RUN**(부여 전에 수행).
