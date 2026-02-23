# Failover Status Management - Quick Start Guide

Get the failover status management system up and running in minutes.

## What This Project Does

This system provides real-time failover status management for Angular applications using:
- **Kafka** for event ingestion
- **AWS Lambda** for event processing
- **DynamoDB** as the source of truth
- **Atom Stores** for reactive state management with WebSocket

**Result**: Angular applications automatically display failover banners when infrastructure issues are detected.

## Prerequisites

- AWS Account with CLI configured
- Terraform 1.0+
- Python 3.11+
- Node.js 20+
- Docker (optional)
- Kafka cluster
- Ansible 2.9+

## 5-Minute Setup

### 1. Build Lambda Functions

```bash
./build.sh
```

### 2. Deploy AWS Infrastructure

```bash
# Configure
cat > terraform.tfvars <<EOF
aws_region = "us-east-1"
lambda_function_name = "failover-system"
dynamodb_table_name = "failover-status"
EOF

# Deploy
terraform init
terraform apply -auto-approve
```

### 3. Configure Kafka Integration

```bash
# Get Lambda ARN
LAMBDA_ARN=$(terraform output -raw kafka_consumer_lambda_arn)

# Create event source mapping
aws lambda create-event-source-mapping \
  --function-name $LAMBDA_ARN \
  --event-source-arn arn:aws:kafka:REGION:ACCOUNT:cluster/CLUSTER_NAME \
  --topics failover-events \
  --starting-position LATEST
```

### 4. Deploy Read Flags Service

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

### 5. Deploy Atom Store Server

```bash
cd atom_store/server
docker build -t atom-store-service:latest .
docker run -d \
  --name atom-store-service \
  -p 3000:3000 \
  atom-store-service:latest
```

### 6. Integrate in Angular App

```bash
# No additional packages needed - uses built-in Angular features
```

```typescript
// failover.service.ts
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
  
  constructor(private ngZone: NgZone) {}

  connect(atomStoreUrl: string): void {
    this.ws = new WebSocket(atomStoreUrl);
    this.ws.onopen = () => {
      this.ngZone.run(() => {
        console.log('Connected to Atom Store');
        this.fetchCurrentStatus(atomStoreUrl);
      });
    };
    this.ws.onmessage = (event) => {
      this.ngZone.run(() => {
        const data = JSON.parse(event.data);
        this.updateFailoverStatus(data);
      });
    };
  }

  private async fetchCurrentStatus(atomStoreUrl: string): Promise<void> {
    const httpUrl = atomStoreUrl.replace('ws://', 'http://').replace('wss://', 'https://');
    const response = await fetch(`${httpUrl}/api/failover/status`);
    const data = await response.json();
    const statusMap = new Map<string, FailoverStatus>();
    Object.entries(data).forEach(([appId, status]) => {
      statusMap.set(appId, status as FailoverStatus);
    });
    this.failoverStatus.next(statusMap);
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

  disconnect(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}

// app.component.ts
import { Component, OnInit } from '@angular/core';
import { FailoverService } from './failover.service';

@Component({
  selector: 'app-root',
  template: `<app-my-component></app-my-component>`
})
export class AppComponent implements OnInit {
  constructor(private failoverService: FailoverService) {}

  ngOnInit(): void {
    this.failoverService.connect('ws://atom-store-service:3000');
  }
}

// my-component.ts
import { Component, OnInit, OnDestroy } from '@angular/core';
import { Subscription } from 'rxjs';
import { FailoverService, FailoverStatus } from './failover.service';

@Component({
  selector: 'app-my-component',
  template: `
    <div *ngIf="failoverStatus?.failoverActive">
      ⚠️ System is in failover mode: {{ failoverStatus.reason }}
    </div>
    <div *ngIf="!failoverStatus?.failoverActive">Normal operation</div>
  `
})
export class MyComponent implements OnInit, OnDestroy {
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

### 7. Test the System

```bash
# Trigger failover
ansible-playbook ansible-example/trigger-failover.yml

# Verify Kafka message
kafka-console-consumer --topic failover-events --from-beginning

# Check Lambda execution
aws logs tail /aws/lambda/failover-system-kafka-consumer --follow

# Verify DynamoDB
aws dynamodb get-item \
  --table-name failover-status \
  --key '{"pk": {"S": "FAILOVER_STATUS"}, "sk": {"S": "CURRENT"}}'

# Check Atom Store
curl http://localhost:3000/api/failover/status
```

## Architecture Flow

```
Ansible → Kafka → Lambda → DynamoDB → Read Flags Service → Atom Store → Angular Apps
```

1. Ansible detects infrastructure issue
2. Sends event to Kafka
3. Lambda processes and writes to DynamoDB
4. Read Flags Service polls DynamoDB
5. Updates Atom Store when changes detected
6. Angular apps receive updates via WebSocket
7. UI automatically updates

## Key Endpoints

### Atom Store Server
- `GET /api/failover/status` - Get current status
- `POST /api/failover/update` - Update status (used by Read Flags Service)
- `GET /health` - Health check
- `WebSocket /` - Real-time updates

### AWS Resources
- Lambda: `failover-system-kafka-consumer`
- DynamoDB: `failover-status`
- CloudWatch: `/aws/lambda/failover-system-kafka-consumer`

## Monitoring

```bash
# View CloudWatch dashboard
terraform output cloudwatch_dashboard_url

# Lambda logs
aws logs tail /aws/lambda/failover-system-kafka-consumer --follow

# Read Flags Service logs
docker logs -f read-flags-service

# Atom Store logs
docker logs -f atom-store-service
```

## Troubleshooting

### No updates in Angular app?
1. Check Atom Store is running: `curl http://localhost:3000/health`
2. Check Read Flags Service logs: `docker logs read-flags-service`
3. Verify WebSocket connection in browser console
4. Check Failover Service is initialized in Angular app

### Lambda not processing Kafka events?
1. Check event source mapping: `aws lambda list-event-source-mappings`
2. Verify Kafka cluster connectivity
3. Check Lambda logs for errors

### DynamoDB not updating?
1. Check Lambda has correct IAM permissions
2. Verify event format from Kafka
3. Check Lambda logs for validation errors

## Next Steps

- Review [ARCHITECTURE.md](ARCHITECTURE.md) for detailed architecture
- See [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md) for complete deployment guide
- Check [angular-client-example/](angular-client-example/) for more Angular examples
- Configure monitoring and alerting
- Set up CI/CD pipelines
- Add authentication to Atom Store API

## Configuration Options

### Reduce Latency
- Decrease `POLLING_INTERVAL` to 5 seconds
- Use DynamoDB Streams instead of polling
- Scale Read Flags Service horizontally

### Optimize Costs
- Increase `POLLING_INTERVAL` to 30 seconds
- Use DynamoDB on-demand billing (already configured)
- Implement caching in Read Flags Service

## Support

For detailed documentation, see:
- [README.md](README.md) - Complete system documentation
- [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md) - Step-by-step deployment
- [SYSTEM_OVERVIEW.md](SYSTEM_OVERVIEW.md) - Architecture diagrams
- [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) - Deployment checklist
