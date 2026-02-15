# Lambda Function Outputs
output "lambda_function_name" {
  description = "Name of the Cloudflare data sync Lambda function"
  value       = aws_lambda_function.cloudflare_data_sync.function_name
}

output "lambda_function_arn" {
  description = "ARN of the Cloudflare data sync Lambda function"
  value       = aws_lambda_function.cloudflare_data_sync.arn
}

output "lambda_function_url" {
  description = "URL of the Lambda function for HTTP invocation"
  value       = aws_lambda_function_url.cloudflare_data_sync_url.function_url
}

output "dynamodb_table_name" {
  description = "Name of the DynamoDB table for Cloudflare data"
  value       = aws_dynamodb_table.cloudflare_kv_data_with_stream.name
}

output "dynamodb_table_arn" {
  description = "ARN of the DynamoDB table for Cloudflare data"
  value       = aws_dynamodb_table.cloudflare_kv_data_with_stream.arn
}

output "secrets_manager_secret_name" {
  description = "Name of the Secrets Manager secret for Cloudflare credentials"
  value       = aws_secretsmanager_secret.cloudflare_credentials.name
}

output "secrets_manager_secret_arn" {
  description = "ARN of the Secrets Manager secret for Cloudflare credentials"
  value       = aws_secretsmanager_secret.cloudflare_credentials.arn
}

output "cloudwatch_dashboard_url" {
  description = "URL to the CloudWatch dashboard for Lambda monitoring"
  value       = "https://${data.aws_region.current.name}.console.aws.amazon.com/cloudwatch/home?region=${data.aws_region.current.name}#dashboards:name=${aws_cloudwatch_dashboard.lambda_dashboard.dashboard_name}"
}

output "lambda_log_group_name" {
  description = "Name of the CloudWatch log group for Lambda function"
  value       = aws_cloudwatch_log_group.lambda_logs.name
}

# Notification Lambda Outputs
output "notification_lambda_function_name" {
  description = "Name of the notification Lambda function"
  value       = aws_lambda_function.notification_handler.function_name
}

output "notification_lambda_function_arn" {
  description = "ARN of the notification Lambda function"
  value       = aws_lambda_function.notification_handler.arn
}

# SSE Lambda Outputs
output "sse_lambda_function_name" {
  description = "Name of the SSE Lambda function"
  value       = aws_lambda_function.sse_endpoint.function_name
}

output "sse_lambda_function_arn" {
  description = "ARN of the SSE Lambda function"
  value       = aws_lambda_function.sse_endpoint.arn
}

# SSE Infrastructure Outputs
output "sse_messages_table_name" {
  description = "Name of the SSE messages DynamoDB table"
  value       = aws_dynamodb_table.sse_messages.name
}

output "sse_messages_table_arn" {
  description = "ARN of the SSE messages DynamoDB table"
  value       = aws_dynamodb_table.sse_messages.arn
}

# API Gateway Outputs
output "sse_api_gateway_url" {
  description = "URL of the SSE API Gateway"
  value       = "https://${aws_api_gateway_rest_api.sse_api.id}.execute-api.${data.aws_region.current.name}.amazonaws.com/prod"
}

output "sse_events_endpoint" {
  description = "SSE events endpoint URL for Angular client"
  value       = "https://${aws_api_gateway_rest_api.sse_api.id}.execute-api.${data.aws_region.current.name}.amazonaws.com/prod/events"
}

output "sse_health_endpoint" {
  description = "SSE health check endpoint URL"
  value       = "https://${aws_api_gateway_rest_api.sse_api.id}.execute-api.${data.aws_region.current.name}.amazonaws.com/prod/health"
}

# Additional Log Groups
output "notification_lambda_log_group_name" {
  description = "Name of the notification Lambda function log group"
  value       = aws_cloudwatch_log_group.notification_lambda_logs.name
}

output "sse_lambda_log_group_name" {
  description = "Name of the SSE Lambda function log group"
  value       = aws_cloudwatch_log_group.sse_lambda_logs.name
}

output "update_lambda_log_group_name" {
  description = "Name of the update Lambda function log group"
  value       = aws_cloudwatch_log_group.update_lambda_logs.name
}

# Update API Outputs
output "update_lambda_function_name" {
  description = "Name of the update Lambda function"
  value       = aws_lambda_function.redirect_status_update.function_name
}

output "update_lambda_function_arn" {
  description = "ARN of the update Lambda function"
  value       = aws_lambda_function.redirect_status_update.arn
}

output "update_api_gateway_url" {
  description = "URL of the update API Gateway"
  value       = "https://${aws_api_gateway_rest_api.update_api.id}.execute-api.${data.aws_region.current.name}.amazonaws.com/prod"
}

output "update_api_base_url" {
  description = "Base URL for the update API (for Angular service configuration)"
  value       = "https://${aws_api_gateway_rest_api.update_api.id}.execute-api.${data.aws_region.current.name}.amazonaws.com/prod"
}

output "update_redirect_status_endpoint" {
  description = "Endpoint to update redirect status (POST)"
  value       = "https://${aws_api_gateway_rest_api.update_api.id}.execute-api.${data.aws_region.current.name}.amazonaws.com/prod/redirect-status"
}

output "get_redirect_status_endpoint" {
  description = "Endpoint to get current redirect status (GET)"
  value       = "https://${aws_api_gateway_rest_api.update_api.id}.execute-api.${data.aws_region.current.name}.amazonaws.com/prod/redirect-status"
}

output "update_health_endpoint" {
  description = "Update API health check endpoint URL"
  value       = "https://${aws_api_gateway_rest_api.update_api.id}.execute-api.${data.aws_region.current.name}.amazonaws.com/prod/health"
}

# Kafka Consumer Lambda Outputs
output "kafka_consumer_lambda_function_name" {
  description = "Name of the Kafka consumer Lambda function"
  value       = aws_lambda_function.kafka_consumer.function_name
}

output "kafka_consumer_lambda_function_arn" {
  description = "ARN of the Kafka consumer Lambda function"
  value       = aws_lambda_function.kafka_consumer.arn
}

output "kafka_consumer_lambda_log_group_name" {
  description = "Name of the Kafka consumer Lambda function log group"
  value       = aws_cloudwatch_log_group.kafka_consumer_logs.name
}
