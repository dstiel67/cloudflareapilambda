# Quick Start Guide - Cloudflare KV to DynamoDB Sync

## What This Project Does

This Lambda function automatically syncs data from your Cloudflare KV (Key-Value) storage to Amazon DynamoDB.

## Prerequisites

- AWS CLI configured
- Terraform installed (1.0+)
- Cloudflare API credentials (API token, account ID, namespace ID)

## Deploy in 4 Steps

### 1. Build Lambda Package

```bash
./build_lambda.sh
```

This packages the Lambda function with all Python dependencies.

### 2. Deploy Infrastructure

```bash
terraform init
terraform apply
```

### 3. Add Cloudflare Credentials

```bash
# Get secret name
SECRET_NAME=$(terraform output -raw secrets_manager_secret_name)

# Add your credentials
aws secretsmanager update-secret \
  --secret-id "$SECRET_NAME" \
  --secret-string '{
    "api_token": "YOUR_CLOUDFLARE_API_TOKEN",
    "account_id": "YOUR_ACCOUNT_ID",
    "kv_namespace_id": "YOUR_NAMESPACE_ID",
    "kv_namespace": "YOUR_NAMESPACE_NAME"
  }'
```

### 4. Test It

```bash
# Get function name
FUNCTION_NAME=$(terraform output -raw lambda_function_name)

# Test the function
aws lambda invoke \
  --function-name "$FUNCTION_NAME" \
  --payload '{"max_keys": 10}' \
  response.json

# Check results
cat response.json
```

## What Gets Created

- Lambda function (cloudflare-data-sync)
- DynamoDB table (cloudflare-kv-data)
- Secrets Manager secret (cloudflare-kv-credentials)
- CloudWatch logs, metrics, and dashboard
- IAM roles and policies

## Monitoring

View the CloudWatch dashboard:
```bash
terraform output cloudwatch_dashboard_url
```

View logs:
```bash
aws logs tail "/aws/lambda/cloudflare-data-sync" --follow
```

## Configuration (Optional)

Edit `terraform.tfvars` to customize:
- `lambda_timeout`: Execution timeout (default: 300 seconds)
- `lambda_memory_size`: Memory allocation (default: 512 MB)
- `alert_email`: Email for CloudWatch alarms (optional)

## Cleanup

```bash
terraform destroy
```

## Need Help?

- See `README.md` for detailed documentation
- See `DEPLOYMENT.md` for troubleshooting
- Check CloudWatch logs for errors
