data "aws_vpc" "network" {
  id = var.network_handoff.vpc_id
}

data "aws_subnet" "transport" {
  id = var.network_handoff.subnets.public_transport_a.id
}

data "aws_route_table" "selected" {
  for_each       = var.activate_onprem_routes ? var.onprem_route_keys : toset([])
  route_table_id = var.network_handoff.subnets[each.key].route_table_id
}

data "aws_ami" "relay" {
  owners = ["125523088429"]
  filter {
    name   = "image-id"
    values = ["ami-079a2667364cee804"]
  }
  filter {
    name   = "state"
    values = ["available"]
  }
}

data "aws_iam_instance_profile" "relay" {
  name = "FDS-Relay-SSM"
  lifecycle {
    postcondition {
      condition = (
        self.arn == "arn:aws:iam::774055931866:instance-profile/FDS-Relay-SSM" &&
        self.role_arn == "arn:aws:iam::774055931866:role/FDS-Relay-SSM"
      )
      error_message = "Existing CloudFormation-owned Relay identity differs from the adopted identity."
    }
  }
}

data "aws_kms_key" "ebs" {
  key_id = "alias/aws/ebs"
}

# This root owns only its Relay SG. No additional inner ingress is inferred.
resource "aws_security_group" "relay" {
  name_prefix = "fds-relay-"
  description = "D21 Relay outer IKE/NAT-T; not full hybrid readiness"
  vpc_id      = var.network_handoff.vpc_id
  tags        = { Name = "fds-relay" }

  lifecycle {
    precondition {
      condition = (
        var.execution_enabled && terraform.workspace == "default" &&
        length(var.relay_egress) > 0 && length(trimspace(var.egress_contract_reference)) > 0
      )
      error_message = "Disabled candidate, wrong workspace, or missing reviewed egress contract. Existing GO/role/Freeze requirements still apply."
    }
    precondition {
      condition = (
        data.aws_vpc.network.cidr_block == "10.20.0.0/16" &&
        data.aws_subnet.transport.vpc_id == var.network_handoff.vpc_id &&
        data.aws_subnet.transport.cidr_block == "10.20.110.0/24" &&
        data.aws_subnet.transport.availability_zone == "ap-northeast-2a" &&
        data.aws_subnet.transport.availability_zone_id == "apne2-az1" &&
        !data.aws_subnet.transport.map_public_ip_on_launch
      )
      error_message = "Live VPC/subnet identity, geometry, AZ or automatic public IP differs from the handoff."
    }
    precondition {
      condition     = !var.activate_onprem_routes || (length(var.onprem_route_keys) > 0 && length(trimspace(var.tunnel_readiness_reference)) > 0)
      error_message = "Do not activate routes before exact target keys and actual tunnel readiness evidence are supplied."
    }
  }
}

resource "aws_vpc_security_group_ingress_rule" "ike" {
  for_each          = toset(["500", "4500"])
  security_group_id = aws_security_group.relay.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "udp"
  from_port         = tonumber(each.key)
  to_port           = tonumber(each.key)
  description       = "D21 outer IKE/NAT-T only"
}

resource "aws_vpc_security_group_egress_rule" "reviewed" {
  for_each          = var.relay_egress
  security_group_id = aws_security_group.relay.id
  cidr_ipv4         = each.value.cidr_ipv4
  ip_protocol       = each.value.protocol
  from_port         = each.value.port
  to_port           = each.value.port
  description       = each.value.description
}

resource "aws_instance" "relay" {
  ami                         = data.aws_ami.relay.id
  instance_type               = "t3.medium"
  subnet_id                   = var.network_handoff.subnets.public_transport_a.id
  private_ip                  = "10.20.110.10"
  associate_public_ip_address = false
  source_dest_check           = false
  vpc_security_group_ids      = [aws_security_group.relay.id]
  iam_instance_profile        = data.aws_iam_instance_profile.relay.name
  user_data                   = templatefile("${path.module}/bootstrap.sh.tftpl", { libreswan_package_spec = var.libreswan_package_spec })
  user_data_replace_on_change = true
  tags                        = { Name = "fds-relay" }

  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required"
  }
  credit_specification {
    cpu_credits = var.cpu_credit_mode
  }
  root_block_device {
    volume_type           = "gp3"
    volume_size           = 40
    encrypted             = true
    kms_key_id            = data.aws_kms_key.ebs.arn
    delete_on_termination = var.root_delete_on_termination
  }
  depends_on = [aws_vpc_security_group_ingress_rule.ike, aws_vpc_security_group_egress_rule.reviewed]
}

# EIP creation is downstream of the guarded instance, not an independent bypass.
resource "aws_eip" "relay" {
  domain     = "vpc"
  tags       = { Name = "fds-relay" }
  depends_on = [aws_instance.relay]
}

resource "aws_eip_association" "relay" {
  allocation_id        = aws_eip.relay.id
  network_interface_id = aws_instance.relay.primary_network_interface_id
  private_ip_address   = "10.20.110.10"
  allow_reassociation  = false
}

resource "aws_route" "onprem" {
  for_each               = var.activate_onprem_routes ? var.onprem_route_keys : toset([])
  route_table_id         = var.network_handoff.subnets[each.key].route_table_id
  destination_cidr_block = "10.1.93.0/24"
  network_interface_id   = aws_instance.relay.primary_network_interface_id
  depends_on             = [aws_eip_association.relay]
  lifecycle {
    precondition {
      condition = (
        data.aws_route_table.selected[each.key].vpc_id == var.network_handoff.vpc_id &&
        anytrue([for a in data.aws_route_table.selected[each.key].associations : a.subnet_id == var.network_handoff.subnets[each.key].id])
      )
      error_message = "Selected route table must belong to the handoff VPC and be explicitly associated with its target subnet."
    }
  }
}
