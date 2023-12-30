terraform {
  required_providers {
    aws = {
      source = "hashicorp/aws"
    }
  }
  backend "s3" {
    bucket         = "state-openbookcollective"
    key            = "obc/terraform.tfstate"
    region         = "eu-west-2"
    encrypt        = true
    kms_key_id     = "arn:aws:kms:eu-west-2:193177445855:key/36aadd5a-8fa7-4f19-b806-85221e9c3977"
    dynamodb_table = "lock-openbookcollective"
  }
}

provider "aws" {
  region = var.region
}

module "sg" {
  source     = "./modules/sg"
  vpc        = module.vpc.vpc
  depends_on = [module.vpc]
}

module "key" {
  source = "./modules/key"
}

module "route53" {
  source      = "./modules/route53"
  # primary_ip  = module.ec2.ips[0]
  primary_ip  = "18.170.47.219"
  domain_name = var.domain_name
}

module "vpc" {
  source             = "./modules/vpc"
  availability_zones = var.availability_zones
}

module "ec2" {
  source             = "./modules/ec2"
  key_name           = module.key.wirevpn-key
  security_groups    = module.sg.sg-out-main-sg-id
  iam_instance_profile  = aws_iam_instance_profile.s3-instance-profile.name
  availability_zones = var.availability_zones
  subnets            = module.vpc.subnets
  depends_on = [
    module.sg,
    module.key,
    module.vpc
  ]
}

# ansible configuration
module "ansible" {
  source     = "./modules/ansible"
  depends_on = [module.ec2]
  ips        = module.ec2.ips
}


# block storage
module "ebs" {
  source     = "./modules/ebs"
  instances  = [module.ec2.instances]
  depends_on = [module.ec2]
}


# s3 storage for backups
module "s3-private-bucket" {
  source                   = "registry.terraform.io/trussworks/s3-private-bucket/aws"
  version                  = "4.0.0"
  bucket                   = "openbookcollectivebackup"
  use_account_alias_prefix = false
}

module "s3_user" {
  source = "registry.terraform.io/cloudposse/iam-s3-user/aws"

  version      = "0.15.9"
  namespace    = "openbookcollective"
  stage        = "production"
  name         = "obc"
  s3_actions   = ["s3:*", "kms:Decrypt", "kms:GenerateDataKey"]
  s3_resources = [module.s3-private-bucket.arn, "${module.s3-private-bucket.arn}/*"]
}

provider "aws" {
  alias  = "replica"
  region = "eu-west-2"
}

module "remote_state" {
  source  = "registry.terraform.io/nozaq/remote-state-s3-backend/aws"
  version = "1.2.0"

  override_s3_bucket_name = true
  s3_bucket_name          = "state-openbookcollective"
  dynamodb_table_name     = "lock-openbookcollective"

  noncurrent_version_transitions = []
  noncurrent_version_expiration = {
    days = 90
  }

  providers = {
    aws         = aws
    aws.replica = aws.replica
  }
}

resource "aws_iam_policy" "s3-policy" {
  name        = "S3-Bucket-Access-Policy"
  description = "Provides permission to access S3"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "s3:*",
        ]
        Effect   = "Allow"
        Resource = ["arn:aws:s3:::*" ]
      },
    ]
  })
}

resource "aws_iam_role" "s3-role" {
  name = "ec2_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Sid    = "RoleForEC2"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      },
    ]
  })
}

resource "aws_iam_role_policy_attachment" "s3-role-policy-attachment" {
  role       = aws_iam_role.s3-role.name
  policy_arn = aws_iam_policy.s3-policy.arn
}

resource "aws_iam_instance_profile" "s3-instance-profile" {
  name = "ec2_instance_profile"
  role = aws_iam_role.s3-role.name
}
