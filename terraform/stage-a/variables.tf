variable "aws_region" {
  description = "AWS/ROSA target Region."
  type        = string
  default     = "ap-northeast-2"

  validation {
    condition     = var.aws_region == "ap-northeast-2"
    error_message = "P2-IAC-01 Stage-A currently fixes the AWS/ROSA Region to ap-northeast-2."
  }
}

variable "vpc_cidr" {
  description = "Project VPC CIDR. Must not overlap On-Prem or OCI Relay networks."
  type        = string
  default     = "10.20.0.0/16"

  validation {
    condition     = var.vpc_cidr == "10.20.0.0/16"
    error_message = "P2-IAC-01 Stage-A currently fixes the project VPC CIDR to 10.20.0.0/16."
  }
}

variable "subnets" {
  description = "Exact Stage-A subnet mapping. No default: Architecture Freeze must supply AZ/CIDR/role."
  type = map(object({
    az   = string
    cidr = string
    role = string
  }))

  validation {
    condition = alltrue([
      for s in values(var.subnets) :
      contains(["public", "private"], s.role)
    ])
    error_message = "Each subnet role must be public or private."
  }
}

variable "vpn_attachment_type" {
  description = "Approved AWS VPN attachment type. Deliberately has no default until Architecture Freeze."
  type        = string

  validation {
    condition     = contains(["vgw", "tgw"], var.vpn_attachment_type)
    error_message = "vpn_attachment_type must be vgw or tgw."
  }
}
