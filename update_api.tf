# Update API Infrastructure
# This file contains resources for the redirect status update API

# Variables for update API configuration
variable "update_lambda_function_name" {
  description = "Name of the update Lambda function"
  type        = string
  default     = "redirect-status-update"
}

variable "update_api_gateway_name" {
  description = "Name of the API Gateway for update endpoint"
  type        = string
  default     = "redirect-status-api"
}

# Build update Lambda package
resource "null_resource" "update_lambda_build" {
  triggers = {
    source_hash = fileexists("${path.module}/update_lambda/lambda_function.py") ? filesha256("${path.module}/update_lambda/lambda_function.py") : ""
    requirements_hash = fileexists("${path.module}/update_lambda/requirements.txt") ? filesha256("${path.module}/update_lambda/requirements.txt") : ""
  }

  provisioner "local-exec" {
    command = "./build_update_lambda.sh"
    working_dir = path.module
  }
}

# IAM role for update Lambda function
resource "aws_iam_role" "update_lambda_role" {
  name = "${var.update_lambda_function_name}-role"

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
    Name        = "${var.update_lambda_function_name}-role"
    Purpose     = "RedirectStatusUpdate"
    Environment = "production"
  }
}

# IAM policy for update Lambda function
resource "aws_iam_policy" "update_lambda_policy" {
  name        = "${var.update_lambda_function_name}-policy"
  description = "IAM policy for update Lambda function"

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
        Resource = "arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/${var.update_lambda_function_name}*"
      },
      # DynamoDB permissions
      {
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:GetItem",
          "dynamodb:Query"
        ]
        Resource = aws_dynamodb_table.cloudflare_kv_data_with_stream.arn
      }
    ]
  })

  tags = {
    Name        = "${var.update_lambda_function_name}-policy"
    Purpose     = "RedirectStatusUpdate"
    Environment = "production"
  }
}

# Attach policy to update Lambda role
resource "aws_iam_role_policy_attachment" "update_lambda_policy_attachment" {
  role       = aws_iam_role.update_lambda_role.name
  policy_arn = aws_iam_policy.update_lambda_policy.arn
}

# CloudWatch Log Group for update Lambda function
resource "aws_cloudwatch_log_group" "update_lambda_logs" {
  name              = "/aws/lambda/${var.update_lambda_function_name}"
  retention_in_days = 14

  tags = {
    Name        = "${var.update_lambda_function_name}-logs"
    Purpose     = "RedirectStatusUpdate"
    Environment = "production"
  }
}

# Update Lambda function
resource "aws_lambda_function" "redirect_status_update" {
  filename         = "${path.module}/update_lambda.zip"
  function_name    = var.update_lambda_function_name
  role            = aws_iam_role.update_lambda_role.arn
  handler         = "lambda_function.lambda_handler"
  source_code_hash = filebase64sha256("${path.module}/update_lambda.zip")
  runtime         = "python3.11"
  timeout         = 30
  memory_size     = 256

  environment {
    variables = {
      DYNAMODB_TABLE_NAME = aws_dynamodb_table.cloudflare_kv_data_with_stream.name
    }
  }

  # Dead Letter Queue configuration
  dead_letter_config {
    target_arn = aws_sqs_queue.update_lambda_dlq.arn
  }

  depends_on = [
    aws_iam_role_policy_attachment.update_lambda_policy_attachment,
    aws_iam_role_policy_attachment.update_lambda_dlq_policy_attachment,
    aws_cloudwatch_log_group.update_lambda_logs,
    null_resource.update_lambda_build
  ]

  tags = {
    Name        = var.update_lambda_function_name
    Purpose     = "RedirectStatusUpdate"
    Environment = "production"
  }
}

# API Gateway for update endpoint
resource "aws_api_gateway_rest_api" "update_api" {
  name        = var.update_api_gateway_name
  description = "API Gateway for redirect status update endpoint"

  endpoint_configuration {
    types = ["REGIONAL"]
  }

  tags = {
    Name        = var.update_api_gateway_name
    Purpose     = "RedirectStatusUpdate"
    Environment = "production"
  }
}

# API Gateway resource for redirect-status endpoint
resource "aws_api_gateway_resource" "redirect_status" {
  rest_api_id = aws_api_gateway_rest_api.update_api.id
  parent_id   = aws_api_gateway_rest_api.update_api.root_resource_id
  path_part   = "redirect-status"
}

# API Gateway resource for health endpoint
resource "aws_api_gateway_resource" "update_health" {
  rest_api_id = aws_api_gateway_rest_api.update_api.id
  parent_id   = aws_api_gateway_rest_api.update_api.root_resource_id
  path_part   = "health"
}

# API Gateway method for redirect-status POST
resource "aws_api_gateway_method" "redirect_status_post" {
  rest_api_id   = aws_api_gateway_rest_api.update_api.id
  resource_id   = aws_api_gateway_resource.redirect_status.id
  http_method   = "POST"
  authorization = "NONE"
  api_key_required = true  # Require API key for authentication
}

# API Gateway method for redirect-status GET
resource "aws_api_gateway_method" "redirect_status_get" {
  rest_api_id   = aws_api_gateway_rest_api.update_api.id
  resource_id   = aws_api_gateway_resource.redirect_status.id
  http_method   = "GET"
  authorization = "NONE"
  api_key_required = true  # Require API key for authentication
}

# API Gateway method for redirect-status OPTIONS (CORS)
resource "aws_api_gateway_method" "redirect_status_options" {
  rest_api_id   = aws_api_gateway_rest_api.update_api.id
  resource_id   = aws_api_gateway_resource.redirect_status.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

# API Gateway method for health GET
resource "aws_api_gateway_method" "update_health_get" {
  rest_api_id   = aws_api_gateway_rest_api.update_api.id
  resource_id   = aws_api_gateway_resource.update_health.id
  http_method   = "GET"
  authorization = "NONE"
}

# API Gateway integration for redirect-status POST
resource "aws_api_gateway_integration" "redirect_status_post_integration" {
  rest_api_id = aws_api_gateway_rest_api.update_api.id
  resource_id = aws_api_gateway_resource.redirect_status.id
  http_method = aws_api_gateway_method.redirect_status_post.http_method

  integration_http_method = "POST"
  type                   = "AWS_PROXY"
  uri                    = aws_lambda_function.redirect_status_update.invoke_arn
}

# API Gateway integration for redirect-status GET
resource "aws_api_gateway_integration" "redirect_status_get_integration" {
  rest_api_id = aws_api_gateway_rest_api.update_api.id
  resource_id = aws_api_gateway_resource.redirect_status.id
  http_method = aws_api_gateway_method.redirect_status_get.http_method

  integration_http_method = "POST"
  type                   = "AWS_PROXY"
  uri                    = aws_lambda_function.redirect_status_update.invoke_arn
}

# API Gateway integration for redirect-status OPTIONS
resource "aws_api_gateway_integration" "redirect_status_options_integration" {
  rest_api_id = aws_api_gateway_rest_api.update_api.id
  resource_id = aws_api_gateway_resource.redirect_status.id
  http_method = aws_api_gateway_method.redirect_status_options.http_method

  integration_http_method = "POST"
  type                   = "AWS_PROXY"
  uri                    = aws_lambda_function.redirect_status_update.invoke_arn
}

# API Gateway integration for health GET
resource "aws_api_gateway_integration" "update_health_get_integration" {
  rest_api_id = aws_api_gateway_rest_api.update_api.id
  resource_id = aws_api_gateway_resource.update_health.id
  http_method = aws_api_gateway_method.update_health_get.http_method

  integration_http_method = "POST"
  type                   = "AWS_PROXY"
  uri                    = aws_lambda_function.redirect_status_update.invoke_arn
}

# Lambda permission for API Gateway to invoke update endpoint
resource "aws_lambda_permission" "api_gateway_invoke_update" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.redirect_status_update.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.update_api.execution_arn}/*/*"
}

# API Gateway deployment
resource "aws_api_gateway_deployment" "update_api_deployment" {
  depends_on = [
    aws_api_gateway_integration.redirect_status_post_integration,
    aws_api_gateway_integration.redirect_status_get_integration,
    aws_api_gateway_integration.redirect_status_options_integration,
    aws_api_gateway_integration.update_health_get_integration
  ]

  rest_api_id = aws_api_gateway_rest_api.update_api.id

  lifecycle {
    create_before_destroy = true
  }
}

# API Gateway stage
resource "aws_api_gateway_stage" "update_api_stage" {
  deployment_id = aws_api_gateway_deployment.update_api_deployment.id
  rest_api_id   = aws_api_gateway_rest_api.update_api.id
  stage_name    = "prod"

  tags = {
    Name        = "${var.update_api_gateway_name}-prod-stage"
    Purpose     = "RedirectStatusUpdate"
    Environment = "production"
  }
}


# ============================================================================
# API Key Authentication
# ============================================================================

# API Key for authentication
resource "aws_api_gateway_api_key" "update_api_key" {
  name        = "${var.update_api_gateway_name}-key"
  description = "API key for redirect status update endpoint"
  enabled     = true

  tags = {
    Name        = "${var.update_api_gateway_name}-key"
    Purpose     = "RedirectStatusUpdate"
    Environment = "production"
  }
}

# Usage Plan for rate limiting and throttling
resource "aws_api_gateway_usage_plan" "update_api_usage_plan" {
  name        = "${var.update_api_gateway_name}-usage-plan"
  description = "Usage plan for redirect status update API"

  api_stages {
    api_id = aws_api_gateway_rest_api.update_api.id
    stage  = aws_api_gateway_stage.update_api_stage.stage_name
  }

  # Rate limiting: 1000 requests per second
  throttle_settings {
    burst_limit = 2000
    rate_limit  = 1000
  }

  # Quota: 1 million requests per month
  quota_settings {
    limit  = 1000000
    period = "MONTH"
  }

  tags = {
    Name        = "${var.update_api_gateway_name}-usage-plan"
    Purpose     = "RedirectStatusUpdate"
    Environment = "production"
  }
}

# Associate API key with usage plan
resource "aws_api_gateway_usage_plan_key" "update_api_usage_plan_key" {
  key_id        = aws_api_gateway_api_key.update_api_key.id
  key_type      = "API_KEY"
  usage_plan_id = aws_api_gateway_usage_plan.update_api_usage_plan.id
}

# Output the API key value (sensitive)
output "update_api_key_value" {
  description = "API key for Update API (keep secure!)"
  value       = aws_api_gateway_api_key.update_api_key.value
  sensitive   = true
}

# Output instructions for retrieving the API key
output "update_api_key_instructions" {
  description = "Instructions for retrieving the API key"
  value       = "Run: terraform output -raw update_api_key_value"
}
