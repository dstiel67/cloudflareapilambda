# Testing Summary - Best Way to Test This Solution

## Quick Answer

**The best way to test is the 3-tier approach:**

1. **Quick Test (5 min)** - Validates core functionality
2. **Integration Test (10 min)** - Tests component interactions  
3. **End-to-End Test (15 min)** - Tests complete flow

## Fastest Path to Validation

### With Docker
```bash
# 1. Start local test environment
docker-compose -f docker-compose.test.yml up -d

# 2. Wait for services (30 seconds)
sleep 30

# 3. Run quick test
./scripts/quick-test.sh

# ✅ Done! System validated in ~5 minutes
```

### Without Docker (AWS-Only)
```bash
# 1. Deploy to AWS
terraform apply

# 2. Run AWS-only test
./scripts/aws-only-test.sh

# ✅ Done! System validated in ~5 minutes
```

## What Each Test Level Covers

### Level 1: Quick Test (5 minutes)
**Purpose:** Validate core components work

**What it tests:**
- ✅ AWS connectivity
- ✅ DynamoDB read/write
- ✅ Lambda deployment
- ✅ Atom Store API
- ✅ Data flow (DynamoDB → Atom Store)

**Run it:**
```bash
./scripts/quick-test.sh
```

**When to use:** After deployment, before committing code

---

### Level 2: Integration Test (10 minutes)
**Purpose:** Test component pairs

**What it tests:**
- ✅ Kafka → Lambda integration
- ✅ Lambda → DynamoDB integration
- ✅ DynamoDB → Read Flags Service
- ✅ Read Flags Service → Atom Store
- ✅ WebSocket connections

**Run it:**
```bash
# Send test Kafka event
python scripts/send-test-kafka-event.py

# Verify DynamoDB update
aws dynamodb get-item \
  --table-name failover-status \
  --key '{"pk": {"S": "FAILOVER_STATUS"}, "sk": {"S": "CURRENT"}}'

# Check Atom Store
curl http://localhost:3000/api/failover/status
```

**When to use:** Before production deployment, after infrastructure changes

---

### Level 3: End-to-End Test (15 minutes)
**Purpose:** Test complete user flow

**What it tests:**
- ✅ Ansible → Kafka → Lambda → DynamoDB → Read Flags → Atom Store → UI
- ✅ Failover activation
- ✅ Failover deactivation
- ✅ Multiple applications
- ✅ Real-time updates
- ✅ UI banner display

**Run it:**
```bash
# Trigger failover via Ansible
ansible-playbook ansible-example/trigger-failover.yml

# Wait for propagation
sleep 20

# Verify in Atom Store
curl http://localhost:3000/api/failover/status

# Check UI (open browser)
open http://localhost:4200
```

**When to use:** Before production release, for demos

---

## Testing Without Docker

**Don't have Docker? No problem!** You have several options:

### Option 1: AWS-Only Testing (Recommended)
```bash
# Test using only AWS services
./scripts/aws-only-test.sh
```

### Option 2: Native Services
```bash
# Run services directly with Python/Node.js
./scripts/native-services-test.sh

# Or use tmux to run all services
./scripts/start-native-services-tmux.sh
```

### Option 3: Manual Testing
```bash
# Terminal 1: Start Atom Store
cd atom_store/server && npm start

# Terminal 2: Start Read Flags Service
cd read_flags_service && python service.py

# Terminal 3: Test
aws dynamodb put-item --table-name failover-status ...
```

See [TESTING_WITHOUT_DOCKER.md](TESTING_WITHOUT_DOCKER.md) for complete guide.

## Testing Without AWS (Local Development)

Use the Docker Compose test environment:

```bash
# Start all services locally
docker-compose -f docker-compose.test.yml up -d

# Services included:
# - Kafka (localhost:9092)
# - DynamoDB Local (localhost:8000)
# - Atom Store (localhost:3000)
# - Read Flags Service
# - Kafka UI (localhost:8080)

# Run tests against local services
export AWS_ENDPOINT_URL=http://localhost:8000
./scripts/quick-test.sh
```

## Performance Testing

Test system under load:

```bash
# Install dependencies
pip install kafka-python

# Run load test (100 events)
python scripts/load-test.py

# Results show:
# - Average latency
# - Throughput
# - Error rate
```

## Continuous Testing

Add to your CI/CD pipeline:

```yaml
# GitHub Actions example
- name: Test Failover System
  run: |
    docker-compose -f docker-compose.test.yml up -d
    sleep 30
    ./scripts/quick-test.sh
```

## Test Files Created

```
scripts/
├── quick-test.sh                    # 5-minute validation (Docker)
├── aws-only-test.sh                 # 5-minute validation (No Docker)
├── native-services-test.sh          # Setup native services
├── start-native-services-tmux.sh    # Start services in tmux
├── send-test-kafka-event.py         # Kafka integration test
└── load-test.py                     # Performance testing

test-data/
└── sample-events.json               # Test event templates

docker-compose.test.yml              # Local test environment (Docker)
TESTING_GUIDE.md                     # Comprehensive guide
TESTING_WITHOUT_DOCKER.md            # No Docker guide
README_TESTING.md                    # Quick reference
TESTING_WORKFLOW.md                  # Visual workflows
```

## Monitoring During Tests

### Watch Logs
```bash
# All services
docker-compose -f docker-compose.test.yml logs -f

# Specific service
docker logs -f atom-store-test
```

### Check Health
```bash
# Atom Store
curl http://localhost:3000/health

# Kafka UI
open http://localhost:8080
```

### View Metrics
```bash
# CloudWatch (AWS)
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=failover-system-kafka-consumer \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum
```

## Common Test Scenarios

### Scenario 1: Single App Failover
```bash
# Activate
aws dynamodb put-item --table-name failover-status --item '{
  "pk": {"S": "FAILOVER_STATUS"},
  "sk": {"S": "CURRENT"},
  "app1_Failover": {"S": "Y"}
}'

# Verify
curl http://localhost:3000/api/failover/status | jq '.app1'
```

### Scenario 2: Multiple Apps
```bash
# Activate multiple
aws dynamodb put-item --table-name failover-status --item '{
  "pk": {"S": "FAILOVER_STATUS"},
  "sk": {"S": "CURRENT"},
  "app1_Failover": {"S": "Y"},
  "app2_Failover": {"S": "Y"},
  "app3_Failover": {"S": "N"}
}'
```

### Scenario 3: Rapid Changes
```bash
# Test rapid failover toggles
for i in {1..10}; do
  STATUS=$( [ $((i % 2)) -eq 0 ] && echo "Y" || echo "N" )
  aws dynamodb put-item --table-name failover-status --item "{
    \"pk\": {\"S\": \"FAILOVER_STATUS\"},
    \"sk\": {\"S\": \"CURRENT\"},
    \"test_Failover\": {\"S\": \"$STATUS\"}
  }"
  sleep 2
done
```

## Troubleshooting Tests

### Test Fails: "Cannot connect to DynamoDB"
```bash
# Check DynamoDB is running
docker ps | grep dynamodb

# Test connection
aws dynamodb list-tables --endpoint-url http://localhost:8000

# Restart if needed
docker-compose -f docker-compose.test.yml restart dynamodb-local
```

### Test Fails: "Atom Store not responding"
```bash
# Check Atom Store logs
docker logs atom-store-test

# Test health endpoint
curl http://localhost:3000/health

# Restart if needed
docker-compose -f docker-compose.test.yml restart atom-store
```

### Test Fails: "Kafka connection refused"
```bash
# Check Kafka is running
docker ps | grep kafka

# List topics
docker exec kafka-test kafka-topics.sh --list --bootstrap-server localhost:9092

# Restart if needed
docker-compose -f docker-compose.test.yml restart kafka
```

## Best Practices

1. **Test locally first** - Use Docker Compose before AWS
2. **Run quick test often** - After every code change
3. **Run integration tests** - Before committing
4. **Run E2E tests** - Before deploying to production
5. **Monitor during tests** - Watch logs and metrics
6. **Clean up after tests** - Remove test data
7. **Automate in CI/CD** - Run tests on every PR

## Test Coverage

| Component | Unit Tests | Integration Tests | E2E Tests |
|-----------|-----------|-------------------|-----------|
| Kafka Consumer Lambda | ✅ | ✅ | ✅ |
| Read Flags Service | ✅ | ✅ | ✅ |
| Atom Store Server | ✅ | ✅ | ✅ |
| DynamoDB | N/A | ✅ | ✅ |
| Kafka | N/A | ✅ | ✅ |
| UI Integration | ✅ | ✅ | ✅ |

## Time Investment

- **Initial setup:** 10 minutes (one-time)
- **Quick test:** 5 minutes (run frequently)
- **Integration test:** 10 minutes (before commits)
- **E2E test:** 15 minutes (before releases)
- **Load test:** 20 minutes (periodic)

**Total for comprehensive testing: ~60 minutes**

## Recommended Testing Schedule

### Daily (Developers)
- Quick test after code changes
- Unit tests before commits

### Weekly (Team)
- Integration tests
- E2E tests
- Review test results

### Before Release
- Full test suite
- Load testing
- Performance validation
- Security testing

## Next Steps

1. **Read:** [TESTING_GUIDE.md](TESTING_GUIDE.md) for detailed instructions
2. **Quick start:** Run `./scripts/quick-test.sh`
3. **Local testing:** Use `docker-compose.test.yml`
4. **Production testing:** Deploy and run E2E tests
5. **Automate:** Add tests to CI/CD pipeline

## Summary

**The best way to test this solution is:**

1. Start with the **quick test** (`./scripts/quick-test.sh`) - validates core functionality in 5 minutes
2. Run **integration tests** for component interactions - 10 minutes
3. Execute **E2E tests** for complete flow validation - 15 minutes
4. Use **Docker Compose** for local testing without AWS
5. Automate tests in your **CI/CD pipeline**

This approach gives you confidence in the system with minimal time investment.
