terraform {
  required_version = ">= 1.0"

  # Local backend — S3 doesn't exist yet when bootstrap runs.
  # After bootstrap, all other modules use the S3 backend it creates.
  backend "local" {}

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  profile = "terraform"
  region  = "ap-south-1"
}
