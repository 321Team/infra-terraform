output "stage_a_contract" {
  description = "Topology-independent Stage-A inputs only. No AWS resource is created by the scaffold."
  value = {
    aws_region          = var.aws_region
    vpc_cidr            = var.vpc_cidr
    subnets             = var.subnets
    vpn_attachment_type = var.vpn_attachment_type
  }
}
