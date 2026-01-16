# Cloudflare Data Sync - Deployment Guide

This guide explains how to deploy the Cloudflare-to-DynamoDB Lambda function infrastructure using Terraform.

## Prerequisites

1. **AWS CLI configured** with appropriate credentials
2. **Terraform installed** (version 1.0 or later)
3. **Cloudflare API credentials** with KV namespace access
4. **Python 3.11** for local testing (optional)

## Infrastructure Components

The Terraform configuration creates:

- **Lambda Function**: Executes the Cloudflare data sync
- **DynamoDB Table**: Stores the synchronized Cloudflare data
- **Secrets Manager Secret**: Securely stores Cloudflare API credentials
- **IAM Roles & Policies**: Provides necessary permissions
- **CloudWatch Monitoring**: Logs, metrics, and alarms
- **X-Ray Tracing**: Performance monitoring and debugging

## Deployment Steps

### 1. Configure Terraform Variables

Create or update `terraform.tfvars` with your specific values:

```hcl
# Existing variables (if any)
aws_region = "us-east-1"
bucket_name = "your-existing-bucket-name"
# ... other existing variables

# Lambda function variables
lambda_function_name = "cloudflare-data-sync"
dynamodb_table_name = "cloudflare-kv-data"
cloudflare_secret_name = "cloudflare-kv-credentials"

# Optional: Monitoring configuration
alert_email = "your-email@example.com"
lambda_timeout = 300
lambda_memory_size = 512
error_rate_threshold = 5
duration_threshold_ms = 60000
```

### 2. Deploy Infrastructure

```bash
# Initialize Terraform (if not already done)
terraform init

# Plan the deployment
terraform plan

# Apply the configuration
terraform apply
```

### 3. Configure Cloudflare Credentials

After deployment, update the Secrets Manager secret with your actual Cloudflare credentials:

```bash
# Get the secret name from Terraform output
SECRET_NAME=$(terraform output -raw secrets_manager_secret_name)

# Update the secret with your actual credentials
aws secretsmanager update-secret \
  --secret-id "$SECRET_NAME" \
  --secret-string '{
    "api_token": "your_cloudflare_api_token",
    "account_id": "your_cloudflare_account_id", 
    "kv_namespace_id": "your_kv_namespace_id",
    "kv_namespace": "your_namespace_name"
  }'
```

### 4. Test the Lambda Function

```bash
# Get the function name from Terraform output
FUNCTION_NAME=$(terraform output -raw lambda_function_name)

# Test with a simple invocation
aws lambda invoke \
  --function-name "$FUNCTION_NAME" \
  --payload '{"max_keys": 10}' \
  response.json

# Check the response
cat response.json
```

## Monitoring and Observability

### CloudWatch Dashboard

Access the monitoring dashboard:
```bash
# Get dashboard URL from Terraform output
terraform output cloudwatch_dashboard_url
```

### Log Analysis

View Lambda function logs:
```bash
# Get log group name
LOG_GROUP=$(terraform output -raw lambda_log_group_name)

# View recent logs
aws logs tail "$LOG_GROUP" --follow
```

### X-Ray Tracing

View performance traces in the AWS X-Ray console:
- Navigate to AWS X-Ray in the AWS Console
- Select "Traces" to view execution traces
- Use filters to analyze performance patterns

## Configuration Options

### Environment Variables

The Lambda function uses these environment variables (automatically configured):

- `SECRETS_MANAGER_SECRET_NAME`: Name of the secret containing Cloudflare credentials
- `DYNAMODB_TABLE_NAME`: Target DynamoDB table name
- `RETRY_MAX_ATTEMPTS`: Maximum retry attempts (default: 3)
- `API_TIMEOUT_SECONDS`: API call timeout (default: 30)

### Lambda Function URL

The function includes an optional HTTP endpoint for direct invocation:

```bash
# Get the function URL
FUNCTION_URL=$(terraform output -raw lambda_function_url)

# Invoke via HTTP (requires AWS IAM authentication)
curl -X POST "$FUNCTION_URL" \
  -H "Content-Type: application/json" \
  -d '{"max_keys": 10}' \
  --aws-sigv4 "aws:amz:us-east-1:lambda"
```

## Troubleshooting

### Common Issues

1. **Permission Errors**: Ensure your AWS credentials have sufficient permissions
2. **Cloudflare Authentication**: Verify API token has KV namespace access
3. **DynamoDB Throttling**: Monitor write capacity and adjust if needed
4. **Lambda Timeouts**: Increase timeout for large datasets

### Debugging Steps

1. **Check CloudWatch Logs**:
   ```bash
   aws logs describe-log-streams --log-group-name "/aws/lambda/cloudflare-data-sync"
   ```

2. **Verify Secrets Manager**:
   ```bash
   aws secretsmanager get-secret-value --secret-id cloudflare-kv-credentials
   ```

3. **Test DynamoDB Access**:
   ```bash
   aws dynamodb describe-table --table-name cloudflare-kv-data
   ```

4. **Check X-Ray Traces**: Look for bottlenecks and errors in the X-Ray console

## Security Considerations

- **Secrets Management**: Cloudflare credentials are stored securely in AWS Secrets Manager
- **IAM Permissions**: Lambda function has minimal required permissions
- **Network Security**: Consider VPC configuration for additional isolation
- **Data Encryption**: DynamoDB encryption at rest is enabled by default

## Cost Optimization

- **DynamoDB**: Uses pay-per-request billing mode
- **Lambda**: Optimize memory size based on actual usage
- **CloudWatch**: Log retention set to 14 days to control costs
- **Monitoring**: Alarms only created when alert email is provided

## Cleanup

To remove all resources:

```bash
terraform destroy
```

Note: This will permanently delete all data in the DynamoDB table and remove all monitoring configuration.