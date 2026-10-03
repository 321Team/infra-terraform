variable "aws_region" {
  description = "AWS/ROSA target Region."
  type        = string
  default     = "ap-northeast-2"

  validation {
    condition     = var.aws_region == "ap-northeast-2"
    error_message = "P2-IAC-01 Stage-A fixes the AWS/ROSA Region to ap-northeast-2."
  }
}

variable "vpc_cidr" {
  description = "Project VPC CIDR. Must not overlap On-Prem or OCI PoC networks."
  type        = string
  default     = "10.20.0.0/16"

  validation {
    condition     = var.vpc_cidr == "10.20.0.0/16"
    error_message = "P2-IAC-01 Stage-A fixes the project VPC CIDR to 10.20.0.0/16."
  }
}

variable "transport_adapter_type" {
  description = "D21-selected provider adapter. Provider-specific implementation stays behind this contract."
  type        = string

  validation {
    condition     = var.transport_adapter_type == "aws_ec2_eip_relay"
    error_message = "D21 selected aws_ec2_eip_relay for the P0 Transport Adapter."
  }
}

variable "subnets" {
  description = "Architecture-frozen Stage-A subnet mapping."
  type = map(object({
    az      = string
    zone_id = string
    cidr    = string
    role    = string
  }))

  validation {
    condition = try(
      length(var.subnets) == 4 &&
      var.subnets["private_a"].az == "ap-northeast-2a" &&
      var.subnets["private_a"].zone_id == "apne2-az1" &&
      var.subnets["private_a"].cidr == "10.20.10.0/24" &&
      var.subnets["private_a"].role == "private" &&
      var.subnets["private_b"].az == "ap-northeast-2b" &&
      var.subnets["private_b"].zone_id == "apne2-az2" &&
      var.subnets["private_b"].cidr == "10.20.20.0/24" &&
      var.subnets["private_b"].role == "private" &&
      var.subnets["private_c"].az == "ap-northeast-2c" &&
      var.subnets["private_c"].zone_id == "apne2-az3" &&
      var.subnets["private_c"].cidr == "10.20.30.0/24" &&
      var.subnets["private_c"].role == "private" &&
      var.subnets["public_transport_a"].az == "ap-northeast-2a" &&
      var.subnets["public_transport_a"].zone_id == "apne2-az1" &&
      var.subnets["public_transport_a"].cidr == "10.20.110.0/24" &&
      var.subnets["public_transport_a"].role == "public_transport",
      false
    )
    error_message = "subnets must match the 2026-10-03 Architecture Freeze mapping."
  }
}

variable "relay" {
  description = "D21-selected AWS EC2+EIP Libreswan Relay contract."
  type = object({
    subnet_key            = string
    private_ip            = string
    instance_type         = string
    ami_id                = string
    ami_owner_id          = string
    root_volume_type      = string
    root_volume_gib       = number
    root_volume_encrypted = bool
    allocate_eip          = bool
    auto_public_ipv4      = bool
    source_dest_check     = bool
    public_ssh_enabled    = bool
    ike_ingress_cidrs     = list(string)
    protected_onprem_cidr = string
    protected_aws_cidr    = string
  })

  validation {
    condition = (
      var.relay.subnet_key == "public_transport_a" &&
      var.relay.private_ip == "10.20.110.10" &&
      var.relay.instance_type == "t3.medium" &&
      var.relay.ami_id == "ami-079a2667364cee804" &&
      var.relay.ami_owner_id == "125523088429" &&
      var.relay.root_volume_type == "gp3" &&
      var.relay.root_volume_gib == 40 &&
      var.relay.root_volume_encrypted &&
      var.relay.allocate_eip &&
      !var.relay.auto_public_ipv4 &&
      !var.relay.source_dest_check &&
      !var.relay.public_ssh_enabled &&
      length(var.relay.ike_ingress_cidrs) == 1 &&
      var.relay.ike_ingress_cidrs[0] == "0.0.0.0/0" &&
      var.relay.protected_onprem_cidr == "10.1.93.0/24" &&
      var.relay.protected_aws_cidr == "10.20.0.0/16"
    )
    error_message = "relay must match the D21 2026-10-03 AWS EC2+EIP Relay contract."
  }
}
