# Failover Status Management System - Integration Guide

This guide provides step-by-step instructions for deploying and integrating all components of the failover status management system.

## System Architecture

```
Ansible → Kafka → Lambda → DynamoDB → Read Flags Service → Atom Store → Applications
```

## Components Overview

1. **Ansible Script**: Triggers failover events
2. **Kafka**: Event streaming platform
3. **Kafka Consumer Lambda**: Processes events and updates DynamoDB
4. **DynamoDB**: Source of truth for failover status
5. **Read Flags Service**: Polls DynamoDB and updates Atom Store
6. **Atom Store Server**: API and WebSocket server for real-time updates
7. **Atom Store Library**: React/Recoil library for applications
8. **Applications**: Frontend apps that subscribe to failover status

## Prerequisites

- AWS Account with appropriate permissions
- Terraform 1.0+
- Python 3.11+
- Node.js 20+
- Docker (for containerized deployments)
- Kubernetes cluster (optional, for K8s deployment)
- Kafka cluster (managed or self-hosted)
- Ansible 2.9+ (for failover triggers)

## Step 1: Deploy AWS Infrastructure

### 1.1 Build Lambda Functions

```bash
# Build all Lambda functions
./build.sh
```

This creates:
- `kafka_consumer_lambda.zip` - Kafka event processor
- `update_lambda.zip` - Update API (optional)
- `notification_lambda.zip` - Notification handler (optional)
- `sse_lambda.zip` - SSE endpoint (optional)

### 1.2 Configure Terraform

Edit `terraform.tfvars`:

```hcl
aws_region          = "us-east-1"
lambda_function_name = "failover-system"
dynamodb_table_name = "failover-status"
lambda_timeout      = 300
lambda_memory_size  = 512
```

### 1.3 Deploy Infrastructure

```bash
terraform init
terraform plan
terraform apply
```

### 1.4 Configure Kafka Event Source

After deployment, configure the Lambda to consume from Kafka:

```bash
# Get Lambda ARN
LAMBDA_ARN=$(terraform output -raw kafka_consumer_lambda_arn)

# Create event source mapping (adjust for your Kafka setup)
aws lambda create-event-source-mapping \
  --function-name $LAMBDA_ARN \
  --event-source-arn arn:aws:kafka:us-east-1:123456789012:cluster/my-cluster \
  --topics failover-events \
  --starting-position LATEST
```

## Step 2: Deploy Read Flags Service

The Read Flags Service polls DynamoDB and updates the Atom Store.

### Option A: Docker Deployment

```bash
# Build Docker image
cd read_flags_service
docker build -t read-flags-service:latest .

# Run container
docker run -d \
  --name read-flags-service \
  -e DYNAMODB_TABLE_NAME=failover-status \
  -e ATOM_STORE_URL=http://atom-store-service:3000 \
  -e POLLING_INTERVAL=10 \
  -e AWS_REGION=us-east-1 \
  -e AWS_ACCESS_KEY_ID=your_key \
  -e AWS_SECRET_ACCESS_KEY=your_secret \
  read-flags-service:latest
```

### Option B: Kubernetes Deployment

```bash
# Apply Kubernetes deployment
kubectl apply -f read_flags_service/k8s-deployment.yaml

# Verify deployment
kubectl get pods -l app=read-flags-service
kubectl logs -f deployment/read-flags-service
```

### Option C: Direct Python Execution

```bash
cd read_flags_service
pip install -r requirements.txt

export DYNAMODB_TABLE_NAME=failover-status
export ATOM_STORE_URL=http://localhost:3000
export POLLING_INTERVAL=10

python service.py
```

## Step 3: Deploy Atom Store Server

The Atom Store Server provides REST API and WebSocket endpoints.

### 3.1 Build and Deploy

#### Option A: Docker Deployment

```bash
# Build Docker image
cd atom_store/server
docker build -t atom-store-service:latest .

# Run container
docker run -d \
  --name atom-store-service \
  -p 3000:3000 \
  -e PORT=3000 \
  -e NODE_ENV=production \
  atom-store-service:latest
```

#### Option B: Kubernetes Deployment

```bash
# Apply Kubernetes deployment
kubectl apply -f atom_store/server/k8s-deployment.yaml

# Verify deployment
kubectl get pods -l app=atom-store-service
kubectl get svc atom-store-service
```

#### Option C: Direct Node.js Execution

```bash
cd atom_store/server
npm install
npm run build
npm start
```

### 3.2 Verify Atom Store Server

```bash
# Health check
curl http://localhost:3000/health

# Get current status
curl http://localhost:3000/api/failover/status

# Test WebSocket (using wscat)
npm install -g wscat
wscat -c ws://localhost:3000
```

## Step 4: Integrate Atom Store in Applications

### 4.1 Install Atom Store Library

```bash
npm install @failover/atom-store recoil
```

### 4.2 Setup Recoil Root

```tsx
import { RecoilRoot } from 'recoil';

function App() {
  return (
    <RecoilRoot>
      <YourApp />
    </RecoilRoot>
  );
}
```

### 4.3 Use Failover Service

```tsx
import { useEffect } from 'react';
import { FailoverService } from '@failover/atom-store';

function YourComponent() {
  useEffect(() => {
    // Initialize failover service
    const service = new FailoverService('http://atom-store-service:3000');
    service.startPolling();

    return () => service.stopPolling();
  }, []);

  return <div>Your App</div>;
}
```

### 4.4 Subscribe to Failover Status

```tsx
import { useFailoverStatus } from '@failover/atom-store';

function App1Component() {
  const failoverStatus = useFailoverStatus('app1');

  if (failoverStatus?.failoverActive) {
    return (
      <div className="failover-banner">
        ⚠️ System is in failover mode: {failoverStatus.reason}
      </div>
    );
  }

  return <div>Normal operation</div>;
}
```

See `application_examples/` for complete integration examples.

## Step 5: Configure Ansible Failover Triggers

### 5.1 Install Ansible

```bash
pip install ansible kafka-python
```

### 5.2 Configure Kafka Connection

```bash
export KAFKA_BOOTSTRAP_SERVERS="kafka.example.com:9092"
```

### 5.3 Trigger Failover

```bash
cd ansible-example

# Activate failover
ansible-playbook trigger-failover.yml

# Deactivate failover
ansible-playbook trigger-failover.yml \
  -e "failover_apps=[{app_id: 'app1', failover_status: 'N', reason: 'Maintenance complete'}]"
```

## Step 6: Testing the Complete Flow

### 6.1 Trigger Failover Event

```bash
# Using Ansible
ansible-playbook ansible-example/trigger-failover.yml \
  -e "failover_apps=[{app_id: 'app1', failover_status: 'Y', reason: 'Test failover'}]"
```

### 6.2 Verify Kafka Message

```bash
kafka-console-consumer \
  --bootstrap-server $KAFKA_BOOTSTRAP_SERVERS \
  --topic failover-events \
  --from-beginning
```

### 6.3 Check Lambda Execution

```bash
aws logs tail /aws/lambda/failover-system-kafka-consumer --follow
```

### 6.4 Verify DynamoDB Update

```bash
aws dynamodb get-item \
  --table-name failover-status \
  --key '{"pk": {"S": "FAILOVER_STATUS"}, "sk": {"S": "CURRENT"}}'
```

### 6.5 Monitor Read Flags Service

```bash
# Docker
docker logs -f read-flags-service

# Kubernetes
kubectl logs -f deployment/read-flags-service
```

### 6.6 Check Atom Store Updates

```bash
# Get current status
curl http://localhost:3000/api/failover/status

# Connect to WebSocket
wscat -c ws://localhost:3000
```

### 6.7 Verify Application Updates

Open your application in a browser and verify the failover banner appears.

## Monitoring and Observability

### CloudWatch Logs

```bash
# Kafka Consumer Lambda
aws logs tail /aws/lambda/failover-system-kafka-consumer --follow

# DynamoDB metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/DynamoDB \
  --metric-name ConsumedReadCapacityUnits \
  --dimensions Name=TableName,Value=failover-status \
  --start-time 2024-01-15T00:00:00Z \
  --end-time 2024-01-15T23:59:59Z \
  --period 3600 \
  --statistics Sum
```

### Application Metrics

Monitor these key metrics:

- Kafka consumer lag
- Lambda invocation count and errors
- DynamoDB read/write capacity
- Read Flags Service polling frequency
- Atom Store WebSocket connections
- Application failover banner display rate

## Troubleshooting

### Issue: Kafka Consumer Not Processing Events

**Check:**
1. Lambda event source mapping is configured
2. Kafka cluster is accessible from Lambda
3. Lambda has correct IAM permissions
4. Kafka topic exists and has messages

```bash
# Check event source mapping
aws lambda list-event-source-mappings --function-name failover-system-kafka-consumer

# Check Lambda logs
aws logs tail /aws/lambda/failover-system-kafka-consumer --follow
```

### Issue: DynamoDB Not Updating

**Check:**
1. Lambda has DynamoDB write permissions
2. Table name is correct
3. Event format is valid

```bash
# Test Lambda manually
aws lambda invoke \
  --function-name failover-system-kafka-consumer \
  --payload file://test-event.json \
  response.json
```

### Issue: Read Flags Service Not Polling

**Check:**
1. Service is running
2. DynamoDB table is accessible
3. AWS credentials are configured
4. Atom Store URL is correct

```bash
# Check service logs
docker logs read-flags-service

# Test DynamoDB access
aws dynamodb scan --table-name failover-status
```

### Issue: Atom Store Not Receiving Updates

**Check:**
1. Atom Store Server is running
2. Read Flags Service can reach Atom Store
3. WebSocket connections are established

```bash
# Check Atom Store health
curl http://localhost:3000/health

# Check WebSocket connections
curl http://localhost:3000/api/failover/status
```

### Issue: Applications Not Showing Failover

**Check:**
1. Application is subscribed to correct atom
2. Failover Service is initialized
3. WebSocket connection is active
4. Browser console for errors

## Performance Tuning

### Reduce Latency

1. **Decrease polling interval**: Set `POLLING_INTERVAL=5` (5 seconds)
2. **Use DynamoDB Streams**: Replace polling with stream-based updates
3. **Increase Read Flags Service replicas**: Scale horizontally
4. **Use WebSocket instead of polling**: In Failover Service

### Optimize Costs

1. **Increase polling interval**: Set `POLLING_INTERVAL=30` (30 seconds)
2. **Use DynamoDB on-demand billing**: Already configured
3. **Reduce Lambda memory**: Adjust based on actual usage
4. **Implement caching**: Cache DynamoDB reads in Read Flags Service

## Security Considerations

1. **Kafka Authentication**: Use SASL/SSL for Kafka connections
2. **DynamoDB Encryption**: Enable encryption at rest (default)
3. **IAM Permissions**: Use least privilege for Lambda roles
4. **API Authentication**: Add authentication to Atom Store API
5. **Network Security**: Use VPC for Lambda and services
6. **Secrets Management**: Use AWS Secrets Manager for credentials

## Next Steps

1. Set up monitoring dashboards
2. Configure alerting for failures
3. Implement automated testing
4. Add authentication to Atom Store API
5. Set up CI/CD pipelines
6. Document runbooks for common scenarios
7. Implement disaster recovery procedures

## Support

For issues or questions:
1. Check CloudWatch Logs for detailed errors
2. Review service logs (Docker/Kubernetes)
3. Verify IAM permissions and network connectivity
4. Test individual components in isolation
