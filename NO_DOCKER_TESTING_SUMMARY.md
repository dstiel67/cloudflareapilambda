# Testing Without Docker - Summary

## Yes! You Can Test Without Docker

You have **3 excellent options** for testing without Docker:

## Option 1: AWS-Only Testing ⭐ Recommended

**What it does:** Tests using only AWS services (no local setup)

**How to run:**
```bash
# 1. Deploy to AWS
terraform apply

# 2. Run test
./scripts/aws-only-test.sh
```

**Time:** 5 minutes

**What it tests:**
- ✅ DynamoDB read/write
- ✅ Lambda function invocation
- ✅ CloudWatch logs
- ✅ Complete AWS infrastructure

**Pros:**
- No local setup required
- Tests production environment
- Most realistic testing
- Automated script

**Cons:**
- Requires AWS account
- Small AWS costs (~$0.01)

---

## Option 2: Native Services

**What it does:** Runs services directly with Python and Node.js

**How to run:**
```bash
# Setup (one-time)
./scripts/native-services-test.sh

# Start services (choose one):

# A. Manual (3 terminals)
# Terminal 1
cd atom_store/server && npm start

# Terminal 2
cd read_flags_service && python service.py

# Terminal 3
aws dynamodb put-item ...

# B. Automatic (tmux)
./scripts/start-native-services-tmux.sh
```

**Time:** 15 minutes

**What it tests:**
- ✅ Atom Store API
- ✅ Read Flags Service
- ✅ DynamoDB integration
- ✅ Service communication

**Pros:**
- Full control over services
- Can debug easily
- No Docker needed
- Free (uses AWS DynamoDB)

**Cons:**
- Requires Python 3.11+ and Node.js 20+
- Multiple terminals needed (unless using tmux)
- Manual setup

---

## Option 3: Component Testing

**What it does:** Tests individual components separately

**How to run:**
```bash
# Test DynamoDB
aws dynamodb put-item --table-name failover-status --item '{
  "pk": {"S": "FAILOVER_STATUS"},
  "sk": {"S": "CURRENT"},
  "test_Failover": {"S": "Y"}
}'

# Test Lambda
aws lambda invoke \
  --function-name failover-system-kafka-consumer \
  --payload file://test-event.json \
  response.json

# Test Atom Store (if running)
curl http://localhost:3000/api/failover/status
```

**Time:** 5 minutes per component

**What it tests:**
- ✅ Individual components
- ✅ AWS services
- ✅ Basic functionality

**Pros:**
- Very fast
- Simple commands
- No setup needed
- Good for debugging

**Cons:**
- Doesn't test integration
- Manual verification
- Limited scope

---

## Comparison Table

| Feature | AWS-Only | Native Services | Component |
|---------|----------|-----------------|-----------|
| **Setup Time** | 0 min | 5 min | 0 min |
| **Test Time** | 5 min | 15 min | 5 min |
| **Docker Required** | ❌ No | ❌ No | ❌ No |
| **AWS Required** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Local Services** | ❌ No | ✅ Yes | ❌ No |
| **Tests Integration** | ✅ Yes | ✅ Yes | ❌ No |
| **Automated** | ✅ Yes | ⚠️ Partial | ❌ No |
| **Best For** | Quick validation | Development | Debugging |

---

## Recommended Approach

### For Quick Validation
```bash
./scripts/aws-only-test.sh
```
**Why:** Fastest, automated, tests real AWS infrastructure

### For Development
```bash
./scripts/start-native-services-tmux.sh
```
**Why:** Full control, can debug, see logs in real-time

### For Debugging Issues
```bash
# Test components individually
aws dynamodb scan --table-name failover-status
aws lambda invoke --function-name ...
curl http://localhost:3000/health
```
**Why:** Isolate problems, quick feedback

---

## Prerequisites

### All Options Need:
- ✅ AWS CLI configured
- ✅ AWS account with permissions
- ✅ Terraform (for deployment)

### Native Services Also Need:
- ✅ Python 3.11+
- ✅ Node.js 20+
- ✅ npm

### Optional (Makes Life Easier):
- ⭐ tmux (for running multiple services)
- ⭐ jq (for JSON parsing)
- ⭐ watch (for monitoring)

---

## Installation Commands

### Install Python Dependencies
```bash
cd read_flags_service
pip install -r requirements.txt
```

### Install Node.js Dependencies
```bash
cd atom_store/server
npm install
```

### Install Optional Tools
```bash
# macOS
brew install tmux jq watch

# Ubuntu/Debian
sudo apt install tmux jq watch

# Windows (Git Bash)
# tmux not available, use separate terminals
```

---

## Step-by-Step: AWS-Only Testing

```bash
# 1. Deploy infrastructure
terraform init
terraform apply

# 2. Run test script
chmod +x scripts/aws-only-test.sh
./scripts/aws-only-test.sh

# 3. Review results
# Script will show:
# ✅ DynamoDB access
# ✅ Write operations
# ✅ Read operations
# ✅ Lambda invocation
# ✅ CloudWatch logs

# Done! 🎉
```

---

## Step-by-Step: Native Services

```bash
# 1. Setup (one-time)
./scripts/native-services-test.sh

# 2. Start services
./scripts/start-native-services-tmux.sh

# 3. Test (in tmux window 3)
aws dynamodb put-item \
  --table-name failover-status \
  --item '{
    "pk": {"S": "FAILOVER_STATUS"},
    "sk": {"S": "CURRENT"},
    "test_Failover": {"S": "Y"}
  }'

# 4. Verify
curl http://localhost:3000/api/failover/status | jq

# 5. Stop services
tmux kill-session -t failover-test

# Done! 🎉
```

---

## Troubleshooting

### "AWS CLI not found"
```bash
# Install AWS CLI
# macOS
brew install awscli

# Ubuntu/Debian
sudo apt install awscli

# Windows
# Download from: https://aws.amazon.com/cli/
```

### "Cannot access DynamoDB table"
```bash
# Check if table exists
aws dynamodb list-tables

# Check AWS credentials
aws sts get-caller-identity

# Check region
aws configure get region
```

### "Node.js not found"
```bash
# Install Node.js 20+
# macOS
brew install node@20

# Ubuntu/Debian
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install nodejs

# Windows
# Download from: https://nodejs.org/
```

### "Python not found"
```bash
# Install Python 3.11+
# macOS
brew install python@3.11

# Ubuntu/Debian
sudo apt install python3.11

# Windows
# Download from: https://www.python.org/
```

---

## What Each Test Script Does

### `aws-only-test.sh`
1. Checks AWS CLI is installed
2. Gets DynamoDB table name
3. Writes test data to DynamoDB
4. Reads test data back
5. Invokes Lambda function (if deployed)
6. Checks CloudWatch logs
7. Cleans up test data
8. Shows summary

### `native-services-test.sh`
1. Checks Python and Node.js installed
2. Installs Atom Store dependencies
3. Installs Read Flags Service dependencies
4. Shows instructions for starting services
5. Provides test commands

### `start-native-services-tmux.sh`
1. Creates tmux session
2. Starts Atom Store in window 1
3. Starts Read Flags Service in window 2
4. Opens test terminal in window 3
5. Attaches to session

---

## Documentation

- **Complete guide:** [TESTING_WITHOUT_DOCKER.md](TESTING_WITHOUT_DOCKER.md)
- **Quick reference:** [TESTING_QUICK_REFERENCE.md](TESTING_QUICK_REFERENCE.md)
- **Full testing guide:** [TESTING_GUIDE.md](TESTING_GUIDE.md)
- **Summary:** [TESTING_SUMMARY.md](TESTING_SUMMARY.md)

---

## Summary

**You absolutely can test without Docker!**

- ⭐ **Easiest:** `./scripts/aws-only-test.sh` (5 minutes)
- 🔧 **Most control:** `./scripts/start-native-services-tmux.sh` (15 minutes)
- 🐛 **For debugging:** Test components individually (5 minutes)

All methods are fully documented and ready to use.
