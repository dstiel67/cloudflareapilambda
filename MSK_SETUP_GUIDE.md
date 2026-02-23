# AWS MSK (Managed Streaming for Apache Kafka) Setup Guide

This guide explains how to deploy and configure AWS MSK for the failover status management system.

## Overview

The Terraform configuration in `msk.tf` creates a fully managed Kafka cluster with:
- VPC and networking (private subnets, security groups)
- MSK cluster with configurable broker nodes
- Encryption at rest (KMS) and in transit (TLS)
- CloudWatch logging
- Lambda event source mapping
- IAM policies for Lambda access

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         AWS VPC                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              MSK Cluster                             │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐          │   │
│  │  │ Broker 1 │  │ Broker 2 │  │ Broker 3 │          │   │
│  │  │  (AZ-1)  │  │  (AZ-2)  │  │  (AZ-3)  │          │   │
│  │  └──────────┘  └──────────┘  └──────────┘          │   │
│  │                                                      │   │
│  │  Topic: failover-events                             │   │
│  │  Partitions: 3                                      │   │
│  │  Replication: 2                                     │   │
│  └──────────────────────────────────────────────────────┘   │
│                           ▲                                  │
│                           │                                  │
│                  ┌────────┴────────┐                         │
│                  │ Lambda Function │                         │
│                  │ (Kafka Consumer)│                         │
│                  └─────────────────┘                         │
└─────────────────────────────────────────────────────────────┘
```

## Configuration Options

### Instance Types

Choose based on your throughput requirements:

| Instance Type | vCPU | RAM | Network | Cost/Month* | Use Case |
|--------------|------|-----|---------|-------------|----------|
| kafka.t3.small | 2 | 2 GB | Up to 5 Gbps | ~$50 | Dev/Test |
| kafka.m5.large | 2 | 8 GB | Up to 10 Gbps | ~$150 | Small Production |
| kafka.m5.xlarge | 4 | 16 GB | Up to 10 Gbps | ~$300 | Medium Production |
| kafka.m5.2xlarge | 8 | 32 GB | Up to 10 Gbps | ~$600 | Large Production |

*Per broker, approximate pricing for us-east-1

### Broker Nodes

- **Minimum**: 2 brokers (for high availability)
- **Recommended**: 3 brokers (for better fault tolerance)
- **Must be**: Multiple of availability zones

### Storage

- **Default**: 100 GB EBS per broker
- **Minimum**: 1 GB
- **Maximum**: 16,384 GB (16 TB)
- **Auto-scaling**: Not enabled by default (can be added)

## Deployment Steps

### 1. Configure Variables

Edit `terraform.tfvars`:

```hcl
# Enable MSK creation
create_msk_cluster = true

# MSK Configuration
msk_cluster_name           = "failover-events-cluster"
msk_kafka_version          = "3.5.1"
msk_instance_type          = "kafka.t3.small"  # Change for production
msk_number_of_broker_nodes = 2
msk_ebs_volume_size        = 100
```

### 2. Deploy Infrastructure

```bash
# Initialize Terraform (if not already done)
terraform init

# Review the plan
terraform plan

# Deploy (MSK creation takes 15-30 minutes)
terraform apply
```

### 3. Verify MSK Cluster

```bash
# Get cluster ARN
terraform output msk_cluster_arn

# Get bootstrap brokers
terraform output msk_bootstrap_brokers

# Check cluster status
aws kafka describe-cluster \
  --cluster-arn $(terraform output -raw msk_cluster_arn)
```

### 4. Verify Lambda Event Source Mapping

The Terraform automatically creates the event source mapping:

```bash
# List event source mappings
aws lambda list-event-source-mappings \
  --function-name $(terraform output -raw kafka_consumer_lambda_arn)

# Check mapping status (should be "Enabled")
aws lambda get-event-source-mapping \
  --uuid <UUID_FROM_ABOVE>
```

## Kafka Topic Configuration

The MSK cluster is configured to auto-create topics. The `failover-events` topic will be created automatically when the first message is published.

### Topic Settings (Auto-Created)

- **Name**: `failover-events`
- **Partitions**: 3 (default from MSK config)
- **Replication Factor**: 2
- **Retention**: 7 days (168 hours)

### Manual Topic Creation (Optional)

If you prefer to create the topic manually:

```bash
# Get bootstrap brokers
BOOTSTRAP_BROKERS=$(terraform output -raw msk_bootstrap_brokers)

# Create topic using Kafka CLI (requires Kafka tools installed)
kafka-topics.sh --create \
  --bootstrap-server $BOOTSTRAP_BROKERS \
  --topic failover-events \
  --partitions 3 \
  --replication-factor 2 \
  --config retention.ms=604800000
```

## Testing the Setup

### 1. Test Kafka Connectivity

```bash
# Get bootstrap brokers
BOOTSTRAP_BROKERS=$(terraform output -raw msk_bootstrap_brokers)

# List topics (requires Kafka tools)
kafka-topics.sh --list \
  --bootstrap-server $BOOTSTRAP_BROKERS
```

### 2. Send Test Message

```bash
# Using Kafka console producer
echo '{"event_type":"failover","timestamp":"2024-01-15T10:30:00Z","applications":[{"app_id":"app1","failover_status":"Y","reason":"Test"}],"triggered_by":"manual"}' | \
kafka-console-producer.sh \
  --bootstrap-server $BOOTSTRAP_BROKERS \
  --topic failover-events
```

### 3. Verify Lambda Processes Message

```bash
# Check Lambda logs
aws logs tail /aws/lambda/failover-system-kafka-consumer --follow

# Check DynamoDB for update
aws dynamodb get-item \
  --table-name failover-status \
  --key '{"pk": {"S": "FAILOVER_STATUS"}, "sk": {"S": "CURRENT"}}'
```

## Monitoring

### CloudWatch Metrics

MSK automatically publishes metrics to CloudWatch:

```bash
# View MSK metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Kafka \
  --metric-name BytesInPerSec \
  --dimensions Name=Cluster Name,Value=failover-events-cluster \
  --start-time 2024-01-15T00:00:00Z \
  --end-time 2024-01-15T23:59:59Z \
  --period 3600 \
  --statistics Average
```

### Key Metrics to Monitor

- **BytesInPerSec**: Incoming data rate
- **BytesOutPerSec**: Outgoing data rate
- **MessagesInPerSec**: Message rate
- **FetchConsumerTotalTimeMs**: Consumer fetch latency
- **ProduceLocalTimeMs**: Producer latency
- **UnderReplicatedPartitions**: Replication health
- **OfflinePartitionsCount**: Partition availability

### CloudWatch Logs

MSK broker logs are sent to CloudWatch:

```bash
# View MSK logs
aws logs tail /aws/msk/failover-events-cluster --follow
```

### Lambda Consumer Lag

Monitor Kafka consumer lag:

```bash
# Check event source mapping metrics
aws lambda get-event-source-mapping \
  --uuid <EVENT_SOURCE_MAPPING_UUID>
```

## Security

### Encryption

- **At Rest**: KMS encryption enabled
- **In Transit**: TLS encryption between brokers
- **Client-Broker**: TLS_PLAINTEXT (both TLS and plaintext allowed)

### Network Security

- **VPC**: Private subnets only
- **Security Group**: Restricts access to VPC CIDR
- **Public Access**: Disabled

### IAM Permissions

Lambda has the following MSK permissions:
- `kafka:DescribeCluster`
- `kafka:GetBootstrapBrokers`
- `kafka-cluster:Connect`
- `kafka-cluster:*Topic*`
- `kafka-cluster:ReadData`
- `kafka-cluster:WriteData`

## Cost Optimization

### Development/Testing

```hcl
msk_instance_type          = "kafka.t3.small"
msk_number_of_broker_nodes = 2
msk_ebs_volume_size        = 100
```

**Estimated Cost**: ~$100/month

### Production

```hcl
msk_instance_type          = "kafka.m5.large"
msk_number_of_broker_nodes = 3
msk_ebs_volume_size        = 500
```

**Estimated Cost**: ~$450/month

### Cost Reduction Tips

1. **Use t3.small for dev/test**: Significant savings for non-production
2. **Right-size storage**: Start with 100 GB, increase as needed
3. **Monitor usage**: Use CloudWatch to track actual utilization
4. **Consider Serverless**: AWS MSK Serverless for variable workloads
5. **Delete unused clusters**: Don't forget to destroy test clusters

## Troubleshooting

### MSK Cluster Creation Fails

**Issue**: Terraform times out or fails during MSK creation

**Solutions**:
- MSK creation takes 15-30 minutes - be patient
- Check AWS service limits for MSK
- Verify VPC has available IP addresses
- Check CloudWatch logs for errors

### Lambda Can't Connect to MSK

**Issue**: Lambda event source mapping shows errors

**Solutions**:
1. Verify Lambda has MSK IAM permissions
2. Check security group allows Lambda access
3. Verify Lambda is in same VPC as MSK (or has VPC peering)
4. Check MSK cluster is in "ACTIVE" state

### No Messages Being Consumed

**Issue**: Messages sent to Kafka but Lambda not triggered

**Solutions**:
1. Verify event source mapping is "Enabled"
2. Check topic name matches: `failover-events`
3. Verify messages are in correct format
4. Check Lambda logs for errors
5. Verify consumer group is not at end of topic

### High Latency

**Issue**: Messages take too long to process

**Solutions**:
1. Increase Lambda concurrency
2. Adjust batch size and batching window
3. Scale up MSK instance type
4. Add more broker nodes
5. Increase partition count

## Scaling

### Vertical Scaling (Larger Instances)

```bash
# Update instance type in terraform.tfvars
msk_instance_type = "kafka.m5.xlarge"

# Apply changes
terraform apply
```

**Note**: Requires cluster restart, plan for downtime

### Horizontal Scaling (More Brokers)

```bash
# Update broker count in terraform.tfvars
msk_number_of_broker_nodes = 3

# Apply changes
terraform apply
```

**Note**: Can be done without downtime

### Storage Scaling

```bash
# Update storage size in terraform.tfvars
msk_ebs_volume_size = 200

# Apply changes
terraform apply
```

**Note**: Can only increase, not decrease

## Disaster Recovery

### Backup Strategy

MSK doesn't have built-in backups. Consider:
1. **Topic Replication**: Use MirrorMaker for cross-region replication
2. **Message Retention**: Increase retention period
3. **Consumer Offsets**: Store offsets in DynamoDB for recovery

### Recovery Procedures

1. **Broker Failure**: MSK automatically replaces failed brokers
2. **AZ Failure**: Replicas in other AZs continue serving
3. **Region Failure**: Requires cross-region replication setup

## Cleanup

To destroy the MSK cluster:

```bash
# Set create_msk_cluster to false
# OR
terraform destroy -target=aws_msk_cluster.kafka_cluster

# Full cleanup
terraform destroy
```

**Warning**: This will permanently delete the Kafka cluster and all data!

## Alternative: Skip MSK Creation

If you want to use an external Kafka cluster:

```hcl
# In terraform.tfvars
create_msk_cluster = false
```

Then manually configure the Lambda event source mapping:

```bash
aws lambda create-event-source-mapping \
  --function-name failover-system-kafka-consumer \
  --event-source-arn arn:aws:kafka:REGION:ACCOUNT:cluster/YOUR_CLUSTER \
  --topics failover-events \
  --starting-position LATEST
```

## Additional Resources

- [AWS MSK Documentation](https://docs.aws.amazon.com/msk/)
- [MSK Pricing](https://aws.amazon.com/msk/pricing/)
- [Apache Kafka Documentation](https://kafka.apache.org/documentation/)
- [Lambda with MSK](https://docs.aws.amazon.com/lambda/latest/dg/with-msk.html)

## Support

For MSK-specific issues:
1. Check CloudWatch logs: `/aws/msk/failover-events-cluster`
2. Review MSK cluster status in AWS Console
3. Verify network connectivity and security groups
4. Check IAM permissions for Lambda
5. Monitor consumer lag metrics
