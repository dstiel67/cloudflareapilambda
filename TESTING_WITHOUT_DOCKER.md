# Testing Without Docker

This guide shows you how to test the failover system without Docker, using AWS services directly or native tools.

## Quick Answer

**Yes! You can test without Docker using:**
1. **AWS-only testing** - Deploy to AWS and test there
2. **Native services** - Run services directly with Python/Node.js
3. **Simplified testing** - Test individual components

## Option 1: AWS-Only Testing (Recommended)

Test everything directly on AWS without any local services.

### Prerequisites
- AWS CLI configured
- Terraform installed
- Python 3.11+
- Node.js 20+ (for Atom Store)

### Step 1: Deploy to AWS

```bash
# Build Lambda functions
./build.sh

# Deploy infrastructure
terraform init
terraform apply
```

### Step 2: Test DynamoDB Directly

```bash
# Get table name
TABLE_NAME=$(terraform output -raw dynamodb_table_name)

# Write test data
aws dynamodb put-item \
  --table-name "$TABLE_NAME" \
  --item '{
    "pk": {"S": "FAILOVER_STATUS"},
    "sk": {"S": "CURRENT"},
    "test-app_Failover": {"S": "Y"},
    "test-app_LastUpdated": {"S": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"},
    "test-app_Reason": {"S": "AWS test"},
    "LastUpdatedBy": {"S": "test-script"}
  }'

# Verify write
aws dynamodb get-item \
  --table-name "$TABLE_NAME" \
  --key '{"pk": {"S": "FAILOVER_STATUS"}, "sk": {"S": "CURRENT"}}'
```

### Step 3: Test Lambda Function

```bash
# Get Lambda function name
LAMBDA_NAME=$(terraform output -raw kafka_consumer_lambda_function_name)

# Create test event file
cat > test-event.json << 'EOF'
{
  "records": {
    "failover-events-0": [{
      "value": "eyJldmVudF90eXBlIjogImZhaWxvdmVyIiwgInRpbWVzdGFtcCI6ICIyMDI0LTAxLTE1VDEwOjMwOjAwWiIsICJhcHBsaWNhdGlvbnMiOiBbeyJhcHBfaWQiOiAidGVzdC1hcHAiLCAiZmFpbG92ZXJfc3RhdHVzIjogIlkiLCAicmVhc29uIjogIlRlc3QifV0sICJ0cmlnZ2VyZWRfYnkiOiAidGVzdCJ9"
    }]
  }
}
EOF

# Invoke Lambda
aws lambda invoke \
  --function-name "$LAMBDA_NAME" \
  --payload file://test-event.json \
  response.json

# Check response
cat response.json
```

### Step 4: Monitor CloudWatch Logs

```bash
# View Lambda logs
aws logs tail "/aws/lambda/$LAMBDA_NAME" --follow

# Search for errors
aws logs filter-log-events \
  --log-group-name "/aws/lambda/$LAMBDA_NAME" \
  --filter-pattern "ERROR"
```

### Step 5: Verify DynamoDB Update

```bash
# Check if Lambda updated DynamoDB
aws dynamodb get-item \
  --table-name "$TABLE_NAME" \
  --key '{"pk": {"S": "FAILOVER_STATUS"}, "sk": {"S": "CURRENT"}}' \
  | jq '.Item'
```

## Option 2: Native Services (No Docker)

Run services directly on your machine.

### Run Atom Store Server Natively

```bash
# Install dependencies
cd atom_store/server
npm install

# Start server
PORT=3000 npm start

# In another terminal, test it
curl http://localhost:3000/health
```

### Run Read Flags Service Natively

```bash
# Install dependencies
cd read_flags_service
pip install -r requirements.txt

# Configure environment
export DYNAMODB_TABLE_NAME="failover-status"
export ATOM_STORE_URL="http://localhost:3000"
export POLLING_INTERVAL="10"
export AWS_REGION="us-east-1"

# Run service
python service.py
```

### Test the Flow

```bash
# Terminal 1: Run Atom Store
cd atom_store/server && npm start

# Terminal 2: Run Read Flags Service
cd read_flags_service && python service.py

# Terminal 3: Update DynamoDB
aws dynamodb put-item \
  --table-name failover-status \
  --item '{
    "pk": {"S": "FAILOVER_STATUS"},
    "sk": {"S": "CURRENT"},
    "app1_Failover": {"S": "Y"}
  }'

# Terminal 4: Watch Atom Store
curl http://localhost:3000/api/failover/status
```

## Option 3: Simplified Component Testing

Test each component individually without dependencies.

### Test 1: Lambda Function Unit Test

```bash
cd kafka_consumer_lambda

# Install test dependencies
pip install pytest pytest-mock

# Run unit tests
python -m pytest tests/ -v
```

### Test 2: DynamoDB Operations

```bash
# Test write
aws dynamodb put-item \
  --table-name failover-status \
  --item '{"pk": {"S": "TEST"}, "sk": {"S": "TEST"}}'

# Test read
aws dynamodb get-item \
  --table-name failover-status \
  --key '{"pk": {"S": "TEST"}, "sk": {"S": "TEST"}}'

# Test scan
aws dynamodb scan --table-name failover-status --limit 5

# Cleanup
aws dynamodb delete-item \
  --table-name failover-status \
  --key '{"pk": {"S": "TEST"}, "sk": {"S": "TEST"}}'
```

### Test 3: Atom Store API

```bash
# Start Atom Store
cd atom_store/server
npm install
npm start

# In another terminal, test API
# Health check
curl http://localhost:3000/health

# Get status
curl http://localhost:3000/api/failover/status

# Update status (simulate Read Flags Service)
curl -X POST http://localhost:3000/api/failover/update \
  -H "Content-Type: application/json" \
  -d '{
    "test-app": {
      "appId": "test-app",
      "failoverActive": true,
      "lastUpdated": "2024-01-15T10:30:00Z",
      "reason": "Test",
      "updatedBy": "test"
    }
  }'

# Verify update
curl http://localhost:3000/api/failover/status | jq
```

## Option 4: Manual End-to-End Test

Test the complete flow manually without automation.

### Step-by-Step Manual Test

**1. Deploy Infrastructure**
```bash
terraform apply
```

**2. Start Atom Store (Terminal 1)**
```bash
cd atom_store/server
npm install
npm start
```

**3. Start Read Flags Service (Terminal 2)**
```bash
cd read_flags_service
pip install -r requirements.txt
export DYNAMODB_TABLE_NAME="failover-status"
export ATOM_STORE_URL="http://localhost:3000"
export POLLING_INTERVAL="10"
python service.py
```

**4. Trigger Failover (Terminal 3)**
```bash
# Update DynamoDB directly
aws dynamodb put-item \
  --table-name failover-status \
  --item '{
    "pk": {"S": "FAILOVER_STATUS"},
    "sk": {"S": "CURRENT"},
    "app1_Failover": {"S": "Y"},
    "app1_LastUpdated": {"S": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"},
    "app1_Reason": {"S": "Manual test"}
  }'
```

**5. Monitor (Terminal 4)**
```bash
# Watch Read Flags Service logs (Terminal 2)
# Should see: "Changes detected, updating Atom Store"

# Check Atom Store
watch -n 2 'curl -s http://localhost:3000/api/failover/status | jq'
```

**6. Verify**
- Read Flags Service logs show change detected
- Atom Store API returns updated status
- If you have a UI, the banner should appear

**7. Clear Failover**
```bash
aws dynamodb put-item \
  --table-name failover-status \
  --item '{
    "pk": {"S": "FAILOVER_STATUS"},
    "sk": {"S": "CURRENT"},
    "app1_Failover": {"S": "N"}
  }'
```

## Option 5: AWS-Only Quick Test Script

Create a simplified test script that only uses AWS:

```bash
#!/bin/bash
# aws-only-test.sh - Test without Docker

set -e

echo "Testing Failover System (AWS Only)"
echo "==================================="

# Get AWS resources
TABLE_NAME=$(terraform output -raw dynamodb_table_name)
LAMBDA_NAME=$(terraform output -raw kafka_consumer_lambda_function_name)

echo "✓ Using DynamoDB table: $TABLE_NAME"
echo "✓ Using Lambda function: $LAMBDA_NAME"
echo ""

# Test 1: DynamoDB Write
echo "Test 1: Writing to DynamoDB..."
aws dynamodb put-item \
  --table-name "$TABLE_NAME" \
  --item '{
    "pk": {"S": "FAILOVER_STATUS"},
    "sk": {"S": "CURRENT"},
    "test_Failover": {"S": "Y"},
    "test_LastUpdated": {"S": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"}
  }' > /dev/null 2>&1
echo "✓ Write successful"
echo ""

# Test 2: DynamoDB Read
echo "Test 2: Reading from DynamoDB..."
RESULT=$(aws dynamodb get-item \
  --table-name "$TABLE_NAME" \
  --key '{"pk": {"S": "FAILOVER_STATUS"}, "sk": {"S": "CURRENT"}}' \
  --query 'Item.test_Failover.S' \
  --output text)

if [ "$RESULT" == "Y" ]; then
  echo "✓ Read successful: $RESULT"
else
  echo "✗ Read failed"
  exit 1
fi
echo ""

# Test 3: Lambda Invocation
echo "Test 3: Testing Lambda function..."
aws lambda invoke \
  --function-name "$LAMBDA_NAME" \
  --payload '{"test": true}' \
  response.json > /dev/null 2>&1

if [ -f response.json ]; then
  echo "✓ Lambda invoked successfully"
  cat response.json | jq
else
  echo "✗ Lambda invocation failed"
  exit 1
fi
echo ""

# Cleanup
echo "Cleaning up..."
rm -f response.json
echo "✓ Cleanup complete"
echo ""

echo "🎉 All tests passed!"
```

Save as `scripts/aws-only-test.sh` and run:
```bash
chmod +x scripts/aws-only-test.sh
./scripts/aws-only-test.sh
```

## Option 6: Using Managed Kafka (No Local Kafka)

If you have access to a Kafka cluster (AWS MSK, Confluent Cloud, etc.):

### Send Test Event to Managed Kafka

```bash
# Install kafka-python
pip install kafka-python

# Create test script
cat > send-to-kafka.py << 'EOF'
import json
from kafka import KafkaProducer
from datetime import datetime

producer = KafkaProducer(
    bootstrap_servers='your-kafka-broker:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

event = {
    "event_type": "failover",
    "timestamp": datetime.utcnow().isoformat() + "Z",
    "applications": [{
        "app_id": "test-app",
        "failover_status": "Y",
        "reason": "Test"
    }],
    "triggered_by": "manual_test"
}

producer.send('failover-events', event)
producer.close()
print("Event sent!")
EOF

# Run it
python send-to-kafka.py
```

## Comparison: Testing Methods

| Method | Pros | Cons | Time |
|--------|------|------|------|
| AWS-Only | No local setup, production-like | Costs money, slower | 10 min |
| Native Services | Full control, free | Manual setup, multiple terminals | 15 min |
| Component Testing | Fast, isolated | Doesn't test integration | 5 min |
| Manual E2E | Complete validation | Time-consuming | 20 min |
| AWS Quick Script | Automated, simple | Limited scope | 5 min |

## Recommended Approach Without Docker

**For quick validation:**
```bash
./scripts/aws-only-test.sh
```

**For thorough testing:**
1. Deploy to AWS: `terraform apply`
2. Run native services: Atom Store + Read Flags Service
3. Test manually: Update DynamoDB → Verify Atom Store
4. Monitor logs: CloudWatch + service logs

## Troubleshooting Without Docker

### Issue: Can't run Kafka locally

**Solution:** Use AWS MSK or skip Kafka testing
```bash
# Test Lambda directly
aws lambda invoke \
  --function-name your-lambda \
  --payload file://test-event.json \
  response.json
```

### Issue: Can't run DynamoDB locally

**Solution:** Use AWS DynamoDB directly
```bash
# All tests use real AWS DynamoDB
aws dynamodb put-item --table-name failover-status ...
```

### Issue: Multiple terminals needed

**Solution:** Use tmux or screen
```bash
# Install tmux
brew install tmux  # macOS
sudo apt install tmux  # Linux

# Start session
tmux new -s failover-test

# Split panes
Ctrl+b then "  # Split horizontally
Ctrl+b then %  # Split vertically
```

## Summary

**You don't need Docker! Here are your options:**

1. **Simplest:** Use AWS-only testing script
2. **Most thorough:** Run services natively (Python + Node.js)
3. **Fastest:** Test components individually
4. **Most realistic:** Deploy to AWS and test there

All testing methods are documented and ready to use without Docker.
