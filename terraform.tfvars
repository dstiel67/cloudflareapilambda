# Terraform configuration for Cloudflare KV to DynamoDB sync Lambda function

# AWS Configuration
aws_region = "us-east-1"

# Lambda Function Configuration
lambda_function_name   = "cloudflare-data-sync"
dynamodb_table_name    = "cloudflare-kv-data"
cloudflare_secret_name = "cloudflare-kv-credentials"

# Lambda Performance Settings
lambda_timeout     = 300  # 5 minutes
lambda_memory_size = 512  # MB

# Monitoring and Alerting (optional)
# alert_email = "your-email@example.com"  # Uncomment to enable CloudWatch alerts
error_rate_threshold  = 5      # Percentage
duration_threshold_ms = 60000  # 60 seconds
