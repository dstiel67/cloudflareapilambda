# Failover Status Management System - Deployment Guide

Complete deployment guide for the failover status management system using Kafka, DynamoDB, and Atom Stores.

## Prerequisites

### Required
1. **AWS CLI** configured with appropriate credentials
2. **Terraform** installed (version 1.0 or later)
3. **Python 3.11+** for Lambda functions and Read Flags Service
4. **Node.js 20+** for Atom Store Server
5. **Kafka cluster** (managed or self-hosted)
6. **Ansible 2.9+** for failover triggers

### Optional
7. **Docker** for containerized deployments
8. **Kubernetes cluster** for K8s deployment
9. **kubectl** configured for K8s access

## Architecture Overview

```
Ansible → Kafka → Lambda → DynamoDB → Read Flags Service → Atom Store → Angular Apps
```

## Infrastructure Components

### AWS Infrastructure (Terraform)
- **Kafka Consumer Lambda**: Processes Kafka failover events
- **DynamoDB Table**: Source of truth for failover status
- **Dead Letter Queues**: Captures failed Lambda invocations
- **IAM Roles & Policies**: Least privilege permissions
- **CloudWatch Monitoring**: Logs, metrics, dashboards, and alarms
- **X-Ray Tracing**: Performance monitoring

### Application Layer (Docker/K8s)
- **Read Flags Service**: Polls DynamoDB and updates Atom Store
- **Atom Store Server**: REST API and WebSocket server for Angular apps

### External Components
- **Kafka Cluster**: Message broker for failover events
- **Ansible Scripts**: Initiates failover events

## Deployment Steps

### Step 1: Build Lambda Functions

Build all Lambda function packages:

```bash
# Universal build script (recommended)
./build.sh
```

This creates:
- `kafka_consumer_lambda.zip` - Kafka event processor

**Platform-specific alternatives**:
- Linux: `./build_kafka_consumer_lambda.sh`
- Windows: `build_kafka_consumer_lambda.bat`

### Step 2: Configure Terraform Variables

Create `terraform.tfvars`:

```hcl
# AWS Configuration
aws_region = "us-east-1"

# Lambda Configuration
lambda_function_name = "failover-system"
dynamodb_table_name  = "failover-status"
lambda_timeout       = 300  # 5 minutes
lambda_memory_size   = 512  # MB

# Monitoring (optional)
alert_email = "your-email@example.com"  # Leave empty to disable alerts
```

### Step 3: Deploy AWS Infrastructure

```bash
# Initialize Terraform
terraform init

# Review the deployment plan
terraform plan

# Deploy the infrastructure
terraform apply
```

**What gets deployed**:
- Kafka Consumer Lambda function
- DynamoDB table with on-demand billing
- Dead Letter Queue for Lambda
- IAM roles and policies
- CloudWatch log groups (14-day retention)
- CloudWatch alarms (if alert_email configured)
- X-Ray tracing configuration

### Step 4: Configure Kafka Event Source

After Terraform deployment, configure the Lambda to consume from Kafka:

```bash
# Get Lambda ARN from Terraform output
LAMBDA_ARN=$(terraform output -raw kafka_consumer_lambda_arn)

# Create event source mapping
aws lambda create-event-source-mapping \
  --function-name $LAMBDA_ARN \
  --event-source-arn arn:aws:kafka:REGION:ACCOUNT:cluster/CLUSTER_NAME \
  --topics failover-events \
  --starting-position LATEST \
  --batch-size 100 \
  --maximum-batching-window-in-seconds 5
```

**For AWS MSK (Managed Streaming for Kafka)**:
```bash
# Get MSK cluster ARN
MSK_ARN=$(aws kafka list-clusters --query 'ClusterInfoList[0].ClusterArn' --output text)

# Create event source mapping
aws lambda create-event-source-mapping \
  --function-name $LAMBDA_ARN \
  --event-source-arn $MSK_ARN \
  --topics failover-events \
  --starting-position LATEST
```

**Verify event source mapping**:
```bash
aws lambda list-event-source-mappings --function-name $LAMBDA_ARN
```

### Step 5: Deploy Read Flags Service

The Read Flags Service polls DynamoDB and updates the Atom Store.

#### Option A: Docker Deployment

```bash
cd read_flags_service

# Build Docker image
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

# Verify container is running
docker ps | grep read-flags-service

# Check logs
docker logs -f read-flags-service
```

#### Option B: Kubernetes Deployment

```bash
# Update k8s-deployment.yaml with your configuration
# - DYNAMODB_TABLE_NAME
# - ATOM_STORE_URL
# - AWS credentials (use IAM roles for service accounts if possible)

# Apply deployment
kubectl apply -f read_flags_service/k8s-deployment.yaml

# Verify deployment
kubectl get pods -l app=read-flags-service
kubectl get svc read-flags-service

# Check logs
kubectl logs -f deployment/read-flags-service
```

#### Option C: Direct Python Execution

```bash
cd read_flags_service

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DYNAMODB_TABLE_NAME=failover-status
export ATOM_STORE_URL=http://localhost:3000
export POLLING_INTERVAL=10
export AWS_REGION=us-east-1

# Run service
python service.py
```

**Configuration Options**:
- `DYNAMODB_TABLE_NAME`: DynamoDB table to poll (required)
- `ATOM_STORE_URL`: Atom Store Server endpoint (required)
- `POLLING_INTERVAL`: Seconds between polls (default: 10)
- `AWS_REGION`: AWS region (required)
- `AWS_ACCESS_KEY_ID`: AWS credentials (optional if using IAM role)
- `AWS_SECRET_ACCESS_KEY`: AWS credentials (optional if using IAM role)

### Step 6: Deploy Atom Store Server

The Atom Store Server provides REST API and WebSocket endpoints for Angular applications.

#### Option A: Docker Deployment

```bash
cd atom_store/server

# Build Docker image
docker build -t atom-store-service:latest .

# Run container
docker run -d \
  --name atom-store-service \
  -p 3000:3000 \
  -e PORT=3000 \
  -e NODE_ENV=production \
  atom-store-service:latest

# Verify container is running
docker ps | grep atom-store-service

# Check logs
docker logs -f atom-store-service

# Test health endpoint
curl http://localhost:3000/health
```

#### Option B: Kubernetes Deployment

```bash
# Apply deployment
kubectl apply -f atom_store/server/k8s-deployment.yaml

# Verify deployment
kubectl get pods -l app=atom-store-service
kubectl get svc atom-store-service

# Check logs
kubectl logs -f deployment/atom-store-service

# Get service URL
kubectl get svc atom-store-service
```

#### Option C: Direct Node.js Execution

```bash
cd atom_store/server

# Install dependencies
npm install

# Build TypeScript
npm run build

# Start server
npm start

# Or for development
npm run dev
```

**Configuration Options**:
- `PORT`: Server port (default: 3000)
- `NODE_ENV`: Environment (production/development)

**Verify Atom Store Server**:
```bash
# Health check
curl http://localhost:3000/health

# Get current status
curl http://localhost:3000/api/failover/status

# Test WebSocket (using wscat)
npm install -g wscat
wscat -c ws://localhost:3000
```

### Step 7: Integrate Atom Store in Angular Applications

#### Install Dependencies

Angular applications use built-in features, so no additional packages are required.

#### Create Failover Service

Create `failover.service.ts` in your Angular project. See the complete example in `angular-client-example/failover.service.ts`.

#### Use Failover Status in Components

```typescript
import { Component, OnInit, OnDestroy } from '@angular/core';
import { Subscription } from 'rxjs';
import { FailoverService, FailoverStatus } from './failover.service';

@Component({
  selector: 'app-app1',
  template: `
    <div *ngIf="failoverStatus?.failoverActive" class="failover-banner">
      ⚠️ System is in failover mode: {{ failoverStatus.reason }}
    </div>
    <div *ngIf="!failoverStatus?.failoverActive">
      Normal operation
    </div>
  `
})
export class App1Component implements OnInit, OnDestroy {
  failoverStatus: FailoverStatus | undefined;
  private subscription: Subscription | null = null;

  constructor(private failoverService: FailoverService) {}

  ngOnInit(): void {
    this.subscription = this.failoverService
      .getFailoverStatus('app1')
      .subscribe(status => {
        this.failoverStatus = status;
      });
  }

  ngOnDestroy(): void {
    this.subscription?.unsubscribe();
  }
}
```

#### Initialize in App Component

```typescript
import { Component, OnInit } from '@angular/core';
import { FailoverService } from './failover.service';

@Component({
  selector: 'app-root',
  template: `<app-app1></app-app1>`
})
export class AppComponent implements OnInit {
  constructor(private failoverService: FailoverService) {}

  ngOnInit(): void {
    // Connect to Atom Store WebSocket
    this.failoverService.connect('ws://atom-store-service:3000');
  }
}
```

See `angular-client-example/` for complete integration examples.

### Step 8: Configure Ansible Failover Triggers

#### Install Ansible and Dependencies

```bash
pip install ansible kafka-python
```

#### Configure Kafka Connection

```bash
export KAFKA_BOOTSTRAP_SERVERS="kafka.example.com:9092"
```

#### Trigger Failover

```bash
cd ansible-example

# Activate failover
ansible-playbook trigger-failover.yml

# Deactivate failover
ansible-playbook trigger-failover.yml \
  -e "failover_apps=[{app_id: 'app1', failover_status: 'N', reason: 'Maintenance complete'}]"
```

See `ansible-example/README.md` for detailed Ansible configuration.

## Testing the Complete Flow

### 1. Trigger Failover Event

```bash
# Using Ansible
ansible-playbook ansible-example/trigger-failover.yml \
  -e "failover_apps=[{app_id: 'app1', failover_status: 'Y', reason: 'Test failover'}]"
```

### 2. Verify Kafka Message

```bash
kafka-console-consumer \
  --bootstrap-server $KAFKA_BOOTSTRAP_SERVERS \
  --topic failover-events \
  --from-beginning
```

### 3. Check Lambda Execution

```bash
aws logs tail /aws/lambda/failover-system-kafka-consumer --follow
```

### 4. Verify DynamoDB Update

```bash
aws dynamodb get-item \
  --table-name failover-status \
  --key '{"pk": {"S": "FAILOVER_STATUS"}, "sk": {"S": "CURRENT"}}'
```

### 5. Monitor Read Flags Service

```bash
# Docker
docker logs -f read-flags-service

# Kubernetes
kubectl logs -f deployment/read-flags-service
```

### 6. Check Atom Store Updates

```bash
# Get current status
curl http://localhost:3000/api/failover/status

# Connect to WebSocket
wscat -c ws://localhost:3000
```

### 7. Verify Application Updates

Open your Angular application in a browser and verify the failover banner appears.

## Monitoring

### CloudWatch Dashboard

```bash
# Get dashboard URL
terraform output cloudwatch_dashboard_url
```

The dashboard includes:
- Lambda invocations, errors, duration, and throttles
- DynamoDB read/write capacity and throttles
- Custom application metrics
- Recent error logs

### View Logs

```bash
# Lambda logs
aws logs tail /aws/lambda/failover-system-kafka-consumer --follow

# Read Flags Service logs
docker logs -f read-flags-service
kubectl logs -f deployment/read-flags-service

# Atom Store logs
docker logs -f atom-store-service
kubectl logs -f deployment/atom-store-service
```

### CloudWatch Alarms

When `alert_email` is configured, the following alarms are created:
- Lambda function errors (threshold: 5 errors per 5 minutes)
- Lambda high duration (threshold: 60 seconds)
- Lambda throttles (any occurrence)
- DynamoDB throttles (any occurrence)
- DLQ messages (any message in dead letter queue)

### Key Metrics to Monitor

- **Kafka Consumer Lambda**: Invocation count, errors, duration, consumer lag
- **Read Flags Service**: Polling frequency, DynamoDB read errors, change detection rate
- **Atom Store Server**: Active WebSocket connections, API request rate, update latency
- **DynamoDB**: Read/write capacity consumption, throttled requests

## Troubleshooting

### Kafka Consumer Not Processing Events

**Symptoms**: Kafka events not updating DynamoDB

**Checks**:
1. Verify event source mapping is configured:
   ```bash
   aws lambda list-event-source-mappings --function-name failover-system-kafka-consumer
   ```
2. Check Kafka consumer lag
3. Review Lambda logs for processing errors
4. Verify Kafka cluster connectivity and permissions

**Solutions**:
- Ensure Lambda has network access to Kafka cluster
- Verify Kafka topic exists and has messages
- Check Lambda IAM permissions for Kafka access
- Review event format matches expected schema

### Read Flags Service Not Polling

**Symptoms**: Atom Store not receiving updates

**Checks**:
1. Verify service is running:
   ```bash
   docker ps | grep read-flags-service
   kubectl get pods -l app=read-flags-service
   ```
2. Check service logs for errors
3. Verify DynamoDB table is accessible
4. Test Atom Store URL connectivity

**Solutions**:
- Ensure AWS credentials are configured correctly
- Verify DynamoDB table name is correct
- Check network connectivity to Atom Store
- Verify polling interval is reasonable (5-30 seconds)

### Atom Store Not Receiving Updates

**Symptoms**: Angular apps not showing failover status

**Checks**:
1. Verify Atom Store Server is running:
   ```bash
   curl http://localhost:3000/health
   ```
2. Check Read Flags Service can reach Atom Store
3. Verify WebSocket connections are established

**Solutions**:
- Ensure Atom Store Server is accessible from Read Flags Service
- Check firewall rules and network policies
- Verify port 3000 is open
- Review Atom Store logs for errors

### Applications Not Showing Failover

**Symptoms**: UI not updating with failover status

**Checks**:
1. Verify application is subscribed to correct failover status
2. Check Failover Service is initialized
3. Verify WebSocket connection is active
4. Check browser console for errors
5. Verify Angular service is properly injected

**Solutions**:
- Ensure Failover Service is provided in Angular module
- Verify Failover Service is started with correct URL
- Check network connectivity to Atom Store
- Review browser console for JavaScript errors

### High Latency

**Symptoms**: Updates taking longer than expected (>30 seconds)

**Solutions**:
1. Reduce polling interval in Read Flags Service
2. Check Kafka consumer lag
3. Review Lambda duration in CloudWatch
4. Consider using DynamoDB Streams instead of polling
5. Check network latency between services

## Performance Optimization

### Reduce Latency
1. **Decrease polling interval**: Set `POLLING_INTERVAL=5` (5 seconds)
2. **Use DynamoDB Streams**: Replace polling with stream-based updates (~100-500ms)
3. **Increase Read Flags Service replicas**: Scale horizontally
4. **Use WebSocket**: Push updates instead of polling in Failover Service

### Optimize Costs
1. **Increase polling interval**: Set `POLLING_INTERVAL=30` (30 seconds)
2. **Use DynamoDB on-demand billing**: Already configured
3. **Reduce Lambda memory**: Adjust based on actual usage
4. **Implement caching**: Cache DynamoDB reads in Read Flags Service

## Security Considerations

### AWS Security
- **IAM Permissions**: Lambda uses least privilege roles
- **DynamoDB Encryption**: Encryption at rest enabled by default
- **VPC**: Consider VPC configuration for Lambda (optional)
- **Secrets Management**: Use AWS Secrets Manager for credentials

### Kafka Security
- **Authentication**: Use SASL/SSL for Kafka connections
- **Authorization**: Configure Kafka ACLs
- **Encryption**: Enable TLS for data in transit

### Application Security
- **API Authentication**: Add authentication to Atom Store API
- **CORS**: Configure CORS for Atom Store Server
- **Rate Limiting**: Implement rate limiting on Atom Store API
- **Input Validation**: Validate all inputs in Lambda and services

## Cleanup

To destroy all AWS resources:

```bash
terraform destroy
```

**Warning**: This will permanently delete:
- Lambda function
- DynamoDB table and all data
- CloudWatch logs and metrics
- IAM roles and policies
- Dead Letter Queues

**Manual cleanup required**:
- Kafka event source mapping
- Read Flags Service (Docker/K8s)
- Atom Store Server (Docker/K8s)

## Next Steps

1. Set up monitoring dashboards
2. Configure alerting for failures
3. Implement automated testing
4. Add authentication to Atom Store API
5. Set up CI/CD pipelines
6. Document runbooks for common scenarios
7. Implement disaster recovery procedures

## Additional Resources

- [ARCHITECTURE.md](ARCHITECTURE.md) - Detailed system architecture
- [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md) - Complete integration guide
- [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) - Deployment checklist
- [BUILD.md](BUILD.md) - Build system documentation
- [DLQ_GUIDE.md](DLQ_GUIDE.md) - Dead Letter Queue monitoring
- `angular-client-example/` - Angular integration examples
- `ansible-example/` - Ansible failover trigger examples

## Support

For issues or questions:
1. Check CloudWatch Logs for detailed errors
2. Review service logs (Docker/Kubernetes)
3. Verify IAM permissions and network connectivity
4. Test individual components in isolation
5. Consult the troubleshooting section above
