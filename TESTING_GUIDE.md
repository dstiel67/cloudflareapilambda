# Failover Status Management System - Testing Guide

This guide provides comprehensive testing strategies for the failover system, from unit tests to end-to-end integration testing.

## Testing Strategy Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Testing Pyramid                          │
│                                                             │
│                    ┌─────────────┐                          │
│                    │   E2E Tests │  (Manual/Automated)      │
│                    └─────────────┘                          │
│                  ┌───────────────────┐                      │
│                  │ Integration Tests │  (Component pairs)   │
│                  └───────────────────┘                      │
│              ┌─────────────────────────────┐                │
│              │      Unit Tests             │  (Individual)  │
│              └─────────────────────────────┘                │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start Testing (5 Minutes)

For a quick validation that everything works:

```bash
# 1. Deploy infrastructure
terraform apply -auto-approve

# 2. Start local services
docker-compose up -d  # If using Docker Compose

# 3. Run the quick test script
./scripts/quick-test.sh
```

## Testing Levels

### 1. Unit Testing

Test individual components in isolation.

#### Lambda Functions

**Kafka Consumer Lambda:**
```bash
cd kafka_consumer_lambda
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=lambda_function --cov-report=html
```

**Test file example** (`kafka_consumer_lambda/tests/test_lambda_function.py`):
```python
import pytest
import json
from lambda_function import lambda_handler, decode_kafka_message, process_failover_event

def test_decode_kafka_message():
    """Test Kafka message decoding"""
    import base64
    
    message = {"event_type": "failover", "applications": []}
    encoded = base64.b64encode(json.dumps(message).encode('utf-8')).decode('utf-8')
    
    kafka_record = {"value": encoded}
    result = decode_kafka_message(kafka_record)
    
    assert result["event_type"] == "failover"
    assert "applications" in result

def test_lambda_handler_success(mocker):
    """Test successful Lambda execution"""
    # Mock DynamoDB
    mock_table = mocker.Mock()
    mocker.patch('lambda_function.dynamodb.Table', return_value=mock_table)
    
    event = {
        "records": {
            "topic-0": [{
                "value": base64.b64encode(json.dumps({
                    "event_type": "failover",
                    "applications": [{"app_id": "app1", "failover_status": "Y"}]
                }).encode('utf-8')).decode('utf-8')
            }]
        }
    }
    
    result = lambda_handler(event, None)
    assert result["statusCode"] == 200
```

**Read Flags Service:**
```bash
cd read_flags_service
python -m pytest tests/ -v
```

**Atom Store Server:**
```bash
cd atom_store/server
npm test
```

### 2. Integration Testing

Test component interactions.

#### Test Kafka → Lambda → DynamoDB

**Setup test Kafka:**
```bash
# Start local Kafka (Docker)
docker run -d --name kafka-test \
  -p 9092:9092 \
  -e KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://localhost:9092 \
  apache/kafka:latest
```

**Send test event:**
```bash
# Install kafka-python
pip install kafka-python

# Send test message
python scripts/send-test-kafka-event.py
```

**Verify DynamoDB:**
```bash
aws dynamodb get-item \
  --table-name failover-status \
  --key '{"pk": {"S": "FAILOVER_STATUS"}, "sk": {"S": "CURRENT"}}'
```

#### Test Update API → DynamoDB

**Get API key:**
```bash
API_KEY=$(terraform output -raw update_api_key_value)
```

**Test update endpoint:**
```bash
# Turn redirect ON
curl -X POST "$(terraform output -raw update_redirect_status_endpoint)" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $API_KEY" \
  -d '{"value": "ON", "updated_by": "test", "reason": "Integration test"}'

# Verify in DynamoDB
aws dynamodb get-item \
  --table-name cloudflare-kv-data \
  --key '{"pk": {"S": "NAMESPACE#your-namespace-id"}, "sk": {"S": "KEY#redirect-all-users-to-essentials"}}'
```

#### Test DynamoDB → Read Flags Service → Atom Store

**Manual DynamoDB update:**
```bash
aws dynamodb put-item \
  --table-name failover-status \
  --item '{
    "pk": {"S": "FAILOVER_STATUS"},
    "sk": {"S": "CURRENT"},
    "app1_Failover": {"S": "Y"},
    "app1_LastUpdated": {"S": "2024-01-15T10:30:00Z"},
    "app1_Reason": {"S": "Test failover"}
  }'
```

**Check Read Flags Service logs:**
```bash
# Docker
docker logs -f read-flags-service

# Kubernetes
kubectl logs -f deployment/read-flags-service
```

**Verify Atom Store received update:**
```bash
curl http://localhost:3000/api/failover/status
```

### 3. End-to-End Testing

Test the complete flow from trigger to UI update.

#### Automated E2E Test Script

Create `scripts/e2e-test.sh`:
```bash
#!/bin/bash
set -e

echo "Starting End-to-End Test..."

# 1. Trigger failover via Ansible
echo "Step 1: Triggering failover..."
API_KEY=$(terraform output -raw update_api_key_value)
curl -X POST "$(terraform output -raw update_redirect_status_endpoint)" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $API_KEY" \
  -d '{"value": "ON", "updated_by": "e2e-test", "reason": "E2E Test"}'

# 2. Wait for Kafka processing
echo "Step 2: Waiting for Kafka processing (5s)..."
sleep 5

# 3. Check Lambda execution
echo "Step 3: Checking Lambda logs..."
aws logs tail /aws/lambda/failover-system-kafka-consumer --since 1m

# 4. Verify DynamoDB
echo "Step 4: Verifying DynamoDB..."
RESULT=$(aws dynamodb get-item \
  --table-name failover-status \
  --key '{"pk": {"S": "FAILOVER_STATUS"}, "sk": {"S": "CURRENT"}}' \
  --query 'Item.test-app_Failover.S' \
  --output text)

if [ "$RESULT" == "Y" ]; then
  echo "✅ DynamoDB updated successfully"
else
  echo "❌ DynamoDB update failed"
  exit 1
fi

# 5. Wait for Read Flags Service polling
echo "Step 5: Waiting for Read Flags Service (15s)..."
sleep 15

# 6. Check Atom Store
echo "Step 6: Checking Atom Store..."
ATOM_RESULT=$(curl -s http://localhost:3000/api/failover/status | jq -r '.["test-app"].failoverActive')

if [ "$ATOM_RESULT" == "true" ]; then
  echo "✅ Atom Store updated successfully"
else
  echo "❌ Atom Store update failed"
  exit 1
fi

# 7. Clear failover
echo "Step 7: Clearing failover..."
curl -X POST "$(terraform output -raw update_redirect_status_endpoint)" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $API_KEY" \
  -d '{"value": "OFF", "updated_by": "e2e-test", "reason": "E2E Test Complete"}'

sleep 15

# 8. Verify cleared
CLEARED=$(curl -s http://localhost:3000/api/failover/status | jq -r '.["test-app"].failoverActive')

if [ "$CLEARED" == "false" ]; then
  echo "✅ Failover cleared successfully"
else
  echo "❌ Failover clear failed"
  exit 1
fi

echo ""
echo "🎉 End-to-End Test PASSED!"
```

Make it executable:
```bash
chmod +x scripts/e2e-test.sh
./scripts/e2e-test.sh
```

### 4. Performance Testing

Test system performance under load.

#### Load Test Script

Create `scripts/load-test.py`:
```python
#!/usr/bin/env python3
"""
Load test for failover system.
Sends multiple failover events and measures latency.
"""

import time
import json
from kafka import KafkaProducer
from datetime import datetime
import statistics

def send_failover_event(producer, app_id, status):
    """Send a failover event to Kafka"""
    event = {
        "event_type": "failover",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "applications": [{
            "app_id": app_id,
            "failover_status": status,
            "reason": "Load test"
        }],
        "triggered_by": "load_test",
        "severity": "info"
    }
    
    start_time = time.time()
    future = producer.send('failover-events', event)
    result = future.get(timeout=10)
    end_time = time.time()
    
    return end_time - start_time

def main():
    # Create Kafka producer
    producer = KafkaProducer(
        bootstrap_servers='localhost:9092',
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    
    latencies = []
    num_events = 100
    
    print(f"Sending {num_events} failover events...")
    
    for i in range(num_events):
        app_id = f"load-test-app-{i % 10}"  # 10 different apps
        status = "Y" if i % 2 == 0 else "N"
        
        latency = send_failover_event(producer, app_id, status)
        latencies.append(latency)
        
        if (i + 1) % 10 == 0:
            print(f"Sent {i + 1}/{num_events} events...")
    
    producer.close()
    
    # Calculate statistics
    print("\n" + "="*50)
    print("Load Test Results")
    print("="*50)
    print(f"Total events sent: {num_events}")
    print(f"Average latency: {statistics.mean(latencies)*1000:.2f}ms")
    print(f"Median latency: {statistics.median(latencies)*1000:.2f}ms")
    print(f"Min latency: {min(latencies)*1000:.2f}ms")
    print(f"Max latency: {max(latencies)*1000:.2f}ms")
    print(f"Std deviation: {statistics.stdev(latencies)*1000:.2f}ms")

if __name__ == '__main__':
    main()
```

Run load test:
```bash
python scripts/load-test.py
```

#### Measure End-to-End Latency

Create `scripts/measure-latency.sh`:
```bash
#!/bin/bash

echo "Measuring end-to-end latency..."

# Record start time
START=$(date +%s%N)

# Trigger failover
ansible-playbook ansible-example/trigger-failover.yml \
  -e "failover_apps=[{app_id: 'latency-test', failover_status: 'Y', reason: 'Latency test'}]" \
  > /dev/null 2>&1

# Poll Atom Store until update appears
while true; do
  RESULT=$(curl -s http://localhost:3000/api/failover/status | jq -r '.["latency-test"].failoverActive' 2>/dev/null)
  
  if [ "$RESULT" == "true" ]; then
    END=$(date +%s%N)
    LATENCY=$(( (END - START) / 1000000 ))  # Convert to milliseconds
    echo "✅ End-to-end latency: ${LATENCY}ms"
    break
  fi
  
  sleep 0.5
done
```

### 5. UI Testing

Test application integration.

#### Manual Browser Test

1. **Start application:**
   ```bash
   cd your-app
   npm start
   ```

2. **Open browser console** and watch for updates

3. **Trigger failover:**
   ```bash
   ansible-playbook ansible-example/trigger-failover.yml
   ```

4. **Verify:**
   - Failover banner appears
   - Console shows atom state change
   - Banner disappears when cleared

#### Automated UI Test (Playwright)

Create `tests/ui/failover-banner.spec.ts`:
```typescript
import { test, expect } from '@playwright/test';

test('failover banner appears and disappears', async ({ page }) => {
  // Navigate to app
  await page.goto('http://localhost:4200');
  
  // Verify no banner initially
  await expect(page.locator('.failover-banner')).not.toBeVisible();
  
  // Trigger failover (via API or Ansible)
  // ... trigger code ...
  
  // Wait for banner to appear
  await expect(page.locator('.failover-banner')).toBeVisible({ timeout: 30000 });
  
  // Verify banner content
  await expect(page.locator('.failover-banner')).toContainText('failover mode');
  
  // Clear failover
  // ... clear code ...
  
  // Wait for banner to disappear
  await expect(page.locator('.failover-banner')).not.toBeVisible({ timeout: 30000 });
});
```

Run UI tests:
```bash
npx playwright test
```

## Testing Checklist

### Pre-Deployment Testing

- [ ] Unit tests pass for all Lambda functions
- [ ] Unit tests pass for Read Flags Service
- [ ] Unit tests pass for Atom Store Server
- [ ] Integration tests pass for Kafka → Lambda → DynamoDB
- [ ] Integration tests pass for DynamoDB → Read Flags → Atom Store
- [ ] Build scripts work on target OS
- [ ] Terraform plan shows expected resources

### Post-Deployment Testing

- [ ] All Lambda functions deployed successfully
- [ ] DynamoDB tables created and accessible
- [ ] Kafka event source mapping configured
- [ ] Read Flags Service running and polling
- [ ] Atom Store Server responding to requests
- [ ] End-to-end test passes
- [ ] Performance test shows acceptable latency
- [ ] UI test shows banner appears/disappears

### Regression Testing

Run after any code changes:

```bash
# Run all tests
./scripts/run-all-tests.sh
```

Create `scripts/run-all-tests.sh`:
```bash
#!/bin/bash
set -e

echo "Running all tests..."

# Unit tests
echo "1. Running Lambda unit tests..."
cd kafka_consumer_lambda && python -m pytest tests/ -v && cd ..

echo "2. Running Read Flags Service tests..."
cd read_flags_service && python -m pytest tests/ -v && cd ..

echo "3. Running Atom Store tests..."
cd atom_store/server && npm test && cd ../..

# Integration tests
echo "4. Running integration tests..."
./scripts/integration-test.sh

# E2E test
echo "5. Running E2E test..."
./scripts/e2e-test.sh

echo ""
echo "✅ All tests passed!"
```

## Monitoring During Testing

### CloudWatch Logs

Monitor in real-time:
```bash
# Kafka Consumer Lambda
aws logs tail /aws/lambda/failover-system-kafka-consumer --follow

# All Lambda functions
aws logs tail /aws/lambda/failover-system-kafka-consumer \
  /aws/lambda/failover-system-update \
  /aws/lambda/failover-system-notification \
  --follow
```

### Metrics Dashboard

Create test metrics dashboard:
```bash
# View Lambda metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=failover-system-kafka-consumer \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum
```

## Troubleshooting Test Failures

### Lambda Test Failures

**Issue:** Lambda not processing events

**Debug:**
```bash
# Check Lambda logs
aws logs tail /aws/lambda/failover-system-kafka-consumer --follow

# Test Lambda manually
aws lambda invoke \
  --function-name failover-system-kafka-consumer \
  --payload file://test-event.json \
  response.json

cat response.json
```

### DynamoDB Test Failures

**Issue:** DynamoDB not updating

**Debug:**
```bash
# Check table exists
aws dynamodb describe-table --table-name failover-status

# Check IAM permissions
aws lambda get-function --function-name failover-system-kafka-consumer \
  --query 'Configuration.Role'

# Scan table
aws dynamodb scan --table-name failover-status
```

### Atom Store Test Failures

**Issue:** Atom Store not receiving updates

**Debug:**
```bash
# Check Atom Store logs
docker logs atom-store-service

# Test API directly
curl -X POST http://localhost:3000/api/failover/update \
  -H "Content-Type: application/json" \
  -d '{"test-app": {"appId": "test-app", "failoverActive": true}}'

# Verify update
curl http://localhost:3000/api/failover/status
```

## Continuous Integration

### GitHub Actions Example

Create `.github/workflows/test.yml`:
```yaml
name: Test Failover System

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      kafka:
        image: apache/kafka:latest
        ports:
          - 9092:9092
      
      dynamodb:
        image: amazon/dynamodb-local
        ports:
          - 8000:8000
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r kafka_consumer_lambda/requirements.txt
          pip install pytest pytest-cov pytest-mock
      
      - name: Run unit tests
        run: |
          cd kafka_consumer_lambda
          python -m pytest tests/ -v --cov
      
      - name: Run integration tests
        run: |
          ./scripts/integration-test.sh
```

## Test Data Management

### Sample Test Events

Create `test-data/failover-events.json`:
```json
{
  "single_app_failover": {
    "event_type": "failover",
    "timestamp": "2024-01-15T10:30:00Z",
    "applications": [{
      "app_id": "app1",
      "failover_status": "Y",
      "reason": "Test failover"
    }],
    "triggered_by": "test",
    "severity": "info"
  },
  "multi_app_failover": {
    "event_type": "failover",
    "timestamp": "2024-01-15T10:30:00Z",
    "applications": [
      {"app_id": "app1", "failover_status": "Y", "reason": "Test"},
      {"app_id": "app2", "failover_status": "Y", "reason": "Test"}
    ],
    "triggered_by": "test",
    "severity": "critical"
  }
}
```

## Best Practices

1. **Test in isolation first** - Unit tests before integration
2. **Use test data** - Don't test with production data
3. **Clean up after tests** - Reset state between tests
4. **Monitor during tests** - Watch logs and metrics
5. **Automate regression tests** - Run on every commit
6. **Test failure scenarios** - Network issues, timeouts, etc.
7. **Measure performance** - Track latency over time
8. **Document test results** - Keep a test log

## Summary

The best testing approach follows this sequence:

1. **Unit Tests** (5 min) - Test individual components
2. **Integration Tests** (10 min) - Test component pairs
3. **E2E Test** (5 min) - Test complete flow
4. **Performance Test** (10 min) - Test under load
5. **UI Test** (5 min) - Test application integration

**Total testing time: ~35 minutes for comprehensive validation**

For quick validation, run the E2E test script which covers the critical path in about 5 minutes.
