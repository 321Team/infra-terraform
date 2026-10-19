# ALL IDs, destinations and references in this file are synthetic MOCK fixtures.
mock_provider "aws" {}

run "session_document_defaults_to_unmanaged" {
  command = plan
  assert {
    condition     = length(aws_ssm_document.session_preferences) == 0 && !output.session_document_source.managed_here
    error_message = "Never adopt or overwrite the account default document implicitly."
  }
}

run "document_without_absence_evidence_is_rejected" {
  command = plan
  variables { create_session_document = true }
  expect_failures = [aws_ssm_document.session_preferences]
}

run "adopted_session_preferences_are_preserved" {
  command = plan
  variables {
    create_session_document             = true
    document_absence_readback_reference = "MOCK-ONLY-NOT-READBACK"
  }
  assert {
    condition = (
      aws_ssm_document.session_preferences[0].document_type == "Session" &&
      jsondecode(aws_ssm_document.session_preferences[0].content).sessionType == "Standard_Stream" &&
      jsondecode(aws_ssm_document.session_preferences[0].content).inputs.s3BucketName == "" &&
      jsondecode(aws_ssm_document.session_preferences[0].content).inputs.cloudWatchLogGroupName == "" &&
      jsondecode(aws_ssm_document.session_preferences[0].content).inputs.kmsKeyId == "" &&
      !jsondecode(aws_ssm_document.session_preferences[0].content).inputs.runAsEnabled
    )
    error_message = "Adopted document content changed. This mock does not prove AWS acceptance or defaults."
  }
}

run "unpinned_package_is_rejected" {
  command = plan
  variables { libreswan_package_spec = "libreswan" }
  expect_failures = [var.libreswan_package_spec]
}

run "all_protocol_egress_is_rejected" {
  command = plan
  variables {
    relay_egress = { bad = { protocol = "-1", port = 443, cidr_ipv4 = "192.0.2.10/32", description = "MOCK invalid rule" } }
  }
  expect_failures = [var.relay_egress]
}

variables {
  libreswan_package_spec     = "libreswan-0.0.0-0.TEST_ONLY"
  execution_enabled          = true
  root_delete_on_termination = false
  cpu_credit_mode            = "standard"
  egress_contract_reference  = "MOCK-ONLY-NOT-AN-APPROVAL"
  relay_egress = {
    fixture = { protocol = "tcp", port = 443, cidr_ipv4 = "0.0.0.0/0", description = "MOCK adopted tuple; no AWS call" }
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
}

override_data {
  target = data.aws_vpc.network
  values = { cidr_block = "10.20.0.0/16" }
}
override_data {
  target = data.aws_subnet.transport
  values = {
    vpc_id                  = "vpc-00000000000000001"
    cidr_block              = "10.20.110.0/24"
    availability_zone       = "ap-northeast-2a"
    availability_zone_id    = "apne2-az1"
    map_public_ip_on_launch = false
  }
}
override_data {
  target = data.aws_ami.relay
  values = { id = "ami-08d855918a18d0cf9" }
}
override_data {
  target = data.aws_iam_instance_profile.relay
  values = {
    arn      = "arn:aws:iam::774055931866:instance-profile/FDS-Relay-SSM"
    role_arn = "arn:aws:iam::774055931866:role/FDS-Relay-SSM"
  }
}
override_data {
  target = data.aws_kms_key.ebs
  values = { arn = "arn:aws:kms:ap-northeast-2:774055931866:key/00000000-0000-0000-0000-000000000001" }
}

run "disabled_candidate_is_rejected" {
  command = plan
  variables { execution_enabled = false }
  expect_failures = [aws_security_group.relay]
}

run "missing_egress_is_rejected" {
  command = plan
  variables { relay_egress = {} }
  expect_failures = [aws_security_group.relay]
}

run "relay_controls_and_no_early_routes" {
  command = plan
  assert {
    condition = (
      aws_instance.relay.instance_type == "t3.medium" &&
      aws_instance.relay.private_ip == "10.20.110.10" &&
      !aws_instance.relay.associate_public_ip_address && !aws_instance.relay.source_dest_check &&
      aws_instance.relay.metadata_options[0].http_tokens == "required" &&
      aws_instance.relay.root_block_device[0].encrypted &&
      aws_instance.relay.root_block_device[0].volume_size == 40 &&
      aws_instance.relay.root_block_device[0].volume_type == "gp3"
    )
    error_message = "Adopted Relay identity, IMDS or EBS controls changed."
  }
  assert {
    condition = length(aws_vpc_security_group_ingress_rule.ike) == 2 && alltrue([
      for r in aws_vpc_security_group_ingress_rule.ike :
      r.ip_protocol == "udp" && contains([500, 4500], r.from_port) && r.from_port == r.to_port && r.cidr_ipv4 == "0.0.0.0/0"
    ])
    error_message = "Only the two adopted outer UDP rules belong in this ingress set."
  }
  assert {
    condition     = length(aws_route.onprem) == 0 && !output.relay_handoff.stage_a_ready && !aws_eip_association.relay.allow_reassociation
    error_message = "No pre-tunnel routes, readiness claim or implicit EIP reassociation."
  }
}

run "wrong_profile_is_rejected" {
  command = plan
  override_data {
    target = data.aws_iam_instance_profile.relay
    values = {
      arn      = "arn:aws:iam::774055931866:instance-profile/unapproved"
      role_arn = "arn:aws:iam::774055931866:role/unapproved"
    }
  }
  expect_failures = [data.aws_iam_instance_profile.relay]
}

run "wrong_subnet_vpc_is_rejected" {
  command = plan
  override_data {
    target = data.aws_subnet.transport
    values = {
      vpc_id                  = "vpc-00000000000000099"
      cidr_block              = "10.20.110.0/24"
      availability_zone       = "ap-northeast-2a"
      availability_zone_id    = "apne2-az1"
      map_public_ip_on_launch = false
    }
  }
  expect_failures = [aws_security_group.relay]
}

run "early_route_activation_is_rejected" {
  command = plan
  variables { activate_onprem_routes = true }
  expect_failures = [aws_security_group.relay]
}

run "reviewed_route_targets_only" {
  command = plan
  variables {
    worker_subnet_key          = "private_a"
    worker_source_reference    = "MOCK-ONLY-NOT-ACCEPTANCE"
    activate_onprem_routes     = true
    onprem_route_keys          = ["private_a"]
    tunnel_readiness_reference = "MOCK-ONLY-NOT-RUNTIME"
  }
  override_data {
    target = data.aws_route_table.selected["private_a"]
    values = {
      vpc_id       = "vpc-00000000000000001"
      associations = [{ subnet_id = "subnet-00000000000000001", main = false, route_table_association_id = "rtbassoc-00000000000000001", route_table_id = "rtb-00000000000000001", gateway_id = "" }]
    }
  }
  assert {
    condition     = length(aws_route.onprem) == 1 && aws_route.onprem["private_a"].destination_cidr_block == "10.1.93.0/24"
    error_message = "Activate only the supplied target and adopted destination."
  }
}

run "wrong_route_association_is_rejected" {
  command = plan
  variables {
    worker_subnet_key          = "private_a"
    worker_source_reference    = "MOCK-ONLY-NOT-ACCEPTANCE"
    activate_onprem_routes     = true
    onprem_route_keys          = ["private_a"]
    tunnel_readiness_reference = "MOCK-ONLY-NOT-RUNTIME"
  }
  override_data {
    target = data.aws_route_table.selected["private_a"]
    values = {
      vpc_id       = "vpc-00000000000000001"
      associations = []
    }
  }
  expect_failures = [aws_route.onprem]
}

override_data {
  target = data.aws_subnet.worker
  values = {
    vpc_id                  = "vpc-00000000000000001"
    cidr_block              = "10.20.10.0/24"
    availability_zone_id    = "apne2-az1"
    map_public_ip_on_launch = false
  }
}
run "stream9_and_no_unselected_worker" {
  command = plan
  assert {
    condition     = aws_instance.relay.ami == "ami-08d855918a18d0cf9" && length(aws_vpc_security_group_ingress_rule.worker_db) == 0 && length(aws_vpc_security_group_ingress_rule.worker_harbor) == 0
    error_message = "Stream9 candidate and empty worker boundary must be preserved."
  }
}
run "accepted_single_worker_subnet" {
  command = plan
  variables {
    worker_subnet_key       = "private_a"
    worker_source_reference = "MOCK-ONLY"
  }
  assert {
    condition = (
      length(aws_vpc_security_group_ingress_rule.worker_db) == 1 &&
      aws_vpc_security_group_ingress_rule.worker_db[0].cidr_ipv4 == "10.20.10.0/24" &&
      aws_vpc_security_group_ingress_rule.worker_db[0].from_port == 5432 &&
      aws_vpc_security_group_ingress_rule.worker_db[0].to_port == 5432 &&
      aws_vpc_security_group_ingress_rule.worker_db[0].ip_protocol == "tcp" &&
      length(aws_route.onprem) == 0
    )
    error_message = "Only the exact worker subnet DB ingress may be added before separate route acceptance."
  }
}
run "harbor_ingress_absent_by_default" {
  command = plan
  variables {
    worker_subnet_key       = "private_a"
    worker_source_reference = "MOCK-ONLY"
  }
  assert {
    condition     = length(aws_vpc_security_group_ingress_rule.worker_harbor) == 0
    error_message = "Worker TCP443 ingress must stay absent without a window B reference."
  }
}
run "harbor_ingress_exact_with_reference" {
  command = plan
  variables {
    worker_subnet_key       = "private_a"
    worker_source_reference = "MOCK-ONLY"
    harbor_path_reference   = "MOCK-ONLY-NOT-AN-APPROVAL"
  }
  assert {
    condition = (
      length(aws_vpc_security_group_ingress_rule.worker_harbor) == 1 &&
      aws_vpc_security_group_ingress_rule.worker_harbor[0].cidr_ipv4 == "10.20.10.0/24" &&
      aws_vpc_security_group_ingress_rule.worker_harbor[0].from_port == 443 &&
      aws_vpc_security_group_ingress_rule.worker_harbor[0].to_port == 443 &&
      aws_vpc_security_group_ingress_rule.worker_harbor[0].ip_protocol == "tcp" &&
      length(aws_vpc_security_group_ingress_rule.worker_db) == 1 &&
      length(aws_vpc_security_group_ingress_rule.ike) == 2 &&
      length(aws_route.onprem) == 0
    )
    error_message = "Only the exact worker subnet TCP443 ingress is added; DB/IKE unchanged and no route without separate activation."
  }
}
run "harbor_reference_without_worker_rejected" {
  command = plan
  variables { harbor_path_reference = "MOCK-ONLY-NOT-AN-APPROVAL" }
  expect_failures = [aws_security_group.relay]
}
run "worker_without_reference_rejected" {
  command = plan
  variables { worker_subnet_key = "private_a" }
  expect_failures = [aws_security_group.relay]
}
run "transport_as_worker_rejected" {
  command = plan
  variables { worker_subnet_key = "public_transport_a" }
  expect_failures = [var.worker_subnet_key]
}
run "wrong_actual_worker_rejected" {
  command = plan
  variables {
    worker_subnet_key       = "private_a"
    worker_source_reference = "MOCK-ONLY"
  }
  override_data {
    target = data.aws_subnet.worker[0]
    values = {
      vpc_id                  = "vpc-00000000000000099"
      cidr_block              = "10.20.10.0/24"
      availability_zone_id    = "apne2-az1"
      map_public_ip_on_launch = false
    }
  }
  expect_failures = [data.aws_subnet.worker]
}
run "http_without_repo_evidence_rejected" {
  command = plan
  variables {
    relay_egress = {
      https = { protocol = "tcp", port = 443, cidr_ipv4 = "0.0.0.0/0", description = "MOCK" }
      http  = { protocol = "tcp", port = 80, cidr_ipv4 = "0.0.0.0/0", description = "MOCK" }
    }
  }
  expect_failures = [aws_security_group.relay]
}
run "accepted_conditional_http" {
  command = plan
  variables {
    http_repository_evidence_reference = "MOCK-ONLY-NOT-APPROVAL"
    relay_egress = {
      https = { protocol = "tcp", port = 443, cidr_ipv4 = "0.0.0.0/0", description = "MOCK" }
      http  = { protocol = "tcp", port = 80, cidr_ipv4 = "0.0.0.0/0", description = "MOCK" }
    }
  }
  assert {
    condition     = length(aws_vpc_security_group_egress_rule.reviewed) == 2
    error_message = "Only explicitly evidenced conditional HTTP is accepted."
  }
}
run "udp_egress_rejected" {
  command = plan
  variables {
    relay_egress = { ike = { protocol = "udp", port = 500, cidr_ipv4 = "0.0.0.0/0", description = "MOCK" } }
  }
  expect_failures = [var.relay_egress]
}
run "wrong_route_subnet_rejected" {
  command = plan
  variables {
    worker_subnet_key          = "private_a"
    worker_source_reference    = "MOCK-ONLY"
    activate_onprem_routes     = true
    onprem_route_keys          = ["private_b"]
    tunnel_readiness_reference = "MOCK-ONLY"
  }
  override_data {
    target = data.aws_route_table.selected["private_b"]
    values = {
      vpc_id       = "vpc-00000000000000001"
      associations = [{ subnet_id = "subnet-00000000000000002", main = false, route_table_association_id = "rtbassoc-00000000000000002", route_table_id = "rtb-00000000000000002", gateway_id = "" }]
    }
  }
  expect_failures = [aws_security_group.relay]
}
