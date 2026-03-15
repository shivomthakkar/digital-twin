terraform {
  required_version = ">= 1.0"

  # Partial S3 backend — static fields only.
  # The following are injected via -backend-config flags at init time:
  #   bucket         = "twin-terraform-state-<account_id>"
  #   key            = "foundation/<env>/terraform.tfstate"
  #   dynamodb_table = "twin-terraform-locks"
  backend "s3" {
    region  = "ap-south-1"
    profile = "terraform"
    encrypt = true
  }

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

# Required for ACM certificates (CloudFront mandates us-east-1)
provider "aws" {
  profile = "terraform"
  alias   = "us_east_1"
  region  = "us-east-1"
}
