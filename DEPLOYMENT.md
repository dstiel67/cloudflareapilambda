# DynamoDB Redirect Status Management - Deployment Guide

This guide explains how to deploy the DynamoDB-based redirect status management system with real-time notifications using Terraform.

## Prerequisites

1. **AWS CLI configured** with appropriate credentials
2. **Terraform installed** (version 1.0 or later)
3. **Python 3.11** for local testing (optional)
4. **Cloudflare API credentials** (optional - only for legacy sync)

## Infrastructure Components

The Terraform configuration creates:

- **Update API Lambda**: REST API to update redirect status
- **Notification Lambda**: Processes DynamoDB Stream events
- **SSE Endpoint Lambda**: Provides Server-Sent Events for real-time notifications
- **DynamoDB Table with Streams**: Source of truth for redirect status
- **SSE Messages Table**: Temporary storage for notifications
- **API Gateways**: HTTP endpoints for Update API and SSE
- **Secrets Manager Secret**: Stores Cloudflare credentials (optional, for legacy sync)
- **IAM Roles & Policies**: Provides necessary permissions
- **CloudWatch Monitoring**: Logs, metrics, and alarms
- **X-Ray Tracing**: Performance monitoring and debugging

## Deployment Steps

### 1. Build Lambda Packages

Build all Lambda function packages:

```bash
# Universal build script (recommended)
./build.sh

# Or platform-specific:
# Linux: Uses optimized scripts automatically
# macOS/Windows Git Bash: Uses cross-platform scripts
# Windows Command Prompt: build_all.bat
```

This creates:
- `update_lambda.zip` - Update API (~15MB)
- `notification_lambda.zip` - Notification handler (~15MB)
- `sse_lambda.zip` - SSE endpoint (~15MB)
- `lambda_function.zip` - Legacy Cloudflare sync (~33MB, optional)

### 2. Configure Terraform Variables

Create or update `terraform.tfvars` with your specific values:

```hcl
# AWS Configuration
aws_region = "us-east-1"

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

### 3. Deploy Infrastructure

```bash
# Initialize Terraform (if not already done)
terraform init

# Plan the deployment
terraform plan

# Apply the configuration
terraform apply
```

### 4. Test the Update API

```bash
# Get update endpoint
UPDATE_ENDPOINT=$(terraform output -raw update_redirect_status_endpoint)

# Turn redirect ON
curl -X POST "$UPDATE_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{"value": "ON", "updated_by": "admin", "reason": "Testing"}'

# Get current status
curl "$(terraform output -raw get_redirect_status_endpoint)"
```

### 5. Test Real-Time Notifications

```bash
# Terminal 1: Connect to SSE stream
curl -N -H "Accept: text/event-stream" "$(terraform output -raw sse_events_endpoint)"

# Terminal 2: Update status
curl -X POST "$(terraform output -raw update_redirect_status_endpoint)" \
  -H "Content-Type: application/json" \
  -d '{"value": "OFF", "updated_by": "test"}'

# Terminal 1 will show the update immediately
```

### 6. (Optional) Configure Cloudflare Sync

Only needed if you want to use the legacy Cloudflare KV sync:

```bash
# Get the secret name from Terraform output
SECRET_NAME=$(terraform output -raw secrets_manager_secret_name)

# Update the secret with your Cloudflare credentials
aws secretsmanager update-secret \
  --secret-id "$SECRET_NAME" \
  --secret-string '{
    "api_token": "your_cloudflare_api_token",
    "account_id": "your_cloudflare_account_id", 
    "kv_namespace_id": "your_kv_namespace_id",
    "kv_namespace": "your_namespace_name"
  }'

# Test the legacy sync
aws lambda invoke \
  --function-name "$(terraform output -raw lambda_function_name)" \
  --payload '{}' \
  response.json
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
# Update API logs
aws logs tail "/aws/lambda/redirect-status-update" --follow

# Notification handler logs
aws logs tail "/aws/lambda/cloudflare-notification-handler" --follow

# SSE endpoint logs
aws logs tail "/aws/lambda/cloudflare-sse-endpoint" --follow

# Legacy sync logs (if using)
aws logs tail "/aws/lambda/cloudflare-data-sync" --follow
```

### X-Ray Tracing

View performance traces in the AWS X-Ray console:
- Navigate to AWS X-Ray in the AWS Console
- Select "Traces" to view execution traces
- Use filters to analyze performance patterns

## Configuration Options

### Environment Variables

The Lambda functions use these environment variables (automatically configured):

**Update Lambda:**
- `DYNAMODB_TABLE_NAME`: Target DynamoDB table name

**Notification Lambda:**
- `SSE_MESSAGES_TABLE_NAME`: SSE messages table name

**SSE Endpoint Lambda:**
- `SSE_MESSAGES_TABLE_NAME`: SSE messages table name

**Legacy Sync Lambda (optional):**
- `SECRETS_MANAGER_SECRET_NAME`: Name of the secret containing Cloudflare credentials
- `DYNAMODB_TABLE_NAME`: Target DynamoDB table name
- `RETRY_MAX_ATTEMPTS`: Maximum retry attempts (default: 3)
- `API_TIMEOUT_SECONDS`: API call timeout (default: 30)

### Lambda Function URL

The legacy sync function includes an optional HTTP endpoint for direct invocation:

```bash
# Get the function URL
FUNCTION_URL=$(terraform output -raw lambda_function_url)

# Invoke via HTTP (requires AWS IAM authentication)
curl -X POST "$FUNCTION_URL" \
  -H "Content-Type: application/json" \
  -d '{}' \
  --aws-sigv4 "aws:amz:us-east-1:lambda"
```

## Troubleshooting

### Common Issues

1. **Permission Errors**: Ensure your AWS credentials have sufficient permissions
2. **Update API Errors**: Verify request body format (value must be "ON" or "OFF")
3. **No SSE Events**: Check DynamoDB Stream is enabled and notification Lambda is working
4. **DynamoDB Throttling**: Monitor write capacity and adjust if needed
5. **Lambda Timeouts**: Increase timeout for large datasets
6. **Cloudflare Authentication** (legacy sync only): Verify API token has KV namespace access

### Debugging Steps

1. **Check CloudWatch Logs**:
   ```bash
   # Update API
   aws logs describe-log-streams --log-group-name "/aws/lambda/redirect-status-update"
   
   # Notification handler
   aws logs describe-log-streams --log-group-name "/aws/lambda/cloudflare-notification-handler"
   
   # SSE endpoint
   aws logs describe-log-streams --log-group-name "/aws/lambda/cloudflare-sse-endpoint"
   ```

2. **Verify Secrets Manager** (for legacy sync):
   ```bash
   aws secretsmanager get-secret-value --secret-id cloudflare-kv-credentials
   ```

3. **Test DynamoDB Access**:
   ```bash
   aws dynamodb describe-table --table-name cloudflare-kv-data-with-stream
   ```

4. **Test API Endpoints**:
   ```bash
   # Update API health
   curl "$(terraform output -raw update_health_endpoint)"
   
   # SSE health
   curl "$(terraform output -raw sse_health_endpoint)"
   ```

5. **Check X-Ray Traces**: Look for bottlenecks and errors in the X-Ray console

## Security Considerations

- **Secrets Management**: Cloudflare credentials stored securely in AWS Secrets Manager (if using legacy sync)
- **IAM Permissions**: Lambda functions have minimal required permissions
- **Network Security**: Consider VPC configuration for additional isolation
- **Data Encryption**: DynamoDB encryption at rest is enabled by default
- **API Authentication**: Consider adding authentication to Update API and SSE endpoints
- **Rate Limiting**: Consider implementing rate limiting for public endpoints

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