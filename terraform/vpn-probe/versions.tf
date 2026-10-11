terraform {
  required_version = "= 1.16.4"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "= 6.66.0"
    }
  }
  backend "s3" {
    use_lockfile = true
  }
}

provider "aws" {
  region              = "ap-northeast-2"
  allowed_account_ids = ["774055931866"]
  default_tags {
    tags = {
      Project   = "fds-hybrid"
      ManagedBy = "terraform"
      Phase     = "phase2"
      Component = "vpn-probe"
    }
  }
}
