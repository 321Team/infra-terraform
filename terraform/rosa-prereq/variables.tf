# A local safety switch, not evidence of approval or a replacement for #35/#12 gates.
variable "execution_enabled" {
  type        = bool
  default     = false
  description = "Keep false outside mock tests until exact-source review, policy grant and existing execution gates are satisfied."
}

# Stage 2 switch. Operator roles need the managed OIDC config ID, so they are created
# only after stage 1 readback and a `rosa create operator-roles --mode manual` name/policy comparison.
variable "create_operator_roles" {
  type        = bool
  default     = false
  description = "Create the 8 HCP operator roles. Enable only after stage 1 (account roles + OIDC) readback passes."
}

variable "rh_installer_principal_arn" {
  type        = string
  default     = "arn:aws:iam::710019948333:role/RH-Managed-OpenShift-Installer"
  description = "Red Hat installer principal. Matches ROSA CLI 1.2.53 manual output (sts_installer_trust_policy.json, 2026-10-09)."
  validation {
    condition     = can(regex("^arn:aws:iam::[0-9]{12}:role/RH-Managed-OpenShift-Installer$", var.rh_installer_principal_arn))
    error_message = "Installer principal must be the Red Hat RH-Managed-OpenShift-Installer role."
  }
}

# No default: the role name contains the Red Hat organization external ID.
# Supply it from an uncommitted tfvars file. Value must equal ROSA CLI sts_support_trust_policy.json.
variable "rh_support_principal_arn" {
  type        = string
  description = "Red Hat SRE support principal (arn:aws:iam::<RH account>:role/RH-Technical-Support-<org external id>)."
  validation {
    condition     = can(regex("^arn:aws:iam::[0-9]{12}:role/RH-Technical-Support-[0-9]+$", var.rh_support_principal_arn))
    error_message = "Support principal must be a Red Hat RH-Technical-Support-<org external id> role."
  }
}

variable "openshift_version_tag" {
  type        = string
  default     = "4.22"
  description = "Value of the rosa_openshift_version tag the ROSA CLI 1.2.53 puts on account roles. Tag only; HCP account roles use AWS managed policies."
}
