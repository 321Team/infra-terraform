# U1-I5 오류 종료·잠금 해제·재계획 절차 검토안

2026-10-10 / 이권욱 / CODEX_ASSISTED. **문서 작성·검토 요청이며 RUNTIME NOT_RUN.** #9/#35 기존 U1-I5를 구체화한다. Phase 1 운영·AC, IAM, 실행 승인 범위를 변경하지 않는다.

## 기준과 범위

[기존 U1 표](gwonuk-u1-plan.md)의 I5는 오류 종료·정상 잠금 해제·동일 source 재계획이다. I3 fixture PASS는 실제 Terraform 오류 복구를 대신하지 않는다. 과거 준비 자료에서 강제 종료를 I5 자체와 동일시한 표현은 아래처럼 구분한다.

- **I5-A 권고 회차:** 기존 `execution_enabled=false`의 VPC precondition 오류 → Terraform 자체 잠금 해제 → 동일 source의 `execution_enabled=true` 재Plan. 실제 실행 후에만 오류 복구 범위 PASS 판단.
- **I5-B 별도 후보:** 프로세스 강제 종료·잔여 잠금 수동 복구. 이번 실행안과 승인 범위 밖이며 I5-A가 성공해도 시험한 것으로 표시하지 않는다. 강제 종료를 새 P0 AC로 추가하지 않는다.
- I5-A는 기본 안전 스위치를 사용하므로 새 잘못된 AWS 자원을 만들거나 운영 소스를 고치지 않는다. `false → true`는 의도된 시험 입력 차이이며, 이를 입력 완전 동일이라고 표현하지 않는다.

검토 근거: [HashiCorp locking](https://developer.hashicorp.com/terraform/language/state/locking), [S3 backend](https://developer.hashicorp.com/terraform/language/backend/s3), [Plan 명령](https://developer.hashicorp.com/terraform/cli/commands/plan). 자동 잠금과 상세 종료코드는 문서 근거이며 **본 소스의 precondition 오류 시 실제 잠금 획득·해제 순서는 아직 관측하지 않은 검증 가설**이다. 획득 증거를 놓치면 재시험을 자동 반복하지 않고 INCONCLUSIVE로 남긴다.

## 실행 전 고정할 입력

| 입력 | 값·검증 기준 |
|---|---|
| 대상 | 서울 개인 CloudShell, 권욱의 기존 MFA 경로, `FDS-IaC-Operator/321team-gwonuk`, account `774055931866` |
| source | `81162467bb2f99a099cb7067fbc3f63e1c0dbed8` network 6파일. 실행 전 Git blob·manifest와 대조. 변경 시 새 리뷰 |
| tool | Terraform 1.16.4 linux_amd64 공식 해시, AWS provider 6.66.0 reviewed lock. AWS CLI 버전·조건부 옵션 기록 |
| backend | S3 `fds-tfstate-774055931866-ap-northeast-2`, key `phase2/network/terraform.tfstate`, lock key는 뒤에 `.tflock`, default workspace, `use_lockfile=true`, encryption/versioning 확인 |
| 환경 | 새 HOME0700 evidence/source 폴더. provider/backend 로컬 자료는 새 /tmp0700 경로. /tmp 유실 시 이전 init 재사용 금지. HOME·/tmp 공간과 바이너리 경로 사전 확인 |
| 승인 | 검토된 이 문서 HEAD, 수행할 I5-A 범위, 시작/종료 시각, 다른 network writer 부재·종료까지 미사용 합의. 만료된 I3 작업창 재사용 금지 |
| 권한 | 실행 직전 trust/4정책/inline/versioning readback과 승인본 비교. fresh 역할 만료 여유 확인. root·새 사용자·장기키·권한 확대 없음 |
| 최초 state | state/lock exact prefix 비어 있고 current lock NoSuchKey 확인. 403·timeout·기존 state/lock이면 이 빈-state 시나리오는 STOP |

`REPO`, `TF`, `WORK`, `EVIDENCE`, `TF_DATA_DIR`는 위 검증으로 정한 절대 경로를 회차 기록에 적는다. 이전 실행 디렉터리를 그대로 추정해 쓰지 않는다. 전체 환경변수·자격증명 값은 저장하지 않는다. 오류 감추는 `|| true`나 로그 출력 전 일괄 즉시 종료로 RC를 잃는 래퍼를 사용하지 않는다.

## 실행 순서 — 검토·작업창 확인 후 수동 수행할 명령 계약

아래는 자동 실행 스크립트가 아니다. 각 단계 stdout/stderr·명령·시작/종료 시각·RC를 별도 파일로 수집하고 다음 조건을 확인한다. 기록 실패도 STOP이다.

1. PR22 실행기의 **기본 읽기 모드** 또는 동등한 검토된 절차로 고정 source 복원·init/validate·workspace/backend 검증을 한다. `--execute`는 I3를 실행하므로 I5 준비에 사용하지 않는다. Plan에 사용할 WORK와 TF_DATA_DIR를 summary의 실제값으로 연결한다.
2. 같은 계정의 관측 세션에서 exact lock에 대한 GetObject 관측을 준비한다. region/expected owner 고정, 결과 파일은 요청마다 새 경로에 보존한다. 최소 필드: 시각·RC·ID/Who/Created/Path·ETag/VersionId·원문 SHA. credential은 기록하지 않는다. `NoSuchKey`만 부재다.
3. 아래 오류 Plan을 본인 프로세스로 시작하고 실제 PID/PPID/시작 시각/실행 파일/명령을 기록한다. observer는 이 시작 이후 lock을 관측한다. 임의 fixture나 잠금 지연을 끼우지 않는다.

```sh
"$TF" -chdir="$WORK" plan -input=false -no-color -detailed-exitcode \
  -lock-timeout=5s -var=execution_enabled=false -out="$EVIDENCE/error.tfplan"
```

4. 기대는 **rc1 + aws_vpc.project의 기존 disabled/default-workspace precondition 오류**이다. 권한 오류·source/네트워크 오류·lock-acquisition 오류·다른 rc1은 실패 원인이 달라 I5-A PASS가 아니다. 성공 반환도 STOP. observer에서 자기 lock과 실제 Plan 프로세스의 호스트/사용자·생성 시각·Path를 연결해야 한다. lock Who가 role ARN 형태라고 가정하지 않는다.
5. Plan 종료를 기다리고 PID 종료를 확인한다. 강제 종료 신호를 보내지 않는다. 종료 지연이면 원래 작업창 종료 전 관련자에게 정리 중임을 알리고 쓰기 중단을 유지한다. 세션/프로세스가 살아 있는 상태에서 잠금을 지우지 않는다.
6. current lock NoSuchKey 및 exact state prefix empty를 확인한다. 권한이 이미 허용하는 version-history 조회를 보완 증거로 쓸 수 있으나, 이전 I3 객체 이력을 이번 Plan 획득 증거로 사용하지 않는다. live 관측을 놓쳤고 이번 고유 lock의 내용/생성·해제 연결도 확인할 수 없으면 INCONCLUSIVE. 새 조회 권한을 이 절차로 부여하지 않는다.
7. 같은 source/tool/backend에서 아래 재Plan을 수행한다. `execution_enabled=true` 외 입력 차이가 없음을 기록한다.

```sh
"$TF" -chdir="$WORK" plan -input=false -no-color -detailed-exitcode \
  -lock-timeout=60s -var=execution_enabled=true -out="$EVIDENCE/retry.tfplan"
"$TF" -chdir="$WORK" show -json "$EVIDENCE/retry.tfplan"
```

8. retry rc2, show rc0, managed **20 create/0 update/0 delete**, source/lock hash 불변, 정상 잠금 획득·해제, state 미생성 및 current lock 부재까지 대조한다. show JSON·saved Plan은 비공개 보관한다. 이 Plan을 Apply용 승인 파일로 자동 채택하지 않는다.
9. 수집 manifest·원본 archive 해시와 내부 파일 집합을 확인하고 작업 종료를 #9에 기록한다. 결과를 오류/정리/재Plan 각 단계로 분리한다.

## 중단·복구 분기

| 상황 | 조치·판정 |
|---|---|
| 오류 전에 lock 획득 미관측 | INCONCLUSIVE. 단순 rc1/잠금 없음만으로 I5 PASS 금지. 빈도를 올린 무한 polling이나 반복 Plan 금지 |
| Plan 정상 종료 뒤 own lock 잔존 | STOP/RECOVERY_REQUIRED. ID·ETag·VersionId·원문·프로세스 종료 증거 보존. 새 Plan 금지 |
| 타인 lock, ID/ETag 변경, 소유 불명 | 즉시 STOP. 본인 I3 fixture 정리 승인을 실제 Terraform lock에 전용하지 않음 |
| 403/timeout/세션 만료 | 상태 UNKNOWN. MFA/정책을 완화하지 않고 담당자에게 현 상태 전달, 최신 읽기 확인 후 다음 조치 검토 |
| 예상 밖 state 생성/변경, delete/recreate | STOP. 이전 존재·hash/version metadata와 비교. state 삭제·복원·전체 destroy 실행 금지 |
| 원본 저장 공간/파일쓰기 실패 | STOP. 캐시·/tmp 전체 삭제 금지. 남은 원본 보존, 작업창/프로세스/lock부터 확인 |

잔여 **실제 Terraform 잠금** 복구는 대상 bucket/key·Lock ID·소유/프로세스 종료·현재 ETag/VersionId·versioning·영향·실패 시 중단을 포함한 별도 1회 변경안으로 리뷰한다. 이 문서는 force-unlock, 무조건 DeleteObject, version 영구삭제를 승인하거나 실행하지 않는다. 정리 실패 상태에서 창을 '정상 해제'로 기록하지 않는다.

## 증적·독립 검토 완료조건

필수: 실행 승인/작업창 링크, 역할/trust 근거, host/KST/UTC, source6개 hash·TF/provider, backend identity, 시작 PID와 종료 확인, error Plan 원문/RC, 그 회차 lock ID·관측/해제 연결, retry Plan/JSON hash·20개 대조, 전후 state/lock, 중단/실패 회차, manifest·수신 기록.

원본과 공개 검토용 projection을 분리하고 원본 누락을 숨기지 않는다. Windows 수신본은 원문 LF/CRLF 바이트 보존, 개인 절대 경로를 재현 필수 상수로 하드코딩하지 않는다. 생산자 권욱의 자체 확인과 독립 승인 분리. 독립 리뷰어는 작성·실행 미참여자가 exact HEAD를 확인한다.

현재 상태: **PROCEDURE_DRAFT_READY / STATIC 문서 검토 대상 / MOCK NOT_RUN / RUNTIME NOT_RUN / REVIEW PENDING**. I5-A 실행 승인·새 작업창 전에는 위 명령을 실행하지 않는다. Phase 1/Apply/ROSA 생성·비용 GO와 무관하다.
