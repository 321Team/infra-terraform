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
- No AWS resource blocks are present in this scaffold.
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

The exact S3 bucket and component state keys remain Stage-A inputs. Do not collapse these boundaries into one authoritative `p2-iac/terraform.tfstate` key.

## Safe static validation

```bash
terraform fmt -check -recursive
terraform init -backend=false -lockfile=readonly
terraform validate
```

Static validation is not a reviewed plan, apply, runtime acceptance, or G4 evidence. Do not run `apply` from this scaffold until #35 execution gates and independent review are satisfied.
