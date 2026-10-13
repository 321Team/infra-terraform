# A local safety switch, not evidence of approval or a replacement for infra-rosa#4 gates
# (G4, Freeze, ROSA Cost GO, Create GO and operating window).
variable "execution_enabled" {
  type        = bool
  default     = false
  description = "Keep false outside mock tests. Set true only for an approved saved-Plan collection or Apply step; setting it is not an approval."
}

variable "network_handoff" {
  description = "Non-secret network_handoff output from the exact reviewed network root; never copy state payload."
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
      var.network_handoff.subnets.private_a.cidr == "10.20.10.0/24" &&
      var.network_handoff.subnets.private_a.zone_id == "apne2-az1" &&
      var.network_handoff.subnets.public_transport_a.cidr == "10.20.110.0/24" &&
      var.network_handoff.subnets.public_transport_a.zone_id == "apne2-az1",
      false
    )
    error_message = "Handoff must be the adopted network: private_a 10.20.10.0/24 and public_transport_a 10.20.110.0/24, both apne2-az1."
  }
}

variable "rosa_prereq_handoff" {
  description = "Non-secret rosa_prereq_handoff output after rosa-prereq stage 2 readback. operator_role_prefix must be set."
  type = object({
    account_role_prefix  = string
    installer_role_arn   = string
    support_role_arn     = string
    worker_role_arn      = string
    oidc_config_id       = string
    operator_role_prefix = string
  })
  validation {
    condition = try(
      var.rosa_prereq_handoff.account_role_prefix == "fds-rosa" &&
      var.rosa_prereq_handoff.operator_role_prefix == "fds-rosa" &&
      can(regex("^arn:aws:iam::774055931866:role/fds-rosa-HCP-ROSA-Installer-Role$", var.rosa_prereq_handoff.installer_role_arn)) &&
      can(regex("^arn:aws:iam::774055931866:role/fds-rosa-HCP-ROSA-Support-Role$", var.rosa_prereq_handoff.support_role_arn)) &&
      can(regex("^arn:aws:iam::774055931866:role/fds-rosa-HCP-ROSA-Worker-Role$", var.rosa_prereq_handoff.worker_role_arn)) &&
      length(trimspace(var.rosa_prereq_handoff.oidc_config_id)) > 0,
      false
    )
    error_message = "Use the reviewed fds-rosa account roles in 774055931866 and a stage-2 handoff (operator_role_prefix set)."
  }
}

# No default: the cluster name is fixed at creation and is part of the reviewed create input.
variable "cluster_name" {
  type        = string
  description = "ROSA cluster name. Immutable after creation."
  validation {
    condition     = can(regex("^[a-z]([-a-z0-9]{0,52}[a-z0-9])?$", var.cluster_name))
    error_message = "Lower-case DNS label, at most 54 characters."
  }
}

# No default: #34 Freeze fixes the version (4.22.16 candidate). Check `rosa list versions --hosted-cp` before Plan.
variable "openshift_version" {
  type        = string
  description = "Exact OpenShift x.y.z version adopted by Freeze. No floating channel."
  validation {
    condition     = can(regex("^4\\.[0-9]+\\.[0-9]+$", var.openshift_version))
    error_message = "Supply an exact 4.y.z version."
  }
}

# infra-rosa#4 decision 6120548351: true = public API + external default Ingress (approved).
# false = private API + internal default Ingress (not selected; kept for review only, no GO).
variable "public_cluster" {
  type        = bool
  nullable    = false
  description = "Sets both cluster `private` (API) and rhcs_hcp_default_ingress listening_method. No default so the choice is always recorded in tfvars."
}

# Harbor registry trust (infra-rosa#11 output 4). null only when D22 selects a registry that needs no private CA.
variable "registry_trust" {
  description = "Path and expected SHA256 of the reviewed additional-trusted-CA JSON, or null when not used."
  type = object({
    json_path       = string
    expected_sha256 = string
  })
  nullable = true
  validation {
    condition = var.registry_trust == null ? true : try(
      filesha256(var.registry_trust.json_path) == var.registry_trust.expected_sha256 &&
      toset(keys(jsondecode(file(var.registry_trust.json_path)))) == toset(["10.1.93.54", "harbor.fds.internal"]) &&
      alltrue([for v in values(jsondecode(file(var.registry_trust.json_path))) : startswith(v, "-----BEGIN CERTIFICATE-----\n")]),
      false
    )
    error_message = "Registry CA JSON must match the expected SHA256, have exactly the 10.1.93.54 and harbor.fds.internal keys, and hold PEM certificates."
  }
}

variable "delete_protection" {
  type        = bool
  default     = true
  description = "OCM delete protection. Set false and apply in the approved teardown window (infra-rosa#8 v3.1) before destroy."
}

# Minimum free IPs required in public_transport_a before the public Ingress NLB is created (#35 review 6119267125).
variable "min_free_transport_ips" {
  type        = number
  default     = 16
  description = "Stop before create if public_transport_a has fewer free addresses than this."
}
