# LOCAL CANDIDATE. No cloud plan/apply is authorized by this source.
# Scope (infra-rosa#4): one ROSA HCP cluster and its default worker machine pool.
# Not managed here: VPC/subnets/tags (network), account/operator roles + OIDC (rosa-prereq),
# IdP/RBAC/namespaces (infra-rosa#5), registry pull path (infra-rosa#11/#12, #35, #37).
provider "aws" {
  region              = "ap-northeast-2"
  allowed_account_ids = ["774055931866"]
  default_tags {
    tags = {
      Project   = "fds-hybrid"
      ManagedBy = "terraform"
      Phase     = "phase2"
      Component = "rosa-runtime"
    }
  }
}

# Authentication comes from the environment (RHCS_CLIENT_ID/RHCS_CLIENT_SECRET or RHCS_TOKEN).
# Never put Red Hat credentials in tfvars, backend examples or the repository.
provider "rhcs" {}

locals {
  region = "ap-northeast-2"
  az     = "ap-northeast-2a"

  # Adopted in infra-rosa#3: 1 AZ (private_a) x m5.xlarge x 3, autoscaling off, 300 GiB, IMDSv2 required.
  worker = {
    instance_type = "m5.xlarge"
    replicas      = 3
    disk_size_gib = 300
    imds_tokens   = "required"
  }

  # OpenShift defaults, recorded explicitly so Plan shows them. No overlap with the VPC 10.20.0.0/16
  # or On-Prem 10.1.93.0/24. Immutable after creation.
  pod_cidr     = "10.128.0.0/14"
  service_cidr = "172.30.0.0/16"
  host_prefix  = 23

  private_subnet_id   = var.network_handoff.subnets.private_a.id
  transport_subnet_id = var.network_handoff.subnets.public_transport_a.id

  # public/public needs the public subnet in the same AZ (AWS ROSA HCP getting started).
  rosa_subnet_keys = var.public_cluster ? ["public_transport_a", "private_a"] : ["private_a"]
  rosa_subnet_ids  = [for k in local.rosa_subnet_keys : var.network_handoff.subnets[k].id]

  registry_additional_trusted_ca = var.registry_trust == null ? null : tomap(jsondecode(file(var.registry_trust.json_path)))

  cluster_tags = {
    Project   = "fds-hybrid"
    ManagedBy = "terraform"
    Phase     = "phase2"
    Component = "rosa-runtime"
  }
}

data "aws_caller_identity" "current" {}

# Live identity of the subnets ROSA will use. Role tags come from the network root (infra-terraform#27).
data "aws_subnet" "rosa" {
  for_each = toset(local.rosa_subnet_keys)
  id       = var.network_handoff.subnets[each.key].id
}

resource "rhcs_cluster_rosa_hcp" "this" {
  name                   = var.cluster_name
  cloud_region           = local.region
  aws_account_id         = data.aws_caller_identity.current.account_id
  aws_billing_account_id = data.aws_caller_identity.current.account_id
  aws_subnet_ids         = local.rosa_subnet_ids
  availability_zones     = [local.az]
  private                = !var.public_cluster
  version                = var.openshift_version

  machine_cidr = var.network_handoff.vpc_cidr
  pod_cidr     = local.pod_cidr
  service_cidr = local.service_cidr
  host_prefix  = local.host_prefix

  # Initial pool only. Day-2 changes go through rhcs_hcp_machine_pool.workers below.
  compute_machine_type     = local.worker.instance_type
  replicas                 = local.worker.replicas
  autoscaling_enabled      = false
  worker_disk_size         = local.worker.disk_size_gib
  ec2_metadata_http_tokens = local.worker.imds_tokens

  sts = {
    role_arn         = var.rosa_prereq_handoff.installer_role_arn
    support_role_arn = var.rosa_prereq_handoff.support_role_arn
    instance_iam_roles = {
      worker_role_arn = var.rosa_prereq_handoff.worker_role_arn
    }
    operator_role_prefix = var.rosa_prereq_handoff.operator_role_prefix
    oidc_config_id       = var.rosa_prereq_handoff.oidc_config_id
  }

  # Changing registry config after creation recreates every machine pool node (infra-rosa#11 ②), so it is a create input.
  registry_config = local.registry_additional_trusted_ca == null ? null : {
    additional_trusted_ca = local.registry_additional_trusted_ca
  }

  properties = {
    rosa_creator_arn = data.aws_caller_identity.current.arn
  }
  tags = local.cluster_tags

  # No kubeadmin-style user; access is through the IdP set up in infra-rosa#5.
  create_admin_user                   = false
  delete_protection                   = var.delete_protection
  wait_for_create_complete            = true
  wait_for_std_compute_nodes_complete = true

  lifecycle {
    precondition {
      condition     = var.execution_enabled && terraform.workspace == "default"
      error_message = "Local candidate is disabled, or workspace is not the approved default. G4/Freeze/ROSA Cost GO/Create GO still apply."
    }
    precondition {
      condition     = data.aws_caller_identity.current.account_id == "774055931866"
      error_message = "Caller is not in the approved account."
    }
    precondition {
      condition = alltrue([
        for k in local.rosa_subnet_keys :
        data.aws_subnet.rosa[k].vpc_id == var.network_handoff.vpc_id &&
        data.aws_subnet.rosa[k].cidr_block == var.network_handoff.subnets[k].cidr &&
        data.aws_subnet.rosa[k].availability_zone_id == var.network_handoff.subnets[k].zone_id &&
        data.aws_subnet.rosa[k].availability_zone == local.az &&
        !data.aws_subnet.rosa[k].map_public_ip_on_launch
      ])
      error_message = "Live subnet identity, geometry, AZ or automatic public IP differs from the network handoff. Stop; do not substitute a subnet."
    }
    precondition {
      condition     = lookup(data.aws_subnet.rosa["private_a"].tags, "kubernetes.io/role/internal-elb", "") == "1"
      error_message = "private_a lacks kubernetes.io/role/internal-elb=1. Apply the reviewed network tag change (infra-terraform#27) first."
    }
    precondition {
      condition     = !var.public_cluster || try(lookup(data.aws_subnet.rosa["public_transport_a"].tags, "kubernetes.io/role/elb", "") == "1", false)
      error_message = "public_transport_a lacks kubernetes.io/role/elb=1. Apply the reviewed network tag change (infra-terraform#27) first."
    }
    precondition {
      condition     = !var.public_cluster || try(data.aws_subnet.rosa["public_transport_a"].available_ip_address_count >= var.min_free_transport_ips, false)
      error_message = "public_transport_a has too few free IPs for the public Ingress load balancer. Stop and report; do not widen other subnets."
    }
  }
}

# Default single-AZ HCP pool is named "workers". Declaring it here adopts it on apply ("magic import", rhcs guide
# worker-machine-pool.md) so later changes are reviewed through this resource. Values match the initial pool.
resource "rhcs_hcp_machine_pool" "workers" {
  cluster     = rhcs_cluster_rosa_hcp.this.id
  name        = "workers"
  subnet_id   = local.private_subnet_id
  replicas    = local.worker.replicas
  auto_repair = true
  autoscaling = {
    enabled = false
  }
  aws_node_pool = {
    instance_type            = local.worker.instance_type
    disk_size                = local.worker.disk_size_gib
    ec2_metadata_http_tokens = local.worker.imds_tokens
  }
  # Replacement adds at most one node above 3 and never drops below 3 (infra-rosa#4 C1: max 4 workers).
  management = {
    max_surge       = "1"
    max_unavailable = "0"
  }
}

# `private` above sets API listening only (rhcs v1.7.9 SetAPIPrivacy). The apps Ingress exposure is pinned here
# so it shows in Plan (infra-rosa#4 decision 6120548351 §3). This edits the default Ingress the cluster already has;
# it creates no extra load balancer. Create waits for cluster Ready; destroy only drops it from state (rhcs warning).
resource "rhcs_hcp_default_ingress" "default" {
  cluster          = rhcs_cluster_rosa_hcp.this.id
  listening_method = var.public_cluster ? "external" : "internal"
}
