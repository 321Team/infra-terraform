## #12 ROSA 계정 준비 실행 자료 (초안, 하영, 2026-10-09)

대상: [infra-terraform#12](https://github.com/321Team/infra-terraform/issues/12) · 원티켓 #35. 근거: [v3 보완판](https://github.com/321Team/fds-project-baseline/issues/35#issuecomment-6074050926), [이권욱 10-09 v3 수용·실행 자료 요청](https://github.com/321Team/fds-project-baseline/issues/35#issuecomment-6074663186).
이 자료는 실행 승인 요청용이다. **활성화·청구 연결·IAM 부여·생성·초대는 리뷰 승인 전에는 하지 않는다.**

---

### 1. 대체 접근 계정 — 실제 역할·범위·연결 확인 (요청 ①)

v3 §3 ②의 "조회로 접근 검증"을 아래로 대체한다. **조회 성공(`rosa whoami`·`rosa list clusters`)만으로 삭제 권한 PASS로 판정하지 않는다.**

#### 1-1. 계정별 표 (초대 후 기입)

| 팀원 | Red Hat 로그인 | 부여 OCM 역할 이름 | 역할 범위(문서 근거) | user-role 필요 여부 | AWS 쪽 접근 |
|---|---|---|---|---|---|
| 이권욱 | `<마스킹 기입>` | `<초대 화면 실제 이름>` | `<클러스터 조회·삭제 포함 여부, Red Hat 문서 링크>` | §1-2 판단 결과 | 본인 MFA 역할(#9·IaC Grant 경로) |
| 이재환 | `<마스킹 기입>` | 〃 | 〃 | 〃 | 〃 |

- 이메일·전체 로그인 ID는 공개 댓글에 쓰지 않는다. 토큰은 각자 본인 것만 쓴다.
- 역할은 **클러스터 조회·삭제가 가능한 가장 작은 역할**을 고른다. 조직 관리자(Org. Administrator)를 기본으로 주지 않는다. 그 역할로 삭제가 안 되는 것으로 확인되면 사유를 적고 리뷰를 받는다.

#### 1-2. user-role은 필요할 때만

- 대체 계정이 클러스터를 **삭제**하는 데 본인 `user-role`(AWS 역할)과 AWS 계정 연결이 꼭 필요한지 Red Hat 문서로 먼저 확인한다.
- **필요할 때만** `rosa create user-role --prefix fds-rosa --mode manual` 출력을 검토한 뒤 중앙 실행 경로에서 만들고 §2 inventory에 넣는다(rev2: 위임 역할에는 IAM 쓰기가 없다). 필요 없으면 만들지 않는다(AWS 자원·IAM 권한을 늘리지 않음).
- 판단 결과와 근거 문서 링크를 §1-1 표에 적는다.

#### 1-3. 삭제 권한 증명 방법 (실제 삭제 시험 없음)

| 증거 | 내용 |
|---|---|
| 역할 증거 | 조직 User Access 화면의 부여 역할 이름 캡처 + 그 역할에 클러스터 삭제 권한이 있다는 Red Hat 문서 근거 |
| 연결 증거 | 각자 본인 로그인으로 `rosa whoami`(조직 `2042****` 확인), user-role을 만든 경우 `rosa list user-role` Linked 상태 |
| AWS 증거 | rev2에서 AWS IAM 생성·회수(operator role·OIDC provider 등)는 중앙 실행 경로다. 대체 계정은 본인 MFA 역할의 조회 권한으로 readback할 수 있는지만 확인한다 |
| 판정 | 위 3개가 모두 있으면 `ALT_DELETE_CAPABILITY=EVIDENCED(문서·역할 기준)`. 조회만 되면 `ACCESS_ONLY` |

---

### 2. 프로젝트 소유 inventory 기준 정리 (요청 ②)

v3 §3의 "AWS 콘솔 ROSA·EC2 자원 0건"을 **철회**한다. 교육장 계정에는 우리 다른 자원(Harbor·Relay·NAT 등)과 우리 소유가 아닌 자원이 있어 계정 전체 0건은 기준이 될 수 없다. **#12가 만든 자원 목록(inventory)만** 기준으로 정리한다.

#### 2-1. #12 소유 inventory

| 위치 | 자원 | 식별 기준 | 기록 시점 |
|---|---|---|---|
| AWS IAM | account roles(Installer·Support·Worker) | 이름 prefix `fds-rosa` + Terraform state | 생성 직후 ARN 기록 |
| AWS IAM | operator roles | 이름 prefix `fds-rosa` + Terraform state | 〃 |
| AWS IAM | 고객 관리형 정책(생성되는 경우) | 이름 prefix `fds-rosa` + Terraform state | 〃 |
| AWS IAM | OIDC provider | managed OIDC config ID가 들어간 provider ARN + Terraform state | 〃 |
| AWS IAM | `ocm-role`, `user-role`(하영·필요 시 대체 계정) | 이름 prefix `fds-rosa` | CLI 생성 직후 ARN 기록 |
| Red Hat | managed OIDC config | OIDC config ID | 생성 직후 |
| Red Hat | 조직 연결(`ocm-role`·`user-role` link), 청구 연결 | 조직 `2042****` ↔ AWS `774055931866` | 연결 직후 |

- 클러스터 자원(EC2·LB·볼륨 등)은 #4 소유다. #4는 클러스터 ID와 ROSA가 붙이는 클러스터 태그로 자기 inventory를 만들고, #12는 그 결과(클러스터 삭제 완료)만 입력으로 받는다.
- VPC·subnet·NAT·Relay·Harbor 경로는 #35 network/#11 소유로, #12 정리 대상이 아니다.

#### 2-2. 공유 참조 확인 (회수 전)

- `rosa list clusters`(조직 `2042****`)에서 이 account role·OIDC config·operator role을 쓰는 클러스터가 0건
- 다른 티켓이 같은 `fds-rosa` 역할·OIDC config를 참조하지 않음(참조가 있으면 회수 중단·보고)

#### 2-3. 정리 완료 판정

- §2-1 inventory 각 행이 readback에서 **ABSENT**(AWS는 `get-role`·`get-open-id-connect-provider` 등 NoSuchEntity, Red Hat은 `rosa list oidc-config`·`ocm-role`·`user-role`에 없음)
- 청구 연결 해제 여부는 A2 회수 항목으로 별도 판단
- 비용 판단은 #34 교육장 리포트 기준(중앙 통제). 계정 전체 EC2=0은 요구하지 않는다.

---

### 3. 부분 실패 대조 항목 (요청 추가분, v3 §2-1 보완)

부분 실패 시 아래를 **모두** 대조한 뒤 다시 `terraform plan`을 돌린다.

| 대조 대상 | 확인 방법 |
|---|---|
| AWS 실제 자원 | §2-1 AWS 행 readback |
| Terraform 장부 | `terraform state list` |
| 명령 결과 | 명령별 RC·원본 출력 |
| **Red Hat OIDC config** | `rosa list oidc-config` — Terraform이 아는 ID와 같은지, 고아 config가 없는지 |
| **OCM 연결** | `rosa list ocm-role`·`rosa list user-role` Linked 상태, `rosa whoami` 조직 |

---

### 4. 실행 묶음 연결 (요청 ③)

실행 승인 요청 시 아래를 **하나의 묶음**으로 낸다.

| 산출물 | 상태 |
|---|---|
| A1·A3 full policy/trust JSON + 정책 SHA + Action별 한 줄 용도 설명 | rev2 작성(A3는 조회만, IAM 쓰기는 중앙 실행 경로 — README) |
| Terraform `rosa-prereq` source + source commit SHA | 작성(`terraform/rosa-prereq`). commit SHA는 실행 승인 시 고정 |
| `.terraform.lock.hcl`(AWS 6.66.0·rhcs 1.7.9 hash) | 작성(`terraform/rosa-prereq/.terraform.lock.hcl`) |
| 실행 도구(대조·부여) | 별도 PR(브랜치 `tools/rosa-grant-check-12`). 병합 전 실행 안 함 |
| Terraform 1.16.4·ROSA CLI exact 버전·바이너리 SHA-256 | 설치 후 기록 |
| 이 문서(대체 접근·inventory·부분 실패 대조) | 초안 |

---

체크포인트: `ALT_ACCESS=ROLE_EVIDENCE_REQUIRED(NOT_YET_INVITED) / ALT_USER_ROLE=IF_REQUIRED / CLEANUP_BASIS=PROJECT_INVENTORY(account-wide EC2=0 철회) / PARTIAL_FAIL_CHECK=+OIDC_CONFIG,+OCM_LINK / EXEC_BUNDLE=PENDING(JSON·source·lock·CLI pin) / EXECUTION=NOT_RUN`

AWS·Red Hat 쓰기 작업 없음. AC·담당·일정·상태 변경 없음.
