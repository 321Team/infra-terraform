provider "aws" {
  region              = var.aws_region
  allowed_account_ids = ["774055931866"]

  default_tags {
    tags = {
      Project   = "fds-hybrid"
      ManagedBy = "terraform"
      Phase     = "phase2"
    }
  }
}
