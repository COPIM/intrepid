# Create a VPC
resource "aws_vpc" "my_vpc" {
  cidr_block = "10.0.0.0/16"
  enable_dns_hostnames = true

  tags = {
    Name = "my_vpc"
  }
}

# Create a subnet in each availability zone in the VPC.
# Keep in mind that at this point these subnets are private without internet access.
resource "aws_subnet" "my_subnet" {
  count             = length(var.availability_zones)
  vpc_id            = aws_vpc.my_vpc.id
  cidr_block        = cidrsubnet("10.0.0.0/16", 8, count.index)
  availability_zone = var.availability_zones[count.index]
  map_public_ip_on_launch = true


  tags = {
    Name = "my-subnet-${count.index}"
  }
}

# this is the internet gateway
resource "aws_internet_gateway" "my_vpc_igw" {
  vpc_id = aws_vpc.my_vpc.id

  tags = {
    Name = "My VPC - Internet Gateway"
  }
}

# this is the public routes table

resource "aws_route_table" "my_vpc_public" {
    vpc_id = aws_vpc.my_vpc.id

    route {
        cidr_block = "0.0.0.0/0"
        gateway_id = aws_internet_gateway.my_vpc_igw.id
    }

    tags = {
        Name = "Public Subnet Route Table."
    }
}

resource "aws_route_table_association" "my_vpc_route_table_association" {
    count = length(aws_subnet.my_subnet)
    subnet_id = aws_subnet.my_subnet[count.index].id
    route_table_id = aws_route_table.my_vpc_public.id
}