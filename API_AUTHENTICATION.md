# API Authentication Guide

This document explains the API authentication implementation for the Failover Status Management System.

## Overview

The Update API is secured with API key authentication to prevent unauthorized access and provide rate limiting. This implementation follows AWS Well-Architected Framework security best practices.

## Authentication Method

**API Key Authentication** via AWS API Gateway

- Simple to implement and use
- Built-in rate limiting and throttling
- Usage quotas for cost control
- Easy to rotate and manage
- No additional infrastructure required

## API Key Details

### Rate Limits

- **Rate Limit**: 1,000 requests per second
- **Burst Limit**: 2,000 requests
- **Monthly Quota**: 1,000,000 requests

These limits protect against abuse while allowing legitimate high-volume usage.

### Retrieving Your API Key

After deploying with Terraform:

```bash
# Get the API key (sensitive output)
terraform output -raw update_api_key_value

# Or view retrieval instructions
terraform output update_api_key_instructions
```

**Important**: The API key is marked as sensitive in Terraform and won't be displayed in normal output.

## Using the API Key

### HTTP Header

Include the API key in the `x-api-key` header:

```bash
curl -X POST "https://your-api-gateway.amazonaws.com/prod/redirect-status" \
  -H "Content-Type: application/json" \
  -H "x-api-key: YOUR_API_KEY_HERE" \
  -d '{"value": "ON", "updated_by": "admin"}'
```

### Endpoints Requiring Authentication

The following endpoints require API key authentication:

- `POST /redirect-status` - Update redirect status
- `GET /redirect-status` - Get current redirect status

### Endpoints NOT Requiring Authentication

These endpoints are publicly accessible:

- `GET /health` - Health check endpoint
- `OPTIONS /redirect-status` - CORS preflight (required for browser requests)

## Client Integration

### Bash/Shell Scripts

```bash
#!/bin/bash

# Store API key securely (use environment variable)
API_KEY="${UPDATE_API_KEY}"

# Or retrieve from Terraform
API_KEY=$(terraform output -raw update_api_key_value)

# Make authenticated request
curl -X POST "https://your-api-gateway.amazonaws.com/prod/redirect-status" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $API_KEY" \
  -d '{"value": "ON", "updated_by": "script"}'
```

### Angular/TypeScript

```typescript
import { HttpClient, HttpHeaders } from '@angular/common/http';

export class RedirectUpdateService {
  private readonly API_KEY = environment.updateApiKey; // From environment
  
  updateRedirectStatus(request: UpdateRequest) {
    const headers = new HttpHeaders({
      'Content-Type': 'application/json',
      'x-api-key': this.API_KEY
    });
    
    return this.http.post(url, request, { headers });
  }
}
```

### Python

```python
import requests
import os

API_KEY = os.environ.get('UPDATE_API_KEY')
API_URL = 'https://your-api-gateway.amazonaws.com/prod/redirect-status'

headers = {
    'Content-Type': 'application/json',
    'x-api-key': API_KEY
}

response = requests.post(
    API_URL,
    headers=headers,
    json={'value': 'ON', 'updated_by': 'python-script'}
)
```

### Node.js

```javascript
const axios = require('axios');

const API_KEY = process.env.UPDATE_API_KEY;
const API_URL = 'https://your-api-gateway.amazonaws.com/prod/redirect-status';

axios.post(API_URL, {
  value: 'ON',
  updated_by: 'node-script'
}, {
  headers: {
    'Content-Type': 'application/json',
    'x-api-key': API_KEY
  }
});
```

## Security Best Practices

### DO ✅

1. **Store API keys securely**
   - Use environment variables
   - Use secrets management services (AWS Secrets Manager, HashiCorp Vault)
   - Use backend services to proxy requests

2. **Rotate API keys regularly**
   - Create new API key
   - Update all clients
   - Delete old API key

3. **Monitor API usage**
   - Check CloudWatch metrics
   - Set up alarms for unusual activity
   - Review API Gateway logs

4. **Use HTTPS only**
   - API Gateway enforces HTTPS
   - Never send API keys over HTTP

5. **Limit API key distribution**
   - Only share with authorized users/services
   - Use separate keys for different environments
   - Document who has access

### DON'T ❌

1. **Never hardcode API keys in source code**
   ```typescript
   // ❌ BAD
   private readonly API_KEY = 'abcd1234...';
   
   // ✅ GOOD
   private readonly API_KEY = environment.updateApiKey;
   ```

2. **Never commit API keys to version control**
   - Add to `.gitignore`
   - Use environment-specific configuration
   - Scan repositories for leaked keys

3. **Never log API keys**
   ```bash
   # ❌ BAD
   echo "Using API key: $API_KEY"
   
   # ✅ GOOD
   echo "Using API key: ${API_KEY:0:4}****"
   ```

4. **Never share API keys in public channels**
   - Slack, email, tickets
   - Use secure sharing methods
   - Rotate if accidentally exposed

5. **Never use production keys in development**
   - Use separate API keys per environment
   - Terraform workspaces can help manage this

## API Key Rotation

### Step 1: Create New API Key

Update `update_api.tf`:

```terraform
resource "aws_api_gateway_api_key" "update_api_key_v2" {
  name        = "${var.update_api_gateway_name}-key-v2"
  description = "API key for redirect status update endpoint (v2)"
  enabled     = true
}

resource "aws_api_gateway_usage_plan_key" "update_api_usage_plan_key_v2" {
  key_id        = aws_api_gateway_api_key.update_api_key_v2.id
  key_type      = "API_KEY"
  usage_plan_id = aws_api_gateway_usage_plan.update_api_usage_plan.id
}
```

### Step 2: Deploy New Key

```bash
terraform apply
terraform output -raw update_api_key_v2_value
```

### Step 3: Update Clients

Update all clients to use the new API key.

### Step 4: Verify New Key Works

```bash
NEW_API_KEY=$(terraform output -raw update_api_key_v2_value)

curl -X GET "$(terraform output -raw get_redirect_status_endpoint)" \
  -H "x-api-key: $NEW_API_KEY"
```

### Step 5: Disable Old Key

```terraform
resource "aws_api_gateway_api_key" "update_api_key" {
  enabled = false  # Disable old key
}
```

### Step 6: Remove Old Key (After Grace Period)

```terraform
# Remove old key resources from Terraform
# resource "aws_api_gateway_api_key" "update_api_key" { ... }
# resource "aws_api_gateway_usage_plan_key" "update_api_usage_plan_key" { ... }
```

## Monitoring and Troubleshooting

### Check API Key Usage

```bash
# Get usage plan ID
USAGE_PLAN_ID=$(aws apigateway get-usage-plans \
  --query "items[?name=='redirect-status-api-usage-plan'].id" \
  --output text)

# Get API key ID
API_KEY_ID=$(aws apigateway get-api-keys \
  --query "items[?name=='redirect-status-api-key'].id" \
  --output text)

# Check usage
aws apigateway get-usage \
  --usage-plan-id "$USAGE_PLAN_ID" \
  --key-id "$API_KEY_ID" \
  --start-date "2024-01-01" \
  --end-date "2024-01-31"
```

### Common Error Responses

#### 403 Forbidden - Missing API Key

```json
{
  "message": "Forbidden"
}
```

**Solution**: Include `x-api-key` header in request.

#### 403 Forbidden - Invalid API Key

```json
{
  "message": "Forbidden"
}
```

**Solution**: Verify API key is correct and enabled.

#### 429 Too Many Requests

```json
{
  "message": "Too Many Requests"
}
```

**Solution**: You've exceeded rate limits. Wait and retry with exponential backoff.

### CloudWatch Metrics

Monitor these metrics in CloudWatch:

- `Count` - Total API requests
- `4XXError` - Client errors (including auth failures)
- `5XXError` - Server errors
- `Latency` - Request latency

### CloudWatch Alarms

Set up alarms for:

```bash
# High 4XX error rate (auth failures)
aws cloudwatch put-metric-alarm \
  --alarm-name update-api-auth-failures \
  --alarm-description "High authentication failure rate" \
  --metric-name 4XXError \
  --namespace AWS/ApiGateway \
  --statistic Sum \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold
```

## Advanced Configuration

### Multiple API Keys

Create separate keys for different clients:

```terraform
resource "aws_api_gateway_api_key" "admin_key" {
  name = "admin-api-key"
}

resource "aws_api_gateway_api_key" "service_key" {
  name = "service-api-key"
}

resource "aws_api_gateway_api_key" "readonly_key" {
  name = "readonly-api-key"
}
```

### Custom Usage Plans

Create different usage plans for different tiers:

```terraform
resource "aws_api_gateway_usage_plan" "premium_plan" {
  name = "premium-usage-plan"
  
  throttle_settings {
    burst_limit = 5000
    rate_limit  = 2000
  }
  
  quota_settings {
    limit  = 10000000
    period = "MONTH"
  }
}

resource "aws_api_gateway_usage_plan" "basic_plan" {
  name = "basic-usage-plan"
  
  throttle_settings {
    burst_limit = 1000
    rate_limit  = 500
  }
  
  quota_settings {
    limit  = 100000
    period = "MONTH"
  }
}
```

## Migration from No Auth

If you're migrating from an unauthenticated API:

### Option 1: Gradual Migration (Recommended)

1. Deploy API key authentication
2. Keep both authenticated and unauthenticated endpoints
3. Update clients gradually
4. Monitor usage of old endpoints
5. Remove unauthenticated endpoints after migration

### Option 2: Immediate Migration

1. Deploy API key authentication
2. Distribute API keys to all clients
3. Update all clients simultaneously
4. Test thoroughly before deployment

## Cost Considerations

API Gateway API keys are free, but you pay for:

- API Gateway requests: $3.50 per million requests
- Data transfer: $0.09 per GB (first 10 TB)
- CloudWatch Logs: $0.50 per GB ingested

With 1M requests/month:
- API Gateway: ~$3.50/month
- Minimal additional cost for API key management

## Compliance and Audit

### Audit Trail

All API requests are logged to CloudWatch:

```bash
# View API Gateway access logs
aws logs tail /aws/apigateway/redirect-status-api --follow
```

### Compliance Requirements

API key authentication helps meet:

- **Access Control**: Only authorized users can update status
- **Rate Limiting**: Prevents abuse and DoS attacks
- **Audit Trail**: All requests logged with API key ID
- **Usage Tracking**: Monitor who is using the API

## Summary

API key authentication provides:

✅ Simple implementation and usage
✅ Built-in rate limiting and throttling
✅ Usage quotas for cost control
✅ Easy rotation and management
✅ CloudWatch integration for monitoring
✅ No additional infrastructure required

For production deployments, consider:
- Regular API key rotation
- Separate keys per environment
- Monitoring and alerting
- Secure key storage
- Client-side retry logic

## References

- [AWS API Gateway API Keys](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-api-key-source.html)
- [AWS API Gateway Usage Plans](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-api-usage-plans.html)
- [AWS Well-Architected Security Pillar](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/welcome.html)
