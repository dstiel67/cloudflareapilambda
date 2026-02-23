# Failover Status Management System with Real-Time Notifications

## System Overview

This project provides a complete solution for tracking and broadcasting failover status across multiple applications. The system uses DynamoDB as the source of truth, with Atom stores providing reactive state management for real-time updates to subscribed applications.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          Application Layer                              │
│                                                                         │
│  ┌──────────────┐                                    ┌──────────────┐   │
│  │    App 1     │─────Subscribe to Failover Atom────▶│              │   │
│  │              │                                    │              │   │
│  └──────────────┘                                    │              │   │
│                                                      │   Failover   │   │
│  ┌──────────────┐                                    │   Atom Store │   │
│  │    App 2     │─────Subscribe to Failover Atom────▶│              │   │
│  │              │                                    │  ┌─────────┐ │   │
│  └──────────────┘                                    │  │ App 1   │ │   │
│                                                      │  │ Failover│ │   │
│  ┌──────────────┐                                    │  │  Flag   │ │   │
│  │    App N     │─────Subscribe to Failover Atom────▶│  └─────────┘ │   │
│  │              │                                    │  ┌─────────┐ │   │
│  └──────────────┘                                    │  │ App 2   │ │   │
│                                                      │  │ Failover│ │   │
│                                                      │  │  Flag   │ │   │
│                                                      │  └─────────┘ │   │
│                                                      └──────────────┘   │
│                                                             ▲           │
│                                                             │           │
│                       ┌─────────────────────────────────────┘           │
│                       │                                                 │
│              ┌────────────────────┐                                     │
│              │  Read Flags Service│                                     │
│              │  (Polls DynamoDB)  │                                     │
│              └────────────────────┘                                     │
│                       ▲                                                 │
└───────────────────────┼─────────────────────────────────────────────────┘
                        │
                        │ Read Flags
                        │
              ┌─────────▼──────────┐
              │                    │
              │     DynamoDB       │
              │  (Source of Truth) │
              │                    │
              │  {                 │
              │   App1_Failover:"Y"│
              │   App2_Failover:"Y"│
              │  }                 │
              │                    │
              └─────────▲──────────┘
                        │
                        │ Update Flags
                        │
              ┌─────────┴──────────┐
              │                    │
              │   Lambda Function  │
              │  (Update Handler)  │
              │                    │
              └─────────▲──────────┘
                        │
                        │ Failover Event
                        │
              ┌─────────┴──────────┐
              │                    │
              │       Kafka        │
              │   (Event Stream)   │
              │                    │
              └─────────▲──────────┘
                        │
                        │ Trigger Failover
                        │
              ┌─────────┴──────────┐
              │                    │
              │  Ansible Script    │
              │ (Failover Control) │
              │                    │
              └────────────────────┘


┌──────────────────────────────────────────────────────────────────────────┐
│                         Legend                                           │
│                                                                          │
│  ┌─────────────┐  Light Blue = Atom (Reactive State)                     │
│  │    Atom     │                                                         │
│  └─────────────┘                                                         │
│                                                                          │
│  ┌─────────────┐  Dark Blue = Store (Container for Atoms)                │
│  │    Store    │                                                         │
│  └─────────────┘                                                         │
└──────────────────────────────────────────────────────────────────────────┘
```

## Components

### Core Components (Always Deployed)

#### 1. Update API Lambda
- **Purpose**: REST API endpoint for updating redirect/failover status
- **Trigger**: API Gateway HTTP requests
- **Key Feature**: API key authentication, audit trail
- **Output**: Updates DynamoDB with new status

#### 2. DynamoDB Table (Source of Truth)
- **Purpose**: Stores current redirect/failover status
- **Schema**: Key-value pairs with timestamps and metadata
- **Key Feature**: Single source of truth, Streams enabled
- **Billing**: Pay-per-request (on-demand)

#### 3. DynamoDB Streams
- **Purpose**: Captures all changes to DynamoDB table
- **Trigger**: Any INSERT, MODIFY, or REMOVE operation
- **Key Feature**: Near real-time change data capture
- **Output**: Triggers Notification Lambda

#### 4. Notification Lambda
- **Purpose**: Processes DynamoDB Stream events
- **Trigger**: DynamoDB Streams
- **Key Feature**: Transforms stream records to SSE format
- **Output**: Writes to SSE Messages Table

#### 5. SSE Endpoint Lambda
- **Purpose**: Provides Server-Sent Events endpoint
- **Trigger**: API Gateway HTTP requests (long-polling)
- **Key Feature**: Real-time push notifications to web clients
- **Output**: Streams events to connected clients

#### 6. SSE Messages Table
- **Purpose**: Temporary storage for Server-Sent Event messages
- **TTL**: 1 hour (automatic cleanup)
- **Key Feature**: Decouples notification generation from delivery
- **Access**: Read by SSE Endpoint Lambda

#### 7. Kafka Consumer Lambda
- **Purpose**: Processes Kafka failover events and updates DynamoDB
- **Trigger**: Kafka messages (when configured)
- **Key Feature**: Validates and transforms Kafka events
- **Output**: Updates DynamoDB with failover flags
- **Status**: Deployed but inactive until Kafka cluster is configured

#### 8. API Gateways
- **Purpose**: HTTP endpoints for Update API and SSE
- **Key Feature**: CORS enabled, API key authentication
- **Endpoints**: 
  - Update API: POST/GET /redirect-status
  - SSE API: GET /events

#### 9. Dead Letter Queues (DLQs)
- **Purpose**: Captures failed Lambda invocations
- **Key Feature**: Automatic alerting on message arrival
- **Monitoring**: CloudWatch alarms

#### 10. CloudWatch Monitoring
- **Purpose**: Logs, metrics, dashboards, and alarms
- **Key Feature**: Custom dashboards, configurable alerts
- **Retention**: 14 days for logs

#### 11. X-Ray Tracing
- **Purpose**: Performance monitoring and debugging
- **Key Feature**: Distributed tracing across all Lambdas
- **Access**: AWS X-Ray console

### Optional Components (Pattern 2 Only)

#### 12. Read Flags Service
- **Purpose**: Polls DynamoDB for current failover flags
- **Trigger**: Periodic polling (5-30 seconds configurable)
- **Key Feature**: Detects changes in failover status
- **Output**: Updates Atom Store when flags change
- **Deployment**: Docker, Kubernetes, or direct Python execution
- **Status**: Optional - only needed for Pattern 2 (React/Atom Store)

#### 13. Atom Store Server
- **Purpose**: REST API and WebSocket server for React apps
- **Technology**: Node.js/TypeScript
- **Key Feature**: Real-time updates via WebSocket, reactive state management
- **Deployment**: Docker, Kubernetes, or direct Node.js execution
- **Status**: Optional - only needed for Pattern 2 (React/Atom Store)

#### 14. Atom Store Library
- **Purpose**: React/Recoil integration library
- **Technology**: TypeScript, Recoil atoms
- **Key Feature**: Provides hooks for subscribing to failover status
- **Integration**: npm package for React applications
- **Status**: Optional - only needed for Pattern 2 (React/Atom Store)

### Legacy Components (Optional)

#### 15. Cloudflare Sync Lambda
- **Purpose**: One-time data migration from Cloudflare KV
- **Trigger**: Manual invocation or scheduled
- **Key Feature**: Syncs data from Cloudflare KV to DynamoDB
- **Status**: Optional - only for legacy data migration
- **Secrets**: Requires Cloudflare API credentials in Secrets Manager

#### 16. Ansible Script (External)
- **Purpose**: Initiates failover events based on infrastructure monitoring
- **Trigger**: Infrastructure failure detection, manual failover
- **Output**: Sends failover event to Kafka
- **Status**: Optional - only for Pattern 2 with Kafka integration

#### 17. Kafka Cluster (External)
- **Purpose**: Message broker for failover events
- **Key Feature**: Decouples failover control from status updates
- **Consumers**: Kafka Consumer Lambda
- **Status**: Optional - only for Pattern 2 deployments

## Data Flow

1. **Failover Triggered**: Ansible script detects infrastructure issue or receives manual trigger
2. **Event Published**: Ansible sends failover event to Kafka with app identifiers and status
3. **Lambda Consumes**: Lambda function consumes Kafka message
4. **Validation**: Lambda validates event data and transforms to DynamoDB format
5. **DynamoDB Update**: Lambda updates failover flags in DynamoDB (e.g., `App1_Failover: "Y"`)
6. **Polling**: Read Flags Service periodically polls DynamoDB for changes
7. **Atom Update**: When flags change, Read Flags Service updates corresponding atoms in Failover Atom Store
8. **Reactive Propagation**: All applications subscribed to changed atoms automatically receive updates
9. **UI Update**: Applications react to atom changes and update their UI (show banners, redirect, etc.)

## Event Types

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
  "App1_Failover": "Y",
  "App2_Failover": "Y",
  "App1_LastUpdated": "2024-01-15T10:30:00Z",
  "App2_LastUpdated": "2024-01-15T10:30:00Z",
  "UpdatedBy": "ansible_monitoring"
}
```

### Atom State (in Failover Atom Store)
```javascript
// App 1 Failover Atom
{
  appId: "app1",
  failoverActive: true,
  lastUpdated: "2024-01-15T10:30:00Z",
  reason: "Primary datacenter unavailable"
}

// App 2 Failover Atom
{
  appId: "app2",
  failoverActive: true,
  lastUpdated: "2024-01-15T10:30:00Z",
  reason: "Primary datacenter unavailable"
}
```

## Deployment

### Prerequisites
- AWS CLI configured
- Terraform installed
- Python 3.11+
- Kafka cluster configured
- Ansible playbooks for failover control
- Frontend applications with Atom state management (Recoil/Jotai/etc.)

### Quick Deploy
```bash
# Build all Lambda packages
./build.sh

# Deploy infrastructure
terraform init
terraform apply

# Configure Kafka integration
# (Add Lambda as Kafka consumer)

# Deploy Read Flags Service
# (Configure polling interval and DynamoDB connection)

# Integrate Atom Store in applications
# (Subscribe to failover atoms)
```

### Testing the Complete Flow

1. **Trigger failover via Ansible**:
   ```bash
   ansible-playbook trigger-failover.yml --extra-vars "app=app1 status=Y"
   ```

2. **Verify Kafka message**:
   ```bash
   kafka-console-consumer --topic failover-events --from-beginning
   ```

3. **Check Lambda execution**:
   ```bash
   aws logs tail "/aws/lambda/failover-update-handler" --follow
   ```

4. **Verify DynamoDB update**:
   ```bash
   aws dynamodb get-item \
     --table-name failover-status \
     --key '{"pk": {"S": "App1_Failover"}}'
   ```

5. **Monitor Read Flags Service**:
   ```bash
   # Check service logs for polling activity
   kubectl logs -f read-flags-service-pod
   ```

6. **Observe application updates**:
   - Open App 1 in browser
   - Watch for failover banner/redirect
   - Check browser console for atom state changes

## Monitoring

### CloudWatch Logs
- `/aws/lambda/failover-update-handler` - Lambda processing Kafka events
- `/aws/lambda/read-flags-service` - Polling service logs (if Lambda-based)

### Key Metrics
- Lambda invocations and errors
- Kafka consumer lag
- DynamoDB read/write capacity
- Read Flags Service polling frequency
- Atom update latency
- Application subscription count

### Alarms
- Lambda function errors
- Kafka consumer lag exceeds threshold
- DynamoDB throttling
- Read Flags Service polling failures
- High Lambda duration

## Security

### IAM Permissions
- **Update Lambda**: DynamoDB write, read
- **Notification Lambda**: DynamoDB Stream read, SSE table write
- **SSE Lambda**: SSE table read/write
- **Legacy Sync Lambda**: DynamoDB write, Secrets Manager read (optional)

### Network Security
- API Gateways with CORS enabled
- No VPC required (uses AWS managed services)
- Secrets stored in AWS Secrets Manager
- Public endpoints (consider adding authentication)

### Data Security
- Cloudflare credentials encrypted in Secrets Manager (only if using legacy sync)
- DynamoDB encryption at rest (default)
- TTL on SSE messages (1 hour)
- Audit trail with timestamps and user tracking
- No secrets needed for primary system components (Update API, Notification, SSE)

## Performance

### Latency
- **Ansible to Kafka**: ~10-50ms (event publishing)
- **Kafka to Lambda**: ~100-500ms (consumer lag)
- **Lambda to DynamoDB**: ~50-100ms (write operation)
- **DynamoDB to Read Flags**: Depends on polling interval (5-30 seconds typical)
- **Read Flags to Atom Update**: ~10-50ms (state update)
- **Atom to Application**: ~1-10ms (reactive subscription)
- **Total end-to-end**: ~5-30 seconds (dominated by polling interval)

### Optimization Options
- **Reduce polling interval**: Faster updates but higher DynamoDB read costs
- **Use DynamoDB Streams**: Near real-time updates (~100-500ms) instead of polling
- **WebSocket instead of polling**: Push-based updates for sub-second latency
- **Kafka Streams**: Process events in real-time before DynamoDB

### Scalability
- **DynamoDB**: Auto-scaling with on-demand billing
- **Lambda**: Automatic scaling up to 1000 concurrent executions
- **Kafka**: Horizontal scaling with partitions
- **Atom Store**: Client-side, scales with number of applications
- **Read Flags Service**: Can be horizontally scaled if needed

### Cost Optimization
- Pay-per-request DynamoDB billing
- Lambda charged per invocation and duration
- Kafka costs depend on cluster size and throughput
- Polling frequency directly impacts DynamoDB read costs
- Consider DynamoDB Streams for cost-effective real-time updates

## Troubleshooting

### Common Issues

1. **No atom updates in applications**:
   - Check Read Flags Service is running and polling
   - Verify DynamoDB table has correct data
   - Check atom subscriptions are properly configured
   - Verify Read Flags Service can reach DynamoDB

2. **Kafka events not processed**:
   - Check Lambda is subscribed to correct Kafka topic
   - Verify Kafka consumer group configuration
   - Check Lambda execution logs for errors
   - Verify network connectivity to Kafka cluster

3. **DynamoDB not updating**:
   - Check Lambda has correct IAM permissions
   - Verify event format from Kafka is correct
   - Check Lambda logs for validation errors
   - Ensure DynamoDB table exists and is accessible

4. **Slow failover propagation**:
   - Reduce Read Flags Service polling interval
   - Consider using DynamoDB Streams instead of polling
   - Check for network latency issues
   - Monitor Lambda cold starts

5. **Ansible failover trigger fails**:
   - Verify Kafka cluster is accessible
   - Check Ansible playbook configuration
   - Verify Kafka topic exists
   - Check authentication credentials

### Debug Commands

```bash
# Check Kafka topic
kafka-topics --list --bootstrap-server localhost:9092

# Monitor Kafka messages
kafka-console-consumer --topic failover-events --from-beginning

# Check Lambda logs
aws logs tail "/aws/lambda/failover-update-handler" --follow

# Query DynamoDB
aws dynamodb scan --table-name failover-status

# Check Lambda function
aws lambda get-function --function-name failover-update-handler

# Test Lambda manually
aws lambda invoke \
  --function-name failover-update-handler \
  --payload '{"app":"app1","status":"Y"}' \
  response.json
```

## Future Enhancements

### Potential Improvements
- **DynamoDB Streams instead of polling**: Near real-time updates (~100-500ms latency)
- **WebSocket connections**: Push-based updates instead of polling
- **GraphQL subscriptions**: Real-time updates with better query flexibility
- **Multi-region failover**: Geographic redundancy for failover system itself
- **Failover history**: Track and visualize failover events over time
- **Automated rollback**: Automatic recovery when primary systems restore
- **Health checks**: Automated failover based on application health metrics
- **Gradual failover**: Percentage-based traffic shifting
- **A/B testing integration**: Use failover flags for feature flags
- **Audit logging**: Comprehensive tracking of all failover events

### Scaling Considerations
- **Replace polling with DynamoDB Streams**: More efficient and real-time
- **Use Kafka Streams**: Process events before storing in DynamoDB
- **Implement caching**: Redis/ElastiCache for frequently accessed flags
- **Add CloudFront**: Global distribution for Read Flags Service
- **Horizontal scaling**: Multiple Read Flags Service instances
- **Event sourcing**: Store complete event history for replay/audit

## Support

For issues or questions:
1. Check CloudWatch Logs for detailed error information
2. Review Terraform outputs for correct endpoint URLs
3. Test individual components in isolation
4. Verify IAM permissions and resource configurations