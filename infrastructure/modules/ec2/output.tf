output "instances" {
  value = aws_instance.ubuntu
}

output "ips" {
  value = aws_instance.ubuntu.*.public_ip
}

