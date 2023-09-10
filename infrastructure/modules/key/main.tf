resource "aws_key_pair" "martin" {
  key_name   = "aws_key"
  public_key = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAINFGSc/zIId1CbzNQRgZ9YbTZNVHy0ar3mnZgfSYV8Vi martin@rocket"
}