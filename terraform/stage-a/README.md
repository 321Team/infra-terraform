# P2-IAC-01 Stage-A Terraform Scaffold

This directory is the topology-independent Stage-A scaffold for AWS/ROSA provisioning.

## Current boundary

- Region: `ap-northeast-2`
- Project VPC CIDR: `10.20.0.0/16`
- Terraform: `1.16.4`
- AWS provider: `6.66.0`
- S3 backend locking: native `.tflock` via `use_lockfile = true`
- No AWS resource blocks are present in this scaffold.
- Subnet/AZ mapping and VPN attachment type have no accepted production default.
- `terraform plan` must not be treated as approved until those inputs and the backend identity are fixed.

## Safe static validation

```bash
terraform fmt -check -recursive
terraform init -backend=false
terraform validate
```

Do not run `apply` from this scaffold.
