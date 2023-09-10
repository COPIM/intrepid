variable "key_name" {
  type = string
}

variable "security_groups" {
  type = string
}

variable "availability_zones" {
  type = list(string)
}

variable "subnets" {
  type = list
}

variable "iam_instance_profile" {
  type = string
}