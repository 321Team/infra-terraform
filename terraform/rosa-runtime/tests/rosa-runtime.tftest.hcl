# Every run uses mock providers. Never use this as AWS or Red Hat runtime evidence.
# ALL IDs, ARNs and the CA JSON in this file are synthetic MOCK fixtures.
mock_provider "aws" {
  mock_data "aws_caller_identity" {
    defaults = {
      account_id = "774055931866"
      arn        = "arn:aws:iam::774055931866:user/mock-only"
    }
  }
}

mock_provider "rhcs" {}

override_data {
  target = data.aws_subnet.rosa["private_a"]
  values = {
    vpc_id                     = "vpc-00000000000000001"
    cidr_block                 = "10.20.10.0/24"
    availability_zone_id       = "apne2-az1"
    availability_zone          = "ap-northeast-2a"
    map_public_ip_on_launch    = false
    available_ip_address_count = 240
    tags                       = { Name = "fds-private_a", "kubernetes.io/role/internal-elb" = "1" }
  }
}

override_data {
  target = data.aws_subnet.rosa["public_transport_a"]
  values = {
    vpc_id                     = "vpc-00000000000000001"
    cidr_block                 = "10.20.110.0/24"
    availability_zone_id       = "apne2-az1"
    availability_zone          = "ap-northeast-2a"
    map_public_ip_on_launch    = false
    available_ip_address_count = 240
    tags                       = { Name = "fds-public_transport_a", "kubernetes.io/role/elb" = "1" }
  }
}

variables {
  execution_enabled = true
  cluster_name      = "fds-rosa-mock"
  openshift_version = "4.22.16"
  public_cluster    = true
  registry_trust = {
    json_path       = "tests/fixtures/registry-ca.mock.json"
    expected_sha256 = "500505fb3101e59739a3edb8265e12313256b32336b3a9cf0ae6934a5269b8bf"
  }
  network_handoff = {
    region   = "ap-northeast-2"
    vpc_id   = "vpc-00000000000000001"
    vpc_cidr = "10.20.0.0/16"
    subnets = {
      private_a          = { id = "subnet-00000000000000001", cidr = "10.20.10.0/24", zone_id = "apne2-az1", route_table_id = "rtb-00000000000000001" }
      private_b          = { id = "subnet-00000000000000002", cidr = "10.20.20.0/24", zone_id = "apne2-az2", route_table_id = "rtb-00000000000000002" }
      private_c          = { id = "subnet-00000000000000003", cidr = "10.20.30.0/24", zone_id = "apne2-az3", route_table_id = "rtb-00000000000000003" }
      public_transport_a = { id = "subnet-00000000000000004", cidr = "10.20.110.0/24", zone_id = "apne2-az1", route_table_id = "rtb-00000000000000004" }
    }
  }
  rosa_prereq_handoff = {
    account_role_prefix  = "fds-rosa"
    installer_role_arn   = "arn:aws:iam::774055931866:role/fds-rosa-HCP-ROSA-Installer-Role"
    support_role_arn     = "arn:aws:iam::774055931866:role/fds-rosa-HCP-ROSA-Support-Role"
    worker_role_arn      = "arn:aws:iam::774055931866:role/fds-rosa-HCP-ROSA-Worker-Role"
    oidc_config_id       = "mockoidcconfigid0000000000000000"
    operator_role_prefix = "fds-rosa"
  }
}

run "disabled_without_execution_switch" {
  command = plan
  variables {
    execution_enabled = false
  }
  expect_failures = [rhcs_cluster_rosa_hcp.this]
}

run "public_public_single_az_shape" {
  command = plan
  assert {
    condition     = rhcs_cluster_rosa_hcp.this.aws_subnet_ids == tolist(["subnet-00000000000000004", "subnet-00000000000000001"]) && !rhcs_cluster_rosa_hcp.this.private
    error_message = "public/public must pass public_transport_a then private_a, with private=false."
  }
  assert {
    # cluster ID is unknown at plan time; the wiring is in main.tf and checked by readback after apply.
    condition     = rhcs_hcp_default_ingress.default.listening_method == "external"
    error_message = "public/public must pin the existing default Ingress to external."
  }
  assert {
    condition     = rhcs_cluster_rosa_hcp.this.availability_zones == tolist(["ap-northeast-2a"]) && rhcs_cluster_rosa_hcp.this.cloud_region == "ap-northeast-2"
    error_message = "Cluster must be single AZ ap-northeast-2a."
  }
  assert {
    condition = (
      rhcs_cluster_rosa_hcp.this.compute_machine_type == "m5.xlarge" &&
      rhcs_cluster_rosa_hcp.this.replicas == 3 &&
      !rhcs_cluster_rosa_hcp.this.autoscaling_enabled &&
      rhcs_cluster_rosa_hcp.this.worker_disk_size == 300 &&
      rhcs_cluster_rosa_hcp.this.ec2_metadata_http_tokens == "required"
    )
    error_message = "Initial pool must be m5.xlarge x 3, autoscaling off, 300 GiB, IMDSv2 required (infra-rosa#3)."
  }
  assert {
    condition = (
      rhcs_cluster_rosa_hcp.this.machine_cidr == "10.20.0.0/16" &&
      rhcs_cluster_rosa_hcp.this.pod_cidr == "10.128.0.0/14" &&
      rhcs_cluster_rosa_hcp.this.service_cidr == "172.30.0.0/16" &&
      rhcs_cluster_rosa_hcp.this.host_prefix == 23
    )
    error_message = "Network CIDRs changed."
  }
  assert {
    condition     = toset(keys(rhcs_cluster_rosa_hcp.this.registry_config.additional_trusted_ca)) == toset(["10.1.93.54", "harbor.fds.internal"])
    error_message = "Registry trust must carry exactly the reviewed IP and FQDN keys."
  }
  assert {
    condition     = rhcs_cluster_rosa_hcp.this.registry_config.registry_sources != null
    error_message = "registry_sources must be an object (rhcs 1.7.9 cannot decode a null registry_sources at apply)."
  }

  assert {
    condition     = rhcs_cluster_rosa_hcp.this.sts.operator_role_prefix == "fds-rosa" && rhcs_cluster_rosa_hcp.this.sts.oidc_config_id == "mockoidcconfigid0000000000000000"
    error_message = "STS input must come from the rosa-prereq handoff."
  }
  assert {
    condition     = !rhcs_cluster_rosa_hcp.this.create_admin_user && rhcs_cluster_rosa_hcp.this.delete_protection
    error_message = "No admin user; delete protection on by default."
  }
}

run "default_pool_is_managed_with_surge_one" {
  command = plan
  assert {
    condition = (
      rhcs_hcp_machine_pool.workers.name == "workers" &&
      rhcs_hcp_machine_pool.workers.subnet_id == "subnet-00000000000000001" &&
      rhcs_hcp_machine_pool.workers.replicas == 3 &&
      rhcs_hcp_machine_pool.workers.auto_repair &&
      !rhcs_hcp_machine_pool.workers.autoscaling.enabled
    )
    error_message = "Default pool must be workers in private_a, 3 replicas, auto repair on, autoscaling off."
  }
  assert {
    condition = (
      rhcs_hcp_machine_pool.workers.aws_node_pool.instance_type == "m5.xlarge" &&
      rhcs_hcp_machine_pool.workers.aws_node_pool.disk_size == 300 &&
      rhcs_hcp_machine_pool.workers.aws_node_pool.ec2_metadata_http_tokens == "required"
    )
    error_message = "Pool node settings must match the initial cluster pool."
  }
  assert {
    condition     = rhcs_hcp_machine_pool.workers.management.max_surge == "1" && rhcs_hcp_machine_pool.workers.management.max_unavailable == "0"
    error_message = "Replacement may add at most one node and never go below 3 (C1 max 4)."
  }
}

run "private_private_uses_private_subnet_only" {
  command = plan
  variables {
    public_cluster = false
  }
  assert {
    condition     = rhcs_cluster_rosa_hcp.this.aws_subnet_ids == tolist(["subnet-00000000000000001"]) && rhcs_cluster_rosa_hcp.this.private
    error_message = "private/private must use private_a only, with private=true."
  }
  assert {
    condition     = rhcs_hcp_default_ingress.default.listening_method == "internal"
    error_message = "private/private must pin the existing default Ingress to internal."
  }
}

run "no_registry_trust_when_null" {
  command = plan
  variables {
    registry_trust = null
  }
  assert {
    condition     = rhcs_cluster_rosa_hcp.this.registry_config == null
    error_message = "No registry config when trust is not used."
  }
}

run "ca_json_hash_mismatch_is_rejected" {
  command = plan
  variables {
    registry_trust = {
      json_path       = "tests/fixtures/registry-ca.mock.json"
      expected_sha256 = "4d86507ecd81789e376669940f68b2dbb27f5989e6fd4315238c9f61a2401da4"
    }
  }
  expect_failures = [var.registry_trust]
}

run "missing_internal_elb_tag_is_rejected" {
  command = plan
  override_data {
    target = data.aws_subnet.rosa["private_a"]
    values = {
      vpc_id                     = "vpc-00000000000000001"
      cidr_block                 = "10.20.10.0/24"
      availability_zone_id       = "apne2-az1"
      availability_zone          = "ap-northeast-2a"
      map_public_ip_on_launch    = false
      available_ip_address_count = 240
      tags                       = { Name = "fds-private_a" }
    }
  }
  expect_failures = [rhcs_cluster_rosa_hcp.this]
}

run "missing_public_elb_tag_is_rejected" {
  command = plan
  override_data {
    target = data.aws_subnet.rosa["public_transport_a"]
    values = {
      vpc_id                     = "vpc-00000000000000001"
      cidr_block                 = "10.20.110.0/24"
      availability_zone_id       = "apne2-az1"
      availability_zone          = "ap-northeast-2a"
      map_public_ip_on_launch    = false
      available_ip_address_count = 240
      tags                       = { Name = "fds-public_transport_a" }
    }
  }
  expect_failures = [rhcs_cluster_rosa_hcp.this]
}

run "too_few_transport_ips_is_rejected" {
  command = plan
  override_data {
    target = data.aws_subnet.rosa["public_transport_a"]
    values = {
      vpc_id                     = "vpc-00000000000000001"
      cidr_block                 = "10.20.110.0/24"
      availability_zone_id       = "apne2-az1"
      availability_zone          = "ap-northeast-2a"
      map_public_ip_on_launch    = false
      available_ip_address_count = 3
      tags                       = { Name = "fds-public_transport_a", "kubernetes.io/role/elb" = "1" }
    }
  }
  expect_failures = [rhcs_cluster_rosa_hcp.this]
}

run "live_subnet_mismatch_is_rejected" {
  command = plan
  override_data {
    target = data.aws_subnet.rosa["private_a"]
    values = {
      vpc_id                     = "vpc-00000000000000009"
      cidr_block                 = "10.20.10.0/24"
      availability_zone_id       = "apne2-az1"
      availability_zone          = "ap-northeast-2a"
      map_public_ip_on_launch    = false
      available_ip_address_count = 240
      tags                       = { Name = "fds-private_a", "kubernetes.io/role/internal-elb" = "1" }
    }
  }
  expect_failures = [rhcs_cluster_rosa_hcp.this]
}

run "stage1_only_prereq_handoff_is_rejected" {
  command = plan
  variables {
    rosa_prereq_handoff = {
      account_role_prefix  = "fds-rosa"
      installer_role_arn   = "arn:aws:iam::774055931866:role/fds-rosa-HCP-ROSA-Installer-Role"
      support_role_arn     = "arn:aws:iam::774055931866:role/fds-rosa-HCP-ROSA-Support-Role"
      worker_role_arn      = "arn:aws:iam::774055931866:role/fds-rosa-HCP-ROSA-Worker-Role"
      oidc_config_id       = "mockoidcconfigid0000000000000000"
      operator_role_prefix = ""
    }
  }
  expect_failures = [var.rosa_prereq_handoff]
}

run "floating_version_is_rejected" {
  command = plan
  variables {
    openshift_version = "4.22"
  }
  expect_failures = [var.openshift_version]
}
