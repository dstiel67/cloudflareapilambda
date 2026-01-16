# AWS Configuration
variable "aws_region" {
  description = "AWS region for Lambda function and DynamoDB"
  type        = string
  default     = "us-east-1"
}
