# rosa-runtime — ROSA HCP 클러스터 생성 (infra-rosa#4)

상태: **LOCAL CANDIDATE / Plan·Apply 승인 없음.** `execution_enabled=false`가 기본값이라 실제 생성 계획이 만들어지지 않는다.
**이 root의 apply는 유료 자원을 만든다.** ROSA Cost GO와 Create GO 없이 실행하지 않는다(현재 둘 다 미발행).

## 이 코드가 만드는 것

| 자원 | 값 | 근거 |
|---|---|---|
| `rhcs_cluster_rosa_hcp.this` | HCP, `ap-northeast-2`, 1 AZ(`ap-northeast-2a`), `private = !public_cluster` — **API 공개 여부만** 정한다(rhcs v1.7.9 `SetAPIPrivacy`) | infra-rosa#3, #4 |
| `rhcs_hcp_default_ingress.default` | 클러스터가 이미 가진 기본 Ingress의 `listening_method`를 `external`(public) / `internal`(private)로 고정. **LB를 새로 만들지 않는다** | infra-rosa#4 결정 [6120548351](https://github.com/321Team/infra-rosa/issues/4#issuecomment-6120548351) §3, rhcs `resources/hcp_default_ingress.md` |
| 초기 worker pool | m5.xlarge × 3, autoscaling off, 300 GiB, IMDSv2 required | infra-rosa#3 |
| `rhcs_hcp_machine_pool.workers` | 기본 pool `workers`를 apply 때 가져와(magic import) 관리. `max_surge=1`, `max_unavailable=0` | rhcs `guides/worker-machine-pool.md`, infra-rosa#4 C1(최대 4대) |
| registry trust | `registry_config.additional_trusted_ca` = Harbor CA JSON (key `10.1.93.54`·`harbor.fds.internal`) | infra-rosa#11 출력 4 |
| 네트워크 | machine `10.20.0.0/16`, pod `10.128.0.0/14`, service `172.30.0.0/16`, host prefix 23 | OpenShift 기본값을 명시 |
| subnet | public/public: `[public_transport_a, private_a]`, private/private: `[private_a]` | AWS ROSA HCP 시작하기 |

ROSA가 우리 계정에 함께 만드는 것(예상, 생성 후 readback으로 확정): API PrivateLink VPC endpoint 1, 기본 Ingress NLB 1(public이면 internet-facing), SG·ENI, 그리고 확인되지 않은 Route 53 private hosted zone·image registry S3. 목록은 infra-rosa#4 [6119537859](https://github.com/321Team/infra-rosa/issues/4#issuecomment-6119537859) A1을 따른다.

**만들지 않는 것:** VPC·subnet·태그(network), account/operator role·OIDC(rosa-prereq), IdP·RBAC·namespace(infra-rosa#5), Harbor pull 경로(#35·#37·P1-HBR-01), admin user(`create_admin_user=false`).

## 생성 전에 멈추는 조건 (precondition)

- `execution_enabled`가 false이거나 workspace가 `default`가 아님
- 호출 계정이 `774055931866`이 아님
- 실제 subnet의 VPC·CIDR·AZ·자동 공인 IP가 network handoff와 다름
- `private_a`에 `kubernetes.io/role/internal-elb=1`이 없음 / public이면 `public_transport_a`에 `kubernetes.io/role/elb=1`이 없음 → network 태그 변경([infra-terraform#27](https://github.com/321Team/infra-terraform/pull/27))을 먼저 적용
- public이면 `public_transport_a`의 남은 IP가 `min_free_transport_ips`(기본 16) 미만
- 변수 검증: CA JSON의 SHA256·key·PEM 형식 불일치, rosa-prereq stage 2 전 handoff(`operator_role_prefix` 없음), 정확한 `4.y.z`가 아닌 버전

## 입력

`terraform.tfvars.example` 참조. 채운 파일은 커밋하지 않는다.

| 변수 | 기본값 | 설명 |
|---|---|---|
| `execution_enabled` | `false` | 승인된 Plan 수집·Apply 단계에서만 `true`. 승인의 증거가 아니다 |
| `cluster_name` | 없음 | 생성 후 변경 불가 |
| `openshift_version` | 없음 | #34 Freeze 값. Plan 전에 `rosa list versions --hosted-cp`로 확인 |
| `public_cluster` | 없음 | `true` = public API + external Ingress (승인된 방식). `false`(private/private)는 시험용 분기이며 선택·GO가 아니다 |
| `registry_trust` | 없음 (`null` 허용) | Harbor CA JSON 경로와 기대 SHA256 `4d86507e…1da4`. D22가 사설 CA가 필요 없는 registry를 고르면 `null` |
| `network_handoff` | 없음 | network root output |
| `rosa_prereq_handoff` | 없음 | rosa-prereq stage 2 readback 후 output |
| `delete_protection` | `true` | teardown 창에서 false로 apply한 뒤 destroy |
| `min_free_transport_ips` | `16` | public LB용 여유 IP 하한 |

Red Hat 인증은 환경변수(`RHCS_CLIENT_ID`/`RHCS_CLIENT_SECRET` 또는 `RHCS_TOKEN`)로만 넣는다.

## 실행 순서

`execution_enabled=true`는 승인된 단계에서 Plan·Apply를 가능하게 하는 입력일 뿐이다. 그 값을 켰다는 사실이 승인의 증거가 되지 않는다.

**A. 선행 확인 (조회만)**
1. 실제 선행조건 readback: network 태그 apply·readback([#27](https://github.com/321Team/infra-terraform/pull/27)), rosa-prereq stage 1·2 readback, Red Hat 로그인·조직 연결(계정 준비 기록). G4·ROSA Freeze·중앙 비용 판단의 현재 상태를 기록한다
2. CA JSON 추출: `git show 70bdb92:evidence/DEC-P2-REG-01/infra-rosa-issue-11-registry-ca-json-20261008/rosa-hcp-registry-additional-trusted-ca.json > <path>` → `sha256sum`이 `4d86507e…1da4`인지 확인

**B. saved Plan 수집 (Plan 수집이 허용된 범위에서, 생성 없음)**

3. `terraform init -backend-config=backend.hcl` (state `phase2/rosa-runtime/terraform.tfstate`, workspace `default`)
4. `execution_enabled=true`로 `terraform plan -var-file=<비공개>.tfvars -out=create.plan`, `terraform show -json create.plan > create.plan.json`
   - 기대: **create 3** (`rhcs_cluster_rosa_hcp.this`, `rhcs_hcp_machine_pool.workers`, `rhcs_hcp_default_ingress.default`), update·delete 0
   - create 3은 AWS 자원 3개라는 뜻이 아니다. 클러스터가 간접으로 만드는 노드·EBS·NLB·endpoint는 생성 후 실제 ID로 따로 센다. pool은 기본 pool을 가져오는 것이고, ingress는 기본 Ingress 설정을 바꾸는 것이다
   - Plan에서 `private = false`, `listening_method = "external"`, 위 표의 값을 확인한다. 다르면 STOP

**C. 검토와 Apply (유료)**

5. 아래 "생성 승인본에 연결할 것"을 붙여 saved Plan 독립 검토 → 별도 Apply GO
6. `terraform apply create.plan` — **검토된 그 Plan 파일만** 적용한다. state·source·입력이 바뀌어 Plan이 달라졌으면 옛 Plan을 대신 쓰지 않는다. 바뀐 부분의 영향만 다시 검토받고 새 Plan을 쓴다
7. readback: `rosa describe cluster`(API listening), `rosa list ingress -c <cluster>`(기본 Ingress 1개, external), `rosa list machinepools`·`rosa describe machinepool workers`(3대, surge 1 / unavailable 0), `oc get nodes -o wide`, 예상 자원 실측(infra-rosa#4 A1 — 기본 NLB 1 외 **추가 LB 없음** 확인). 결과는 infra-rosa#4 Ready 확인과 Basic Ready Handoff에 연결

### 생성 승인본에 연결할 것

| 구분 | 항목 |
|---|---|
| source | 저장소 commit SHA, `rosa-runtime` 디렉터리 파일 해시, `.terraform.lock.hcl` 해시 |
| 입력 | 비공개 tfvars의 SHA256(값은 올리지 않음), CA JSON SHA256 `4d86507e…1da4`, `min_free_transport_ips = 16`(낮추지 않음) |
| state | backend key `phase2/rosa-runtime/terraform.tfstate`, workspace `default`, state lineage·serial |
| Plan | `create.plan`과 `create.plan.json`의 SHA256, `terraform plan` 명령·RC |
| 도구 | Terraform `1.16.4`, aws `6.66.0`, rhcs `1.7.9`, ROSA CLI 버전 |

## 삭제

infra-rosa#8 v3.1 단계별 가드를 따른다: namespace 삭제 receipt → `delete_protection=false` apply → `terraform destroy` → 클러스터 소유 자원 ID별 `DELETED` 확인. IAM role·OIDC·network는 이 root가 지우지 않는다(`RETAINED_SHARED_APPROVED`).

기본 pool은 클러스터의 마지막 pool이라 destroy 때 Terraform 기록에서만 빠지고, 실제로는 클러스터 삭제와 함께 정리된다(rhcs guide).
`rhcs_hcp_default_ingress`도 destroy 때 기본 Ingress를 지우지 않는다. 경고("Cannot delete default ingress")를 내고 기록에서만 빠지며, 기본 Ingress와 그 NLB는 클러스터 삭제와 함께 정리된다(rhcs v1.7.9 `provider/defaultingress/hcp/resource.go` Delete). 삭제 후 NLB ID가 `DELETED`인지 #8 inventory로 확인한다.

## 로컬 검사 (비용 없음)

```bash
terraform init -backend=false
terraform validate
terraform test
```

`terraform test`는 mock provider만 쓴다. AWS·Red Hat 런타임 증적이 아니다. 시험용 CA JSON(`tests/fixtures/registry-ca.mock.json`)은 인증서가 아닌 가짜 값이다.

## 확인되지 않은 것 (UNVERIFIED)

- Route 53 private hosted zone·image registry S3 생성 여부 → 생성 후 readback
- 실제 적용 결과(API listening, 기본 Ingress external, pool 3대·surge 1/unavailable 0) → 소스 경로는 리뷰에서 확인했으나 첫 apply 후 readback으로 확정한다. magic import의 management 반영 경로는 rhcs v1.7.9 `machine_pool_resource.go`(readState→doUpdate)로 확인됨(PR #29 리뷰)
- HCP 최소 worker 수 → 이권욱 리뷰에서 Red Hat 구조 문서의 최소 EC2 footprint 2대로 보완. 이 코드는 3대 고정
