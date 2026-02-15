# Testing Workflow - Visual Guide

## Testing Decision Tree

```
┌─────────────────────────────────────────────────────────────┐
│  What do you want to test?                                  │
└─────────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
        ▼                 ▼                 ▼
┌───────────────┐  ┌──────────────┐  ┌──────────────┐
│ Just changed  │  │ Before       │  │ Production   │
│ code?         │  │ deployment?  │  │ validation?  │
└───────────────┘  └──────────────┘  └──────────────┘
        │                 │                 │
        ▼                 ▼                 ▼
┌───────────────┐  ┌──────────────┐  ┌──────────────┐
│ Quick Test    │  │ Integration  │  │ E2E Test     │
│ (5 min)       │  │ Test (10min) │  │ (15 min)     │
└───────────────┘  └──────────────┘  └──────────────┘
```

## Quick Test Workflow (5 minutes)

```
┌──────────────────────────────────────────────────────────────┐
│                    Quick Test Flow                           │
└──────────────────────────────────────────────────────────────┘

Step 1: Check Prerequisites
├─ AWS CLI installed? ────────────────────────────────► ✅ or ❌
├─ Atom Store running? ───────────────────────────────► ✅ or ❌
└─ DynamoDB accessible? ──────────────────────────────► ✅ or ❌

Step 2: Write Test Data to DynamoDB
├─ Create test failover record ──────────────────────► ✅
└─ Verify write successful ──────────────────────────► ✅

Step 3: Wait for Propagation
└─ Sleep 15 seconds (polling interval) ──────────────► ⏳

Step 4: Verify Atom Store
├─ Check Atom Store API ─────────────────────────────► ✅ or ❌
└─ Verify failover status ───────────────────────────► ✅ or ❌

Step 5: Cleanup
└─ Remove test data ─────────────────────────────────► ✅

Result: System validated! 🎉
```

## Integration Test Workflow (10 minutes)

```
┌──────────────────────────────────────────────────────────────┐
│                 Integration Test Flow                        │
└──────────────────────────────────────────────────────────────┘

Step 1: Start Local Services
├─ docker-compose up -d ─────────────────────────────► 🐳
├─ Kafka (localhost:9092) ───────────────────────────► ✅
├─ DynamoDB Local (localhost:8000) ──────────────────► ✅
├─ Atom Store (localhost:3000) ──────────────────────► ✅
└─ Read Flags Service ───────────────────────────────► ✅

Step 2: Send Test Event to Kafka
└─ python scripts/send-test-kafka-event.py ──────────► 📨

Step 3: Verify Lambda Processing
├─ Check Lambda logs ────────────────────────────────► 📋
└─ Verify no errors ─────────────────────────────────► ✅

Step 4: Verify DynamoDB Update
├─ Query DynamoDB ───────────────────────────────────► 🔍
└─ Confirm test data exists ─────────────────────────► ✅

Step 5: Verify Read Flags Service
├─ Check service logs ───────────────────────────────► 📋
└─ Confirm polling detected change ──────────────────► ✅

Step 6: Verify Atom Store
├─ Query Atom Store API ─────────────────────────────► 🔍
└─ Confirm failover status updated ──────────────────► ✅

Result: Integration validated! 🎉
```

## End-to-End Test Workflow (15 minutes)

```
┌──────────────────────────────────────────────────────────────┐
│                    E2E Test Flow                             │
└──────────────────────────────────────────────────────────────┘

Step 1: Trigger Failover via Ansible
└─ ansible-playbook trigger-failover.yml ────────────► 🎭

Step 2: Verify Kafka Message
├─ Check Kafka topic ────────────────────────────────► 📨
└─ Confirm event published ──────────────────────────► ✅

Step 3: Verify Lambda Execution
├─ Check CloudWatch logs ────────────────────────────► 📋
├─ Confirm Lambda invoked ───────────────────────────► ✅
└─ Verify no errors ─────────────────────────────────► ✅

Step 4: Verify DynamoDB Update
├─ Query DynamoDB table ─────────────────────────────► 🔍
├─ Confirm failover flags updated ───────────────────► ✅
└─ Check timestamps ─────────────────────────────────► ✅

Step 5: Wait for Read Flags Service
└─ Sleep 15-20 seconds ──────────────────────────────► ⏳

Step 6: Verify Atom Store Update
├─ Query Atom Store API ─────────────────────────────► 🔍
├─ Confirm status updated ───────────────────────────► ✅
└─ Check WebSocket broadcast ────────────────────────► ✅

Step 7: Verify UI Update
├─ Open application in browser ──────────────────────► 🌐
├─ Confirm failover banner appears ──────────────────► ✅
└─ Check browser console for atom updates ───────────► ✅

Step 8: Clear Failover
└─ ansible-playbook (status=N) ──────────────────────► 🎭

Step 9: Verify Clearance
├─ Wait for propagation ─────────────────────────────► ⏳
├─ Confirm banner disappears ────────────────────────► ✅
└─ Verify atom state cleared ────────────────────────► ✅

Result: Complete flow validated! 🎉
```

## Local Testing Setup

```
┌──────────────────────────────────────────────────────────────┐
│              Local Test Environment Setup                    │
└──────────────────────────────────────────────────────────────┘

1. Start Docker Compose
   $ docker-compose -f docker-compose.test.yml up -d
   
   Services Started:
   ├─ Kafka ──────────────────────────► localhost:9092
   ├─ DynamoDB Local ─────────────────► localhost:8000
   ├─ Atom Store ─────────────────────► localhost:3000
   ├─ Read Flags Service ─────────────► (internal)
   └─ Kafka UI (optional) ────────────► localhost:8080

2. Wait for Services
   $ sleep 30
   
   Health Checks:
   ├─ Kafka ready ────────────────────► ✅
   ├─ DynamoDB ready ─────────────────► ✅
   ├─ Atom Store ready ───────────────► ✅
   └─ Read Flags Service ready ───────► ✅

3. Run Tests
   $ ./scripts/quick-test.sh
   
   Result: Local environment validated! 🎉
```

## Test Data Flow Visualization

```
┌──────────────────────────────────────────────────────────────┐
│                  Data Flow During Testing                    │
└──────────────────────────────────────────────────────────────┘

Test Event Creation
        │
        ▼
┌───────────────┐
│    Ansible    │ Creates failover event
│   Playbook    │
└───────┬───────┘
        │ JSON event
        ▼
┌───────────────┐
│     Kafka     │ Stores event in topic
│     Topic     │
└───────┬───────┘
        │ Kafka record
        ▼
┌───────────────┐
│    Lambda     │ Processes event
│   Consumer    │
└───────┬───────┘
        │ DynamoDB item
        ▼
┌───────────────┐
│   DynamoDB    │ Stores failover flags
│     Table     │
└───────┬───────┘
        │ Polling (every 5-30s)
        ▼
┌───────────────┐
│ Read Flags    │ Detects changes
│   Service     │
└───────┬───────┘
        │ HTTP POST
        ▼
┌───────────────┐
│  Atom Store   │ Updates atoms
│    Server     │
└───────┬───────┘
        │ WebSocket broadcast
        ▼
┌───────────────┐
│ Application   │ Shows failover banner
│      UI       │
└───────────────┘

Test Verification Points:
├─ ✅ Kafka: Event published
├─ ✅ Lambda: Logs show processing
├─ ✅ DynamoDB: Item exists with correct data
├─ ✅ Read Flags: Logs show change detected
├─ ✅ Atom Store: API returns updated status
└─ ✅ UI: Banner visible in browser
```

## Performance Testing Flow

```
┌──────────────────────────────────────────────────────────────┐
│                   Performance Test Flow                      │
└──────────────────────────────────────────────────────────────┘

1. Prepare Load Test
   ├─ Install kafka-python ──────────────────────────► pip install
   └─ Configure test parameters ─────────────────────► 100 events

2. Execute Load Test
   $ python scripts/load-test.py
   
   Progress:
   ├─ Sending events... ─────────────────────────────► [##########] 100%
   └─ Measuring latency ─────────────────────────────► ⏱️

3. Collect Metrics
   ├─ Average latency ───────────────────────────────► 45ms
   ├─ Median latency ────────────────────────────────► 42ms
   ├─ Min latency ───────────────────────────────────► 28ms
   ├─ Max latency ───────────────────────────────────► 89ms
   └─ Std deviation ─────────────────────────────────► 12ms

4. Verify System Health
   ├─ Check Lambda errors ───────────────────────────► 0 errors
   ├─ Check DynamoDB throttles ──────────────────────► 0 throttles
   └─ Check Atom Store connections ──────────────────► All healthy

Result: Performance validated! 🎉
```

## Continuous Testing Pipeline

```
┌──────────────────────────────────────────────────────────────┐
│                    CI/CD Test Pipeline                       │
└──────────────────────────────────────────────────────────────┘

On Pull Request:
├─ 1. Lint Code ──────────────────────────────────► ✅
├─ 2. Unit Tests ─────────────────────────────────► ✅
├─ 3. Build Lambda Packages ──────────────────────► ✅
└─ 4. Quick Test (Docker Compose) ────────────────► ✅

On Merge to Main:
├─ 1. All PR checks ──────────────────────────────► ✅
├─ 2. Integration Tests ──────────────────────────► ✅
├─ 3. Deploy to Staging ──────────────────────────► 🚀
└─ 4. E2E Tests (Staging) ────────────────────────► ✅

On Release Tag:
├─ 1. All previous checks ────────────────────────► ✅
├─ 2. Performance Tests ──────────────────────────► ✅
├─ 3. Security Scan ──────────────────────────────► ✅
├─ 4. Deploy to Production ───────────────────────► 🚀
└─ 5. Smoke Tests (Production) ───────────────────► ✅
```

## Test Failure Recovery

```
┌──────────────────────────────────────────────────────────────┐
│                  When Tests Fail                             │
└──────────────────────────────────────────────────────────────┘

Test Failed
    │
    ▼
Check Logs
    ├─ Lambda logs ───────────────────────────────► CloudWatch
    ├─ Service logs ──────────────────────────────► Docker logs
    └─ Application logs ──────────────────────────► Browser console
    │
    ▼
Identify Issue
    ├─ Connection error? ─────────────────────────► Check network
    ├─ Permission error? ─────────────────────────► Check IAM
    ├─ Data error? ───────────────────────────────► Check format
    └─ Timeout error? ────────────────────────────► Check latency
    │
    ▼
Fix Issue
    ├─ Update code ───────────────────────────────► Commit fix
    ├─ Update config ─────────────────────────────► Apply changes
    └─ Restart services ──────────────────────────► docker-compose restart
    │
    ▼
Re-run Test
    └─ ./scripts/quick-test.sh ───────────────────► ✅ or ❌
```

## Summary

**Choose your testing path:**

```
Quick validation?     → ./scripts/quick-test.sh (5 min)
Before deployment?    → Integration tests (10 min)
Production ready?     → E2E tests (15 min)
Performance check?    → Load tests (20 min)
Local development?    → docker-compose.test.yml
```

**All tests documented in:**
- [TESTING_GUIDE.md](TESTING_GUIDE.md) - Comprehensive guide
- [README_TESTING.md](README_TESTING.md) - Quick reference
- [TESTING_SUMMARY.md](TESTING_SUMMARY.md) - Best practices
