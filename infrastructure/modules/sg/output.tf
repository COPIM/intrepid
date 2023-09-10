output "sg-out-main-sg-name" {
  value = aws_security_group.allow-ssh-and-wireguard.name
}

output "sg-out-main-sg-id" {
  value = aws_security_group.allow-ssh-and-wireguard.id
}