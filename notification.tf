# Notification Infrastructure for SSE (Server-Sent Events)
# This file contains resources for real-time notifications to Angular web clients

# Variables for notification configuration
variable "notification_lambda_function_name" {
  description = "Name of the notification Lambda function"
  type        = string
  default     = "cloudflare-notification-handler"
}

variable "sse_lambda_function_name" {
  description = "Name of the SSE endpoint Lambda function"
  type        = string
  default     = "cloudflare-sse-endpoint"
}

variable "sse_messages_table_name" {
  description = "Name of the DynamoDB table for SSE messages"
  type        = string
  default     = "cloudflare-sse-messages"
}

variable "api_gateway_name" {
  description = "Name of the API Gateway for SSE endpoint"
  type        = string
  default     = "cloudflare-sse-api"
}

# DynamoDB table for SSE messages
resource "aws_dynamodb_table" "sse_messages" {
  name           = var.sse_messages_table_name
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "message_id"

  attribute {
    name = "message_id"
    type = "S"
  }

  # TTL configuration for automatic message cleanup
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  tags = {
    Name        = var.sse_messages_table_name
    Purpose     = "CloudflareSSEMessages"
    Environment = "production"
  }
}

# Enable DynamoDB Streams on the main Cloudflare data table
resource "aws_dynamodb_table" "cloudflare_kv_data_with_stream" {
  name           = "${var.dynamodb_table_name}-with-stream"
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

  # Enable DynamoDB Streams
  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"

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
    Name        = "${var.dynamodb_table_name}-with-stream"
    Purpose     = "CloudflareDataSyncWithStream"
    Environment = "production"
  }
}

# Build notification Lambda package
resource "null_resource" "notification_lambda_build" {
  triggers = {
    source_hash = fileexists("${path.module}/notification_lambda/lambda_function.py") ? filesha256("${path.module}/notification_lambda/lambda_function.py") : ""
    requirements_hash = fileexists("${path.module}/notification_lambda/requirements.txt") ? filesha256("${path.module}/notification_lambda/requirements.txt") : ""
  }

  provisioner "local-exec" {
    command = "./build_notification_lambda.sh"
    working_dir = path.module
  }
}

# Build SSE Lambda package
resource "null_resource" "sse_lambda_build" {
  triggers = {
    source_hash = fileexists("${path.module}/sse_lambda/lambda_function.py") ? filesha256("${path.module}/sse_lambda/lambda_function.py") : ""
    requirements_hash = fileexists("${path.module}/sse_lambda/requirements.txt") ? filesha256("${path.module}/sse_lambda/requirements.txt") : ""
  }

  provisioner "local-exec" {
    command = "./build_sse_lambda.sh"
    working_dir = path.module
  }
}

# IAM role for notification Lambda function
resource "aws_iam_role" "notification_lambda_role" {
  name = "${var.notification_lambda_function_name}-role"

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
    Name        = "${var.notification_lambda_function_name}-role"
    Purpose     = "CloudflareNotification"
    Environment = "production"
  }
}

# IAM policy for notification Lambda function
resource "aws_iam_policy" "notification_lambda_policy" {
  name        = "${var.notification_lambda_function_name}-policy"
  description = "IAM policy for notification Lambda function"

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
        Resource = "arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/${var.notification_lambda_function_name}*"
      },
      # DynamoDB permissions for SSE messages table
      {
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:GetItem"
        ]
        Resource = aws_dynamodb_table.sse_messages.arn
      },
      # DynamoDB Streams permissions
      {
        Effect = "Allow"
        Action = [
          "dynamodb:DescribeStream",
          "dynamodb:GetRecords",
          "dynamodb:GetShardIterator",
          "dynamodb:ListStreams"
        ]
        Resource = "${aws_dynamodb_table.cloudflare_kv_data_with_stream.arn}/stream/*"
      }
    ]
  })

  tags = {
    Name        = "${var.notification_lambda_function_name}-policy"
    Purpose     = "CloudflareNotification"
    Environment = "production"
  }
}

# Attach policy to notification Lambda role
resource "aws_iam_role_policy_attachment" "notification_lambda_policy_attachment" {
  role       = aws_iam_role.notification_lambda_role.name
  policy_arn = aws_iam_policy.notification_lambda_policy.arn
}

# IAM role for SSE Lambda function
resource "aws_iam_role" "sse_lambda_role" {
  name = "${var.sse_lambda_function_name}-role"

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
    Name        = "${var.sse_lambda_function_name}-role"
    Purpose     = "CloudflareSSE"
    Environment = "production"
  }
}

# IAM policy for SSE Lambda function
resource "aws_iam_policy" "sse_lambda_policy" {
  name        = "${var.sse_lambda_function_name}-policy"
  description = "IAM policy for SSE Lambda function"

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
        Resource = "arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/${var.sse_lambda_function_name}*"
      },
      # DynamoDB permissions for SSE messages table
      {
        Effect = "Allow"
        Action = [
          "dynamodb:Scan",
          "dynamodb:UpdateItem",
          "dynamodb:GetItem"
        ]
        Resource = aws_dynamodb_table.sse_messages.arn
      }
    ]
  })

  tags = {
    Name        = "${var.sse_lambda_function_name}-policy"
    Purpose     = "CloudflareSSE"
    Environment = "production"
  }
}

# Attach policy to SSE Lambda role
resource "aws_iam_role_policy_attachment" "sse_lambda_policy_attachment" {
  role       = aws_iam_role.sse_lambda_role.name
  policy_arn = aws_iam_policy.sse_lambda_policy.arn
}

# CloudWatch Log Group for notification Lambda function
resource "aws_cloudwatch_log_group" "notification_lambda_logs" {
  name              = "/aws/lambda/${var.notification_lambda_function_name}"
  retention_in_days = 14

  tags = {
    Name        = "${var.notification_lambda_function_name}-logs"
    Purpose     = "CloudflareNotification"
    Environment = "production"
  }
}

# CloudWatch Log Group for SSE Lambda function
resource "aws_cloudwatch_log_group" "sse_lambda_logs" {
  name              = "/aws/lambda/${var.sse_lambda_function_name}"
  retention_in_days = 14

  tags = {
    Name        = "${var.sse_lambda_function_name}-logs"
    Purpose     = "CloudflareSSE"
    Environment = "production"
  }
}

# Notification Lambda function
resource "aws_lambda_function" "notification_handler" {
  filename         = "${path.module}/notification_lambda.zip"
  function_name    = var.notification_lambda_function_name
  role            = aws_iam_role.notification_lambda_role.arn
  handler         = "lambda_function.lambda_handler"
  source_code_hash = filebase64sha256("${path.module}/notification_lambda.zip")
  runtime         = "python3.11"
  timeout         = 60
  memory_size     = 256

  environment {
    variables = {
      SSE_MESSAGES_TABLE_NAME = aws_dynamodb_table.sse_messages.name
    }
  }

  # Dead Letter Queue configuration
  dead_letter_config {
    target_arn = aws_sqs_queue.notification_lambda_dlq.arn
  }

  depends_on = [
    aws_iam_role_policy_attachment.notification_lambda_policy_attachment,
    aws_iam_role_policy_attachment.notification_lambda_dlq_policy_attachment,
    aws_cloudwatch_log_group.notification_lambda_logs,
    null_resource.notification_lambda_build
  ]

  tags = {
    Name        = var.notification_lambda_function_name
    Purpose     = "CloudflareNotification"
    Environment = "production"
  }
}

# SSE endpoint Lambda function
resource "aws_lambda_function" "sse_endpoint" {
  filename         = "${path.module}/sse_lambda.zip"
  function_name    = var.sse_lambda_function_name
  role            = aws_iam_role.sse_lambda_role.arn
  handler         = "lambda_function.lambda_handler"
  source_code_hash = filebase64sha256("${path.module}/sse_lambda.zip")
  runtime         = "python3.11"
  timeout         = 30
  memory_size     = 256

  environment {
    variables = {
      SSE_MESSAGES_TABLE_NAME = aws_dynamodb_table.sse_messages.name
    }
  }

  # Dead Letter Queue configuration
  dead_letter_config {
    target_arn = aws_sqs_queue.sse_lambda_dlq.arn
  }

  depends_on = [
    aws_iam_role_policy_attachment.sse_lambda_policy_attachment,
    aws_iam_role_policy_attachment.sse_lambda_dlq_policy_attachment,
    aws_cloudwatch_log_group.sse_lambda_logs,
    null_resource.sse_lambda_build
  ]

  tags = {
    Name        = var.sse_lambda_function_name
    Purpose     = "CloudflareSSE"
    Environment = "production"
  }
}

# DynamoDB Stream event source mapping for notification Lambda
resource "aws_lambda_event_source_mapping" "dynamodb_stream" {
  event_source_arn  = aws_dynamodb_table.cloudflare_kv_data_with_stream.stream_arn
  function_name     = aws_lambda_function.notification_handler.arn
  starting_position = "LATEST"
  batch_size        = 10
  maximum_batching_window_in_seconds = 5

  # Filter to only process records for the specific key
  filter_criteria {
    filter {
      pattern = jsonencode({
        dynamodb = {
          NewImage = {
            key_name = {
              S = ["redirect-all-users-to-essentials"]
            }
          }
        }
      })
    }
  }

  depends_on = [aws_iam_role_policy_attachment.notification_lambda_policy_attachment]
}

# API Gateway for SSE endpoint
resource "aws_api_gateway_rest_api" "sse_api" {
  name        = var.api_gateway_name
  description = "API Gateway for Server-Sent Events endpoint"

  endpoint_configuration {
    types = ["REGIONAL"]
  }

  tags = {
    Name        = var.api_gateway_name
    Purpose     = "CloudflareSSE"
    Environment = "production"
  }
}

# API Gateway resource for events endpoint
resource "aws_api_gateway_resource" "events" {
  rest_api_id = aws_api_gateway_rest_api.sse_api.id
  parent_id   = aws_api_gateway_rest_api.sse_api.root_resource_id
  path_part   = "events"
}

# API Gateway resource for health endpoint
resource "aws_api_gateway_resource" "health" {
  rest_api_id = aws_api_gateway_rest_api.sse_api.id
  parent_id   = aws_api_gateway_rest_api.sse_api.root_resource_id
  path_part   = "health"
}

# API Gateway method for events GET
resource "aws_api_gateway_method" "events_get" {
  rest_api_id   = aws_api_gateway_rest_api.sse_api.id
  resource_id   = aws_api_gateway_resource.events.id
  http_method   = "GET"
  authorization = "NONE"
}

# API Gateway method for events OPTIONS (CORS)
resource "aws_api_gateway_method" "events_options" {
  rest_api_id   = aws_api_gateway_rest_api.sse_api.id
  resource_id   = aws_api_gateway_resource.events.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

# API Gateway method for health GET
resource "aws_api_gateway_method" "health_get" {
  rest_api_id   = aws_api_gateway_rest_api.sse_api.id
  resource_id   = aws_api_gateway_resource.health.id
  http_method   = "GET"
  authorization = "NONE"
}

# API Gateway integration for events GET
resource "aws_api_gateway_integration" "events_get_integration" {
  rest_api_id = aws_api_gateway_rest_api.sse_api.id
  resource_id = aws_api_gateway_resource.events.id
  http_method = aws_api_gateway_method.events_get.http_method

  integration_http_method = "POST"
  type                   = "AWS_PROXY"
  uri                    = aws_lambda_function.sse_endpoint.invoke_arn
}

# API Gateway integration for events OPTIONS
resource "aws_api_gateway_integration" "events_options_integration" {
  rest_api_id = aws_api_gateway_rest_api.sse_api.id
  resource_id = aws_api_gateway_resource.events.id
  http_method = aws_api_gateway_method.events_options.http_method

  integration_http_method = "POST"
  type                   = "AWS_PROXY"
  uri                    = aws_lambda_function.sse_endpoint.invoke_arn
}

# API Gateway integration for health GET
resource "aws_api_gateway_integration" "health_get_integration" {
  rest_api_id = aws_api_gateway_rest_api.sse_api.id
  resource_id = aws_api_gateway_resource.health.id
  http_method = aws_api_gateway_method.health_get.http_method

  integration_http_method = "POST"
  type                   = "AWS_PROXY"
  uri                    = aws_lambda_function.sse_endpoint.invoke_arn
}

# Lambda permission for API Gateway to invoke SSE endpoint
resource "aws_lambda_permission" "api_gateway_invoke_sse" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.sse_endpoint.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.sse_api.execution_arn}/*/*"
}

# API Gateway deployment
resource "aws_api_gateway_deployment" "sse_api_deployment" {
  depends_on = [
    aws_api_gateway_integration.events_get_integration,
    aws_api_gateway_integration.events_options_integration,
    aws_api_gateway_integration.health_get_integration
  ]

  rest_api_id = aws_api_gateway_rest_api.sse_api.id

  lifecycle {
    create_before_destroy = true
  }
}

# API Gateway stage
resource "aws_api_gateway_stage" "sse_api_stage" {
  deployment_id = aws_api_gateway_deployment.sse_api_deployment.id
  rest_api_id   = aws_api_gateway_rest_api.sse_api.id
  stage_name    = "prod"

  tags = {
    Name        = "${var.api_gateway_name}-prod-stage"
    Purpose     = "CloudflareSSE"
    Environment = "production"
  }
}