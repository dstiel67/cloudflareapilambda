# Cloudflare KV to DynamoDB Sync - Lambda Function

This project provides an AWS Lambda function that synchronizes data from Cloudflare KV (Key-Value) storage to Amazon DynamoDB. The infrastructure is fully managed using Terraform.

## Architecture

- **Lambda Function**: Executes the Cloudflare KV data sync
- **DynamoDB Table**: Stores the synchronized Cloudflare data with TTL support
- **Secrets Manager**: Securely stores Cloudflare API credentials
- **IAM Roles & Policies**: Provides necessary permissions with least privilege
- **CloudWatch Monitoring**: Logs, metrics, custom dashboards, and alarms
- **X-Ray Tracing**: Performance monitoring and debugging

## Features

### Data Synchronization
- Fetches a specific key value from Cloudflare KV namespace
- Defaults to retrieving 'redirect-all-users-to-essentials' key
- Supports custom key retrieval via event parameter
- Transforms data for DynamoDB storage
- Comprehensive error handling

### Performance & Reliability
- Connection pooling and reuse across invocations
- Cold start optimization
- Timeout management with early termination
- Retry logic with exponential backoff
- Rate limit handling

### Monitoring & Observability
- CloudWatch Logs with structured logging
- Custom CloudWatch metrics and dashboards
- Configurable alarms for errors, duration, and throttles
- X-Ray distributed tracing
- Detailed execution statistics

## Prerequisites

1. **AWS CLI** configured with appropriate credentials
2. **Terraform** installed (version 1.0 or later)
3. **Cloudflare API credentials** with KV namespace access:
   - API Token
   - Account ID
   - KV Namespace ID
   - KV Namespace Name
4. **Python 3.11** for local testing (optional)

## Quick Start

### 1. Build Lambda Package

The Lambda function requires Python dependencies to be packaged:

```bash
./build_lambda.sh
```

This creates `lambda_function.zip` with all dependencies included.

### 2. Configure Variables

Create or update `terraform.tfvars`:

```hcl
# AWS Configuration
aws_region = "us-east-1"

# Lambda Function Configuration
lambda_function_name   = "cloudflare-data-sync"
dynamodb_table_name    = "cloudflare-kv-data"
cloudflare_secret_name = "cloudflare-kv-credentials"

# Lambda Performance Settings
lambda_timeout     = 300  # 5 minutes
lambda_memory_size = 512  # MB

# Monitoring (optional)
alert_email = "your-email@example.com"  # Leave empty to disable alerts
```

### 3. Deploy Infrastructure

```bash
# Initialize Terraform
terraform init

# Review the deployment plan
terraform plan

# Deploy the infrastructure
terraform apply
```

### 4. Configure Cloudflare Credentials

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

### 5. Test the Lambda Function

```bash
# Get the function name from Terraform output
FUNCTION_NAME=$(terraform output -raw lambda_function_name)

# Test with default key (redirect-all-users-to-essentials)
aws lambda invoke \
  --function-name "$FUNCTION_NAME" \
  --payload '{}' \
  response.json

# Test with a custom key
aws lambda invoke \
  --function-name "$FUNCTION_NAME" \
  --payload '{"key_name": "classic-domain"}' \
  response.json

# Check the response
cat response.json
```

## Lambda Function Usage

### Invocation Parameters

The Lambda function accepts the following optional parameter:

```json
{
  "key_name": "redirect-all-users-to-essentials"  // Specific key to fetch (default: 'redirect-all-users-to-essentials')
}
```

### Response Format

Successful response:

```json
{
  "success": true,
  "data": {
    "message": "Cloudflare data sync completed successfully for key 'redirect-all-users-to-essentials'",
    "key_name": "redirect-all-users-to-essentials",
    "processing_summary": {
      "key_retrieved": true,
      "record_processed": true,
      "record_stored": true,
      "record_failed": false
    },
    "lambda_optimizations": {
      "cold_start_detected": false,
      "optimization_time_ms": 5,
      "connection_pool_stats": {...},
      "timeout_management": {...}
    }
  },
  "statistics": {
    "execution_time_ms": 1234,
    "cloudflare_api_calls": 1,
    "dynamodb_writes": 1,
    "records_processed": 1,
    "records_stored": 1,
    "success_rate": 1.0
  }
}
```

Error response:

```json
{
  "success": false,
  "error": {
    "type": "API_ERROR",
    "message": "Error description",
    "timestamp": "2024-01-15T10:30:00Z",
    "is_retryable": true,
    "severity": "error"
  },
  "statistics": {...}
}
```

## Monitoring

### CloudWatch Dashboard

Access the monitoring dashboard:

```bash
terraform output cloudwatch_dashboard_url
```

The dashboard includes:
- Lambda invocations, errors, duration, and throttles
- Custom application metrics (success count, error types)
- Recent error logs

### View Logs

```bash
# Get log group name
LOG_GROUP=$(terraform output -raw lambda_log_group_name)

# View recent logs
aws logs tail "$LOG_GROUP" --follow

# Search for errors
aws logs filter-log-events \
  --log-group-name "$LOG_GROUP" \
  --filter-pattern "ERROR"
```

### CloudWatch Alarms

When `alert_email` is configured, the following alarms are created:
- High error rate (threshold: 5 errors per 5 minutes)
- High duration (threshold: 60 seconds average)
- Authentication errors (any occurrence)
- Lambda throttles (any occurrence)
- DynamoDB throttles (any occurrence)
- DynamoDB system errors (any occurrence)

### X-Ray Tracing

View performance traces in the AWS X-Ray console:
1. Navigate to AWS X-Ray in the AWS Console
2. Select "Traces" to view execution traces
3. Use filters to analyze performance patterns and bottlenecks

## DynamoDB Schema

The DynamoDB table uses a single-table design:

- **Primary Key**: `pk` (partition key) - Format: `NAMESPACE#{namespace_id}`
- **Sort Key**: `sk` (range key) - Format: `KEY#{key_name}`
- **TTL**: `ttl` attribute for automatic data expiration
- **Billing Mode**: Pay-per-request (on-demand)
- **Point-in-Time Recovery**: Enabled

### Record Structure

```json
{
  "pk": "NAMESPACE#abc123",
  "sk": "KEY#my-key-name",
  "key": "my-key-name",
  "value": "...",  // Original value (string or JSON)
  "value_type": "string",  // or "json"
  "namespace_id": "abc123",
  "namespace_name": "my-namespace",
  "metadata": {...},  // Cloudflare key metadata
  "expiration": 1234567890,  // Unix timestamp (if set)
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z",
  "ttl": 1234567890  // For DynamoDB TTL
}
```

## Configuration

### Environment Variables

The Lambda function uses these environment variables (automatically configured by Terraform):

- `SECRETS_MANAGER_SECRET_NAME`: Name of the secret containing Cloudflare credentials
- `DYNAMODB_TABLE_NAME`: Target DynamoDB table name
- `RETRY_MAX_ATTEMPTS`: Maximum retry attempts (default: 3)
- `API_TIMEOUT_SECONDS`: API call timeout (default: 30)

### Lambda Function URL

The function includes an optional HTTP endpoint for direct invocation:

```bash
# Get the function URL
FUNCTION_URL=$(terraform output -raw lambda_function_url)

# Invoke via HTTP with default key (requires AWS IAM authentication)
curl -X POST "$FUNCTION_URL" \
  -H "Content-Type: application/json" \
  -d '{}' \
  --aws-sigv4 "aws:amz:us-east-1:lambda"

# Invoke via HTTP with custom key
curl -X POST "$FUNCTION_URL" \
  -H "Content-Type: application/json" \
  -d '{"key_name": "classic-domain"}' \
  --aws-sigv4 "aws:amz:us-east-1:lambda"
```

## Development

### Project Structure

```
.
├── lambda.tf                    # Terraform configuration for Lambda and infrastructure
├── variables.tf                 # Terraform variable definitions
├── outputs.tf                   # Terraform outputs
├── terraform.tfvars            # Your configuration values
├── lambda_function/
│   ├── lambda_function.py      # Main Lambda handler
│   ├── requirements.txt        # Python dependencies
│   ├── src/
│   │   ├── config.py          # Configuration management
│   │   ├── cloudflare_client.py  # Cloudflare API client
│   │   ├── data_transformer.py   # Data transformation logic
│   │   ├── dynamodb_client.py    # DynamoDB operations
│   │   ├── error_handler.py      # Error handling and logging
│   │   └── lambda_optimizations.py  # Performance optimizations
│   └── tests/
│       ├── test_config.py
│       ├── test_integration.py
│       └── test_lambda_function.py
└── DEPLOYMENT.md               # Detailed deployment guide
```

### Running Tests

```bash
cd lambda_function
python -m pytest tests/ -v
```

All 26 tests should pass, covering:
- Configuration management
- Cloudflare API integration
- DynamoDB operations
- Error handling and recovery
- Lambda optimizations
- End-to-end workflows

### Local Development

1. Install dependencies:
   ```bash
   cd lambda_function
   pip install -r requirements.txt
   ```

2. Set environment variables:
   ```bash
   export SECRETS_MANAGER_SECRET_NAME="cloudflare-kv-credentials"
   export DYNAMODB_TABLE_NAME="cloudflare-kv-data"
   export RETRY_MAX_ATTEMPTS="3"
   export API_TIMEOUT_SECONDS="30"
   ```

3. Run tests:
   ```bash
   python -m pytest tests/ -v
   ```

## Troubleshooting

### Common Issues

1. **Permission Errors**
   - Ensure your AWS credentials have sufficient permissions
   - Check IAM role policies for Lambda function

2. **Cloudflare Authentication Errors**
   - Verify API token has KV namespace access
   - Check that credentials in Secrets Manager are correct
   - Ensure account ID and namespace ID are accurate

3. **DynamoDB Throttling**
   - Monitor write capacity in CloudWatch
   - Consider adjusting batch sizes
   - DynamoDB is configured for on-demand billing to handle bursts

4. **Lambda Timeouts**
   - Increase `lambda_timeout` for large datasets
   - Use pagination with `cursor` parameter
   - Check CloudWatch logs for bottlenecks

### Debugging Steps

1. **Check CloudWatch Logs**:
   ```bash
   aws logs describe-log-streams \
     --log-group-name "/aws/lambda/cloudflare-data-sync"
   ```

2. **Verify Secrets Manager**:
   ```bash
   aws secretsmanager get-secret-value \
     --secret-id cloudflare-kv-credentials
   ```

3. **Test DynamoDB Access**:
   ```bash
   aws dynamodb describe-table \
     --table-name cloudflare-kv-data
   ```

4. **Check X-Ray Traces**: Look for bottlenecks and errors in the X-Ray console

## Security Considerations

- **Secrets Management**: Cloudflare credentials stored securely in AWS Secrets Manager
- **IAM Permissions**: Lambda function has minimal required permissions (least privilege)
- **Encryption**: DynamoDB encryption at rest enabled by default
- **Network Security**: Consider VPC configuration for additional isolation (optional)
- **API Token**: Use scoped Cloudflare API tokens with only KV namespace access

## Cost Optimization

- **DynamoDB**: Uses pay-per-request billing mode (scales automatically)
- **Lambda**: Optimize memory size based on actual usage patterns
- **CloudWatch**: Log retention set to 14 days to control costs
- **Monitoring**: Alarms only created when alert email is provided
- **X-Ray**: Tracing enabled for debugging (consider disabling in production if not needed)

## Maintenance

### Update Lambda Function

1. Modify code in `lambda_function/` directory
2. Run `terraform apply` to redeploy
3. Test the updated function

### Update Cloudflare Credentials

```bash
aws secretsmanager update-secret \
  --secret-id cloudflare-kv-credentials \
  --secret-string '{...}'
```

### Scale Configuration

Adjust in `terraform.tfvars`:
- `lambda_timeout`: Increase for larger datasets
- `lambda_memory_size`: Increase for better performance
- `error_rate_threshold`: Adjust alarm sensitivity
- `duration_threshold_ms`: Adjust performance expectations

## Cleanup

To destroy all resources:

```bash
terraform destroy
```

**Warning**: This will permanently delete all data in the DynamoDB table and remove all monitoring configuration.

## Additional Resources

- [AWS Lambda Documentation](https://docs.aws.amazon.com/lambda/)
- [Amazon DynamoDB Documentation](https://docs.aws.amazon.com/dynamodb/)
- [Cloudflare KV API Documentation](https://developers.cloudflare.com/api/operations/workers-kv-namespace-list-a-namespace'-s-keys)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [AWS Secrets Manager](https://docs.aws.amazon.com/secretsmanager/)

## License

This project is provided as-is for use in your AWS infrastructure.

## Support

For issues or questions:
1. Check CloudWatch Logs for error details
2. Review X-Ray traces for performance issues
3. Verify Cloudflare API credentials and permissions
4. Ensure DynamoDB table is accessible
