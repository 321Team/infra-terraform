provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project   = "fds-hybrid"
      ManagedBy = "terraform"
      Phase     = "phase2"
    }
  }
}
