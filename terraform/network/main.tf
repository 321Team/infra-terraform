# LOCAL CANDIDATE. No cloud plan/apply is authorized by this source.
provider "aws" {
  region              = "ap-northeast-2"
  allowed_account_ids = ["774055931866"]
  default_tags {
    tags = {
      Project   = "fds-hybrid"
      ManagedBy = "terraform"
      Phase     = "phase2"
      Component = "network"
    }
  }
}

# A local safety switch, not evidence of approval or a replacement for #35 gates.
variable "execution_enabled" {
  type        = bool
  default     = false
  description = "Keep false outside mock tests until exact-source review and existing execution gates are satisfied."
}

locals {
  expected_zones = {
    apne2-az1 = "ap-northeast-2a"
    apne2-az2 = "ap-northeast-2b"
    apne2-az3 = "ap-northeast-2c"
  }
  subnets = {
    private_a          = { cidr = "10.20.10.0/24", zone_id = "apne2-az1", expected_az = "ap-northeast-2a" }
    private_b          = { cidr = "10.20.20.0/24", zone_id = "apne2-az2", expected_az = "ap-northeast-2b" }
    private_c          = { cidr = "10.20.30.0/24", zone_id = "apne2-az3", expected_az = "ap-northeast-2c" }
    public_transport_a = { cidr = "10.20.110.0/24", zone_id = "apne2-az1", expected_az = "ap-northeast-2a" }
  }
}

data "aws_availability_zone" "adopted" {
  for_each = local.expected_zones
  zone_id  = each.key
  state    = "available"
}

resource "aws_vpc" "project" {
  cidr_block           = "10.20.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags                 = { Name = "fds-phase2" }

  lifecycle {
    precondition {
      condition     = var.execution_enabled && terraform.workspace == "default"
      error_message = "Local candidate is disabled, or workspace is not the approved default. Existing review/Freeze/cost/role gates still apply."
    }
    precondition {
      condition     = alltrue([for id, name in local.expected_zones : data.aws_availability_zone.adopted[id].name == name])
      error_message = "Account AZ name/Zone ID differs from the adopted mapping. Stop before creating the VPC; do not substitute an AZ."
    }
  }
}

resource "aws_subnet" "project" {
  for_each                = local.subnets
  vpc_id                  = aws_vpc.project.id
  cidr_block              = each.value.cidr
  availability_zone_id    = each.value.zone_id
  map_public_ip_on_launch = false
  tags                    = { Name = "fds-${each.key}" }

  lifecycle {
    postcondition {
      condition     = self.availability_zone == each.value.expected_az
      error_message = "Account AZ name/Zone ID differs from the adopted mapping. Stop; do not substitute an AZ."
    }
  }
}

resource "aws_internet_gateway" "transport" {
  vpc_id = aws_vpc.project.id
  tags   = { Name = "fds-transport" }
}

# No inline routes: vpn will own its standalone On-Prem route resources.
resource "aws_route_table" "subnet" {
  for_each = local.subnets
  vpc_id   = aws_vpc.project.id
  tags     = { Name = "fds-${each.key}" }
}

resource "aws_route_table_association" "subnet" {
  for_each       = local.subnets
  subnet_id      = aws_subnet.project[each.key].id
  route_table_id = aws_route_table.subnet[each.key].id
}

resource "aws_route" "transport_internet" {
  route_table_id         = aws_route_table.subnet["public_transport_a"].id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.transport.id
}

# Single NAT for platform egress (az_count 1). Separate from the Relay EIP; Relay is not an egress bypass.
resource "aws_eip" "nat" {
  domain     = "vpc"
  tags       = { Name = "fds-nat" }
  depends_on = [aws_internet_gateway.transport]
}

resource "aws_nat_gateway" "platform" {
  allocation_id     = aws_eip.nat.id
  subnet_id         = aws_subnet.project["public_transport_a"].id
  connectivity_type = "public"
  tags              = { Name = "fds-nat" }
  depends_on        = [aws_route.transport_internet]
}

# Private default route only. On-Prem routes stay with vpn; private_b/c cross AZ to the az1 NAT.
resource "aws_route" "private_egress" {
  for_each               = toset(["private_a", "private_b", "private_c"])
  route_table_id         = aws_route_table.subnet[each.key].id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = aws_nat_gateway.platform.id
}
