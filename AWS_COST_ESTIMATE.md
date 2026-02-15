# AWS Monthly Cost Estimate

## Executive Summary

**Estimated Monthly Cost: $14-25/month** (depending on usage)

This estimate is based on moderate usage patterns. Actual costs may vary based on your specific traffic patterns and usage.

---

## Detailed Cost Breakdown

### 1. AWS Lambda

**Components:**
- Kafka Consumer Lambda
- Update API Lambda
- Notification Lambda
- SSE Endpoint Lambda
- Legacy Cloudflare Sync Lambda (optional)

**Pricing:**
- **Requests**: $0.20 per 1 million requests
- **Duration**: $0.0000166667 per GB-second
- **Free Tier**: 1 million requests + 400,000 GB-seconds per month (permanent)

**Estimated Usage:**

| Function | Invocations/Month | Memory | Avg Duration | Cost |
|----------|-------------------|--------|--------------|------|
| Kafka Consumer | 100,000 | 512 MB | 500ms | $0.42 |
| Update API | 50,000 | 256 MB | 200ms | $0.13 |
| Notification | 50,000 | 256 MB | 300ms | $0.19 |
| SSE Endpoint | 10,000 | 256 MB | 5000ms | $0.21 |
| Legacy Sync | 1,000 | 512 MB | 2000ms | $0.17 |

**Lambda Subtotal: ~$1.12/month** (after free tier)

**Calculation Details:**
```
Kafka Consumer:
- Requests: 100,000 × $0.20/1M = $0.02
- Duration: 100,000 × 0.5s × 0.5GB × $0.0000166667 = $0.42
- Total: $0.44

Update API:
- Requests: 50,000 × $0.20/1M = $0.01
- Duration: 50,000 × 0.2s × 0.25GB × $0.0000166667 = $0.04
- Total: $0.05

(Most covered by free tier)
```

---

### 2. Amazon DynamoDB

**Tables:**
- Main table: `cloudflare-kv-data` (with Streams)
- SSE Messages table: `sse-messages` (with TTL)

**Pricing (On-Demand):**
- **Write Request Units**: $1.25 per million WRUs
- **Read Request Units**: $0.25 per million RRUs
- **Storage**: $0.25 per GB-month
- **Streams**: $0.02 per 100,000 read request units

**Estimated Usage:**

| Operation | Volume/Month | Cost |
|-----------|--------------|------|
| Write Requests | 200,000 | $0.25 |
| Read Requests | 1,000,000 | $0.25 |
| Storage (1 GB) | 1 GB | $0.25 |
| Streams Reads | 200,000 | $0.04 |

**DynamoDB Subtotal: ~$0.79/month**

**Notes:**
- On-demand billing scales automatically
- No minimum charges
- Point-in-time recovery: Free for first 35 days
- Backups: $0.10 per GB-month (if enabled)

---

### 3. Amazon API Gateway

**APIs:**
- Update API (REST API)
- SSE API (REST API)

**Pricing:**
- **REST API Requests**: $3.50 per million requests
- **Data Transfer Out**: $0.09 per GB (first 10 TB)
- **Free Tier**: 1 million API calls per month for 12 months (new accounts)

**Estimated Usage:**

| API | Requests/Month | Data Transfer | Cost |
|-----|----------------|---------------|------|
| Update API | 50,000 | 5 MB | $0.18 |
| SSE API | 10,000 | 50 MB | $0.04 |

**API Gateway Subtotal: ~$0.22/month** (after free tier)

**Calculation:**
```
Update API:
- Requests: 50,000 × $3.50/1M = $0.175
- Data: 5 MB × $0.09/GB = $0.0004
- Total: $0.18

SSE API:
- Requests: 10,000 × $3.50/1M = $0.035
- Data: 50 MB × $0.09/GB = $0.004
- Total: $0.04
```

**API Key Cost: $0** (API keys are free)

---

### 4. Amazon CloudWatch

**Components:**
- Logs
- Metrics
- Alarms
- Dashboard

**Pricing:**
- **Logs Ingestion**: $0.50 per GB
- **Logs Storage**: $0.03 per GB-month
- **Custom Metrics**: $0.30 per metric per month
- **Alarms**: $0.10 per alarm per month
- **Dashboards**: $3.00 per dashboard per month

**Estimated Usage:**

| Component | Volume | Cost |
|-----------|--------|------|
| Logs Ingestion | 1 GB/month | $0.50 |
| Logs Storage | 0.5 GB | $0.02 |
| Custom Metrics (10) | 10 metrics | $3.00 |
| Alarms (6) | 6 alarms | $0.60 |
| Dashboard (1) | 1 dashboard | $3.00 |

**CloudWatch Subtotal: ~$7.12/month**

**Free Tier:**
- 5 GB log ingestion
- 10 custom metrics
- 10 alarms
- 3 dashboards

**After Free Tier: ~$0.50/month** (if within free tier limits)

---

### 5. AWS X-Ray

**Pricing:**
- **Traces Recorded**: $5.00 per 1 million traces
- **Traces Retrieved**: $0.50 per 1 million traces
- **Free Tier**: 100,000 traces per month (permanent)

**Estimated Usage:**

| Operation | Volume/Month | Cost |
|-----------|--------------|------|
| Traces Recorded | 200,000 | $0.50 |
| Traces Retrieved | 10,000 | $0.01 |

**X-Ray Subtotal: ~$0.51/month** (after free tier)

**Note:** X-Ray can be disabled in production to save costs if not needed.

---

### 6. AWS Secrets Manager

**Pricing:**
- **Secret Storage**: $0.40 per secret per month
- **API Calls**: $0.05 per 10,000 API calls

**Estimated Usage:**

| Component | Volume | Cost |
|-----------|--------|------|
| Secrets (1) | 1 secret | $0.40 |
| API Calls | 50,000 | $0.25 |

**Secrets Manager Subtotal: ~$0.65/month**

**Note:** Only needed for legacy Cloudflare sync. Can be removed if not using that feature.

---

### 7. Amazon SQS (Dead Letter Queue)

**Purpose:** Capture failed Lambda invocations for retry and debugging

**Pricing:**
- **Standard Queue Requests**: $0.40 per 1 million requests (after free tier)
- **Data Transfer**: Included
- **Free Tier**: 1 million requests per month (permanent)

**Estimated Usage:**

| Component | Volume/Month | Cost |
|-----------|--------------|------|
| DLQ Messages (failures) | 1,000 | $0.00 |
| DLQ Reads (monitoring) | 10,000 | $0.00 |
| Message Storage | Minimal | $0.00 |

**SQS DLQ Subtotal: ~$0.00/month** (within free tier)

**Notes:**
- DLQ only receives messages on Lambda failures
- Typical failure rate: <0.1% of invocations
- Storage: First 1 GB free, then $0.40 per GB-month
- Message retention: 4-14 days (configurable)

**Cost if High Failure Rate (10,000 failures/month):**
- Requests: 10,000 × $0.40/1M = $0.004
- Still within free tier

---

### 8. Amazon MSK (Managed Kafka) - Optional

**Note:** This estimate assumes you're using an existing Kafka cluster or self-managed Kafka. If using Amazon MSK:

**Pricing:**
- **kafka.t3.small**: $0.038 per hour × 2 brokers = $55/month
- **Storage**: $0.10 per GB-month
- **Data Transfer**: $0.01 per GB

**MSK Cost: ~$60-100/month** (if using MSK)

**Alternative:** Use self-managed Kafka on EC2 or existing infrastructure to avoid this cost.

---

### 9. Data Transfer

**Pricing:**
- **Data Transfer Out to Internet**: $0.09 per GB (first 10 TB)
- **Data Transfer between AWS services in same region**: Free

**Estimated Usage:**

| Transfer Type | Volume/Month | Cost |
|---------------|--------------|------|
| API Gateway to Internet | 100 MB | $0.01 |
| Lambda to DynamoDB | Free | $0.00 |
| DynamoDB Streams | Free | $0.00 |

**Data Transfer Subtotal: ~$0.01/month**

---

## Total Monthly Cost Summary

### Scenario 1: Light Usage (Without MSK)

| Service | Monthly Cost |
|---------|--------------|
| Lambda | $1.12 |
| DynamoDB | $0.79 |
| API Gateway | $0.22 |
| CloudWatch | $0.50 |
| X-Ray | $0.51 |
| Secrets Manager | $0.65 |
| SQS DLQ | $0.00 |
| Data Transfer | $0.01 |
| **Total** | **~$3.80/month** |

### Scenario 2: Moderate Usage (Without MSK)

| Service | Monthly Cost |
|---------|--------------|
| Lambda (5M invocations) | $2.00 |
| DynamoDB (5M reads/writes) | $2.50 |
| API Gateway (1M requests) | $3.50 |
| CloudWatch (2 GB logs) | $1.00 |
| X-Ray (1M traces) | $5.00 |
| Secrets Manager | $0.65 |
| SQS DLQ | $0.00 |
| Data Transfer | $0.10 |
| **Total** | **~$14.75/month** |

### Scenario 3: High Usage (Without MSK)

| Service | Monthly Cost |
|---------|--------------|
| Lambda (20M invocations) | $8.00 |
| DynamoDB (20M reads/writes) | $10.00 |
| API Gateway (5M requests) | $17.50 |
| CloudWatch (5 GB logs) | $2.50 |
| X-Ray (5M traces) | $25.00 |
| Secrets Manager | $0.65 |
| SQS DLQ | $0.00 |
| Data Transfer | $0.50 |
| **Total** | **~$64.15/month** |

### Scenario 4: With Amazon MSK (Moderate Usage)

| Service | Monthly Cost |
|---------|--------------|
| Lambda | $2.00 |
| DynamoDB | $2.50 |
| API Gateway | $3.50 |
| CloudWatch | $1.00 |
| X-Ray | $5.00 |
| Secrets Manager | $0.65 |
| SQS DLQ | $0.00 |
| **Amazon MSK** | **$60.00** |
| Data Transfer | $0.10 |
| **Total** | **~$74.75/month** |

---

## Cost Optimization Recommendations

### Immediate Savings

1. **Disable X-Ray in Production** (if not needed)
   - Savings: ~$5/month
   - Keep enabled only for debugging

2. **Remove Secrets Manager** (if not using legacy sync)
   - Savings: ~$0.65/month
   - Only needed for Cloudflare credentials

3. **Reduce CloudWatch Log Retention**
   - Change from 14 days to 7 days
   - Savings: ~$0.25/month

4. **Use Lambda ARM64 (Graviton2)**
   - 20% cost savings on Lambda compute
   - Savings: ~$0.40/month

### Medium-term Savings

5. **Implement Caching**
   - Reduce DynamoDB reads by 50%
   - Savings: ~$1.25/month

6. **Optimize Lambda Memory**
   - Right-size based on actual usage
   - Potential savings: 10-30%

7. **Use Reserved Capacity** (if predictable load)
   - DynamoDB reserved capacity: 50% savings
   - Lambda provisioned concurrency: 40% savings

8. **Batch Operations**
   - Reduce API Gateway requests
   - Savings: ~$1-2/month

### Long-term Savings

9. **Use Compute Savings Plans**
   - 1-year commitment: 17% savings
   - 3-year commitment: 28% savings

10. **Implement Auto-scaling**
    - Scale down during off-peak hours
    - Potential savings: 20-40%

---

## Cost Monitoring

### Set Up AWS Budgets

```bash
aws budgets create-budget \
  --account-id YOUR_ACCOUNT_ID \
  --budget file://budget.json \
  --notifications-with-subscribers file://notifications.json
```

**budget.json:**
```json
{
  "BudgetName": "failover-system-budget",
  "BudgetLimit": {
    "Amount": "25",
    "Unit": "USD"
  },
  "TimeUnit": "MONTHLY",
  "BudgetType": "COST"
}
```

### CloudWatch Cost Metrics

Monitor these metrics:
- Lambda invocations
- DynamoDB consumed capacity
- API Gateway requests
- CloudWatch log volume

### Cost Allocation Tags

Tag all resources:
```terraform
tags = {
  Project     = "FailoverSystem"
  Environment = "Production"
  CostCenter  = "Engineering"
}
```

---

## Free Tier Benefits

### Permanent Free Tier

- **Lambda**: 1M requests + 400,000 GB-seconds per month
- **DynamoDB**: 25 GB storage + 25 WCU + 25 RCU
- **SQS**: 1M requests per month
- **CloudWatch**: 10 custom metrics + 10 alarms
- **X-Ray**: 100,000 traces per month

### 12-Month Free Tier (New Accounts)

- **API Gateway**: 1M API calls per month
- **CloudWatch Logs**: 5 GB ingestion + 5 GB storage
- **Data Transfer**: 15 GB per month

**Estimated Savings with Free Tier: $5-10/month**

---

## Cost Comparison by Architecture

### Current Architecture (Serverless)

**Monthly Cost: $14-25/month**

Pros:
- No idle costs
- Automatic scaling
- Minimal operational overhead
- Pay only for what you use

### Alternative: EC2-Based

**Monthly Cost: $50-150/month**

Components:
- EC2 instances (t3.medium × 2): $60/month
- Load balancer: $20/month
- EBS storage: $10/month
- Data transfer: $5/month

Cons:
- Higher base cost
- Manual scaling
- More operational overhead
- Costs even when idle

### Alternative: Container-Based (ECS/EKS)

**Monthly Cost: $70-200/month**

Components:
- ECS/EKS cluster: $70/month
- EC2 instances: $60/month
- Load balancer: $20/month
- Storage: $10/month

Cons:
- Higher complexity
- Higher base cost
- More operational overhead

**Conclusion:** Serverless architecture is the most cost-effective for this use case.

---

## Real-World Cost Examples

### Example 1: Small Team (10 users)

**Usage:**
- 10,000 failover events/month
- 50,000 API requests/month
- 100,000 Lambda invocations/month

**Monthly Cost: ~$5-8/month**

### Example 2: Medium Organization (100 users)

**Usage:**
- 100,000 failover events/month
- 500,000 API requests/month
- 1,000,000 Lambda invocations/month

**Monthly Cost: ~$14-20/month**

### Example 3: Large Enterprise (1000+ users)

**Usage:**
- 1,000,000 failover events/month
- 5,000,000 API requests/month
- 10,000,000 Lambda invocations/month

**Monthly Cost: ~$50-80/month**

---

## Cost Breakdown by Feature

| Feature | Monthly Cost | Can Disable? |
|---------|--------------|--------------|
| Core Lambda Functions | $1-2 | ❌ No |
| DynamoDB Storage | $1-3 | ❌ No |
| API Gateway | $0.50-4 | ❌ No |
| SQS Dead Letter Queue | $0.00 | ⚠️ Recommended |
| CloudWatch Logs | $0.50-2 | ⚠️ Reduce retention |
| X-Ray Tracing | $0.50-5 | ✅ Yes |
| Secrets Manager | $0.65 | ✅ Yes (if not using legacy) |
| Custom Metrics | $1-3 | ⚠️ Reduce count |
| Alarms | $0.60 | ⚠️ Reduce count |
| Dashboard | $3 | ⚠️ Optional |

---

## Summary

### Recommended Configuration (Moderate Usage)

**Estimated Monthly Cost: $14-25/month**

This includes:
- ✅ All core Lambda functions
- ✅ DynamoDB with Streams
- ✅ API Gateway with authentication
- ✅ SQS Dead Letter Queues (free within tier)
- ✅ CloudWatch monitoring
- ✅ X-Ray tracing (can disable to save $5/month)
- ✅ Secrets Manager (can remove if not using legacy sync)

### Cost-Optimized Configuration

**Estimated Monthly Cost: $8-12/month**

Optimizations:
- ❌ Disable X-Ray in production
- ❌ Remove Secrets Manager (if not needed)
- ⚠️ Reduce CloudWatch log retention to 7 days
- ⚠️ Use Lambda ARM64
- ⚠️ Implement caching

### Enterprise Configuration (High Availability)

**Estimated Monthly Cost: $50-100/month**

Includes:
- ✅ Multi-region deployment
- ✅ Enhanced monitoring
- ✅ Increased capacity
- ✅ Additional alarms
- ✅ Backup and disaster recovery

---

## Cost Tracking Tools

1. **AWS Cost Explorer** - Visualize spending patterns
2. **AWS Budgets** - Set spending alerts
3. **AWS Cost and Usage Reports** - Detailed cost analysis
4. **Third-party Tools**:
   - CloudHealth
   - CloudCheckr
   - Spot.io

---

## Conclusion

The serverless architecture provides excellent cost efficiency:

- **Low base cost**: ~$14-25/month for moderate usage
- **Scales automatically**: Pay only for what you use
- **No idle costs**: Unlike EC2-based solutions
- **Predictable**: Usage-based pricing
- **Optimizable**: Multiple cost reduction opportunities

For most use cases, this solution is **significantly cheaper** than traditional server-based architectures while providing better scalability and reliability.

---

## References

- [AWS Lambda Pricing](https://aws.amazon.com/lambda/pricing/)
- [Amazon DynamoDB Pricing](https://aws.amazon.com/dynamodb/pricing/)
- [Amazon API Gateway Pricing](https://aws.amazon.com/api-gateway/pricing/)
- [AWS CloudWatch Pricing](https://aws.amazon.com/cloudwatch/pricing/)
- [AWS X-Ray Pricing](https://aws.amazon.com/xray/pricing/)
- [AWS Free Tier](https://aws.amazon.com/free/)
- [AWS Cost Management](https://aws.amazon.com/aws-cost-management/)
