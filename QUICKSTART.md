# Quick Start Guide - DynamoDB Redirect Status Management

## What This Project Does

This system manages redirect status in DynamoDB with real-time notifications to web clients via Server-Sent Events (SSE).

## Prerequisites

- AWS CLI configured
- Terraform installed (1.0+)
- Python 3.11+ with pip
- (Optional) Cloudflare API credentials for legacy sync

## Deploy in 4 Steps

### 1. Build Lambda Packages

**Recommended (Universal):**
```bash
./build.sh
```

**Platform-Specific:**
- **Linux:** Uses optimized scripts automatically
- **Unix/macOS/Windows Git Bash:** Uses cross-platform scripts
- **Windows Command Prompt:** `build_all.bat`

This packages all Lambda functions with Python dependencies.

### 2. Deploy Infrastructure

```bash
terraform init
terraform apply
```

### 3. Update Redirect Status

```bash
# Get update endpoint
UPDATE_ENDPOINT=$(terraform output -raw update_redirect_status_endpoint)

# Turn redirect ON
curl -X POST "$UPDATE_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{"value": "ON", "updated_by": "admin", "reason": "Maintenance"}'

# Get current status
curl "$(terraform output -raw get_redirect_status_endpoint)"
```

### 4. Test Real-Time Notifications

```bash
# Terminal 1: Connect to SSE stream
curl -N -H "Accept: text/event-stream" "$(terraform output -raw sse_events_endpoint)"

# Terminal 2: Update status
curl -X POST "$(terraform output -raw update_redirect_status_endpoint)" \
  -H "Content-Type: application/json" \
  -d '{"value": "OFF", "updated_by": "test"}'

# Terminal 1 will show the update immediately
```

## What Gets Created

- Update API Lambda (redirect-status-update)
- Notification Lambda (cloudflare-notification-handler)
- SSE Endpoint Lambda (cloudflare-sse-endpoint)
- DynamoDB table with Streams (cloudflare-kv-data-with-stream)
- SSE Messages table (cloudflare-sse-messages)
- API Gateways for Update and SSE endpoints
- CloudWatch logs, metrics, and dashboard
- IAM roles and policies
- (Optional) Legacy Cloudflare sync Lambda

## Monitoring

View the CloudWatch dashboard:
```bash
terraform output cloudwatch_dashboard_url
```

View logs:
```bash
# Update API logs
aws logs tail "/aws/lambda/redirect-status-update" --follow

# Notification logs
aws logs tail "/aws/lambda/cloudflare-notification-handler" --follow

# SSE endpoint logs
aws logs tail "/aws/lambda/cloudflare-sse-endpoint" --follow
```

## Configuration (Optional)

Edit `terraform.tfvars` to customize:
- `lambda_timeout`: Execution timeout (default: 300 seconds)
- `lambda_memory_size`: Memory allocation (default: 512 MB)
- `alert_email`: Email for CloudWatch alarms (optional)

## Optional: Legacy Cloudflare Sync

If you need to sync from Cloudflare KV (for initial migration):

```bash
# Get secret name
SECRET_NAME=$(terraform output -raw secrets_manager_secret_name)

# Add Cloudflare credentials
aws secretsmanager update-secret \
  --secret-id "$SECRET_NAME" \
  --secret-string '{
    "api_token": "YOUR_CLOUDFLARE_API_TOKEN",
    "account_id": "YOUR_ACCOUNT_ID",
    "kv_namespace_id": "YOUR_NAMESPACE_ID",
    "kv_namespace": "YOUR_NAMESPACE_NAME"
  }'

# Run sync
aws lambda invoke \
  --function-name "$(terraform output -raw lambda_function_name)" \
  --payload '{}' \
  response.json
```

## Cleanup

```bash
terraform destroy
```

## Need Help?

- See `README.md` for detailed documentation
- See `SYSTEM_OVERVIEW.md` for architecture details
- See `ARCHITECTURE_CHANGE.md` for migration info
- Check CloudWatch logs for errors
