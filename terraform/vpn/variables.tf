variable "execution_enabled" {
  type        = bool
  default     = false
  description = "Local guard only. Does not grant approval, role access, cost GO or Freeze."
}

variable "network_handoff" {
  description = "Non-secret output from the exact reviewed network root; never copy state payload."
  type = object({
    region   = string
    vpc_id   = string
    vpc_cidr = string
    subnets = map(object({
      id             = string
      cidr           = string
      zone_id        = string
      route_table_id = string
    }))
  })
  validation {
    condition = try(
      var.network_handoff.region == "ap-northeast-2" &&
      var.network_handoff.vpc_cidr == "10.20.0.0/16" &&
      length(var.network_handoff.subnets) == 4 &&
      var.network_handoff.subnets.public_transport_a.cidr == "10.20.110.0/24" &&
      var.network_handoff.subnets.public_transport_a.zone_id == "apne2-az1" &&
      var.network_handoff.subnets.private_a.cidr == "10.20.10.0/24" &&
      var.network_handoff.subnets.private_b.cidr == "10.20.20.0/24" &&
      var.network_handoff.subnets.private_c.cidr == "10.20.30.0/24" &&
      length(toset([for s in var.network_handoff.subnets : s.id])) == 4 &&
      length(toset([for s in var.network_handoff.subnets : s.route_table_id])) == 4,
      false
    )
    error_message = "Handoff must match the adopted four-subnet geometry and distinct subnet/route-table identities."
  }
}

variable "root_delete_on_termination" {
  type        = bool
  nullable    = false
  description = "No project default was adopted. Supply only the reviewed deletion/retention choice; test fixtures are not a decision."
}

variable "cpu_credit_mode" {
  type        = string
  nullable    = false
  description = "Explicit standard/unlimited cost and capacity decision; no implicit t3 account default."
  validation {
    condition     = contains(["standard", "unlimited"], var.cpu_credit_mode)
    error_message = "Choose a reviewed CPU credit mode."
  }
}

variable "libreswan_package_spec" {
  type        = string
  nullable    = false
  description = "Exact reviewed Libreswan package version/release available in the approved AMI repositories; no latest fallback."
  validation {
    condition     = can(regex("^libreswan-[0-9][A-Za-z0-9.+:_~]*-[A-Za-z0-9._+~]+$", var.libreswan_package_spec))
    error_message = "Supply an explicit Libreswan version/release package spec without shell metacharacters."
  }
}

variable "relay_egress" {
  type = map(object({
    protocol    = string
    port        = number
    cidr_ipv4   = string
    description = string
  }))
  default     = {}
  description = "Reviewed single-port IPv4 egress tuples. Empty until repository/Agent/IKE needs and scope are accepted."
  validation {
    condition = alltrue([for r in var.relay_egress :
      contains(["tcp", "udp"], r.protocol) && r.port >= 1 && r.port <= 65535 && floor(r.port) == r.port &&
      can(cidrnetmask(r.cidr_ipv4)) && length(trimspace(r.description)) > 0
    ])
    error_message = "Use explicit TCP/UDP single-port IPv4 tuples and a reason; no all-protocol rule."
  }
}

variable "egress_contract_reference" {
  type        = string
  default     = ""
  description = "Traceable review reference for egress. A nonempty value is not proof of approval."
}

variable "activate_onprem_routes" {
  type        = bool
  default     = false
  description = "Separate post-tunnel route activation; do not route workloads to an unready Relay."
}

variable "onprem_route_keys" {
  type        = set(string)
  default     = []
  description = "Reviewed network handoff subnet keys whose route tables receive the On-Prem route."
  validation {
    condition     = alltrue([for k in var.onprem_route_keys : contains(keys(var.network_handoff.subnets), k)])
    error_message = "Route targets must be part of the supplied network handoff."
  }
}

variable "tunnel_readiness_reference" {
  type        = string
  default     = ""
  description = "Actual Agent/SA/firewall/source/return/negative evidence reference required before route activation."
}
