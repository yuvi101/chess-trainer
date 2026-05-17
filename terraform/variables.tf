variable "aws_region" {
  type        = string
  default     = "eu-central-1" # clossest to uropean users - can choose other regions
  description = "The AWS region to deploy the chess trainer infrastructure"
}

variable "instance_type" {
  type        = string
  default     = "t3.micro" 
  description = "EC2 instance size"
}

variable "project_name" {
  type        = string
  default     = "chess-trainer-platform"
  description = "Resource naming prefix"
}

variable "admin_ip_cidr" {
  description = "Your IP address in CIDR notation for admin access"
  type        = string
}