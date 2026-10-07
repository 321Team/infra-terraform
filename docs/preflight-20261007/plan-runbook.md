# Terraform Plan 준비 / 아직 실행하지 않음

CODEX_ASSISTED. 대상 source `0eabe8daa75a6b9bf960fe1ea5eeaf6a8818f216`(PR5 reviewed head ae39cc6a 병합). 아래는 #35 Lead가 조건 충족 후 사용할 절차다. **현재 IAM/실행 입력 Gate가 미충족이므로 명령을 실행하지 않았다.** 이 문서의 승인이 Apply GO를 대신하지 않는다.

## 대상·권한·선행조건

- 대상: AWS 채택 계정 끝1866 / `ap-northeast-2`, CloudShell 개인 작업 경로의 깨끗한 고정 checkout. 기존 중앙 CFn bootstrap은 소유권 유지.
- 실행자: 이하영 또는 이권욱 **각 본인 MFA FDS-IaC-Operator 세션**. root·일반 IAM 사용자·다른 역할로 업무 Plan/Apply 우회 금지. STS ARN의 role/session name을 기존 배정과 대조하되 ARN만으로 MFA를 입증했다고 표시하지 않는다.
- toolchain: Terraform1.16.4 / AWS provider6.66.0, reviewed lock. 기존 검증과 source15파일 동일성 확인. provider 바이너리 공간은 CloudShell `/tmp`의 별도 TF_DATA_DIR 사용, 소스·로그·plan은 HOME 개인0700 경로에 보존. version/registry/lock을 임의 변경하지 않는다.
- 권한: full policy source 검토·중앙 grant/readback 및 본인 state/lock·거부·복구 시험. credential은 환경의 기존 역할 세션으로만 사용하며 파일·backend-config·plan 변수에 저장하지 않는다.
- Plan 전에 정확한 SHA·backend key·default workspace·명시 입력·source/정책 수용 근거를 기록. 기존 Freeze/비용 조건의 적용 범위를 #35/#34에서 판단하며 미충족한 상태를 Apply 허용으로 확장하지 않는다.

## 1. network Plan

`terraform/stage-a` scaffold에서 remote plan을 하지 않는다. 실제 root는 `terraform/network`이며 backend는 `phase2/network/terraform.tfstate`. network에는 EIP/EC2/NAT/ROSA가 없다. `execution_enabled=false` 기본값은 실제 plan도 차단하므로, 아래 `true`는 **조건을 충족한 plan 회차만의 명시 입력**이다. 승인 증거가 아니다.

CloudShell에서 고정 checkout 절대경로를 `FDS_REPO`, 위 버전의 실제 terraform 절대경로를 `FDS_TF`, 새 HOME 개인 증거 디렉터리를 `FDS_CAPTURE`로 설정한다. 아래 명령은 각 stdout/stderr/RC를 별도 파일로 보존하고 오류 시 다음 명령을 실행하지 않는다. `set -x`를 쓰지 않는다.

```bash
aws sts get-caller-identity --region ap-northeast-2 --output json --no-cli-pager
git -C "$FDS_REPO" rev-parse HEAD
git -C "$FDS_REPO" status --porcelain --untracked-files=all
"$FDS_TF" version -json
umask 077
export TF_DATA_DIR="$(mktemp -d /tmp/fds-network-plan-data-XXXXXX)"
"$FDS_TF" -chdir="$FDS_REPO/terraform/network" init -input=false -lockfile=readonly -backend-config=backend.hcl.example
"$FDS_TF" -chdir="$FDS_REPO/terraform/network" workspace show
"$FDS_TF" -chdir="$FDS_REPO/terraform/network" validate -json
"$FDS_TF" -chdir="$FDS_REPO/terraform/network" plan -input=false -lock-timeout=60s -detailed-exitcode -var=execution_enabled=true -out="$FDS_CAPTURE/network.tfplan"
```

실행 전에 상속된 `TF_CLI_ARGS*`/`TF_VAR_*`, `.auto.tfvars`/`terraform.tfvars`, terraformrc/plugin override 등에 미검토 값이 없는지 확인한다. 값은 로그에 덤프하지 않고 키/파일 존재와 승인 여부를 확인한다. untracked 예상 밖 파일이면 STOP. 기존 backend 재구성/이전 요청이 나오면 STOP하고 `-migrate-state`, `-force-copy`, `-lock=false`로 우회하지 않는다.

Plan RC0=변경 없음 / RC2=차이 있음(검토 대상) / RC1=실패. 새 빈 state의 최초 network plan 기대값은 **15 create / 0 update / 0 delete**, data read 제외. 기존 state/자원이 있으면 15를 강제로 맞추지 않고 소유·drift부터 검토한다. 삭제/교체·중앙 bucket/role/profile·default VPC 변경·예상 밖 태그/route이면 STOP. `terraform show -no-color`와 필요시 `show -json`은 개인 경로로만 보존하고 state/plan 전체를 GitHub에 게시하지 않는다.

## 2. network Apply와 실제 handoff 사이의 경계

network Apply는 이 문서에 실행 명령을 넣지 않았다. **#34 Freeze·기존 비용 한도/자부담0·실행창·saved plan 검토·권한/복구 조건**을 충족한 별도 판단이 필요하다. Apply가 수행된 뒤 `terraform output -json network_handoff`의 비밀 없는 값만 #35가 검증·인계한다. network source에 subnet4개가 있다는 사실이 ROSA 3AZ 결정을 뜻하지 않는다.

## 3. vpn Plan의 필수 입력

vpn은 live `aws_vpc`/`aws_subnet` data를 조회한다. **network Apply 전 합성 ID로 cloud vpn plan을 성공시킬 수 없다.** mock fixture를 actual handoff로 사용하지 않는다.

| 입력 | 현재 준비상태 |
|---|---|
| network_handoff | PENDING: 실제 network 생성·검증 후 |
| root_delete_on_termination | PENDING: EBS 보존/삭제·잔존 비용·복구 판단 |
| cpu_credit_mode | PENDING: standard/unlimited 비용·성능 판단 |
| libreswan_package_spec | PENDING: exact AMI repo의 version-release 및 검증 |
| relay_egress + egress_contract_reference | TCP443 후보/#37 원본 수신, AMI repo 확인 후 최종 수용 |
| execution_enabled | 현재 default false. Gate 통과한 plan 회차만 true |
| activate_onprem_routes / onprem_route_keys | 초기 생성은 **false / []** |
| create_session_document | 초기 기본 false. 실제 부재/소유 수용 없는 생성·import 금지 |

현재 live tfvars는 생성하지 않았다. 모든 입력 확정 뒤 승인된 개인 `vpn.plan.tfvars.json`을 준비/해시하고 별도 TF_DATA_DIR에서 vpn backend(`phase2/vpn/terraform.tfstate`)로 같은 init/workspace/validate/plan 절차를 실행한다. `plan -var-file=... -out=... -detailed-exitcode`를 사용하며 `-target`, `-refresh=false`, lock 우회를 하지 않는다. TCP443 egress 1개·문서/route OFF의 최초 빈 vpn state는 **7 create**가 예상되지만 실제 입력·state에 따라 saved plan 전체를 검토해야 한다.

## 4. route 활성화와 증적·복구

Relay 생성 후 #37 Agent/본인 세션·XFRM/SA·host FORWARD·양단 반환·source·승인/거부·SA-down 차단·복구를 검증한다. inner SG 구현/리뷰, 정확 route-table association, source/NetworkPolicy/DB 계약 수용 후 **별도 route plan**. 문자열 readiness reference만으로 PASS 판정하지 않는다. tunnel runtime 측정에 필요한 임시 시험 경로는 별도 승인/복구 범위에서 준비하며 영구 route 선활성화로 해결하지 않는다.

매 회차 증적: host/계정·본인 session/UTC·KST, source·policy·input hash, backend/workspace/toolchain/lock, 각 명령/RC/timeout/원본, saved plan SHA256, 검토 대상 SHA·수용 범위, 실행 이후 actual ID·readback. SHA256은 무결성이고 시험 성공은 별도 결과다.

Plan 실패 시 원본 보존·원인 수정 후 새 회차. live writer·lock ID·실행 상태 확인 없이 force-unlock하지 않는다. Apply 부분 실패 시 일괄 destroy하지 않고 실제 before/state/생성 자원을 대조한다. 중앙 CFn/보존 EBS/EIP/account 문서의 소유를 유지하고 승인한 대상만 복구한다. source/input/state 변경 또는 plan 유효성 상실 시 기존 saved plan 재사용 금지.

## 10-08 입력 해석 보완

Session document의 무로그/무KMS/RunAs 없음 방향은 이미 #37에서 결정됐다. 실제 소유/부재 및 생성 Gate 수용 후 create_session_document=true이면 TCP443 1개·route OFF의 빈 vpn state 예상치는8create이며, 문서OFF일 때7create다. [기존 결정과 본인 시험](gwonuk-u1-plan.md)을 따른다. 아직 live tfvars/Plan을 실행하지 않았으며 이 예상 개수로 saved plan 검토를 대체하지 않는다.
