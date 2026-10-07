# CloudFormation FDS-Central-Bootstrap-v1 owns the role/profile.
# This data source does not create, import, adopt, or attach either resource.
data "aws_iam_instance_profile" "relay" {
  name = "FDS-Relay-SSM"

  lifecycle {
    precondition {
      condition     = terraform.workspace == "default"
      error_message = "Only the approved default workspace is permitted."
    }

    postcondition {
      condition = (
        self.arn == "arn:aws:iam::774055931866:instance-profile/FDS-Relay-SSM" &&
        self.role_arn == "arn:aws:iam::774055931866:role/FDS-Relay-SSM"
      )
      error_message = "The Relay profile or role differs from the approved bootstrap identity."
    }
  }
}

output "relay_bootstrap_reference" {
  description = "Read-only bootstrap identity; this is not an EC2/Agent/runtime readiness result."
  value = {
    instance_profile_name = data.aws_iam_instance_profile.relay.name
    instance_profile_arn  = data.aws_iam_instance_profile.relay.arn
    role_arn              = data.aws_iam_instance_profile.relay.role_arn
    owner                 = "CloudFormation:FDS-Central-Bootstrap-v1"
  }
}
