# ALL IDs, destinations and references in this file are synthetic MOCK fixtures.
# The AMI ID below must equal local.probe_ami_id in main.tf; the mock does not prove AWS availability.
mock_provider "aws" {}

variables {
  execution_enabled      = true
  probe_window_reference = "MOCK-ONLY-NOT-AN-APPROVAL"
  probe_expires          = "2026-10-13T23:59+09:00"
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
  target = data.aws_subnet.probe
  values = {
    id                      = "subnet-00000000000000001"
    vpc_id                  = "vpc-00000000000000001"
    cidr_block              = "10.20.10.0/24"
    availability_zone_id    = "apne2-az1"
    map_public_ip_on_launch = false
  }
}
override_data {
  target = data.aws_ami.probe
  values = {
    id               = "ami-0870825cefcaafcc8"
    architecture     = "x86_64"
    root_device_type = "ebs"
    name             = "al2023-ami-2023.12.20260930.0-kernel-6.18-x86_64"
  }
}
override_data {
  target = data.aws_iam_instance_profile.probe
  values = {
    name     = "FDS-P2-VPN-Probe-SSM"
    arn      = "arn:aws:iam::774055931866:instance-profile/FDS-P2-VPN-Probe-SSM"
    role_arn = "arn:aws:iam::774055931866:role/FDS-P2-VPN-Probe-SSM"
  }
}
override_data {
  target = data.aws_kms_key.ebs
  values = { arn = "arn:aws:kms:ap-northeast-2:774055931866:key/00000000-0000-0000-0000-000000000001" }
}

run "disabled_candidate_is_rejected" {
  command = plan
  variables { execution_enabled = false }
  expect_failures = [aws_security_group.probe]
}

run "missing_window_reference_is_rejected" {
  command = plan
  variables { probe_window_reference = "  " }
  expect_failures = [aws_security_group.probe]
}

run "bad_expiry_is_rejected" {
  command = plan
  variables { probe_expires = "tomorrow" }
  expect_failures = [var.probe_expires]
}

run "probe_controls" {
  command = plan
  assert {
    condition = (
      aws_instance.probe.instance_type == "t3.medium" &&
      aws_instance.probe.ami == "ami-0870825cefcaafcc8" &&
      aws_instance.probe.subnet_id == "subnet-00000000000000001" &&
      !aws_instance.probe.associate_public_ip_address &&
      aws_instance.probe.iam_instance_profile == "FDS-P2-VPN-Probe-SSM" &&
      aws_instance.probe.metadata_options[0].http_tokens == "required" &&
      aws_instance.probe.credit_specification[0].cpu_credits == "standard" &&
      aws_instance.probe.root_block_device[0].encrypted &&
      aws_instance.probe.root_block_device[0].volume_type == "gp3" &&
      aws_instance.probe.root_block_device[0].volume_size == 8 &&
      aws_instance.probe.root_block_device[0].delete_on_termination
    )
    error_message = "Probe instance type, AMI, subnet, IMDS, credit or EBS controls changed."
  }
  assert {
    condition = (
      aws_instance.probe.tags["Purpose"] == "vpn-probe" &&
      aws_instance.probe.tags["Ticket"] == "P2-VPN-01" &&
      aws_instance.probe.tags["Expires"] == "2026-10-13T23:59+09:00"
    )
    error_message = "Probe ownership and expiry tags are required for cleanup readback and StartSession scoping."
  }
  assert {
    condition = (
      aws_vpc_security_group_egress_rule.ssm.cidr_ipv4 == "0.0.0.0/0" &&
      aws_vpc_security_group_egress_rule.ssm.from_port == 443 &&
      length(aws_vpc_security_group_egress_rule.db01) == 2 &&
      alltrue([for r in aws_vpc_security_group_egress_rule.db01 :
        r.cidr_ipv4 == "10.1.93.55/32" && r.ip_protocol == "tcp" && contains([5432, 22], r.from_port) && r.from_port == r.to_port
      ])
    )
    error_message = "Only SSM 443 and db01 5432/22 egress belong to the probe."
  }
}

run "wrong_profile_is_rejected" {
  command = plan
  override_data {
    target = data.aws_iam_instance_profile.probe
    values = {
      name     = "FDS-Relay-SSM"
      arn      = "arn:aws:iam::774055931866:instance-profile/FDS-Relay-SSM"
      role_arn = "arn:aws:iam::774055931866:role/FDS-Relay-SSM"
    }
  }
  expect_failures = [data.aws_iam_instance_profile.probe]
}

run "public_or_wrong_subnet_is_rejected" {
  command = plan
  override_data {
    target = data.aws_subnet.probe
    values = {
      id                      = "subnet-00000000000000001"
      vpc_id                  = "vpc-00000000000000001"
      cidr_block              = "10.20.10.0/24"
      availability_zone_id    = "apne2-az1"
      map_public_ip_on_launch = true
    }
  }
  expect_failures = [data.aws_subnet.probe]
}

run "wrong_ami_is_rejected" {
  command = plan
  override_data {
    target = data.aws_ami.probe
    values = {
      id               = "ami-0870825cefcaafcc8"
      architecture     = "arm64"
      root_device_type = "ebs"
      name             = "al2023-ami-2023.12.20260930.0-kernel-6.18-arm64"
    }
  }
  expect_failures = [data.aws_ami.probe]
}
