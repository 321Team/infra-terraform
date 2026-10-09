# Every run uses mock providers. Never use this as AWS or Red Hat runtime evidence.
mock_provider "aws" {}

mock_provider "rhcs" {
  mock_resource "rhcs_rosa_oidc_config" {
    defaults = {
      id                = "mockoidcconfigid0000000000000000"
      oidc_endpoint_url = "https://oidc.op1.openshiftapps.com/mockoidcconfigid0000000000000000"
      thumbprint        = "0000000000000000000000000000000000000000"
    }
  }
}

variables {
  rh_support_principal_arn = "arn:aws:iam::469112722088:role/RH-Technical-Support-00000000"
}

run "disabled_without_execution_switch" {
  command         = plan
  expect_failures = [aws_iam_role.account, rhcs_rosa_oidc_config.managed]
}

run "stage1_account_roles_and_managed_oidc" {
  command = apply
  variables {
    execution_enabled = true
  }
  assert {
    condition = toset([for r in aws_iam_role.account : r.name]) == toset([
      "fds-rosa-HCP-ROSA-Installer-Role",
      "fds-rosa-HCP-ROSA-Support-Role",
      "fds-rosa-HCP-ROSA-Worker-Role",
    ])
    error_message = "Account role names must match ROSA CLI 1.2.53 manual output."
  }
  assert {
    condition = toset([for a in aws_iam_role_policy_attachment.account : a.policy_arn]) == toset([
      "arn:aws:iam::aws:policy/service-role/ROSAInstallerPolicy",
      "arn:aws:iam::aws:policy/service-role/ROSASRESupportPolicy",
      "arn:aws:iam::aws:policy/service-role/ROSAWorkerInstancePolicy",
      "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly",
    ])
    error_message = "Only the 4 policies from the CLI manual output may be attached to account roles."
  }
  assert {
    condition     = jsondecode(aws_iam_role.account["installer"].assume_role_policy).Statement[0].Principal.AWS[0] == "arn:aws:iam::710019948333:role/RH-Managed-OpenShift-Installer"
    error_message = "Installer trust must be the Red Hat installer principal."
  }
  assert {
    condition     = jsondecode(aws_iam_role.account["worker"].assume_role_policy).Statement[0].Principal.Service[0] == "ec2.amazonaws.com"
    error_message = "Worker trust must be ec2.amazonaws.com."
  }
  assert {
    condition     = alltrue([for r in aws_iam_role.account : length(jsondecode(r.assume_role_policy).Statement) == 1])
    error_message = "Each account role trust must have exactly one statement."
  }
  assert {
    condition     = alltrue([for r in aws_iam_role.account : startswith(r.name, "fds-rosa-") && r.tags["rosa_role_prefix"] == "fds-rosa" && r.tags["red-hat-managed"] == "true"])
    error_message = "Account roles need the fds-rosa prefix and ROSA CLI discovery tags."
  }
  assert {
    condition     = rhcs_rosa_oidc_config.managed.managed
    error_message = "OIDC config must be managed (no S3 / Secrets Manager)."
  }
  assert {
    condition     = toset(aws_iam_openid_connect_provider.rosa.client_id_list) == toset(["openshift", "sts.amazonaws.com"])
    error_message = "OIDC provider audiences changed."
  }
  assert {
    condition     = length(aws_iam_role.operator) == 0 && output.rosa_prereq_handoff.operator_role_prefix == null
    error_message = "Operator roles must not be created in stage 1."
  }
}

run "stage2_operator_roles" {
  command = apply
  variables {
    execution_enabled     = true
    create_operator_roles = true
  }
  assert {
    condition     = length(aws_iam_role.operator) == 8 && length(aws_iam_role_policy_attachment.operator) == 8
    error_message = "HCP needs 8 operator roles with one ROSA policy each."
  }
  assert {
    condition     = alltrue([for r in aws_iam_role.operator : length(r.name) <= 64 && (startswith(r.name, "fds-rosa-openshift-") || startswith(r.name, "fds-rosa-kube-system-"))])
    error_message = "Operator role names must fit the A3 IAM policy name patterns and the 64-character IAM limit."
  }
  assert {
    condition     = alltrue([for a in aws_iam_role_policy_attachment.operator : startswith(a.policy_arn, "arn:aws:iam::aws:policy/service-role/ROSA")])
    error_message = "Operator roles may only use AWS managed ROSA policies."
  }
  assert {
    condition     = jsondecode(aws_iam_role.operator["kms_provider"].assume_role_policy).Statement[0].Condition.StringEquals["oidc.op1.openshiftapps.com/mockoidcconfigid0000000000000000:sub"][0] == "system:serviceaccount:kube-system:kms-provider"
    error_message = "Operator trust must be scoped to the managed OIDC issuer and its service account."
  }
}
