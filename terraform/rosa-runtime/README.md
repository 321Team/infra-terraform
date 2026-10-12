# rosa-runtime — ROSA HCP 클러스터 생성 (infra-rosa#4)

상태: **LOCAL CANDIDATE / Plan·Apply 승인 없음.** `execution_enabled=false`가 기본값이라 실제 생성 계획이 만들어지지 않는다.
**이 root의 apply는 유료 자원을 만든다.** ROSA Cost GO와 Create GO 없이 실행하지 않는다(현재 둘 다 미발행).

## 이 코드가 만드는 것

| 자원 | 값 | 근거 |
|---|---|---|
| `rhcs_cluster_rosa_hcp.this` | HCP, `ap-northeast-2`, 1 AZ(`ap-northeast-2a`), `private = !public_cluster` | infra-rosa#3, #4 |
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
| `execution_enabled` | `false` | Create GO 작업창에서만 `true` |
| `cluster_name` | 없음 | 생성 후 변경 불가 |
| `openshift_version` | 없음 | #34 Freeze 값. Plan 전에 `rosa list versions --hosted-cp`로 확인 |
| `public_cluster` | 없음 | public/public 제안. 최종 선택은 이권욱 리뷰 |
| `registry_trust` | 없음 (`null` 허용) | Harbor CA JSON 경로와 기대 SHA256 `4d86507e…1da4`. D22가 사설 CA가 필요 없는 registry를 고르면 `null` |
| `network_handoff` | 없음 | network root output |
| `rosa_prereq_handoff` | 없음 | rosa-prereq stage 2 readback 후 output |
| `delete_protection` | `true` | teardown 창에서 false로 apply한 뒤 destroy |
| `min_free_transport_ips` | `16` | public LB용 여유 IP 하한 |

Red Hat 인증은 환경변수(`RHCS_CLIENT_ID`/`RHCS_CLIENT_SECRET` 또는 `RHCS_TOKEN`)로만 넣는다.

## 실행 순서 (모든 Gate 충족 후)

1. 선행 확인: network 태그 apply·readback, rosa-prereq stage 1·2 readback, G4·Freeze·ROSA Cost GO·Create GO 기록
2. CA JSON 추출: `git show 70bdb92:evidence/DEC-P2-REG-01/infra-rosa-issue-11-registry-ca-json-20261008/rosa-hcp-registry-additional-trusted-ca.json > <path>` → `sha256sum`이 `4d86507e…1da4`인지 확인
3. `terraform init -backend-config=backend.hcl` (state `phase2/rosa-runtime/terraform.tfstate`)
4. `terraform plan -var-file=<비공개>.tfvars -out=create.plan` → 기대: **create 2** (`rhcs_cluster_rosa_hcp.this`, `rhcs_hcp_machine_pool.workers`), update·delete 0. 값이 위 표와 다르면 STOP
5. 독립 리뷰 → 별도 Apply GO → `terraform apply create.plan` (유료, 클러스터 Ready까지 대기)
6. readback: `rosa describe cluster`, `rosa list machinepools`, `oc get nodes -o wide`, 예상 자원 실측(infra-rosa#4 A1). 결과는 infra-rosa#4 Ready 확인과 Basic Ready Handoff에 연결

## 삭제

infra-rosa#8 v3.1 단계별 가드를 따른다: namespace 삭제 receipt → `delete_protection=false` apply → `terraform destroy` → 클러스터 소유 자원 ID별 `DELETED` 확인. IAM role·OIDC·network는 이 root가 지우지 않는다(`RETAINED_SHARED_APPROVED`).

기본 pool은 클러스터의 마지막 pool이라 destroy 때 Terraform 기록에서만 빠지고, 실제로는 클러스터 삭제와 함께 정리된다(rhcs guide).

## 로컬 검사 (비용 없음)

```bash
terraform init -backend=false
terraform validate
terraform test
```

`terraform test`는 mock provider만 쓴다. AWS·Red Hat 런타임 증적이 아니다. 시험용 CA JSON(`tests/fixtures/registry-ca.mock.json`)은 인증서가 아닌 가짜 값이다.

## 확인되지 않은 것 (UNVERIFIED)

- magic import가 `management`(max_surge/max_unavailable)를 기본 pool에 그대로 적용하는지 → 첫 apply 후 `rosa describe machinepool`로 확인
- HCP에서 API·Ingress 공개 범위를 서로 다르게 지정할 수 있는지 → 이 코드는 `private` 하나로 함께 바꾼다
- Route 53 private hosted zone·image registry S3 생성 여부 → 생성 후 readback
- HCP 최소 worker 수 → 이권욱 리뷰에서 Red Hat 구조 문서의 최소 EC2 footprint 2대로 보완. 이 코드는 3대 고정
