variable "execution_enabled" {
  type        = bool
  default     = false
  description = "Local guard only. Does not grant approval, role access, cost GO or #37 test window."
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
      var.network_handoff.subnets.private_a.zone_id == "apne2-az1" &&
      var.network_handoff.subnets.private_b.cidr == "10.20.20.0/24" &&
      var.network_handoff.subnets.private_c.cidr == "10.20.30.0/24" &&
      length(toset([for s in var.network_handoff.subnets : s.id])) == 4 &&
      length(toset([for s in var.network_handoff.subnets : s.route_table_id])) == 4,
      false
    )
    error_message = "Handoff must match the adopted four-subnet geometry and distinct subnet/route-table identities."
  }
}

variable "probe_window_reference" {
  type        = string
  default     = ""
  description = "#37 test-window evidence: #35 route activation, #34 cost decision and #47 DB pre-window approvals. A reference is not Runtime evidence."
}

variable "probe_expires" {
  type        = string
  nullable    = false
  description = "Deletion deadline written to the Expires tag (KST, YYYY-MM-DDTHH:MM+09:00). Destroy and readback before this time."
  validation {
    condition     = can(regex("^2026-1[0-2]-[0-3][0-9]T[0-2][0-9]:[0-5][0-9]\\+09:00$", var.probe_expires))
    error_message = "Use an explicit KST deadline such as 2026-10-13T23:59+09:00."
  }
}
