# LOCAL CANDIDATE. No cloud plan/apply is authorized by this source.
# Scope (infra-terraform#12 A3): HCP account roles, managed OIDC config + IAM OIDC provider,
# HCP operator roles. ocm-role / user-role are owned by the ROSA CLI and are not managed here.
provider "aws" {
  region              = "ap-northeast-2"
  allowed_account_ids = ["774055931866"]
  default_tags {
    tags = {
      Project   = "fds-hybrid"
      ManagedBy = "terraform"
      Phase     = "phase2"
      Component = "rosa-prereq"
    }
  }
}

# Authentication comes from the environment (RHCS_CLIENT_ID/RHCS_CLIENT_SECRET or RHCS_TOKEN).
# Never put Red Hat credentials in tfvars, state backends examples or the repository.
provider "rhcs" {}

locals {
  prefix     = "fds-rosa"
  aws_policy = "arn:aws:iam::aws:policy"

  # Names, trust and policies match ROSA CLI 1.2.53 `create account-roles --hosted-cp --mode manual` (2026-10-09).
  account_roles = {
    installer = {
      name       = "${local.prefix}-HCP-ROSA-Installer-Role"
      type       = "installer"
      principals = { type = "AWS", identifiers = [var.rh_installer_principal_arn] }
      policies   = ["${local.aws_policy}/service-role/ROSAInstallerPolicy"]
    }
    support = {
      name       = "${local.prefix}-HCP-ROSA-Support-Role"
      type       = "support"
      principals = { type = "AWS", identifiers = [var.rh_support_principal_arn] }
      policies   = ["${local.aws_policy}/service-role/ROSASRESupportPolicy"]
    }
    worker = {
      name       = "${local.prefix}-HCP-ROSA-Worker-Role"
      type       = "instance_worker"
      principals = { type = "Service", identifiers = ["ec2.amazonaws.com"] }
      policies = [
        "${local.aws_policy}/service-role/ROSAWorkerInstancePolicy",
        "${local.aws_policy}/AmazonEC2ContainerRegistryReadOnly",
      ]
    }
  }

  account_role_attachments = merge([
    for k, r in local.account_roles : {
      for p in r.policies : "${k}:${basename(p)}" => { role = k, policy_arn = p }
    }
  ]...)

  # HCP operator roles. Stage 2 must compare these with
  # `rosa create operator-roles --hosted-cp --prefix fds-rosa --oidc-config-id <id> --mode manual` before enabling.
  operator_roles = {
    ingress = {
      namespace       = "openshift-ingress-operator"
      name            = "cloud-credentials"
      service_account = ["ingress-operator"]
      policy          = "ROSAIngressOperatorPolicy"
    }
    ebs_csi = {
      namespace       = "openshift-cluster-csi-drivers"
      name            = "ebs-cloud-credentials"
      service_account = ["aws-ebs-csi-driver-operator", "aws-ebs-csi-driver-controller-sa"]
      policy          = "ROSAAmazonEBSCSIDriverOperatorPolicy"
    }
    cloud_network_config = {
      namespace       = "openshift-cloud-network-config-controller"
      name            = "cloud-credentials"
      service_account = ["cloud-network-config-controller"]
      policy          = "ROSACloudNetworkConfigOperatorPolicy"
    }
    image_registry = {
      namespace       = "openshift-image-registry"
      name            = "installer-cloud-credentials"
      service_account = ["cluster-image-registry-operator", "registry"]
      policy          = "ROSAImageRegistryOperatorPolicy"
    }
    kube_controller_manager = {
      namespace       = "kube-system"
      name            = "kube-controller-manager"
      service_account = ["kube-controller-manager"]
      policy          = "ROSAKubeControllerPolicy"
    }
    capa_controller_manager = {
      namespace       = "kube-system"
      name            = "capa-controller-manager"
      service_account = ["capa-controller-manager"]
      policy          = "ROSANodePoolManagementPolicy"
    }
    control_plane_operator = {
      namespace       = "kube-system"
      name            = "control-plane-operator"
      service_account = ["control-plane-operator"]
      policy          = "ROSAControlPlaneOperatorPolicy"
    }
    kms_provider = {
      namespace       = "kube-system"
      name            = "kms-provider"
      service_account = ["kms-provider"]
      policy          = "ROSAKMSProviderPolicy"
    }
  }

  oidc_endpoint = rhcs_rosa_oidc_config.managed.oidc_endpoint_url
  oidc_host     = trimprefix(local.oidc_endpoint, "https://")

  rosa_role_tags = {
    "red-hat-managed"       = "true"
    "rosa_hcp_policies"     = "true"
    "rosa_managed_policies" = "true"
    "rosa_role_prefix"      = local.prefix
  }
}

# ---------- Stage 1: account roles ----------
resource "aws_iam_role" "account" {
  for_each = local.account_roles
  name     = each.value.name
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Action    = "sts:AssumeRole"
      Principal = { (each.value.principals.type) = each.value.principals.identifiers }
    }]
  })
  tags = merge(local.rosa_role_tags, {
    "rosa_role_type"         = each.value.type
    "rosa_openshift_version" = var.openshift_version_tag
  })

  lifecycle {
    precondition {
      condition     = var.execution_enabled
      error_message = "execution_enabled=false: no ROSA prereq resource may be planned for creation."
    }
  }
}

resource "aws_iam_role_policy_attachment" "account" {
  for_each   = local.account_role_attachments
  role       = aws_iam_role.account[each.value.role].name
  policy_arn = each.value.policy_arn
}

# ---------- Stage 1: managed OIDC config + IAM OIDC provider ----------
# managed = true: Red Hat hosts the discovery document and signing key. No S3 / Secrets Manager.
resource "rhcs_rosa_oidc_config" "managed" {
  managed = true

  lifecycle {
    precondition {
      condition     = var.execution_enabled
      error_message = "execution_enabled=false: managed OIDC config may not be registered."
    }
  }
}

resource "aws_iam_openid_connect_provider" "rosa" {
  url             = "https://${local.oidc_host}"
  client_id_list  = ["openshift", "sts.amazonaws.com"]
  thumbprint_list = [rhcs_rosa_oidc_config.managed.thumbprint]

  lifecycle {
    precondition {
      condition     = startswith(local.oidc_host, "oidc.op1.openshiftapps.com/")
      error_message = "Unexpected managed OIDC issuer host. The central-path trust review and the A3 read policy (ReadRosaOidcProvider) only cover oidc-provider/oidc.op1.openshiftapps.com/*."
    }
  }
}

# ---------- Stage 2: operator roles ----------
resource "aws_iam_role" "operator" {
  for_each = var.create_operator_roles ? local.operator_roles : {}
  name     = substr("${local.prefix}-${each.value.namespace}-${each.value.name}", 0, 64)
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Action    = "sts:AssumeRoleWithWebIdentity"
      Principal = { Federated = aws_iam_openid_connect_provider.rosa.arn }
      Condition = {
        StringEquals = {
          "${local.oidc_host}:sub" = [for sa in each.value.service_account : "system:serviceaccount:${each.value.namespace}:${sa}"]
        }
      }
    }]
  })
  tags = merge(local.rosa_role_tags, {
    "operator_namespace" = each.value.namespace
    "operator_name"      = each.value.name
  })

  lifecycle {
    precondition {
      condition     = var.execution_enabled
      error_message = "execution_enabled=false: no ROSA prereq resource may be planned for creation."
    }
  }
}

resource "aws_iam_role_policy_attachment" "operator" {
  for_each   = aws_iam_role.operator
  role       = each.value.name
  policy_arn = "${local.aws_policy}/service-role/${local.operator_roles[each.key].policy}"
}
