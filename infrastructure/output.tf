output "ip_addresses" {
  description = "The IP addresses of the instances"
  value       = module.ec2.ips
}

output "primary_nameservers" {
  description = "The nameservers of the primary domain"
  value       = module.route53.primary_nameservers
}

output "access_key" {
  description = "The access key of the S3 backup user"
  value       = module.s3_user.access_key_id
  sensitive   = true
}

output "backup_secret_key" {
  description = "The secret key of the S3 backup user"
  value       = module.s3_user.secret_access_key
  sensitive   = true
}

output "state_bucket_kms_id" {
  description = "The encryption ID for the state bucket"
  value       = module.remote_state.kms_key.arn
}

output "instance_ami" {
  description = "The AMI of the server"
  value = module.ec2.instances
}