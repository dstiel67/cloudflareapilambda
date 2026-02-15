# Dead Letter Queue (DLQ) Guide

## Overview

Dead Letter Queues (DLQs) are configured for all Lambda functions in the failover status management system to capture failed invocations for debugging and retry.

## What is a Dead Letter Queue?

A Dead Letter Queue is an SQS queue that receives messages (failed Lambda invocations) when:
- Lambda function execution fails after all retry attempts
- Lambda function times out
- Lambda function throws an unhandled exception
- Lambda function runs out of memory

## DLQ Configuration

### Queues Created

| Lambda Function | DLQ Name | Retention | Visibility Timeout |
|----------------|----------|-----------|-------------------|
| Legacy Cloudflare Sync | `cloudflare-data-sync-dlq` | 14 days | 5 minutes |
| Update API | `redirect-status-update-dlq` | 14 days | 30 seconds |
| Notification Handler | `cloudflare-notification-handler-dlq` | 14 days | 1 minute |
| SSE Endpoint | `cloudflare-sse-endpoint-dlq` | 14 days | 30 seconds |

### Message Retention

- **Retention Period**: 14 days (1,209,600 seconds)
- Messages older than 14 days are automatically deleted
- Provides sufficient time to investigate and resolve issues

### Visibility Timeout

- Set to match each Lambda function's timeout
- Prevents duplicate processing during investigation
- Can be adjusted based on retry strategy

## Monitoring

### CloudWatch Alarms

Alarms are automatically created (when `alert_email` is configured) to notify when messages appear in any DLQ:

```terraform
# Example alarm configuration
alarm_name          = "lambda-function-dlq-messages"
comparison_operator = "GreaterThanThreshold"
threshold           = "0"
alarm_description   = "Alert when messages appear in DLQ"
```

**Alert Triggers:**
- Any message in DLQ triggers immediate alert
- Alerts sent to configured SNS topic
- Email notification to `alert_email` address

### CloudWatch Metrics

Monitor DLQ metrics in CloudWatch:

```bash
# View DLQ message count
aws cloudwatch get-metric-statistics \
  --namespace AWS/SQS \
  --metric-name ApproximateNumberOfMessagesVisible \
  --dimensions Name=QueueName,Value=cloudflare-data-sync-dlq \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average
```

## Accessing DLQ Messages

### View Messages in Console

1. Navigate to AWS SQS Console
2. Select the DLQ (e.g., `cloudflare-data-sync-dlq`)
3. Click "Send and receive messages"
4. Click "Poll for messages"
5. View message details

### View Messages via CLI

```bash
# List all DLQs
aws sqs list-queues --queue-name-prefix "cloudflare"

# Get DLQ URL
DLQ_URL=$(aws sqs get-queue-url --queue-name cloudflare-data-sync-dlq --query 'QueueUrl' --output text)

# Receive messages (without deleting)
aws sqs receive-message \
  --queue-url "$DLQ_URL" \
  --max-number-of-messages 10 \
  --visibility-timeout 0 \
  --attribute-names All \
  --message-attribute-names All

# Get message count
aws sqs get-queue-attributes \
  --queue-url "$DLQ_URL" \
  --attribute-names ApproximateNumberOfMessages
```

### Message Format

DLQ messages contain:

```json
{
  "MessageId": "unique-message-id",
  "ReceiptHandle": "receipt-handle-for-deletion",
  "Body": "{\"requestContext\": {...}, \"requestPayload\": {...}}",
  "Attributes": {
    "ApproximateReceiveCount": "1",
    "SentTimestamp": "1234567890000",
    "ApproximateFirstReceiveTimestamp": "1234567890000"
  },
  "MessageAttributes": {
    "RequestID": {
      "StringValue": "lambda-request-id",
      "DataType": "String"
    },
    "ErrorCode": {
      "StringValue": "error-code",
      "DataType": "String"
    },
    "ErrorMessage": {
      "StringValue": "error-message",
      "DataType": "String"
    }
  }
}
```

## Troubleshooting Failed Invocations

### Step 1: Identify the Failure

```bash
# Get DLQ URL
DLQ_URL=$(aws sqs get-queue-url --queue-name cloudflare-data-sync-dlq --query 'QueueUrl' --output text)

# Receive and inspect message
aws sqs receive-message \
  --queue-url "$DLQ_URL" \
  --max-number-of-messages 1 \
  --attribute-names All \
  --message-attribute-names All > failed_message.json

# View the message
cat failed_message.json | jq '.'
```

### Step 2: Analyze the Error

Check the message attributes for:
- `ErrorCode`: Type of error (e.g., `Timeout`, `MemoryExceeded`, `UnhandledException`)
- `ErrorMessage`: Detailed error message
- `RequestID`: Lambda request ID for CloudWatch Logs lookup

### Step 3: Check CloudWatch Logs

```bash
# Extract request ID from DLQ message
REQUEST_ID=$(cat failed_message.json | jq -r '.Messages[0].MessageAttributes.RequestID.StringValue')

# Search CloudWatch Logs
aws logs filter-log-events \
  --log-group-name "/aws/lambda/cloudflare-data-sync" \
  --filter-pattern "$REQUEST_ID" \
  --start-time $(date -u -d '24 hours ago' +%s000) \
  --end-time $(date -u +%s000)
```

### Step 4: Fix the Issue

Common issues and solutions:

**Timeout Errors:**
```terraform
# Increase Lambda timeout
resource "aws_lambda_function" "example" {
  timeout = 60  # Increase from 30 to 60 seconds
}
```

**Memory Errors:**
```terraform
# Increase Lambda memory
resource "aws_lambda_function" "example" {
  memory_size = 512  # Increase from 256 to 512 MB
}
```

**Unhandled Exceptions:**
- Review Lambda code
- Add try-catch blocks
- Improve error handling
- Add input validation

**DynamoDB Throttling:**
- Check DynamoDB capacity
- Implement exponential backoff
- Reduce batch sizes

### Step 5: Retry Failed Messages

#### Manual Retry

```bash
# Get message from DLQ
MESSAGE=$(aws sqs receive-message \
  --queue-url "$DLQ_URL" \
  --max-number-of-messages 1 \
  --query 'Messages[0]')

# Extract payload
PAYLOAD=$(echo "$MESSAGE" | jq -r '.Body')

# Invoke Lambda with original payload
aws lambda invoke \
  --function-name cloudflare-data-sync \
  --payload "$PAYLOAD" \
  response.json

# If successful, delete message from DLQ
RECEIPT_HANDLE=$(echo "$MESSAGE" | jq -r '.ReceiptHandle')
aws sqs delete-message \
  --queue-url "$DLQ_URL" \
  --receipt-handle "$RECEIPT_HANDLE"
```

#### Automated Retry Script

Create `scripts/retry-dlq-messages.sh`:

```bash
#!/bin/bash
set -e

DLQ_NAME="$1"
LAMBDA_FUNCTION="$2"

if [ -z "$DLQ_NAME" ] || [ -z "$LAMBDA_FUNCTION" ]; then
  echo "Usage: $0 <dlq-name> <lambda-function-name>"
  exit 1
fi

# Get DLQ URL
DLQ_URL=$(aws sqs get-queue-url --queue-name "$DLQ_NAME" --query 'QueueUrl' --output text)

# Get message count
MESSAGE_COUNT=$(aws sqs get-queue-attributes \
  --queue-url "$DLQ_URL" \
  --attribute-names ApproximateNumberOfMessages \
  --query 'Attributes.ApproximateNumberOfMessages' \
  --output text)

echo "Found $MESSAGE_COUNT messages in DLQ"

# Process each message
for i in $(seq 1 "$MESSAGE_COUNT"); do
  echo "Processing message $i/$MESSAGE_COUNT..."
  
  # Receive message
  MESSAGE=$(aws sqs receive-message \
    --queue-url "$DLQ_URL" \
    --max-number-of-messages 1 \
    --query 'Messages[0]')
  
  if [ "$MESSAGE" == "null" ]; then
    echo "No more messages"
    break
  fi
  
  # Extract payload and receipt handle
  PAYLOAD=$(echo "$MESSAGE" | jq -r '.Body')
  RECEIPT_HANDLE=$(echo "$MESSAGE" | jq -r '.ReceiptHandle')
  
  # Retry Lambda invocation
  if aws lambda invoke \
    --function-name "$LAMBDA_FUNCTION" \
    --payload "$PAYLOAD" \
    response.json > /dev/null 2>&1; then
    
    echo "✅ Retry successful"
    
    # Delete message from DLQ
    aws sqs delete-message \
      --queue-url "$DLQ_URL" \
      --receipt-handle "$RECEIPT_HANDLE"
  else
    echo "❌ Retry failed"
    # Leave message in DLQ for investigation
  fi
  
  sleep 1
done

echo "Retry complete"
```

Usage:
```bash
chmod +x scripts/retry-dlq-messages.sh
./scripts/retry-dlq-messages.sh cloudflare-data-sync-dlq cloudflare-data-sync
```

## Best Practices

### 1. Monitor DLQ Regularly

Set up CloudWatch Dashboard widget:

```json
{
  "type": "metric",
  "properties": {
    "metrics": [
      ["AWS/SQS", "ApproximateNumberOfMessagesVisible", {"stat": "Average"}]
    ],
    "view": "timeSeries",
    "region": "us-east-1",
    "title": "DLQ Message Count",
    "period": 300
  }
}
```

### 2. Set Up Alerts

Ensure `alert_email` is configured in `terraform.tfvars`:

```hcl
alert_email = "ops-team@example.com"
```

### 3. Investigate Immediately

- DLQ messages indicate system issues
- Investigate within 24 hours
- Fix root cause before retrying

### 4. Implement Idempotency

Ensure Lambda functions are idempotent:

```python
def lambda_handler(event, context):
    # Check if already processed
    request_id = context.request_id
    if is_already_processed(request_id):
        return {"statusCode": 200, "body": "Already processed"}
    
    # Process event
    result = process_event(event)
    
    # Mark as processed
    mark_as_processed(request_id)
    
    return result
```

### 5. Use Exponential Backoff

Lambda automatically retries failed invocations:
- Asynchronous invocations: 2 retries
- Event source mappings: Configurable retries

After all retries, message goes to DLQ.

### 6. Clean Up Old Messages

Periodically purge resolved messages:

```bash
# Purge all messages from DLQ (use with caution!)
aws sqs purge-queue --queue-url "$DLQ_URL"
```

### 7. Document Failure Patterns

Keep a log of common failures:
- Error types
- Root causes
- Solutions applied
- Prevention measures

## Cost Considerations

### SQS Pricing

- **Requests**: $0.40 per 1 million requests (after free tier)
- **Storage**: First 1 GB free, then $0.40 per GB-month
- **Free Tier**: 1 million requests per month (permanent)

### Typical Costs

With <0.1% failure rate:

| Invocations/Month | Failures | DLQ Requests | Cost |
|-------------------|----------|--------------|------|
| 100,000 | 100 | 200 | $0.00 |
| 1,000,000 | 1,000 | 2,000 | $0.00 |
| 10,000,000 | 10,000 | 20,000 | $0.01 |

**DLQ cost is negligible** - within free tier for most use cases.

## Integration with Monitoring

### CloudWatch Dashboard

Add DLQ metrics to existing dashboard:

```terraform
resource "aws_cloudwatch_dashboard" "lambda_dashboard" {
  dashboard_body = jsonencode({
    widgets = [
      # ... existing widgets ...
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/SQS", "ApproximateNumberOfMessagesVisible", 
             "QueueName", aws_sqs_queue.lambda_dlq.name],
            [".", ".", ".", aws_sqs_queue.update_lambda_dlq.name],
            [".", ".", ".", aws_sqs_queue.notification_lambda_dlq.name],
            [".", ".", ".", aws_sqs_queue.sse_lambda_dlq.name]
          ]
          title = "DLQ Message Counts"
        }
      }
    ]
  })
}
```

### SNS Notifications

DLQ alarms automatically send notifications to configured SNS topic:

```bash
# Subscribe additional endpoints
aws sns subscribe \
  --topic-arn "arn:aws:sns:us-east-1:123456789012:cloudflare-data-sync-alerts" \
  --protocol email \
  --notification-endpoint "team@example.com"
```

## Troubleshooting Common Issues

### Issue: Messages Not Appearing in DLQ

**Possible Causes:**
1. Lambda function succeeding (no failures)
2. DLQ not configured correctly
3. IAM permissions missing

**Solution:**
```bash
# Check Lambda DLQ configuration
aws lambda get-function-configuration \
  --function-name cloudflare-data-sync \
  --query 'DeadLetterConfig'

# Check IAM permissions
aws iam get-role-policy \
  --role-name cloudflare-data-sync-execution-role \
  --policy-name cloudflare-data-sync-dlq-policy
```

### Issue: Cannot Read Messages from DLQ

**Possible Causes:**
1. IAM permissions missing
2. Incorrect queue URL
3. Messages already deleted

**Solution:**
```bash
# Verify queue exists
aws sqs list-queues --queue-name-prefix "cloudflare"

# Check queue attributes
aws sqs get-queue-attributes \
  --queue-url "$DLQ_URL" \
  --attribute-names All
```

### Issue: Too Many Messages in DLQ

**Possible Causes:**
1. Systemic Lambda failures
2. Configuration issues
3. Downstream service unavailable

**Solution:**
1. Check CloudWatch Logs for error patterns
2. Review recent code/config changes
3. Check downstream service health
4. Fix root cause before retrying

## Summary

Dead Letter Queues provide:

✅ **Failure Capture** - No lost events
✅ **Debugging** - Full context for investigation
✅ **Retry Capability** - Manual or automated retry
✅ **Monitoring** - CloudWatch alarms and metrics
✅ **Cost Effective** - Within free tier for typical usage
✅ **Reliability** - Improved system resilience

**Key Takeaways:**
- Monitor DLQ regularly
- Investigate failures promptly
- Fix root causes before retrying
- Implement idempotent Lambda functions
- Use DLQ metrics in dashboards

## References

- [AWS Lambda DLQ Documentation](https://docs.aws.amazon.com/lambda/latest/dg/invocation-async.html#invocation-dlq)
- [Amazon SQS Documentation](https://docs.aws.amazon.com/sqs/)
- [AWS Lambda Error Handling](https://docs.aws.amazon.com/lambda/latest/dg/python-exceptions.html)
- [SQS Pricing](https://aws.amazon.com/sqs/pricing/)
