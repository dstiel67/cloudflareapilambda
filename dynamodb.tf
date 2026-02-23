# Main DynamoDB Table for Failover Status
# This is the primary table used by the Kafka Consumer Lambda and Read Flags Service

resource "aws_dynamodb_table" "main" {
  name           = "${var.dynamodb_table_name}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "pk"
  range_key      = "sk"

  attribute {
    name = "pk"
    type = "S"
  }

  attribute {
    name = "sk"
    type = "S"
  }

  # TTL configuration for automatic data expiration (optional)
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  # Point-in-time recovery for data protection
  point_in_time_recovery {
    enabled = true
  }

  # Enable encryption at rest
  server_side_encryption {
    enabled = true
  }

  tags = {
    Name        = var.dynamodb_table_name
    Purpose     = "FailoverStatusManagement"
    Environment = "production"
    ManagedBy   = "terraform"
  }
}

# Output the table name and ARN
output "dynamodb_table_name" {
  description = "Name of the main DynamoDB table"
  value       = aws_dynamodb_table.main.name
}

output "dynamodb_table_arn" {
  description = "ARN of the main DynamoDB table"
  value       = aws_dynamodb_table.main.arn
}
