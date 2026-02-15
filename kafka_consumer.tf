# Kafka Consumer Lambda Function
# Processes Kafka failover events and updates DynamoDB

# Lambda Function
resource "aws_lambda_function" "kafka_consumer" {
  filename         = "kafka_consumer_lambda.zip"
  function_name    = "${var.lambda_function_name}-kafka-consumer"
  role            = aws_iam_role.kafka_consumer_role.arn
  handler         = "lambda_function.lambda_handler"
  source_code_hash = filebase64sha256("kafka_consumer_lambda.zip")
  runtime         = "python3.11"
  timeout         = var.lambda_timeout
  memory_size     = var.lambda_memory_size

  environment {
    variables = {
      DYNAMODB_TABLE_NAME = var.dynamodb_table_name
    }
  }

  tracing_config {
    mode = "Active"
  }

  tags = {
    Name        = "${var.lambda_function_name}-kafka-consumer"
    Environment = "production"
    ManagedBy   = "terraform"
  }
}

# IAM Role for Kafka Consumer Lambda
resource "aws_iam_role" "kafka_consumer_role" {
  name = "${var.lambda_function_name}-kafka-consumer-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "${var.lambda_function_name}-kafka-consumer-role"
    Environment = "production"
    ManagedBy   = "terraform"
  }
}

# IAM Policy for Kafka Consumer Lambda
resource "aws_iam_role_policy" "kafka_consumer_policy" {
  name = "${var.lambda_function_name}-kafka-consumer-policy"
  role = aws_iam_role.kafka_consumer_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:*:log-group:/aws/lambda/${var.lambda_function_name}-kafka-consumer:*"
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:UpdateItem"
        ]
        Resource = aws_dynamodb_table.main.arn
      },
      {
        Effect = "Allow"
        Action = [
          "kafka:DescribeCluster",
          "kafka:GetBootstrapBrokers"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "xray:PutTraceSegments",
          "xray:PutTelemetryRecords"
        ]
        Resource = "*"
      }
    ]
  })
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "kafka_consumer_logs" {
  name              = "/aws/lambda/${var.lambda_function_name}-kafka-consumer"
  retention_in_days = 14

  tags = {
    Name        = "${var.lambda_function_name}-kafka-consumer-logs"
    Environment = "production"
    ManagedBy   = "terraform"
  }
}

# Lambda Event Source Mapping for Kafka (requires Kafka cluster ARN)
# Uncomment and configure when Kafka cluster is available
# resource "aws_lambda_event_source_mapping" "kafka_trigger" {
#   event_source_arn  = var.kafka_cluster_arn
#   function_name     = aws_lambda_function.kafka_consumer.arn
#   topics            = ["failover-events"]
#   starting_position = "LATEST"
#
#   # Optional: Configure batch size and window
#   batch_size                         = 100
#   maximum_batching_window_in_seconds = 5
# }
