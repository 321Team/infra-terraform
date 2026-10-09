# Phase 2 IaC IAM 부여·복구 검토안 — 2026-10-09

CODEX_ASSISTED. **PREPARATION COMPLETE / REVIEW PENDING / GRANT NOT_RUN**. 사용자 “착수”에 따라 부여할 내용을 구체화한 문서다. PR17 정책 source 승인과 실제 Grant 승인을 구분한다. Phase1 인수조건·Runtime·정본, 비용 중앙 통제(#34 교육장 리포트), Freeze·생성/삭제창을 변경하지 않는다.

## 이번 결정 대상

**권고: IaC 역할 1개 + 관리형 정책 4개만 신규 생성하고, 검토된 권욱·하영 trust를 마지막에 활성화한다.** Network 역할은 실제 Relay 결속 후 별도이며, Audit과 사용자/공용 그룹 정책을 이번에 수정하지 않는다. 이 단계는 Stage-A 전체 IaC 업무 역할의 부여안이지 역할 일부 권한만 시험적으로 연결해 작업시키는 안이 아니다.

| 자원 | before (16:03 KST 실제 조회) | 승인 시 after | 영향 |
|---|---|---|---|
| FDS-IaC-Operator | ABSENT | path `/`, max session3600, 최종 trust는 승인 원문 | 권욱·하영이 본인 이름+MFA로 역할 진입 가능 |
| FDS-IaC-Guardrails | ABSENT | 신규 관리형 정책, 해당 역할에만 연결 | 리전·소유 태그·세션 문서·CFn 보호 |
| FDS-IaC-State-PassRole | ABSENT | 신규 관리형 정책, 해당 역할에만 연결 | state4key/lock과 exact Relay PassRole, state 삭제 거부 |
| FDS-IaC-Network | ABSENT | PR17 source 그대로 신규 연결 | 서울 소유 태그 network·NAT CRUD |
| FDS-IaC-Vpn | ABSENT | PR17 source 그대로 신규 연결 | 제한 AMI/type/IMDS/volume의 Relay 및 SG·SSM 범위 |
| 권욱·하영 IAM 사용자 | 직접 inline0/managed0, boundary없음, FDS-Human-Bootstrap 소속 | 정책 변경0 | 기존 사용자 권한 유지 |
| Network/Audit/공용 그룹/중앙 bootstrap | Network 부재, Audit 존재; 그룹 원본 수집 | 변경0 | 기존 역할·기능 보존 |

[기계 판독 변경안](grant-plan.json)은 실행기가 아니다. 10개 예정 작업과 파일별 SHA를 고정했다. 최종 업무 정책·trust source는 main `c699d667f8af3f983f54fd54629401562789bdd4`이며 PR17 검토본과 동일하다. 새로운 JSON은 초기 trust 잠금과 회수용 Deny2개뿐이다.

### 사용자 정책을 추가하지 않는 이유

현행 trust는 같은 계정의 두 **사용자 ARN**을 Principal로 직접 지정한다. [STS AssumeRole 공식 설명](https://docs.aws.amazon.com/STS/latest/APIReference/API_AssumeRole.html)에 따르면 이 경우 추가 identity Allow는 필수가 아니다. 기존 명시 Deny/SCP 등은 여전히 우선한다. 따라서 기존 `assume-*.json` 전체(다른 역할 포함)를 사용자에게 부착하지 않는다. trust의 MFA·본인 RoleSessionName 조건은 불변이다. 콘솔 root 세션으로 본인 역할 시험을 대신하지 않는다.

현행 그룹은 관리형 FDS-Human-ReadOnly-Guard-v1(v1), ReadOnlyAccess(v190)와 inline3개다. 수집한 그룹 guard는 승인 사용자 제한 및 MFA/리전 통제를 유지하며, MFA를 가진 승인 사용자의 IaC AssumeRole에 해당하는 별도 명시 Deny는 정적 검토에서 확인되지 않았다. SCP·resource policy·실제 MFA 세션까지 통과했다는 판정은 아니다. 기존 사용자 직접 권한에 대한 전면 감사도 이번 범위가 아니다.

## 증적과 남은 조건값 판정

- [before receipt](before-receipt.json): 16:03:12~16:03:43 KST 중앙 읽기 API25회. RC0 19회 / 명시 NoSuchEntity RC254 6회. 원본 다운로드 후53/53 파일 hash·파일 집합 일치. 이번 collector source `49bf0d4d3f847545c69166ac6bff6af64a0b5274`.
- 원본 archive SHA `794978147d5d33c266c5f4144103ba08c223a79ce3c630aa6154742c57f922dc`; CloudShell `/home/cloudshell-user/fds-grant-before-cnliublh`, 로컬 비공개 `work/phase2-sequence-20261007/private-evidence/fds-grant-before-cnliublh`.
- [조건값27건 개별 판정안](context-disposition.md) / [JSON](context-disposition.json): 26건 무관한 조건키, 1건 의도적 Project 생략. **이권욱의 최종 수용은 PENDING**. 권고 수용 범위는 정적·시뮬레이션 설명뿐이고 실제 다중 자원 인가가 아니다. 하영의 설명 동의를 전체 runtime 승인으로 바꾸지 않는다.
- 이전 ValidatePolicy12·70-case/STATIC 결과는 PR17 receipt를 재사용한다. 정책 불변이므로 같은70-case를 다시 실행하지 않았다.
- 이번 조회기 실패경계 unittest2개 PASS: 쓰기 API 사전 차단, caller 불일치 중단·부분 receipt 보존. 현황 수집 RC0을 Grant 또는 인수 PASS로 표시하지 않는다.

### 신규 잠금·회수 JSON 검증

[중앙 원본 접수표](controls-validation-receipt.json)에 별도 검증을 연결했다. 처음 trust의 `Principal: "*"` 표기는 AWS ValidatePolicy가 ERROR(ROLE_TRUST_POLICY_UNSUPPORTED_WILDCARD_IN_PRINCIPAL)로 거부했다. AWS에 적용하지 않았으며 실패 원본을 보존했다. 계정의 유효한 Principal ARN에 명시 Deny를 주고 Allow를 두지 않는 형태로 수정 후 해당 trust만 재검증했다.

**최종 trust-closed와 deny-role-sessions 모두 findings0**, 입력 bytes는 저장소 파일과 동일. 원본 archive 각각9/9·6/6 파일 hash·집합 재검증. 문법 검사 완료이며 실제 IAM 잠금·회수·권한 부여 시험은 미실행이다. 중앙 실행의 argv·RC·시각은 접수표에 있고 stdout/stderr는 비공개 원본에 있다.

## 실행 전제 및 예정 순서 (아직 미실행)

대상 계정 끝1866/서울, 중앙 부여 권한이 있는 승인된 세션, 검토 source의 절대 경로, 새 private0700 증적 디렉터리를 사용한다. 실행 전 계정/exact caller·collector와7개 정책/trust hash, 최신 HEAD·리뷰·최종 승인 기록을 확인한다. token·MFA·secret은 기록하지 않는다.

1. **독립 리뷰 후 이권욱이 Grant 범위와 context 판정안을 별도 수용한다.** 지금은 이를 요청할 자료를 완성한 단계다. 중앙 root의 기존 조회 승인을 쓰기 승인으로 확대하지 않는다.
2. **쓰기 직전 before 재수집**: role1/예정된 path `/`의 policy ARN4 여전히 ABSENT, 사용자 ARN·그룹/guard 버전 불변 확인. 실행용 collector 기록에 source/입력 hash·명령·RC·UTC·원본 hash·RoleId/PolicyId/생성 시각을 남긴다. 기존 자원이 나타나거나 원본 hash가 달라지면 STOP, 덮어쓰기/자동 import 금지. IAM quota 및 필요한 생성 권한도 확인한다.
3. 검토 JSON으로 관리형 정책4개 생성(아직 어떤 주체에도 연결하지 않음). 생성 태그는 grant-plan.json과 동일. 반환 ARN/PolicyId·default version 문서의 semantic JSON 일치를 확인한다.
4. `trust-closed.json`의 계정 Principal AssumeRole 명시 Deny·Allow 없음 상태로 역할 생성. 역할 max session3600/path `/`/태그·RoleId·closed trust를 확인한다. 역할 생성 자체도 별도 승인된 IAM 쓰기 범위에 포함된다.
5. Guardrails를 먼저, State-PassRole→Network→Vpn 순으로 연결한다. 어떤 실패도 기록·정지하고 trust는 닫힌 상태로 유지한다. 재시도 전 실제 readback과 해당 실행 ledger를 대조한다.
6. **활성화 직전 readback**: closed trust, 정확한4개 부착, inline0/예상 외 boundary0, instance profile 연결 없음, 각 default policy 문서와 승인 원문 일치, 정책의 다른 부착 주체 없음. 불일치면 활성화 금지.
7. 마지막 한 번의 UpdateAssumeRolePolicy로 승인된 최종 trust를 적용한다. 같은 계정 직접 trust이므로 **이 단계가 사용자 접근이 열리는 시점**이다. 사용자 정책이 없다는 이유로 아직 닫혀 있다고 판단하지 않는다. trust readback을 확인한다.
8. 권욱·하영이 각 본인 MFA 세션으로 정확한 RoleSessionName을 사용해 역할 전환한다. credentials를 화면/로그에 출력하지 않고 GetCallerIdentity의 역할 ARN만 증적화한다. 잘못된 이름·MFA 없음·미배정 사용자 거부를 각 승인된 시험 경로에서 확인한다. 로그인이 되었다는 사실만으로 업무 권한 PASS가 아니다.
9. 역할 정책·S3 backend/lock·정책 음성 경계를 기존 U1 절차로 확인한다. 실제 다중 자원 인가는 **실제 inventory가 존재하는 단계**에 맞춰 EC2 DryRun/통제된 Stage-A 실행으로 확인한다. 없는 VPC/subnet ID를 만들어 통과했다고 하지 않는다. network Plan을 위해 아직 존재하지 않는 전체 network 생성 결과를 먼저 요구하지 않는다.
10. Grant/readback/U1의 해당 Gate가 충족되면 기존 Plan 절차를 별도 승인 범위에서 시작한다. Apply·route ON·ROSA 생성 승인은 따라오지 않는다.

이 문서는 위험한 일괄 실행 스크립트를 제공하지 않는다. 실행 시점에 검토된10개 요청을 순차 실행하고 각 readback에서 멈출 수 있어야 한다. IAM eventual consistency 오류는 대기 후 같은 readback을 재검증하며 정책을 넓혀 해결하지 않는다.

## 복구안

**원본 보존·실행 ledger에 본 회차 생성으로 확인된 대상만 회수한다.** 이름만 같다고 삭제하지 않는다. IAM 회수로 이미 생성된 EC2/ROSA 비용이나 자원이 정리되었다고 선언하지 않는다.

- **최종 trust 활성화 전 실패:** trust 잠금 유지. RoleId/PolicyId·생성 시각·정책 hash가 ledger와 일치하고 다른 attachment/boundary 참조가 없으면 본 회차의 연결을 해제하고 신규 role/policy만 역순 정리한다. API timeout은 생성 실패로 단정하지 말고 fresh readback으로 성공 여부를 확인한다. 기존 Audit·사용자·그룹은 복구 대상이 아니다.
- **활성화 후 접근 중단:** 중앙 실행자가 trust를 closed로 되돌려 신규 세션 발급을 막고, 해당 신규 IaC 역할에만 `FDS-Grant-Quarantine-20261009` inline으로 `deny-role-sessions.json`을 부착한다. 초기 최종 승인안에는 이 비상 중단 범위도 함께 포함한다. [AWS 설명](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_temp_control-access_disable-perms.html)처럼 trust만 닫거나 identity Allow만 지워 기존 STS 세션까지 즉시 사라졌다고 판단하지 않는다. 정책 전파·기존 세션의 업무 API 거부를 확인한다.
- **활성화 후 구조 정리:** 기존 세션 만료·실효 거부 및 다른 resource policy/공유 참조 부재를 확인할 때까지 closed trust+quarantine을 유지한다. broad resource policy 경로가 있다면 새 범위의 별도 검토가 필요하다. 임시 quarantine을 먼저 제거하지 않는다. 이후 본 회차4개 정책을 분리하고 참조0·non-default version 목록을 확인한 대상만 정리한다. role inline quarantine 제거/role 삭제는 마지막 구조 정리 단계다. 만료/회수 확인이 불가능하면 잠금 상태로 남기고 담당자·후속 확인시각을 기록한다.
- **복구 완료 구분:** 접근 차단 확인, IAM 구조 원복, 이미 생성된 인프라 정리는 서로 다른 완료 항목이다. 실제 Grant 전인 현재 복구 실행은 필요 없고 수행하지 않았다.

## 담당과 Gate

| 담당 | 다음 작업 | 완료 기준 |
|---|---|---|
| 하영 | 이 변경안·잠금/회수 JSON·before/조건값 판정안 독립 리뷰 | 정확한 PR HEAD 기준 source 승인 또는 지적 |
| 권욱 | context27 정적 수용, 신규5자원·활성화·복구 대상 최종 판단 | 별도 Grant 승인 기록; 비용은 계속 #34 중앙 통제 |
| 중앙 실행자 | 승인 후 fresh before→생성·결속·활성화·readback | ledger/원본/해시·실제 상태 일치 |
| 권욱·하영 | 본인 MFA 역할 및 범위별 U1 | 실제 본인 결과. 토큰 공유/중앙 root 대행 금지 |
| 하영 | ROSA #12 full JSON/source/lock/CLI pin·대체 접근 | 본 Stage-A IAM 승인으로 대체하지 않음 |

미완료: 독립 리뷰, 최종 Grant/context 수용, 쓰기 직전 before, 실제 부여·본인 시험, 후속 Plan/Apply. Network exact target 및 ROSA bootstrap 권한은 별도 단계다.
