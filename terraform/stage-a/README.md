# P2-IAC-01 Stage-A Terraform Scaffold

This directory is the topology-independent Stage-A contract scaffold for AWS/ROSA provisioning.

## Current authority

- D21 decision: `OCI Primary = NO-GO (project suitability)`
- Selected Transport Adapter: `aws_ec2_eip_relay`
- Region: `ap-northeast-2`
- Project VPC CIDR: `10.20.0.0/16`
- Terraform: `1.16.4`
- AWS provider: `6.66.0`
- S3 backend locking: native `.tflock` via `use_lockfile = true`
- No managed AWS resource blocks are present in this scaffold; one read-only bootstrap profile data source is proposed.
- The Stage-A contract consumes the Architecture Freeze values from baseline issues #34/#36.
- Managed AWS VPN attachment (`vgw|tgw`) is not part of the selected D21 path.

## Frozen subnet / relay contract

- `private_a`: `10.20.10.0/24` / `ap-northeast-2a` / `apne2-az1`
- `private_b`: `10.20.20.0/24` / `ap-northeast-2b` / `apne2-az2`
- `private_c`: `10.20.30.0/24` / `ap-northeast-2c` / `apne2-az3`
- `public_transport_a`: `10.20.110.0/24` / `ap-northeast-2a` / `apne2-az1`
- Relay private IP: `10.20.110.10`
- Relay instance: `t3.medium`
- Relay AMI: `ami-079a2667364cee804` / owner `125523088429`
- Root: `gp3 40 GiB`, encrypted
- EIP: required; auto public IPv4 disabled
- ENI source/destination check: disabled
- Public SSH: disabled; management uses SSM/bootstrap
- IKE ingress: UDP/500 and UDP/4500 only; dynamic peer source cannot depend on one observed /32
- Protected selectors: `10.1.93.0/24 <-> 10.20.0.0/16`

## State boundary

The approved logical state boundaries are:

- `network`
- `vpn`
- `rosa-prereq`
- `rosa-runtime`

The exact bucket and keys were adopted by #35 Lead in [6015740112](https://github.com/321Team/fds-project-baseline/issues/35#issuecomment-6015740112). The bucket/profile configuration readback was received in [6031865288](https://github.com/321Team/fds-project-baseline/issues/35#issuecomment-6031865288), reviewed in [6032041833](https://github.com/321Team/fds-project-baseline/issues/35#issuecomment-6032041833). This is user-reported AWS output, not an independent review of the raw captures.

| Boundary | Approved key | Backend example | Implemented component root |
|---|---|---|---|
| network | `phase2/network/terraform.tfstate` | [network](../backends/network.hcl.example) | PENDING |
| vpn | `phase2/vpn/terraform.tfstate` | [vpn](../backends/vpn.hcl.example) | PENDING |
| rosa-prereq | `phase2/rosa-prereq/terraform.tfstate` | [rosa-prereq](../backends/rosa-prereq.hcl.example) | PENDING |
| rosa-runtime | `phase2/rosa-runtime/terraform.tfstate` | [rosa-runtime](../backends/rosa-runtime.hcl.example) | PENDING |

The four files preserve the exact adopted backend HCL bytes from baseline merge `40ac664b83485745ab86b5018b8e19c386484cc8`, under `phase2/permissions/20261006-iac-fixed-inputs/backends/`. The provider and backend each restrict the approved account. State encryption remains SSE-S3/AES256 and locking remains native S3.

These files are inputs for four **separate future component roots**, each with one resource owner and isolated workdir/TF_DATA_DIR. They are not four execution variants of this scaffold. The old generic `backend.hcl.example` is removed to avoid that ambiguity. Do not initialize a remote backend, migrate state, or run plan/apply from this contract scaffold. Keep the default workspace. Component roots, cross-component outputs and resource ownership must be reviewed with the implementation source before remote initialization; names/keys alone do not authorize a write.

## Existing bootstrap ownership and reference

#35 Lead adopted CloudFormation ownership of exactly StateBucket, StateBucketPolicy, Relay role and Relay instance profile in [6031301706](https://github.com/321Team/fds-project-baseline/issues/35#issuecomment-6031301706). Terraform must not create/import/adopt/delete those resources.

`bootstrap-references.tf` reads `FDS-Relay-SSM` with `aws_iam_instance_profile`. A precondition rejects non-default workspaces. Postconditions compare the exact profile and role ARNs to the approved identities and fail on a missing/mismatched role. A data read is not a check of the trust policy, Agent policy, bucket protection, Agent Online, EBS, session document or human permissions. Reuse the accepted bootstrap setting receipt for that configuration checkpoint; reassess changed source/settings before subsequent runtime.

The future VPN implementation can consume the profile name after moving this reference into its reviewed component root. No EC2 or ENI reference is invented here. `stage_a_contract.stage_a_ready` remains `false`.

## API and permissions handoff

| Source path | AWS operation | Candidate role requirement | Current scope |
|---|---|---|---|
| `bootstrap-references.tf` | IAM GetInstanceProfile | `iam:GetInstanceProfile` on the exact Relay instance-profile ARN | Read only; not granted |
| Provider/backend identity validation | STS GetCallerIdentity | Existing authentication/account validation; no new role policy is attached | No AWS calls in this PR task |
| Future component backend | S3 state and `.tflock` operations | Existing approved backend partial policy, with exact key separation | Init/lock/runtime not tested |
| Future network/VPN resources | Not implemented | API/dependent-action inventory and complete permissions JSON required with actual source | PENDING |

The IAM row is grounded in AWS provider `v6.66.0` [data source](https://github.com/hashicorp/terraform-provider-aws/blob/v6.66.0/internal/service/iam/instance_profile_data_source.go) and [lookup function](https://github.com/hashicorp/terraform-provider-aws/blob/v6.66.0/internal/service/iam/instance_profile.go), and AWS [IAM authorization reference](https://docs.aws.amazon.com/ko_kr/service-authorization/latest/reference/list_awsidentityandaccessmanagementiam.html). This read requirement must be composed into the complete reviewed IaC permissions. It is not a standalone grant recommendation or a completed policy.

The network/VPN implementation and its complete permissions may advance independently of future ROSA modules, within the existing Stage-A gates. Execution Lead remains 이하영; central support remains 이권욱. Role grant/readback and each user's MFA AssumeRole/runtime follow source/policy review. Root is not the daily Terraform operator. Actual Relay/Agent/session-document/EBS IDs and exact Network binding/#37 U1 remain later handoffs.

## Safe static validation

```bash
terraform fmt -check -recursive
terraform init -backend=false -lockfile=readonly
terraform validate
```

Static validation is not a reviewed plan, apply, runtime acceptance, or G4 evidence. Do not run `apply` from this scaffold until #35 execution gates and independent review are satisfied.

## Preparation validation and stop/recovery

This is a code/configuration change, requiring an independent reviewer and #35 Lead merge judgment. This task has not run Terraform fmt/init/validate, AWS plan/apply, role grant or runtime. It does not change Phase 1 specifications, existing AC/ownership/schedule, architecture Freeze or cost controls.

Static validation uses the pinned Terraform 1.16.4 and provider 6.66.0 above, from this directory, without AWS credentials or a remote backend. Preserve the approved lock file and stop if init would change it. Inspect the exit codes and source SHA; do not report a failed/unrun command as PASS. Formatting/validation do not satisfy runtime acceptance.

Before merge, the reviewer checks provider/backend account restriction, all four backend bytes/keys, no bootstrap resource ownership, exact profile/role postcondition, default-workspace guard, source API map and remaining execution gates. Revert or close this unapplied preparation PR to recover; no AWS resource cleanup is needed. Do not rerun the completed bootstrap create, 14 tests or 46/9 simulation solely because this draft exists.

AI assistance: CODEX_ASSISTED.
