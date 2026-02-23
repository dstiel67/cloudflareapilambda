# System Architecture - Failover Status Management with Atom Stores

This document describes the architecture of the failover status management system using Kafka, DynamoDB, and Atom Stores for real-time reactive state management.

## Overview

The system provides a complete solution for tracking and broadcasting failover status across multiple React applications. It uses Kafka for event ingestion, DynamoDB as the source of truth, and Atom Stores (Recoil) for reactive state management with real-time updates to subscribed applications.

**Target Applications**: Angular applications using RxJS for reactive state management

**Latency Profile**: ~5-30 seconds end-to-end (configurable via polling interval)

## Architecture Flow

```
Ansible → Kafka → Lambda → DynamoDB → Read Flags Service → Atom Store → Angular Apps
```

### Flow Details

1. **Failover Trigger**: Ansible script detects infrastructure issue or receives manual trigger
2. **Event Published**: Ansible sends failover event to Kafka with app identifiers and status
3. **Lambda Consumes**: Kafka Consumer Lambda processes the message
4. **DynamoDB Update**: Lambda validates and writes failover flags to DynamoDB
5. **Polling**: Read Flags Service periodically polls DynamoDB for changes
6. **Atom Update**: When flags change, Read Flags Service updates Atom Store
7. **Reactive Propagation**: Angular apps subscribed via WebSocket automatically receive updates
8. **UI Update**: Applications react to state changes (show banners, redirect, etc.)

### Latency Breakdown
- **Ansible to Kafka**: ~10-50ms
- **Kafka to Lambda**: ~100-500ms (consumer lag)
- **Lambda to DynamoDB**: ~50-100ms
- **DynamoDB to Read Flags**: 5-30 seconds (polling interval)
- **Read Flags to Atom Store**: ~10-50ms
- **Atom Store to Angular App**: ~1-10ms (WebSocket push)
- **Total end-to-end**: ~5-30 seconds (dominated by polling interval)

## Core Components

### AWS Infrastructure

#### 1. Kafka Consumer Lambda
- **Purpose**: Processes Kafka failover events and updates DynamoDB
- **Trigger**: Kafka messages from failover-events topic
- **Runtime**: Python 3.11
- **Key Features**: Event validation, transformation, error handling
- **Output**: Updates DynamoDB with failover flags

#### 2. DynamoDB Table
- **Purpose**: Source of truth for failover status
- **Billing Mode**: Pay-per-request (on-demand)
- **Schema**: Failover flags per application (e.g., `App1_Failover: "Y"`)
- **Key Features**: Point-in-time recovery, TTL support
- **Access Pattern**: Write by Lambda, read by Read Flags Service

#### 3. Dead Letter Queues (DLQs)
- **Purpose**: Captures failed Lambda invocations
- **Key Features**: Automatic CloudWatch alarms on message arrival
- **Monitoring**: SQS queue metrics

#### 4. CloudWatch Monitoring
- **Logs**: All Lambda invocations (14-day retention)
- **Metrics**: Custom application metrics
- **Dashboards**: Visualization of system health
- **Alarms**: Error rate, duration, throttling alerts

#### 5. X-Ray Tracing
- **Purpose**: Performance monitoring and debugging
- **Key Features**: Distributed tracing across Lambda invocations
- **Access**: AWS X-Ray console

### Application Layer

#### 6. Read Flags Service
- **Purpose**: Polls DynamoDB and updates Atom Store when flags change
- **Technology**: Python 3.11
- **Deployment**: Docker, Kubernetes, or direct Python execution
- **Configuration**: 
  - `DYNAMODB_TABLE_NAME`: DynamoDB table to poll
  - `ATOM_STORE_URL`: Atom Store Server endpoint
  - `POLLING_INTERVAL`: Seconds between polls (default: 10)
- **Key Features**: Change detection, automatic retry, health monitoring

#### 7. Atom Store Server
- **Purpose**: REST API and WebSocket server for Angular applications
- **Technology**: Node.js/TypeScript
- **Deployment**: Docker, Kubernetes, or direct Node.js execution
- **Endpoints**:
  - `GET /api/failover/status` - Get current failover status
  - `POST /api/failover/update` - Update failover status (used by Read Flags Service)
  - `GET /health` - Health check
  - `WebSocket /` - Real-time updates
- **Key Features**: WebSocket push notifications, REST API, in-memory state

#### 8. Atom Store Angular Service
- **Purpose**: Angular service for Atom Store integration
- **Technology**: TypeScript, RxJS Observables
- **Key Features**: 
  - `getFailoverStatus(appId)` - Observable for subscribing to failover status
  - `FailoverService` - Service for managing WebSocket connections
  - Automatic reconnection with exponential backoff
  - Type-safe API with TypeScript interfaces

### External Components

#### 9. Kafka Cluster
- **Purpose**: Message broker for failover events
- **Topics**: `failover-events`
- **Consumers**: Kafka Consumer Lambda
- **Status**: Required for system operation

#### 10. Ansible Scripts
- **Purpose**: Initiates failover events
- **Trigger**: Infrastructure monitoring, manual failover
- **Output**: Publishes events to Kafka
- **Location**: `ansible-example/` directory

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

## Client Integration

### Angular Application Example

```typescript
// failover.service.ts - Angular service for Atom Store integration
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

```typescript
// app1.component.ts - Using the failover service
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

```typescript
// app.component.ts - Initialize the service
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

Complete Angular integration examples are provided in the `angular-client-example/` directory.

## Deployment Guide

### Prerequisites
- AWS Account with appropriate permissions
- Terraform 1.0+
- Python 3.11+
- Node.js 20+
- Docker (for containerized deployments)
- Kafka cluster (managed or self-hosted)
- Ansible 2.9+ (for failover triggers)

### Step 1: Deploy AWS Infrastructure

```bash
# Build Lambda functions
./build.sh

# Configure Terraform
cat > terraform.tfvars <<EOF
aws_region = "us-east-1"
lambda_function_name = "failover-system"
dynamodb_table_name = "failover-status"
EOF

# Deploy infrastructure
terraform init
terraform apply

# Configure Kafka event source mapping
LAMBDA_ARN=$(terraform output -raw kafka_consumer_lambda_arn)
aws lambda create-event-source-mapping \
  --function-name $LAMBDA_ARN \
  --event-source-arn arn:aws:kafka:REGION:ACCOUNT:cluster/CLUSTER_NAME \
  --topics failover-events \
  --starting-position LATEST
```

### Step 2: Deploy Read Flags Service

```bash
# Docker deployment
cd read_flags_service
docker build -t read-flags-service:latest .
docker run -d \
  --name read-flags-service \
  -e DYNAMODB_TABLE_NAME=failover-status \
  -e ATOM_STORE_URL=http://atom-store-service:3000 \
  -e POLLING_INTERVAL=10 \
  -e AWS_REGION=us-east-1 \
  read-flags-service:latest

# OR Kubernetes deployment
kubectl apply -f read_flags_service/k8s-deployment.yaml
```

### Step 3: Deploy Atom Store Server

```bash
# Docker deployment
cd atom_store/server
docker build -t atom-store-service:latest .
docker run -d \
  --name atom-store-service \
  -p 3000:3000 \
  atom-store-service:latest

# OR Kubernetes deployment
kubectl apply -f atom_store/server/k8s-deployment.yaml
```

### Step 4: Integrate in React Applications

```bash
# Install dependencies
npm install @failover/atom-store recoil

# Use in your React components (see examples above)
```

### Step 5: Test the System

```bash
# Trigger failover via Ansible
ansible-playbook ansible-example/trigger-failover.yml

# Verify Kafka message
kafka-console-consumer --topic failover-events --from-beginning

# Check Lambda execution
aws logs tail /aws/lambda/failover-system-kafka-consumer --follow

# Verify DynamoDB update
aws dynamodb get-item \
  --table-name failover-status \
  --key '{"pk": {"S": "FAILOVER_STATUS"}, "sk": {"S": "CURRENT"}}'

# Monitor Read Flags Service
docker logs -f read-flags-service

# Check Atom Store
curl http://localhost:3000/api/failover/status
```

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

### Scalability
- **DynamoDB**: Auto-scaling with on-demand billing
- **Lambda**: Automatic scaling up to 1000 concurrent executions
- **Kafka**: Horizontal scaling with partitions
- **Read Flags Service**: Can be horizontally scaled
- **Atom Store Server**: Stateless, can be scaled horizontally

## Cost Considerations

### Monthly Cost Estimate (Moderate Traffic)

**AWS Services**:
- **Lambda**: ~$5-10/month (1M invocations)
- **DynamoDB**: ~$5-15/month (on-demand, moderate traffic)
- **CloudWatch**: ~$5/month (logs, metrics, alarms)
- **X-Ray**: ~$2/month (tracing)

**External Services**:
- **Kafka**: Varies by provider (AWS MSK: ~$200-500/month for small cluster)
- **Compute**: Docker/K8s hosting for Read Flags Service and Atom Store (~$50-200/month)

**Total Estimated Cost**: $270-730/month (includes Kafka cluster)

### Cost Optimization Tips
- Use DynamoDB on-demand billing (no capacity planning)
- Increase polling interval to reduce DynamoDB reads
- Consider DynamoDB Streams instead of polling (more cost-effective at scale)
- Use spot instances for Read Flags Service
- Monitor and adjust Lambda memory based on actual usage

## Monitoring

### Key Metrics

**Kafka Consumer Lambda**:
- Invocation count and errors
- Duration (p50, p99)
- Kafka consumer lag
- DynamoDB write throttles

**Read Flags Service**:
- Polling frequency
- DynamoDB read errors
- Atom Store update failures
- Change detection rate

**Atom Store Server**:
- Active WebSocket connections
- API request rate
- Update latency
- Connection errors

**DynamoDB**:
- Read/write capacity consumption
- Throttled requests
- Item count

### CloudWatch Alarms

When configured, the following alarms are created:
- Lambda function errors (threshold: 5 errors per 5 minutes)
- Lambda high duration (threshold: 60 seconds)
- Lambda throttles (any occurrence)
- DynamoDB throttles (any occurrence)
- DLQ messages (any message in dead letter queue)

### Monitoring Commands

```bash
# Lambda logs
aws logs tail /aws/lambda/failover-system-kafka-consumer --follow

# Read Flags Service logs
docker logs -f read-flags-service
kubectl logs -f deployment/read-flags-service

# Atom Store logs
docker logs -f atom-store-service
kubectl logs -f deployment/atom-store-service

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
5. Verify AWS credentials are configured

### Atom Store Not Receiving Updates

**Symptoms**: Angular apps not showing failover status

**Checks**:
1. Verify Atom Store Server is running:
   ```bash
   curl http://localhost:3000/health
   ```
2. Check Read Flags Service can reach Atom Store
3. Verify WebSocket connections are established
4. Check browser console for errors

### Applications Not Showing Failover

**Symptoms**: UI not updating with failover status

**Checks**:
1. Verify application is subscribed to correct failover status
2. Check Failover Service is initialized
3. Verify WebSocket connection is active
4. Check browser console for errors
5. Verify Angular service is properly injected

### High Latency

**Symptoms**: Updates taking longer than expected (>30 seconds)

**Solutions**:
1. Reduce polling interval in Read Flags Service
2. Check Kafka consumer lag
3. Review Lambda duration in CloudWatch
4. Consider using DynamoDB Streams instead of polling
5. Check network latency between services

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

### Best Practices
- Rotate credentials regularly
- Monitor authentication failures
- Review IAM policies periodically
- Enable AWS CloudTrail for API auditing
- Use AWS Config for compliance monitoring

## References

- [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md) - Complete deployment guide
- [SYSTEM_OVERVIEW.md](SYSTEM_OVERVIEW.md) - System architecture overview
- [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) - Deployment checklist
- [README.md](README.md) - Complete system documentation
- `angular-client-example/` - Angular integration examples
- `ansible-example/` - Ansible failover trigger examples
- [AWS Lambda Documentation](https://docs.aws.amazon.com/lambda/)
- [Amazon DynamoDB Documentation](https://docs.aws.amazon.com/dynamodb/)
- [Angular Documentation](https://angular.io/docs)
- [RxJS Documentation](https://rxjs.dev/)
- [Apache Kafka Documentation](https://kafka.apache.org/documentation/)
