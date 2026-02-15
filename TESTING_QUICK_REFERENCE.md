# Testing Quick Reference Card

## I Have Docker

```bash
# Quick test (5 min)
docker-compose -f docker-compose.test.yml up -d
sleep 30
./scripts/quick-test.sh
```

## I Don't Have Docker

```bash
# AWS-only test (5 min)
terraform apply
./scripts/aws-only-test.sh
```

## I Want to Test Locally Without AWS

```bash
# Native services (15 min)
# Terminal 1
cd atom_store/server && npm start

# Terminal 2
cd read_flags_service
export DYNAMODB_TABLE_NAME=failover-status
export ATOM_STORE_URL=http://localhost:3000
python service.py

# Terminal 3
aws dynamodb put-item --table-name failover-status --item '...'
```

## I Want the Simplest Test

```bash
# Just test DynamoDB (2 min)
aws dynamodb put-item --table-name failover-status --item '{
  "pk": {"S": "FAILOVER_STATUS"},
  "sk": {"S": "CURRENT"},
  "test_Failover": {"S": "Y"}
}'

aws dynamodb get-item \
  --table-name failover-status \
  --key '{"pk": {"S": "FAILOVER_STATUS"}, "sk": {"S": "CURRENT"}}'
```

## I Want to Test Everything

```bash
# End-to-end test (15 min)
# 1. Deploy
terraform apply

# 2. Start services
docker-compose -f docker-compose.test.yml up -d
# OR
./scripts/start-native-services-tmux.sh

# 3. Trigger failover
ansible-playbook ansible-example/trigger-failover.yml

# 4. Verify
curl http://localhost:3000/api/failover/status
```

## Common Test Commands

### Check DynamoDB
```bash
aws dynamodb scan --table-name failover-status --limit 5
```

### Check Lambda Logs
```bash
aws logs tail /aws/lambda/failover-system-kafka-consumer --follow
```

### Check Atom Store
```bash
curl http://localhost:3000/health
curl http://localhost:3000/api/failover/status | jq
```

### Trigger Failover
```bash
# Via DynamoDB
aws dynamodb put-item --table-name failover-status --item '{
  "pk": {"S": "FAILOVER_STATUS"},
  "sk": {"S": "CURRENT"},
  "app1_Failover": {"S": "Y"}
}'

# Via Ansible
ansible-playbook ansible-example/trigger-failover.yml
```

### Clear Failover
```bash
aws dynamodb put-item --table-name failover-status --item '{
  "pk": {"S": "FAILOVER_STATUS"},
  "sk": {"S": "CURRENT"},
  "app1_Failover": {"S": "N"}
}'
```

## Troubleshooting

### Services not starting?
```bash
# Docker
docker-compose -f docker-compose.test.yml logs

# Native
# Check if ports are in use
lsof -i :3000  # Atom Store
lsof -i :9092  # Kafka
lsof -i :8000  # DynamoDB
```

### Can't connect to AWS?
```bash
# Check credentials
aws sts get-caller-identity

# Check region
aws configure get region
```

### Atom Store not updating?
```bash
# Check Read Flags Service logs
docker logs read-flags-service-test
# OR
# Check terminal where service is running

# Test Atom Store directly
curl -X POST http://localhost:3000/api/failover/update \
  -H "Content-Type: application/json" \
  -d '{"test": {"appId": "test", "failoverActive": true}}'
```

## Documentation

- **Full guide:** [TESTING_GUIDE.md](TESTING_GUIDE.md)
- **No Docker:** [TESTING_WITHOUT_DOCKER.md](TESTING_WITHOUT_DOCKER.md)
- **Summary:** [TESTING_SUMMARY.md](TESTING_SUMMARY.md)
- **Workflows:** [TESTING_WORKFLOW.md](TESTING_WORKFLOW.md)

## Test Scripts

| Script | Purpose | Time | Requires |
|--------|---------|------|----------|
| `quick-test.sh` | Quick validation | 5 min | Docker, AWS |
| `aws-only-test.sh` | AWS-only test | 5 min | AWS only |
| `native-services-test.sh` | Setup native | 2 min | Python, Node |
| `start-native-services-tmux.sh` | Start in tmux | 1 min | tmux |
| `send-test-kafka-event.py` | Kafka test | 1 min | Kafka |

## Quick Decision Tree

```
Do you have Docker?
├─ Yes → ./scripts/quick-test.sh
└─ No
   ├─ Have AWS? → ./scripts/aws-only-test.sh
   └─ Local only → ./scripts/native-services-test.sh
```
