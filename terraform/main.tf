terraform {
  required_version = ">= 1.0.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

data "aws_ami" "ubuntu" {
  most_recent = true
  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }
  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
  owners = ["099720109477"]
}

resource "aws_security_group" "platform_sg" {
  name        = "${var.project_name}-sg"
  description = "Allow inbound traffic for Chess Trainer Platform"

  # HTTPS - public
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }

  # HTTP - for future redirect to HTTPS
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }

  # Grafana - restricted to your IP
  ingress {
    from_port   = 3000
    to_port     = 3000
    protocol    = "tcp"
    cidr_blocks = [var.admin_ip_cidr] 
  }

  # # SSH - restricted to your IP (or remove and use SSM)
  # ingress {
  #   from_port   = 22
  #   to_port     = 22
  #   protocol    = "tcp"
  #   cidr_blocks = [var.admin_ip_cidr]
  # }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-security-group"
  }
}

# IAM Role & Profile
resource "aws_iam_role" "platform_role" {
  name = "${var.project_name}-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })
}

# Attach AWS managed SSM policy to the role
resource "aws_iam_role_policy_attachment" "ssm_policy" {
  role       = aws_iam_role.platform_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "platform_profile" {
  name = "${var.project_name}-profile"
  role = aws_iam_role.platform_role.name
}

resource "aws_instance" "platform_host" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.instance_type
  vpc_security_group_ids = [aws_security_group.platform_sg.id]
  # key_name               = var.key_pair_name
  iam_instance_profile   = aws_iam_instance_profile.platform_profile.name

  metadata_options {
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
    http_endpoint               = "enabled"
  }

  root_block_device {
    volume_size = 30
    encrypted   = true
  }

  # user_data = <<-EOF
  #   #!/bin/bash
  #   apt-get update -y
  #   apt-get upgrade -y
  #   curl -fsSL https://get.docker.com | sh
  #   systemctl start docker
  #   systemctl enable docker
  #   usermod -aG docker ubuntu
  # EOF
  user_data = <<-EOF
    #!/bin/bash
    apt-get update -y
    apt-get upgrade -y
    # Install SSM agent (usually pre-installed on Ubuntu 22.04 but just in case)
    snap install amazon-ssm-agent --classic
    systemctl enable snap.amazon-ssm-agent.amazon-ssm-agent.service
    systemctl start snap.amazon-ssm-agent.amazon-ssm-agent.service
    # Install Docker
    curl -fsSL https://get.docker.com | sh
    systemctl start docker
    systemctl enable docker
    usermod -aG docker ubuntu
  EOF

  tags = {
    Name = var.project_name
  }
}