# P2-VPN-01 (#37) T3·T6 시험 출발지 — private_a 임시 인스턴스 1대.
# 계획: #37 6076566043, #35 수용·조건: #37 6077187634. 생성·삭제는 #35 IaC 역할(이하영)이 수행한다.
# 역할·인스턴스 프로파일은 중앙에서 만들고 여기서는 참조만 한다. 기본은 execution_enabled=false.
# 인스턴스 타입은 승인된 FDS-IaC-Vpn의 DenyRunOtherThanT3Medium에 맞춰 t3.medium이다.

locals {
  # Amazon Linux 2023 표준 이미지(SSM Agent 포함). ID는 PR에서 고정하고 생성 직전에는 동일성만 확인한다.
  probe_ami_id    = "ami-0870825cefcaafcc8"
  probe_ami_owner = "137112412989"
  probe_profile   = "FDS-P2-VPN-Probe-SSM"
  db01            = "10.1.93.55/32"
}

data "aws_vpc" "network" {
  id = var.network_handoff.vpc_id
}

data "aws_subnet" "probe" {
  id = var.network_handoff.subnets.private_a.id
  lifecycle {
    postcondition {
      condition = (
        self.vpc_id == var.network_handoff.vpc_id &&
        self.cidr_block == "10.20.10.0/24" &&
        self.availability_zone_id == "apne2-az1" &&
        !self.map_public_ip_on_launch
      )
      error_message = "Probe subnet must be the reviewed private_a (10.20.10.0/24, apne2-az1) without automatic public IP."
    }
  }
}

data "aws_ami" "probe" {
  owners = [local.probe_ami_owner]
  filter {
    name   = "image-id"
    values = [local.probe_ami_id]
  }
  filter {
    name   = "state"
    values = ["available"]
  }
  lifecycle {
    postcondition {
      condition = (
        self.id == local.probe_ami_id &&
        self.architecture == "x86_64" &&
        self.root_device_type == "ebs" &&
        startswith(self.name, "al2023-ami-2023.")
      )
      error_message = "Probe AMI differs from the pinned Amazon Linux 2023 standard x86_64 image."
    }
  }
}

data "aws_iam_instance_profile" "probe" {
  name = local.probe_profile
  lifecycle {
    postcondition {
      condition = (
        self.arn == "arn:aws:iam::774055931866:instance-profile/${local.probe_profile}" &&
        self.role_arn == "arn:aws:iam::774055931866:role/${local.probe_profile}"
      )
      error_message = "Centrally created probe identity differs from the reviewed identity."
    }
  }
}

data "aws_kms_key" "ebs" {
  key_id = "alias/aws/ebs"
}

resource "aws_security_group" "probe" {
  name_prefix = "fds-vpn-probe-"
  description = "P2-VPN-01 temporary probe: no ingress; SSM 443 and db01 5432/22 egress only"
  vpc_id      = var.network_handoff.vpc_id
  tags        = { Name = "fds-vpn-probe" }

  lifecycle {
    precondition {
      condition = (
        var.execution_enabled && terraform.workspace == "default" &&
        length(trimspace(var.probe_window_reference)) > 0
      )
      error_message = "Disabled candidate, wrong workspace, or missing #37 test-window approvals. Existing GO/role/cost requirements still apply."
    }
    precondition {
      condition = (
        data.aws_vpc.network.cidr_block == "10.20.0.0/16" &&
        data.aws_subnet.probe.vpc_id == var.network_handoff.vpc_id
      )
      error_message = "Live VPC/subnet identity differs from the handoff."
    }
  }
}

# SSM(NAT 경유). 그 밖의 인터넷 egress는 두지 않는다.
resource "aws_vpc_security_group_egress_rule" "ssm" {
  security_group_id = aws_security_group.probe.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
  description       = "SSM endpoints via NAT"
}

# T3 승인 경로. 22번은 승인 밖 포트를 SG가 아니라 Relay host FORWARD가 막는지 보려고 연다(SG 차단은 판정 불가).
resource "aws_vpc_security_group_egress_rule" "db01" {
  for_each          = { "5432" = "T3 approved DB path", "22" = "negative: non-approved port blocked at Relay FORWARD" }
  security_group_id = aws_security_group.probe.id
  cidr_ipv4         = local.db01
  ip_protocol       = "tcp"
  from_port         = tonumber(each.key)
  to_port           = tonumber(each.key)
  description       = each.value
}

resource "aws_instance" "probe" {
  ami                         = data.aws_ami.probe.id
  instance_type               = "t3.medium"
  subnet_id                   = data.aws_subnet.probe.id
  associate_public_ip_address = false
  vpc_security_group_ids      = [aws_security_group.probe.id]
  iam_instance_profile        = data.aws_iam_instance_profile.probe.name

  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required"
  }

  credit_specification {
    cpu_credits = "standard"
  }

  root_block_device {
    volume_type           = "gp3"
    volume_size           = 8
    encrypted             = true
    kms_key_id            = data.aws_kms_key.ebs.arn
    delete_on_termination = true
  }

  tags = {
    Name    = "fds-vpn-probe"
    Ticket  = "P2-VPN-01"
    Purpose = "vpn-probe"
    Owner   = "supreme33-kr"
    Expires = var.probe_expires
  }

  depends_on = [aws_vpc_security_group_egress_rule.ssm, aws_vpc_security_group_egress_rule.db01]
}
