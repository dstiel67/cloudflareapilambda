# Quick Testing Guide

## TL;DR - Fastest Way to Test

```bash
# 1. Start local test environment
docker-compose -f docker-compose.test.yml up -d

# 2. Wait for services to be ready (30 seconds)
sleep 30

# 3. Run quick test
./scripts/quick-test.sh

# 4. Done! ✅
```

## What Gets Tested

The quick test validates:
- ✅ DynamoDB connectivity
- ✅ Lambda function deployment
- ✅ DynamoDB → Read Flags Service flow
- ✅ Read Flags Service → Atom Store flow
- ✅ End-to-end data propagation

## Test Levels

### 1. Quick Test (5 minutes)
```bash
./scripts/quick-test.sh
```
Tests the core flow without Kafka.

### 2. Integration Test (10 minutes)
```bash
# Send test event to Kafka
python scripts/send-test-kafka-event.py

# Verify it flows through the system
aws dynamodb get-item \
  --table-name failover-status \
  --key '{"pk": {"S": "FAILOVER_STATUS"}, "sk": {"S": "CURRENT"}}'
```

### 3. End-to-End Test (15 minutes)
```bash
# Full flow: Ansible → Kafka → Lambda → DynamoDB → Atom Store
ansible-playbook ansible-example/trigger-failover.yml

# Wait and verify
sleep 20
curl http://localhost:3000/api/failover/status
```

### 4. Load Test (20 minutes)
```bash
# Install dependencies
pip install kafka-python

# Run load test
python scripts/load-test.py
```

## Testing Without AWS

Use local services:

```bash
# Start local DynamoDB
docker run -p 8000:8000 amazon/dynamodb-local

# Configure AWS CLI for local
export AWS_ENDPOINT_URL=http://localhost:8000
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test

# Create test table
aws dynamodb create-table \
  --table-name failover-status \
  --attribute-definitions \
    AttributeName=pk,AttributeType=S \
    AttributeName=sk,AttributeType=S \
  --key-schema \
    AttributeName=pk,KeyType=HASH \
    AttributeName=sk,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST
```

## Common Test Scenarios

### Test Failover Activation
```bash
aws dynamodb put-item \
  --table-name failover-status \
  --item '{
    "pk": {"S": "FAILOVER_STATUS"},
    "sk": {"S": "CURRENT"},
    "app1_Failover": {"S": "Y"},
    "app1_LastUpdated": {"S": "2024-01-15T10:30:00Z"},
    "app1_Reason": {"S": "Test"}
  }'
```

### Test Failover Deactivation
```bash
aws dynamodb put-item \
  --table-name failover-status \
  --item '{
    "pk": {"S": "FAILOVER_STATUS"},
    "sk": {"S": "CURRENT"},
    "app1_Failover": {"S": "N"},
    "app1_LastUpdated": {"S": "2024-01-15T11:00:00Z"},
    "app1_Reason": {"S": "Restored"}
  }'
```

### Test Multiple Apps
```bash
aws dynamodb put-item \
  --table-name failover-status \
  --item '{
    "pk": {"S": "FAILOVER_STATUS"},
    "sk": {"S": "CURRENT"},
    "app1_Failover": {"S": "Y"},
    "app2_Failover": {"S": "Y"},
    "app3_Failover": {"S": "N"}
  }'
```

## Monitoring Tests

### Watch Logs
```bash
# Atom Store
docker logs -f atom-store-test

# Read Flags Service
docker logs -f read-flags-service-test

# Kafka
docker logs -f kafka-test
```

### Check Metrics
```bash
# Atom Store health
curl http://localhost:3000/health

# Current failover status
curl http://localhost:3000/api/failover/status | jq

# Kafka topics
docker exec kafka-test kafka-topics.sh --list --bootstrap-server localhost:9092
```

## Troubleshooting

### Services Not Starting
```bash
# Check service status
docker-compose -f docker-compose.test.yml ps

# View logs
docker-compose -f docker-compose.test.yml logs

# Restart services
docker-compose -f docker-compose.test.yml restart
```

### DynamoDB Connection Issues
```bash
# Test local DynamoDB
aws dynamodb list-tables --endpoint-url http://localhost:8000

# Create table if missing
aws dynamodb create-table \
  --table-name failover-status \
  --endpoint-url http://localhost:8000 \
  ...
```

### Atom Store Not Updating
```bash
# Check Read Flags Service logs
docker logs read-flags-service-test

# Test Atom Store API directly
curl -X POST http://localhost:3000/api/failover/update \
  -H "Content-Type: application/json" \
  -d '{"test": {"appId": "test", "failoverActive": true}}'
```

## Cleanup

```bash
# Stop all test services
docker-compose -f docker-compose.test.yml down

# Remove volumes
docker-compose -f docker-compose.test.yml down -v

# Remove test data from AWS
aws dynamodb delete-item \
  --table-name failover-status \
  --key '{"pk": {"S": "FAILOVER_STATUS"}, "sk": {"S": "CURRENT"}}'
```

## CI/CD Integration

Add to your CI pipeline:

```yaml
# .github/workflows/test.yml
- name: Run tests
  run: |
    docker-compose -f docker-compose.test.yml up -d
    sleep 30
    ./scripts/quick-test.sh
    docker-compose -f docker-compose.test.yml down
```

## Next Steps

After testing locally:
1. Deploy to AWS: `terraform apply`
2. Run production tests
3. Monitor CloudWatch metrics
4. Set up alerts

For detailed testing information, see [TESTING_GUIDE.md](TESTING_GUIDE.md).
