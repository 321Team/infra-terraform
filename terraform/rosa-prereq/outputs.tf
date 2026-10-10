output "rosa_prereq_handoff" {
  description = "Inputs for infra-rosa#4 cluster creation. Operator role prefix is set only after stage 2."
  value = {
    account_role_prefix  = local.prefix
    installer_role_arn   = aws_iam_role.account["installer"].arn
    support_role_arn     = aws_iam_role.account["support"].arn
    worker_role_arn      = aws_iam_role.account["worker"].arn
    oidc_config_id       = rhcs_rosa_oidc_config.managed.id
    oidc_provider_arn    = aws_iam_openid_connect_provider.rosa.arn
    operator_role_prefix = var.create_operator_roles ? local.prefix : null
    operator_role_arns   = { for k, r in aws_iam_role.operator : k => r.arn }
  }
}
