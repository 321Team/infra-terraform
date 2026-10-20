# VPN probe IAM 준비 검증·반영 기록

이권욱 / CODEX_ASSISTED · 2026-10-16 KST. 사용자 요청 및 실행 시점의 명시적 승인으로 계정 `774055931866`에 한정 반영했다. 본인 작성·실행 기록이며 타인의 독립 승인으로 표시하지 않는다.

## 기준과 변경

- 검토 기준 main: `038c490e79f80237b43f6bb04cef34edd26bc820`.
- `FDS-IaC-VpnProbe` 및 EC2 전용 trust는 기존 코드 그대로 사용했다.
- `FDS-Network-Operator-Probe`는 문서 검사 조건을 `Bool`→`BoolIfExists`로 수정하고 Terraform provider의 `Project`·`ManagedBy` 기본 태그를 시작 대상 조건에 결속했다. 이 PR은 실제 적용본을 소스와 일치시키는 변경이다.
- probe 역할·인스턴스 프로파일을 만들고 `AmazonSSMManagedInstanceCore` 1개만 연결했다. IaC/Network 역할에는 각각 해당 보충 정책 1개를 추가했다. 기존 역할 trust·기존 정책 버전·MFA·서울 외 거부·state 보호는 유지했다.
- 실제 반영/원문/연결 재조회: **2026-10-16 14:32:30 KST**. 이 기록은 EC2 인스턴스 생성이나 VPN/DB 시험 승인이 아니다.

## 증적 분류

| 단계 | 확인 범위 |
|---|---|
| STATIC | probe 정책 2개·trust와 같은 회차의 권욱 D1 정책을 합친 4개 AWS ValidatePolicy 지적 0; 로컬 probe 정책·Terraform·manifest 정합성 시험 10/10 |
| MOCK / IAM 시뮬레이션 | 반영 전 후보 결합 77/77 기대 일치(14:29:33 KST), 반영 후 후보를 주입하지 않고 실제 부착 정책으로 77/77 기대 일치(14:33:43 KST); MFA, 역할 제한, PassRole 대상/service, state 삭제/TLS/리전, probe 태그, SSM 문서, 본인/타인 세션, 보호 작업 포함 |
| RUNTIME: IAM 설정 | 역할/프로파일/보충 정책 생성·연결 및 원문 readback 완료 |
| RUNTIME: 실제 사용자·probe | **NOT_RUN**. 실제 EC2 생성·SSM Agent 등록·Start/Resume/Terminate·네트워크·DB 성공 미검증 |
| REVIEW / MERGE | 이 변경의 독립 리뷰·병합은 별도 GitHub 상태를 따른다 |

시뮬레이션의 instance/session 값과 조건 키는 합성 입력이다. `RunInstances` 검사는 이미지 자원 단위이며 전체 EC2 생성 요청, 서비스별 추가 인가, bucket policy/SCP, 실제 MFA 세션 및 전파 상태의 성공을 뜻하지 않는다. 검사 0건인 CI를 PASS로 표시하지 않는다.

비공개 원본은 고정 공유 경로에 보존한다. 공개 Plan/state/credential 원본을 첨부하지 않는다.

| 원본 | SHA256 |
|---|---|
| `phase2-access-preflight-20261016T052853Z.tgz` | `1dafd0150af270655ae9c962970c0d47945f2a3d93311a85727bd537548bbf84` |
| `phase2-access-apply-20261016T053221Z.tgz` | `106c4213eba64675a2cf28ea3ed994b16f680670cacdd2000e9fe7af8927bfb7` |
| `phase2-access-postcheck-20261016T053304Z.tgz` | `df5268e33df77b7fe531f06c3bfab77528faec049170410b88c0d6040b789d38` |

세 원본은 작성 측 CloudShell 출력 해시와 로컬 수신 후 해시가 일치하며 각각 83/6/83개 파일 내용을 검토했다. 사후 검사에서 정책 문법 검증은 사전 결과를 재사용했고, 77개 시뮬레이션 요청만 실제 부착 정책을 대상으로 새로 실행했다. SHA256는 무결성 확인값이며 시험 성공/AC 충족의 증명이 아니다.

## 사용·정리·재검증

- 하영: 본인 MFA→기존 IaC 역할, exact probe profile/state/AMI만 사용. 실제 Plan/Apply는 #35/#37의 별도 창·대상 가드를 충족해야 한다.
- 재환·권욱: 본인 MFA→기존 Network 역할. 실제 승인 회차에 생성된 probe의 실제 ID와 태그를 확인하고 접속·거부 시험을 한다. 기존 충분한 Relay 시험 전체 반복을 요구하지 않는다.
- 검증 권한은 준비·재시험·반출·검토 완료까지 유지한다. 완료 후 보충 정책과 미사용 probe identity를 정리하되 실제 사용/의존성 확인 없이 삭제하지 않는다. state 객체는 보존한다.
- 이상 시 이번 추가 정책부터 분리하고 영향·사용 중인 probe를 확인한다. 기존 IAM 정책/role trust 및 Phase1 설정을 변경하여 우회하지 않는다.
- Phase1 DB/pg_hba/영구 방화벽/NetworkManager/route/Harbor CA/공용 OCP/Runner/DNS/LB/AC 변경 없음. ROSA Create GO·VPN 단계B·DB runtime·정본 발행/티켓 종결과 분리한다.
