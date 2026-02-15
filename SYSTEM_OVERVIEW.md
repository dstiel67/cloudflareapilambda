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

### 1. Ansible Script (Failover Control)
- **Purpose**: Initiates failover events based on infrastructure monitoring or manual triggers
- **Trigger**: Infrastructure failure detection, manual failover, scheduled maintenance
- **Output**: Sends failover event to Kafka with application identifiers and status

### 2. Kafka (Event Stream)
- **Purpose**: Message broker for failover events
- **Key Feature**: Decouples failover control from status updates
- **Consumers**: Lambda function subscribes to failover events

### 3. Lambda Function (`redirect-status-update` or similar)
- **Purpose**: Processes Kafka events and updates DynamoDB
- **Trigger**: Kafka messages containing failover events
- **Key Feature**: Validates and transforms failover data
- **Output**: Updates DynamoDB with new failover flags

### 4. DynamoDB Table (Source of Truth)
- **Purpose**: Stores current failover status for all applications
- **Schema**: Key-value pairs like `App1_Failover: "Y"`, `App2_Failover: "Y"`
- **Key Feature**: Single source of truth for failover state
- **Polling**: Read Flags Service polls this table

### 5. Read Flags Service
- **Purpose**: Polls DynamoDB for current failover flags
- **Trigger**: Periodic polling (e.g., every 5-30 seconds)
- **Key Feature**: Detects changes in failover status
- **Output**: Updates Atom Store when flags change

### 6. Failover Atom Store
- **Purpose**: Reactive state container holding failover flags for all applications
- **Technology**: Likely Recoil, Jotai, or similar Atom-based state management
- **Structure**: 
  - Store (Dark Blue): Container for all failover atoms
  - Atoms (Light Blue): Individual reactive state for each app (App 1 Failover Flag, App 2 Failover Flag, etc.)
- **Key Feature**: Provides reactive subscriptions for applications

### 7. Applications (App 1, App 2, App N)
- **Purpose**: Frontend applications that need to react to failover status
- **Integration**: Subscribe to specific failover atoms
- **Behavior**: Automatically re-render/update when subscribed atom changes
- **Use Cases**: 
  - Display failover banners
  - Redirect users to backup systems
  - Disable features during failover
  - Show maintenance messages

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