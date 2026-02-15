# DynamoDB-Based Redirect Status Management with Real-Time Notifications

This project provides an AWS Lambda-based system for managing redirect status in DynamoDB with real-time web client notifications via Server-Sent Events (SSE).

## Architecture

- **Update Lambda Function**: API endpoint to update redirect status in DynamoDB
- **DynamoDB Table**: Source of truth for redirect status with TTL support and Streams enabled
- **Notification Lambda**: Processes DynamoDB Stream events and sends SSE notifications
- **SSE Endpoint Lambda**: Provides Server-Sent Events endpoint for real-time notifications
- **SSE Messages Table**: Temporary storage for Server-Sent Event messages
- **API Gateway**: Provides HTTP endpoints for both update and SSE operations
- **Dead Letter Queues**: SQS queues for capturing failed Lambda invocations
- **IAM Roles & Policies**: Provides necessary permissions with least privilege
- **CloudWatch Monitoring**: Logs, metrics, custom dashboards, and alarms
- **X-Ray Tracing**: Performance monitoring and debugging
- **Secrets Manager** (optional): Only needed for legacy Cloudflare sync - not used by primary system

## Features

### Redirect Status Management
- Update redirect status via REST API (ON/OFF)
- Get current redirect status
- Audit trail with timestamps and user tracking
- Optional reason field for updates
- DynamoDB as single source of truth

### Real-Time Notifications
- DynamoDB Streams trigger notifications when status changes
- Server-Sent Events (SSE) endpoint for real-time web client updates
- Angular service and component examples provided
- Automatic reconnection and error handling
- CORS-enabled API Gateway endpoints

### Legacy Cloudflare Sync (Optional)
- Original Lambda function for syncing from Cloudflare KV
- Can be used for initial data migration
- Supports custom key retrieval via event parameter
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
- Dead Letter Queues for failed invocations
- Automatic alerts on DLQ messages

## Prerequisites

1. **AWS CLI** configured with appropriate credentials
2. **Terraform** installed (version 1.0 or later)
3. **Python 3.11** for local testing (optional)
4. **Cloudflare API credentials** (optional - only needed for legacy sync):
   - API Token
   - Account ID
   - KV Namespace ID
   - KV Namespace Name

## Quick Start

### 1. Build Lambda Packages

The system requires multiple Lambda functions to be packaged. Choose the method that works best for your system:

**Option 1: Universal Build Script (Recommended)**
```bash
./build.sh
```
*Automatically detects your OS and builds ALL Lambda functions using optimal scripts*

**Option 2: Platform-Specific Scripts**

*Linux (optimized for all functions):*
```bash
./build.sh  # Uses Linux-optimized scripts automatically
```

*Unix/macOS/Windows with Git Bash:*
```bash
./build.sh  # Uses cross-platform scripts automatically
```

*Windows (Command Prompt/PowerShell):*
```cmd
build_all.bat
```

**Option 3: Automatic with Terraform**
```bash
terraform apply
```
*Terraform will automatically build all packages using the appropriate scripts*

This creates deployment packages for all Lambda functions:
- `lambda_function.zip` - Legacy Cloudflare sync function (~33-34MB)
- `notification_lambda.zip` - Notification handler (~15MB)  
- `sse_lambda.zip` - SSE endpoint (~15MB)
- `update_lambda.zip` - Update API (~15MB)

**Requirements:**
- Python 3.11+ with pip
- For Windows: Either Git Bash with 7z, or Command Prompt with 7-Zip or PowerShell
- For Unix/Linux: zip command

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

Terraform will automatically build the Lambda package and deploy:

```bash
# Initialize Terraform
terraform init

# Review the deployment plan
terraform plan

# Deploy the infrastructure (includes automatic build)
terraform apply
```

*Note: Terraform automatically detects your operating system and runs the appropriate build script when Lambda source files change.*

### 4. Configure Cloudflare Credentials (Optional - for legacy sync)

If you plan to use the legacy Cloudflare KV sync function, update the Secrets Manager secret with your actual Cloudflare credentials:

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

### 5. Retrieve API Key

The Update API requires authentication via API key:

```bash
# Get the API key (sensitive output)
API_KEY=$(terraform output -raw update_api_key_value)

# Or view instructions
terraform output update_api_key_instructions
```

### 6. Update Redirect Status

The primary way to manage redirect status is through the Update API:

```bash
# Get the update endpoint and API key from Terraform output
UPDATE_ENDPOINT=$(terraform output -raw update_redirect_status_endpoint)
API_KEY=$(terraform output -raw update_api_key_value)

# Turn redirect ON
curl -X POST "$UPDATE_ENDPOINT" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $API_KEY" \
  -d '{"value": "ON", "updated_by": "admin", "reason": "Maintenance mode"}'

# Turn redirect OFF
curl -X POST "$UPDATE_ENDPOINT" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $API_KEY" \
  -d '{"value": "OFF", "updated_by": "admin", "reason": "Maintenance complete"}'

# Get current status
curl -H "x-api-key: $API_KEY" "$(terraform output -raw get_redirect_status_endpoint)"
```

### 7. Test Real-Time Notifications

```bash
# In one terminal, connect to SSE endpoint
curl -N -H "Accept: text/event-stream" "$(terraform output -raw sse_events_endpoint)"

# In another terminal, update the status
API_KEY=$(terraform output -raw update_api_key_value)
curl -X POST "$(terraform output -raw update_redirect_status_endpoint)" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $API_KEY" \
  -d '{"value": "ON", "updated_by": "test"}'

# You should see the update appear in the SSE stream immediately
```

## Server-Sent Events (SSE) Integration

### Real-Time Notifications

The system includes a real-time notification system that sends updates to web clients when the 'redirect-all-users-to-essentials' value changes:

**SSE Endpoint:**
```bash
# Get the SSE endpoint URL
terraform output sse_events_endpoint
```

**Health Check:**
```bash
# Check SSE endpoint health
curl "$(terraform output -raw sse_health_endpoint)"
```

### Angular Integration

Complete Angular integration examples are provided in the `angular-client-example/` directory:

- `redirect-notification.service.ts` - Service for managing SSE connections
- `redirect-status.component.ts` - Component for displaying redirect status
- `README.md` - Detailed integration instructions

**Quick Angular Setup:**
```typescript
import { RedirectNotificationService } from './redirect-notification.service';

// In your component
constructor(private redirectService: RedirectNotificationService) {}

ngOnInit() {
  this.redirectService.connect();
  
  this.redirectService.getRedirectUpdates().subscribe(update => {
    console.log('Redirect status changed:', update);
    // Handle the update in your UI
  });
}
```

### Testing SSE Connection

Test the SSE endpoint directly:
```bash
# Connect to SSE stream
curl -N -H "Accept: text/event-stream" "$(terraform output -raw sse_events_endpoint)"

# In another terminal, trigger an update
aws lambda invoke --function-name cloudflare-data-sync --payload '{}' response.json
```

You should see real-time events in the SSE stream when the redirect status changes.

## Update API Usage

### Update Redirect Status

The Update API is the primary interface for managing redirect status:

**Endpoint:** `POST /redirect-status`

**Request Body:**
```json
{
  "value": "ON",              // Required: "ON" or "OFF"
  "updated_by": "admin",      // Optional: Who made the change
  "reason": "Maintenance"     // Optional: Why the change was made
}
```

**Response:**
```json
{
  "success": true,
  "message": "Redirect status updated to ON",
  "data": {
    "key": "redirect-all-users-to-essentials",
    "value": "ON",
    "timestamp": "2024-01-15T10:30:00Z",
    "updated_by": "admin"
  }
}
```

### Get Current Status

**Endpoint:** `GET /redirect-status`

**Response:**
```json
{
  "success": true,
  "data": {
    "key": "redirect-all-users-to-essentials",
    "value": "ON",
    "timestamp": "2024-01-15T10:30:00Z",
    "updated_by": "admin",
    "source": "api"
  }
}
```

### API Authentication

All Update API endpoints (except health check) require an API key for authentication. Include the API key in the `x-api-key` header:

```bash
# Retrieve your API key
API_KEY=$(terraform output -raw update_api_key_value)
```

### Examples

```bash
# Get API key
API_KEY=$(terraform output -raw update_api_key_value)

# Turn redirect ON
curl -X POST "$(terraform output -raw update_redirect_status_endpoint)" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $API_KEY" \
  -d '{"value": "ON", "updated_by": "admin", "reason": "Scheduled maintenance"}'

# Turn redirect OFF
curl -X POST "$(terraform output -raw update_redirect_status_endpoint)" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $API_KEY" \
  -d '{"value": "OFF", "updated_by": "admin", "reason": "Maintenance complete"}'

# Get current status
curl -H "x-api-key: $API_KEY" "$(terraform output -raw get_redirect_status_endpoint)"

# Health check (no API key required)
curl "$(terraform output -raw update_health_endpoint)"
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
├── update_api.tf                # Update API infrastructure
├── notification.tf              # SSE notification infrastructure
├── variables.tf                 # Terraform variable definitions
├── outputs.tf                   # Terraform outputs
├── terraform.tfvars            # Your configuration values
├── update_lambda/
│   ├── lambda_function.py      # Update API handler
│   └── requirements.txt        # Python dependencies
├── notification_lambda/
│   ├── lambda_function.py      # Notification handler
│   └── requirements.txt        # Python dependencies
├── sse_lambda/
│   ├── lambda_function.py      # SSE endpoint handler
│   └── requirements.txt        # Python dependencies
├── lambda_function/            # Legacy Cloudflare sync (optional)
│   ├── lambda_function.py      # Main Lambda handler
│   ├── requirements.txt        # Python dependencies
│   ├── src/
│   │   ├── config.py          # Configuration management
│   │   ├── cloudflare_client.py  # Cloudflare API client (legacy)
│   │   ├── data_transformer.py   # Data transformation logic
│   │   ├── dynamodb_client.py    # DynamoDB operations
│   │   ├── error_handler.py      # Error handling and logging
│   │   └── lambda_optimizations.py  # Performance optimizations
│   └── tests/
│       ├── test_config.py
│       ├── test_integration.py
│       └── test_lambda_function.py
├── angular-client-example/
│   ├── redirect-notification.service.ts  # SSE service
│   ├── redirect-update.service.ts        # Update API service
│   └── redirect-status.component.ts      # UI component
└── DEPLOYMENT.md               # Detailed deployment guide
```

### Running Tests

Tests are available for the legacy Cloudflare sync Lambda:

```bash
cd lambda_function
python -m pytest tests/ -v
```

All 26 tests should pass, covering:
- Configuration management
- Cloudflare API integration (legacy)
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

- **API Authentication**: Update API secured with API keys and usage plans (rate limiting: 1000 req/s, quota: 1M req/month)
- **Secrets Management**: Cloudflare credentials stored securely in AWS Secrets Manager (if using legacy sync)
- **IAM Permissions**: Lambda functions have minimal required permissions (least privilege)
- **Encryption**: DynamoDB encryption at rest enabled by default
- **Network Security**: Consider VPC configuration for additional isolation (optional)
- **API Key Security**: Store API keys securely, rotate regularly, never commit to version control

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

- **[API Authentication Guide](API_AUTHENTICATION.md)** - Comprehensive guide to API key authentication
- **[API Authentication Summary](API_AUTHENTICATION_SUMMARY.md)** - Quick reference for authentication implementation
- **[Dead Letter Queue Guide](DLQ_GUIDE.md)** - Complete guide to DLQ monitoring and troubleshooting
- **[AWS Cost Estimate](AWS_COST_ESTIMATE.md)** - Detailed monthly cost breakdown
- [AWS Lambda Documentation](https://docs.aws.amazon.com/lambda/)
- [Amazon DynamoDB Documentation](https://docs.aws.amazon.com/dynamodb/)
- [Cloudflare KV API Documentation](https://developers.cloudflare.com/api/operations/workers-kv-namespace-list-a-namespace'-s-keys)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [AWS Secrets Manager](https://docs.aws.amazon.com/secretsmanager/)
- [AWS API Gateway API Keys](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-api-key-source.html)
- [Amazon SQS Dead Letter Queues](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-dead-letter-queues.html)

## License

This project is provided as-is for use in your AWS infrastructure.

## Support

For issues or questions:
1. Check CloudWatch Logs for error details
2. Review X-Ray traces for performance issues
3. Verify IAM permissions and resource configurations
4. Ensure DynamoDB table is accessible
5. For legacy sync: Verify Cloudflare API credentials if using Cloudflare sync
