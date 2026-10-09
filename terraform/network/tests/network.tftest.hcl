# Every run uses a mock provider. Never use this as AWS runtime evidence.
mock_provider "aws" {}

override_data {
  target = data.aws_availability_zone.adopted["apne2-az1"]
  values = { name = "ap-northeast-2a" }
}
override_data {
  target = data.aws_availability_zone.adopted["apne2-az2"]
  values = { name = "ap-northeast-2b" }
}
override_data {
  target = data.aws_availability_zone.adopted["apne2-az3"]
  values = { name = "ap-northeast-2c" }
}

run "disabled_without_execution_switch" {
  command         = plan
  expect_failures = [aws_vpc.project]
}

run "adopted_geometry_and_minimum_public_route" {
  command = plan
  variables {
    execution_enabled = true
  }
  assert {
    condition     = aws_vpc.project.cidr_block == "10.20.0.0/16" && length(aws_subnet.project) == 4
    error_message = "Adopted VPC/subnet geometry changed."
  }
  assert {
    condition     = alltrue([for s in aws_subnet.project : !s.map_public_ip_on_launch])
    error_message = "No subnet may assign an automatic public IPv4. Relay uses its dedicated EIP."
  }
  assert {
    condition     = length(aws_route_table.subnet) == 4 && length(aws_route_table_association.subnet) == 4
    error_message = "Every subnet needs an explicit route table and association."
  }
  assert {
    condition     = aws_route.transport_internet.destination_cidr_block == "0.0.0.0/0" && !output.network_handoff.stage_a_ready
    error_message = "Transport route or incomplete readiness marker changed."
  }
}

run "single_nat_private_egress" {
  command = plan
  variables {
    execution_enabled = true
  }
  assert {
    condition     = aws_eip.nat.domain == "vpc" && aws_nat_gateway.platform.connectivity_type == "public"
    error_message = "NAT must be one public NAT with its own VPC EIP."
  }
  assert {
    condition     = length(aws_route.private_egress) == 3 && alltrue([for r in aws_route.private_egress : r.destination_cidr_block == "0.0.0.0/0"])
    error_message = "Exactly private_a/b/c receive the default route to NAT."
  }
  assert {
    condition     = !contains(keys(aws_route.private_egress), "public_transport_a")
    error_message = "Transport subnet must keep its IGW route, not NAT."
  }
}

run "wrong_account_az_mapping_is_rejected" {
  command = plan
  variables {
    execution_enabled = true
  }
  override_data {
    target = data.aws_availability_zone.adopted["apne2-az1"]
    values = { name = "ap-northeast-2z" }
  }
  expect_failures = [aws_vpc.project]
}
