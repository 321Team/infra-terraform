output "probe_handoff" {
  description = "Identifiers only; actual API readback, #37 T3/T6 results and destroy readback remain required."
  value = {
    instance_id          = aws_instance.probe.id
    private_ip           = aws_instance.probe.private_ip
    primary_eni_id       = aws_instance.probe.primary_network_interface_id
    security_group_id    = aws_security_group.probe.id
    subnet_id            = data.aws_subnet.probe.id
    ami_id               = data.aws_ami.probe.id
    instance_profile_arn = data.aws_iam_instance_profile.probe.arn
    expires              = var.probe_expires
    note                 = "Temporary #37 probe. Destroy and read back absence of instance, ENI and security group before Expires."
  }
}
