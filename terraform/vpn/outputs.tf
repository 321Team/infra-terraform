output "relay_handoff" {
  description = "Identifiers only; actual API readback and #37 acceptance remain required."
  value = {
    instance_id           = aws_instance.relay.id
    primary_eni_id        = aws_instance.relay.primary_network_interface_id
    eip_allocation_id     = aws_eip.relay.id
    eip                   = aws_eip.relay.public_ip
    security_group_id     = aws_security_group.relay.id
    vpc_id                = var.network_handoff.vpc_id
    subnet_id             = var.network_handoff.subnets.public_transport_a.id
    instance_profile_arn  = data.aws_iam_instance_profile.relay.arn
    role_arn              = data.aws_iam_instance_profile.relay.role_arn
    ebs_key_arn           = data.aws_kms_key.ebs.arn
    root_volume_id        = aws_instance.relay.root_block_device[0].volume_id
    delete_on_termination = var.root_delete_on_termination
    route_targets         = { for k, r in aws_route.onprem : k => r.route_table_id }
    stage_a_ready         = false
    tunnel_configuration  = "#37 session only; not in Terraform"
    session_document      = "#35 create-only opt-in here; actual owner/default version/content readback required"
  }
}
