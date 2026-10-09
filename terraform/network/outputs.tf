output "network_handoff" {
  description = "Non-secret identity for later VPN/ROSA roots. Not a runtime acceptance or Stage-A readiness result."
  value = {
    region   = "ap-northeast-2"
    vpc_id   = aws_vpc.project.id
    vpc_cidr = aws_vpc.project.cidr_block
    igw_id   = aws_internet_gateway.transport.id
    nat_id   = aws_nat_gateway.platform.id
    subnets = {
      for name, subnet in aws_subnet.project : name => {
        id             = subnet.id
        cidr           = subnet.cidr_block
        zone_id        = subnet.availability_zone_id
        route_table_id = aws_route_table.subnet[name].id
      }
    }
    hybrid_routes_owner = "vpn (not implemented in this candidate)"
    stage_a_ready       = false
  }
}
