# Cloudflare Data Sync Lambda Function Infrastructure
# This file contains all resources needed for the Cloudflare-to-DynamoDB sync Lambda function

# Variables for Lambda configuration
variable "cloudflare_secret_name" {
  description = "Name of the AWS Secrets Manager secret containing Cloudflare credentials"
  type        = string
  default     = "cloudflare-kv-credentials"
}

variable "lambda_function_name" {
  description = "Name of the Lambda function"
  type        = string
  default     = "cloudflare-data-sync"
}

variable "dynamodb_table_name" {
  description = "Name of the DynamoDB table for storing Cloudflare data"
  type        = string
  default     = "cloudflare-kv-data"
}

variable "lambda_timeout" {
  description = "Lambda function timeout in seconds"
  type        = number
  default     = 300
}

variable "lambda_memory_size" {
  description = "Lambda function memory size in MB"
  type        = number
  default     = 512
}

# DynamoDB table for storing Cloudflare KV data
resource "aws_dynamodb_table" "cloudflare_kv_data" {
  name           = var.dynamodb_table_name
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

  # TTL configuration for automatic data expiration
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  # Point-in-time recovery for data protection
  point_in_time_recovery {
    enabled = true
  }

  tags = {
    Name        = var.dynamodb_table_name
    Purpose     = "CloudflareDataSync"
    Environment = "production"
  }
}

# Secrets Manager secret for Cloudflare credentials
resource "aws_secretsmanager_secret" "cloudflare_credentials" {
  name        = var.cloudflare_secret_name
  description = "Cloudflare API credentials for KV namespace access"

  tags = {
    Name        = var.cloudflare_secret_name
    Purpose     = "CloudflareDataSync"
    Environment = "production"
  }
}

# Placeholder secret version - users need to update with actual credentials
resource "aws_secretsmanager_secret_version" "cloudflare_credentials" {
  secret_id = aws_secretsmanager_secret.cloudflare_credentials.id
  secret_string = jsonencode({
    api_token        = "CF_API_KV_TOKEN"
    account_id       = "CF_API_ACCOUNT_ID"
    kv_namespace_id  = "KV_NAMESPACE_ID"
    kv_namespace     = "KV_NAMESPACE"
  })

  lifecycle {
    ignore_changes = [secret_string]
  }
}

# IAM role for Lambda function
resource "aws_iam_role" "lambda_execution_role" {
  name = "${var.lambda_function_name}-execution-role"

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
    Name        = "${var.lambda_function_name}-execution-role"
    Purpose     = "CloudflareDataSync"
    Environment = "production"
  }
}

# IAM policy for Lambda function permissions
resource "aws_iam_policy" "lambda_policy" {
  name        = "${var.lambda_function_name}-policy"
  description = "IAM policy for Cloudflare data sync Lambda function"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # CloudWatch Logs permissions
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/${var.lambda_function_name}*"
      },
      # DynamoDB permissions
      {
        Effect = "Allow"
        Action = [
          "dynamodb:BatchWriteItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:GetItem",
          "dynamodb:Query",
          "dynamodb:Scan",
          "dynamodb:DescribeTable"
        ]
        Resource = [
          aws_dynamodb_table.cloudflare_kv_data.arn,
          "${aws_dynamodb_table.cloudflare_kv_data.arn}/index/*"
        ]
      },
      # Secrets Manager permissions
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = aws_secretsmanager_secret.cloudflare_credentials.arn
      },
      # X-Ray tracing permissions
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

  tags = {
    Name        = "${var.lambda_function_name}-policy"
    Purpose     = "CloudflareDataSync"
    Environment = "production"
  }
}

# Attach policy to role
resource "aws_iam_role_policy_attachment" "lambda_policy_attachment" {
  role       = aws_iam_role.lambda_execution_role.name
  policy_arn = aws_iam_policy.lambda_policy.arn
}

# Data sources for current AWS account and region
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# Lambda function
resource "aws_lambda_function" "cloudflare_data_sync" {
  filename         = "${path.module}/lambda_function.zip"
  function_name    = var.lambda_function_name
  role            = aws_iam_role.lambda_execution_role.arn
  handler         = "lambda_function.lambda_handler"
  source_code_hash = filebase64sha256("${path.module}/lambda_function.zip")
  runtime         = "python3.11"
  timeout         = var.lambda_timeout
  memory_size     = var.lambda_memory_size

  # Environment variables
  environment {
    variables = {
      SECRETS_MANAGER_SECRET_NAME = aws_secretsmanager_secret.cloudflare_credentials.name
      DYNAMODB_TABLE_NAME        = aws_dynamodb_table.cloudflare_kv_data.name
      RETRY_MAX_ATTEMPTS         = "3"
      API_TIMEOUT_SECONDS        = "30"
    }
  }

  # Enable X-Ray tracing
  tracing_config {
    mode = "Active"
  }

  # VPC configuration (optional - uncomment if Lambda needs VPC access)
  # vpc_config {
  #   subnet_ids         = var.lambda_subnet_ids
  #   security_group_ids = var.lambda_security_group_ids
  # }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_policy_attachment,
    aws_cloudwatch_log_group.lambda_logs
  ]

  tags = {
    Name        = var.lambda_function_name
    Purpose     = "CloudflareDataSync"
    Environment = "production"
  }
}

# CloudWatch Log Group for Lambda function
resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/${var.lambda_function_name}"
  retention_in_days = 14

  tags = {
    Name        = "${var.lambda_function_name}-logs"
    Purpose     = "CloudflareDataSync"
    Environment = "production"
  }
}

# Lambda function URL (optional - for HTTP invocation)
resource "aws_lambda_function_url" "cloudflare_data_sync_url" {
  function_name      = aws_lambda_function.cloudflare_data_sync.function_name
  authorization_type = "AWS_IAM"

  cors {
    allow_credentials = false
    allow_origins     = ["*"]
    allow_methods     = ["POST"]
    allow_headers     = ["date", "keep-alive"]
    expose_headers    = ["date", "keep-alive"]
    max_age          = 86400
  }
}
# Monitoring and Alerting Configuration

# Variables for monitoring configuration
variable "alert_email" {
  description = "Email address for CloudWatch alarms"
  type        = string
  default     = ""
}

variable "error_rate_threshold" {
  description = "Error rate threshold percentage for alarms"
  type        = number
  default     = 5
}

variable "duration_threshold_ms" {
  description = "Duration threshold in milliseconds for alarms"
  type        = number
  default     = 60000
}

# SNS topic for alerts (only create if email is provided)
resource "aws_sns_topic" "lambda_alerts" {
  count = var.alert_email != "" ? 1 : 0
  name  = "${var.lambda_function_name}-alerts"

  tags = {
    Name        = "${var.lambda_function_name}-alerts"
    Purpose     = "CloudflareDataSync"
    Environment = "production"
  }
}

# SNS topic subscription for email alerts
resource "aws_sns_topic_subscription" "lambda_alerts_email" {
  count     = var.alert_email != "" ? 1 : 0
  topic_arn = aws_sns_topic.lambda_alerts[0].arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# CloudWatch metric filter for error logs
resource "aws_cloudwatch_log_metric_filter" "lambda_errors" {
  name           = "${var.lambda_function_name}-errors"
  log_group_name = aws_cloudwatch_log_group.lambda_logs.name
  pattern        = "[timestamp, request_id, level=\"ERROR\", ...]"

  metric_transformation {
    name      = "${var.lambda_function_name}-ErrorCount"
    namespace = "lpl/Lambda"
    value     = "1"
  }
}

# CloudWatch metric filter for authentication errors
resource "aws_cloudwatch_log_metric_filter" "lambda_auth_errors" {
  name           = "${var.lambda_function_name}-auth-errors"
  log_group_name = aws_cloudwatch_log_group.lambda_logs.name
  pattern        = "[timestamp, request_id, level, message=\"*authentication*\" || message=\"*credential*\", ...]"

  metric_transformation {
    name      = "${var.lambda_function_name}-AuthErrorCount"
    namespace = "lpl/Lambda"
    value     = "1"
  }
}

# CloudWatch metric filter for API rate limit errors
resource "aws_cloudwatch_log_metric_filter" "lambda_rate_limit_errors" {
  name           = "${var.lambda_function_name}-rate-limit-errors"
  log_group_name = aws_cloudwatch_log_group.lambda_logs.name
  pattern        = "[timestamp, request_id, level, message=\"*rate limit*\" || message=\"*429*\", ...]"

  metric_transformation {
    name      = "${var.lambda_function_name}-RateLimitErrorCount"
    namespace = "lpl/Lambda"
    value     = "1"
  }
}

# CloudWatch metric filter for successful executions
resource "aws_cloudwatch_log_metric_filter" "lambda_success" {
  name           = "${var.lambda_function_name}-success"
  log_group_name = aws_cloudwatch_log_group.lambda_logs.name
  pattern        = "[timestamp, request_id, level=\"INFO\", message=\"*sync completed successfully*\", ...]"

  metric_transformation {
    name      = "${var.lambda_function_name}-SuccessCount"
    namespace = "lpl/Lambda"
    value     = "1"
  }
}

# CloudWatch alarm for high error rate
resource "aws_cloudwatch_metric_alarm" "lambda_error_rate" {
  count               = var.alert_email != "" ? 1 : 0
  alarm_name          = "${var.lambda_function_name}-high-error-rate"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Sum"
  threshold           = var.error_rate_threshold
  alarm_description   = "This metric monitors lambda error rate"
  alarm_actions       = [aws_sns_topic.lambda_alerts[0].arn]
  ok_actions          = [aws_sns_topic.lambda_alerts[0].arn]

  dimensions = {
    FunctionName = aws_lambda_function.cloudflare_data_sync.function_name
  }

  tags = {
    Name        = "${var.lambda_function_name}-error-rate-alarm"
    Purpose     = "CloudflareDataSync"
    Environment = "production"
  }
}

# CloudWatch alarm for high duration
resource "aws_cloudwatch_metric_alarm" "lambda_duration" {
  count               = var.alert_email != "" ? 1 : 0
  alarm_name          = "${var.lambda_function_name}-high-duration"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Average"
  threshold           = var.duration_threshold_ms
  alarm_description   = "This metric monitors lambda execution duration"
  alarm_actions       = [aws_sns_topic.lambda_alerts[0].arn]
  ok_actions          = [aws_sns_topic.lambda_alerts[0].arn]

  dimensions = {
    FunctionName = aws_lambda_function.cloudflare_data_sync.function_name
  }

  tags = {
    Name        = "${var.lambda_function_name}-duration-alarm"
    Purpose     = "CloudflareDataSync"
    Environment = "production"
  }
}

# CloudWatch alarm for authentication errors
resource "aws_cloudwatch_metric_alarm" "lambda_auth_errors" {
  count               = var.alert_email != "" ? 1 : 0
  alarm_name          = "${var.lambda_function_name}-auth-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "${var.lambda_function_name}-AuthErrorCount"
  namespace           = "lpl/Lambda"
  period              = "300"
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = "This metric monitors authentication errors in lambda function"
  alarm_actions       = [aws_sns_topic.lambda_alerts[0].arn]
  ok_actions          = [aws_sns_topic.lambda_alerts[0].arn]
  treat_missing_data  = "notBreaching"

  tags = {
    Name        = "${var.lambda_function_name}-auth-error-alarm"
    Purpose     = "CloudflareDataSync"
    Environment = "production"
  }
}

# CloudWatch alarm for throttles
resource "aws_cloudwatch_metric_alarm" "lambda_throttles" {
  count               = var.alert_email != "" ? 1 : 0
  alarm_name          = "${var.lambda_function_name}-throttles"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Throttles"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = "This metric monitors lambda throttles"
  alarm_actions       = [aws_sns_topic.lambda_alerts[0].arn]
  ok_actions          = [aws_sns_topic.lambda_alerts[0].arn]
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.cloudflare_data_sync.function_name
  }

  tags = {
    Name        = "${var.lambda_function_name}-throttle-alarm"
    Purpose     = "CloudflareDataSync"
    Environment = "production"
  }
}

# CloudWatch Dashboard for Lambda monitoring
resource "aws_cloudwatch_dashboard" "lambda_dashboard" {
  dashboard_name = "${var.lambda_function_name}-dashboard"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/Lambda", "Invocations", "FunctionName", aws_lambda_function.cloudflare_data_sync.function_name],
            [".", "Errors", ".", "."],
            [".", "Duration", ".", "."],
            [".", "Throttles", ".", "."]
          ]
          view    = "timeSeries"
          stacked = false
          region  = data.aws_region.current.name
          title   = "Lambda Function Metrics"
          period  = 300
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["lpl/Lambda", "${var.lambda_function_name}-ErrorCount"],
            [".", "${var.lambda_function_name}-AuthErrorCount"],
            [".", "${var.lambda_function_name}-RateLimitErrorCount"],
            [".", "${var.lambda_function_name}-SuccessCount"]
          ]
          view    = "timeSeries"
          stacked = false
          region  = data.aws_region.current.name
          title   = "Custom Application Metrics"
          period  = 300
        }
      },
      {
        type   = "log"
        x      = 0
        y      = 12
        width  = 24
        height = 6

        properties = {
          query   = "SOURCE '${aws_cloudwatch_log_group.lambda_logs.name}' | fields @timestamp, @message | filter @message like /ERROR/ | sort @timestamp desc | limit 20"
          region  = data.aws_region.current.name
          title   = "Recent Error Logs"
        }
      }
    ]
  })
}

# DynamoDB CloudWatch alarms
resource "aws_cloudwatch_metric_alarm" "dynamodb_throttles" {
  count               = var.alert_email != "" ? 1 : 0
  alarm_name          = "${var.dynamodb_table_name}-throttles"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "ThrottledRequests"
  namespace           = "AWS/DynamoDB"
  period              = "300"
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = "This metric monitors DynamoDB throttles"
  alarm_actions       = [aws_sns_topic.lambda_alerts[0].arn]
  ok_actions          = [aws_sns_topic.lambda_alerts[0].arn]
  treat_missing_data  = "notBreaching"

  dimensions = {
    TableName = aws_dynamodb_table.cloudflare_kv_data.name
  }

  tags = {
    Name        = "${var.dynamodb_table_name}-throttle-alarm"
    Purpose     = "CloudflareDataSync"
    Environment = "production"
  }
}

# DynamoDB error alarm
resource "aws_cloudwatch_metric_alarm" "dynamodb_errors" {
  count               = var.alert_email != "" ? 1 : 0
  alarm_name          = "${var.dynamodb_table_name}-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "SystemErrors"
  namespace           = "AWS/DynamoDB"
  period              = "300"
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = "This metric monitors DynamoDB system errors"
  alarm_actions       = [aws_sns_topic.lambda_alerts[0].arn]
  ok_actions          = [aws_sns_topic.lambda_alerts[0].arn]
  treat_missing_data  = "notBreaching"

  dimensions = {
    TableName = aws_dynamodb_table.cloudflare_kv_data.name
  }

  tags = {
    Name        = "${var.dynamodb_table_name}-error-alarm"
    Purpose     = "CloudflareDataSync"
    Environment = "production"
  }
}