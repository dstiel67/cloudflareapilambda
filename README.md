# Failover Status Management System with Atom Stores

Complete failover status management system using Kafka, DynamoDB, and Atom Stores for real-time reactive state management in Angular applications.

## Overview

This project provides a production-ready solution for tracking and broadcasting failover status across multiple Angular applications. The system uses:

- **Kafka** for event ingestion
- **AWS Lambda** for event processing
- **DynamoDB** as the source of truth
- **Read Flags Service** for polling and change detection
- **Atom Store** for reactive state management with WebSocket
- **Angular Services** for seamless integration with RxJS Observables

**Target Applications**: Angular applications using RxJS for reactive state management

**Latency**: ~5-30 seconds end-to-end (configurable via polling interval)

## Architecture

```
Ansible → Kafka → Lambda → DynamoDB → Read Flags Service → Atom Store → Angular Apps
```

### Components

#### AWS Infrastructure
- **Kafka Consumer Lambda**: Processes Kafka failover events and updates DynamoDB
- **DynamoDB Table**: Source of truth for failover status
- **Dead Letter Queues**: Captures failed Lambda invocations
- **CloudWatch Monitoring**: Logs, metrics, dashboards, and alarms
- **X-Ray Tracing**: Performance monitoring and debugging

#### Application Layer
- **Read Flags Service**: Polls DynamoDB and updates Atom Store when flags change
- **Atom Store Server**: REST API and WebSocket server for Angular applications
- **Atom Store Angular Service**: Angular service with RxJS integration for failover status

#### External Components
- **Kafka Cluster**: Message broker for failover events
- **Ansible Scripts**: Initiates failover events based on infrastructure monitoring

### Data Flow

1. **Failover Trigger**: Ansible script detects infrastructure issue or receives manual trigger
2. **Event Published**: Ansible sends failover event to Kafka
3. **Lambda Consumes**: Kafka Consumer Lambda processes the message
4. **DynamoDB Update**: Lambda validates and writes failover flags to DynamoDB
5. **Polling**: Read Flags Service periodically polls DynamoDB for changes
6. **Atom Update**: When flags change, Read Flags Service updates Atom Store
7. **Reactive Propagation**: Angular apps subscribed via WebSocket automatically receive updates
8. **UI Update**: Applications react to state changes (show banners, redirect, etc.)

## Features

### Event-Driven Architecture
- Kafka-based event ingestion for decoupled failover control
- Lambda function for reliable event processing
- DynamoDB as single source of truth
- Automatic retry and error handling

### Reactive State Management
- RxJS Observables for reactive state
- Real-time updates via WebSocket
- Automatic reconnection with exponential backoff
- Type-safe TypeScript API

### Scalability & Reliability
- Horizontal scaling for Read Flags Service and Atom Store
- DynamoDB on-demand billing (auto-scaling)
- Lambda automatic scaling
- Dead Letter Queues for failed invocations
- Comprehensive monitoring and alerting

### Developer Experience
- Simple Angular service: `getFailoverStatus('app1')`
- Complete TypeScript types
- Docker and Kubernetes deployment configs
- Comprehensive documentation and examples

## Prerequisites

1. **AWS CLI** configured with appropriate credentials
2. **Terraform** installed (version 1.0 or later)
3. **Python 3.11+** for Lambda functions and Read Flags Service
4. **Node.js 20+** for Atom Store Server
5. **Docker** (optional, for containerized deployments)
6. **Kubernetes cluster** (optional, for K8s deployment)
7. **Kafka cluster** (managed or self-hosted)
8. **Ansible 2.9+** (for failover triggers)

## Quick Start

### 1. Build Lambda Functions

```bash
# Build all Lambda functions
./build.sh
```

This creates:
- `kafka_consumer_lambda.zip` - Kafka event processor

### 2. Configure Terraform

Create `terraform.tfvars`:

```hcl
aws_region = "us-east-1"
lambda_function_name = "failover-system"
dynamodb_table_name = "failover-status"
lambda_timeout = 300
lambda_memory_size = 512
alert_email = "your-email@example.com"  # Optional
```

### 3. Deploy AWS Infrastructure

```bash
# Initialize Terraform
terraform init

# Review the deployment plan
terraform plan

# Deploy the infrastructure
terraform apply
```

### 4. Configure Kafka Event Source

After deployment, configure the Lambda to consume from Kafka:

```bash
# Get Lambda ARN
LAMBDA_ARN=$(terraform output -raw kafka_consumer_lambda_arn)

# Create event source mapping
aws lambda create-event-source-mapping \
  --function-name $LAMBDA_ARN \
  --event-source-arn arn:aws:kafka:REGION:ACCOUNT:cluster/CLUSTER_NAME \
  --topics failover-events \
  --starting-position LATEST \
  --batch-size 100
```

### 5. Deploy Read Flags Service

#### Option A: Docker Deployment

```bash
cd read_flags_service
docker build -t read-flags-service:latest .

docker run -d \
  --name read-flags-service \
  -e DYNAMODB_TABLE_NAME=failover-status \
  -e ATOM_STORE_URL=http://atom-store-service:3000 \
  -e POLLING_INTERVAL=10 \
  -e AWS_REGION=us-east-1 \
  read-flags-service:latest
```

#### Option B: Kubernetes Deployment

```bash
kubectl apply -f read_flags_service/k8s-deployment.yaml
kubectl get pods -l app=read-flags-service
```

#### Option C: Direct Python Execution

```bash
cd read_flags_service
pip install -r requirements.txt

export DYNAMODB_TABLE_NAME=failover-status
export ATOM_STORE_URL=http://localhost:3000
export POLLING_INTERVAL=10

python service.py
```

### 6. Deploy Atom Store Server

#### Option A: Docker Deployment

```bash
cd atom_store/server
docker build -t atom-store-service:latest .

docker run -d \
  --name atom-store-service \
  -p 3000:3000 \
  -e PORT=3000 \
  -e NODE_ENV=production \
  atom-store-service:latest
```

#### Option B: Kubernetes Deployment

```bash
kubectl apply -f atom_store/server/k8s-deployment.yaml
kubectl get svc atom-store-service
```

#### Option C: Direct Node.js Execution

```bash
cd atom_store/server
npm install
npm run build
npm start
```

### 7. Integrate in Angular Applications

#### Install Dependencies

Angular applications use the built-in HttpClient and WebSocket APIs, so no additional packages are required beyond standard Angular.

#### Create Failover Service

Create `failover.service.ts`:

```typescript
import { Injectable, NgZone } from '@angular/core';
import { Observable, BehaviorSubject } from 'rxjs';

export interface FailoverStatus {
  appId: string;
  failoverActive: boolean;
  lastUpdated: string;
  reason: string;
  updatedBy: string;
}

@Injectable({
  providedIn: 'root'
})
export class FailoverService {
  private ws: WebSocket | null = null;
  private failoverStatus = new BehaviorSubject<Map<string, FailoverStatus>>(new Map());
  private connectionStatus = new BehaviorSubject<'connected' | 'disconnected' | 'error'>('disconnected');
  
  constructor(private ngZone: NgZone) {}

  connect(atomStoreUrl: string): void {
    this.ws = new WebSocket(atomStoreUrl);

    this.ws.onopen = () => {
      this.ngZone.run(() => {
        console.log('Connected to Atom Store');
        this.connectionStatus.next('connected');
        this.fetchCurrentStatus(atomStoreUrl);
      });
    };

    this.ws.onmessage = (event) => {
      this.ngZone.run(() => {
        const data = JSON.parse(event.data);
        this.updateFailoverStatus(data);
      });
    };

    this.ws.onerror = () => {
      this.ngZone.run(() => {
        this.connectionStatus.next('error');
      });
    };

    this.ws.onclose = () => {
      this.ngZone.run(() => {
        this.connectionStatus.next('disconnected');
      });
    };
  }

  private async fetchCurrentStatus(atomStoreUrl: string): Promise<void> {
    try {
      const httpUrl = atomStoreUrl.replace('ws://', 'http://').replace('wss://', 'https://');
      const response = await fetch(`${httpUrl}/api/failover/status`);
      const data = await response.json();
      
      const statusMap = new Map<string, FailoverStatus>();
      Object.entries(data).forEach(([appId, status]) => {
        statusMap.set(appId, status as FailoverStatus);
      });
      
      this.failoverStatus.next(statusMap);
    } catch (error) {
      console.error('Failed to fetch current status:', error);
    }
  }

  private updateFailoverStatus(data: any): void {
    const currentMap = new Map(this.failoverStatus.value);
    
    Object.entries(data).forEach(([appId, status]) => {
      currentMap.set(appId, status as FailoverStatus);
    });
    
    this.failoverStatus.next(currentMap);
  }

  getFailoverStatus(appId: string): Observable<FailoverStatus | undefined> {
    return new Observable(observer => {
      const subscription = this.failoverStatus.subscribe(statusMap => {
        observer.next(statusMap.get(appId));
      });
      return () => subscription.unsubscribe();
    });
  }

  getConnectionStatus(): Observable<'connected' | 'disconnected' | 'error'> {
    return this.connectionStatus.asObservable();
  }

  disconnect(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}
```

#### Use in Components

Create `app1.component.ts`:

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
  `,
  styles: [`
    .failover-banner {
      background-color: #fff3cd;
      border: 1px solid #ffc107;
      padding: 15px;
      border-radius: 4px;
      margin: 10px 0;
      color: #856404;
    }
  `]
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

Update `app.component.ts`:

```typescript
import { Component, OnInit } from '@angular/core';
import { FailoverService } from './failover.service';

@Component({
  selector: 'app-root',
  template: `
    <app-app1></app-app1>
  `
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

### 8. Test the Complete Flow

#### Trigger Failover via Ansible

```bash
cd ansible-example

# Activate failover
ansible-playbook trigger-failover.yml

# Deactivate failover
ansible-playbook trigger-failover.yml \
  -e "failover_apps=[{app_id: 'app1', failover_status: 'N', reason: 'Maintenance complete'}]"
```

#### Verify Kafka Message

```bash
kafka-console-consumer \
  --bootstrap-server $KAFKA_BOOTSTRAP_SERVERS \
  --topic failover-events \
  --from-beginning
```

#### Check Lambda Execution

```bash
aws logs tail /aws/lambda/failover-system-kafka-consumer --follow
```

#### Verify DynamoDB Update

```bash
aws dynamodb get-item \
  --table-name failover-status \
  --key '{"pk": {"S": "FAILOVER_STATUS"}, "sk": {"S": "CURRENT"}}'
```

#### Monitor Read Flags Service

```bash
# Docker
docker logs -f read-flags-service

# Kubernetes
kubectl logs -f deployment/read-flags-service
```

#### Check Atom Store Updates

```bash
# Get current status
curl http://localhost:3000/api/failover/status

# Connect to WebSocket (using wscat)
npm install -g wscat
wscat -c ws://localhost:3000
```

#### Verify Application Updates

Open your Angular application in a browser and verify the failover banner appears.

## Event Formats

### Kafka Failover Event

```json
{
  "event_type": "failover",
  "timestamp": "2024-01-15T10:30:00Z",
  "applications": [
    {
      "app_id": "app1",
      "failover_status": "Y",
      "reason": "Primary datacenter unavailable"
    },
    {
      "app_id": "app2",
      "failover_status": "Y",
      "reason": "Primary datacenter unavailable"
    }
  ],
  "triggered_by": "ansible_monitoring",
  "severity": "critical"
}
```

### DynamoDB Record

```json
{
  "pk": "FAILOVER_STATUS",
  "sk": "CURRENT",
  "App1_Failover": "Y",
  "App2_Failover": "Y",
  "App1_LastUpdated": "2024-01-15T10:30:00Z",
  "App2_LastUpdated": "2024-01-15T10:30:00Z",
  "App1_Reason": "Primary datacenter unavailable",
  "App2_Reason": "Primary datacenter unavailable",
  "LastUpdatedBy": "ansible_monitoring"
}
```

### Atom Store State

```javascript
// App 1 Failover Atom
{
  appId: "app1",
  failoverActive: true,
  lastUpdated: "2024-01-15T10:30:00Z",
  reason: "Primary datacenter unavailable",
  updatedBy: "ansible_monitoring"
}
```

## Monitoring

### CloudWatch Dashboard

Access the monitoring dashboard:

```bash
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

### X-Ray Tracing

View performance traces in the AWS X-Ray console:
1. Navigate to AWS X-Ray in the AWS Console
2. Select "Traces" to view execution traces
3. Use filters to analyze performance patterns and bottlenecks

## Configuration

### Environment Variables

#### Kafka Consumer Lambda
- `DYNAMODB_TABLE_NAME`: Target DynamoDB table name

#### Read Flags Service
- `DYNAMODB_TABLE_NAME`: DynamoDB table to poll
- `ATOM_STORE_URL`: Atom Store Server endpoint
- `POLLING_INTERVAL`: Seconds between polls (default: 10)
- `AWS_REGION`: AWS region
- `AWS_ACCESS_KEY_ID`: AWS credentials (if not using IAM role)
- `AWS_SECRET_ACCESS_KEY`: AWS credentials (if not using IAM role)

#### Atom Store Server
- `PORT`: Server port (default: 3000)
- `NODE_ENV`: Environment (production/development)

## Project Structure

```
.
├── kafka_consumer_lambda/      # Kafka event processor Lambda
│   ├── lambda_function.py
│   └── requirements.txt
├── read_flags_service/         # DynamoDB polling service
│   ├── service.py
│   ├── Dockerfile
│   ├── k8s-deployment.yaml
│   └── requirements.txt
├── atom_store/                 # Atom Store implementation
│   ├── server/                 # Node.js/TypeScript server
│   ├── src/                    # React/Recoil library
│   └── package.json
├── application_examples/       # React integration examples
│   ├── App1Example.tsx
│   └── App2Example.tsx
├── ansible-example/            # Ansible failover triggers
│   ├── trigger-failover.yml
│   └── README.md
├── scripts/                    # Testing and utility scripts
├── main.tf                     # Terraform main configuration
├── kafka_consumer.tf           # Kafka Consumer Lambda infrastructure
├── variables.tf                # Terraform variable definitions
├── outputs.tf                  # Terraform outputs
├── terraform.tfvars            # Your configuration values
├── build.sh                    # Universal build script
└── README.md                   # This file
```

## Development

### Running Tests

```bash
# Test Kafka Consumer Lambda locally
cd kafka_consumer_lambda
python -m pytest tests/ -v

# Test Read Flags Service locally
cd read_flags_service
python -m pytest tests/ -v

# Test Atom Store Server
cd atom_store/server
npm test
```

### Local Development

#### Start Services with Docker Compose

```bash
# Start all services locally
docker-compose -f docker-compose.test.yml up

# This starts:
# - Kafka (Zookeeper + Broker)
# - DynamoDB Local
# - Read Flags Service
# - Atom Store Server
```

#### Manual Testing

```bash
# Send test Kafka event
python scripts/send-test-kafka-event.py

# Check DynamoDB
aws dynamodb scan --table-name failover-status --endpoint-url http://localhost:8000

# Check Atom Store
curl http://localhost:3000/api/failover/status
```

## Troubleshooting

### Kafka Consumer Not Processing Events

**Symptoms**: Kafka events not updating DynamoDB

**Checks**:
1. Verify event source mapping is configured
2. Check Kafka consumer lag
3. Review Lambda logs for processing errors
4. Verify Kafka cluster connectivity and permissions

```bash
# Check event source mapping
aws lambda list-event-source-mappings --function-name failover-system-kafka-consumer

# Check Lambda logs
aws logs tail /aws/lambda/failover-system-kafka-consumer --follow
```

### Read Flags Service Not Polling

**Symptoms**: Atom Store not receiving updates

**Checks**:
1. Verify service is running
2. Check service logs for errors
3. Verify DynamoDB table is accessible
4. Test Atom Store URL connectivity

```bash
# Check service status
docker ps | grep read-flags-service
kubectl get pods -l app=read-flags-service

# View logs
docker logs read-flags-service
kubectl logs -f deployment/read-flags-service
```

### Atom Store Not Receiving Updates

**Symptoms**: Angular apps not showing failover status

**Checks**:
1. Verify Atom Store Server is running
2. Check Read Flags Service can reach Atom Store
3. Verify WebSocket connections are established

```bash
# Check Atom Store health
curl http://localhost:3000/health

# Check current status
curl http://localhost:3000/api/failover/status
```

### Applications Not Showing Failover

**Symptoms**: UI not updating with failover status

**Checks**:
1. Verify application is subscribed to correct failover status
2. Check Failover Service is initialized
3. Verify WebSocket connection is active
4. Check browser console for errors
5. Verify Angular service is properly injected

## Performance Optimization

### Reduce Latency
1. **Decrease polling interval**: Set `POLLING_INTERVAL=5` (5 seconds)
2. **Use DynamoDB Streams**: Replace polling with stream-based updates (~100-500ms)
3. **Increase Read Flags Service replicas**: Scale horizontally
4. **Use WebSocket**: Push updates instead of polling

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

## Cost Estimate

### Monthly Cost (Moderate Traffic)

**AWS Services**:
- **Lambda**: ~$5-10/month (1M invocations)
- **DynamoDB**: ~$5-15/month (on-demand, moderate traffic)
- **CloudWatch**: ~$5/month (logs, metrics, alarms)
- **X-Ray**: ~$2/month (tracing)

**External Services**:
- **Kafka**: Varies by provider (AWS MSK: ~$200-500/month for small cluster)
- **Compute**: Docker/K8s hosting for Read Flags Service and Atom Store (~$50-200/month)

**Total Estimated Cost**: $270-730/month (includes Kafka cluster)

See [AWS_COST_ESTIMATE.md](AWS_COST_ESTIMATE.md) for detailed breakdown.

## Additional Resources

- **[INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md)** - Complete deployment guide
- **[SYSTEM_OVERVIEW.md](SYSTEM_OVERVIEW.md)** - System overview with diagrams
- **[DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)** - Deployment checklist
- **[BUILD.md](BUILD.md)** - Build system documentation
- **[DLQ_GUIDE.md](DLQ_GUIDE.md)** - Dead Letter Queue monitoring
- **[AWS_COST_ESTIMATE.md](AWS_COST_ESTIMATE.md)** - Detailed cost breakdown
- `angular-client-example/` - Angular integration examples
- `ansible-example/` - Ansible failover trigger examples
- [AWS Lambda Documentation](https://docs.aws.amazon.com/lambda/)
- [Amazon DynamoDB Documentation](https://docs.aws.amazon.com/dynamodb/)
- [Angular Documentation](https://angular.io/docs)
- [RxJS Documentation](https://rxjs.dev/)
- [Apache Kafka Documentation](https://kafka.apache.org/documentation/)

## License

This project is provided as-is for use in your infrastructure.

## Support

For issues or questions:
1. Check CloudWatch Logs for detailed errors
2. Review service logs (Docker/Kubernetes)
3. Verify IAM permissions and network connectivity
4. Test individual components in isolation
5. Consult the troubleshooting section above
