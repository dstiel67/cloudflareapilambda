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
  value       = aws_dynamodb_table.cloudflare_kv_data.name
}

output "dynamodb_table_arn" {
  description = "ARN of the DynamoDB table for Cloudflare data"
  value       = aws_dynamodb_table.cloudflare_kv_data.arn
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