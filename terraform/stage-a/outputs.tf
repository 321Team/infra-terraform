output "stage_a_contract" {
  description = "Architecture-frozen Stage-A inputs only. No AWS resource is created by the scaffold."
  value = {
    aws_region             = var.aws_region
    vpc_cidr               = var.vpc_cidr
    transport_adapter_type = var.transport_adapter_type
    subnets                = var.subnets
    relay                  = var.relay

    logical_state_boundaries = [
      "network",
      "vpn",
      "rosa-prereq",
      "rosa-runtime",
    ]

    onprem_return_route = {
      minimum_host = "10.1.93.55"
      destination  = "10.20.0.0/16"
      via          = "10.1.93.51"
    }
  }
}
