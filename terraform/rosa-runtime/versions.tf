terraform {
  required_version = "= 1.16.4"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "= 6.66.0"
    }
    rhcs = {
      source  = "terraform-redhat/rhcs"
      version = "= 1.7.9"
    }
  }
  backend "s3" {
    use_lockfile = true
  }
}
