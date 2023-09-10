variable "domain_name" {
  type        = string
  description = "The domain name for the website."
}

variable "common_tags" {
  description = "Common tags you want applied to all components."
}


variable "availability_zones" {
  type    = list(string)
  default = ["eu-west-2a"]
}

variable "region" {
  type    = string
  default = "eu-west-2"
}


