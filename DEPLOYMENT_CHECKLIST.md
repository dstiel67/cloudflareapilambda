# Failover Status Management System - Deployment Checklist

Use this checklist to ensure all components are properly deployed and configured.

## Pre-Deployment

- [ ] AWS account configured with appropriate permissions
- [ ] Terraform installed (version 1.0+)
- [ ] Python 3.11+ installed
- [ ] Node.js 20+ installed
- [ ] Docker installed (for containerized deployments)
- [ ] Kafka cluster available and accessible
- [ ] Ansible installed (for failover triggers)

## AWS Infrastructure Deployment

### Lambda Functions

- [ ] Run `./build.sh` to build all Lambda packages
- [ ] Verify all zip files created:
  - [ ] `kafka_consumer_lambda.zip`
  - [ ] `update_lambda.zip` (optional)
  - [ ] `notification_lambda.zip` (optional)
  - [ ] `sse_lambda.zip` (optional)
  - [ ] `lambda_function.zip` (legacy, optional)

### Terraform Configuration

- [ ] Create/update `terraform.tfvars` with your settings
- [ ] Run `terraform init`
- [ ] Run `terraform plan` and review changes
- [ ] Run `terraform apply` and confirm
- [ ] Save Terraform outputs for later use
- [ ] **Retrieve API key**: `terraform output -raw update_api_key_value`
- [ ] **Store API key securely** (environment variable or secrets manager)

### DynamoDB

- [ ] Verify DynamoDB table created: `failover-status`
- [ ] Confirm table has correct schema (pk, sk)
- [ ] Test table access with AWS CLI

### Kafka Integration

- [ ] Configure Lambda event source mapping for Kafka
- [ ] Verify Kafka topic exists: `failover-events`
- [ ] Test Kafka connectivity from Lambda
- [ ] Confirm Lambda can consume messages

## Read Flags Service Deployment

### Docker Deployment

- [ ] Build Docker image: `docker build -t read-flags-service:latest .`
- [ ] Configure environment variables
- [ ] Run container with correct settings
- [ ] Verify container is running: `docker ps`
- [ ] Check logs: `docker logs read-flags-service`

### Kubernetes Deployment

- [ ] Apply K8s deployment: `kubectl apply -f k8s-deployment.yaml`
- [ ] Verify pods are running: `kubectl get pods`
- [ ] Check pod logs: `kubectl logs -f deployment/read-flags-service`
- [ ] Verify service is accessible

### Configuration

- [ ] Set `DYNAMODB_TABLE_NAME` environment variable
- [ ] Set `ATOM_STORE_URL` environment variable
- [ ] Set `POLLING_INTERVAL` (recommended: 10 seconds)
- [ ] Configure AWS credentials (IAM role or access keys)
- [ ] Test DynamoDB connectivity

## Atom Store Server Deployment

### Docker Deployment

- [ ] Build Docker image: `docker build -t atom-store-service:latest .`
- [ ] Run container on port 3000
- [ ] Verify container is running: `docker ps`
- [ ] Check logs: `docker logs atom-store-service`

### Kubernetes Deployment

- [ ] Apply K8s deployment: `kubectl apply -f k8s-deployment.yaml`
- [ ] Verify pods are running: `kubectl get pods`
- [ ] Check service: `kubectl get svc atom-store-service`
- [ ] Verify LoadBalancer or Ingress is configured

### Verification

- [ ] Test health endpoint: `curl http://localhost:3000/health`
- [ ] Test status endpoint: `curl http://localhost:3000/api/failover/status`
- [ ] Test WebSocket connection: `wscat -c ws://localhost:3000`
- [ ] Verify CORS is configured correctly

## Application Integration

### Atom Store Library

- [ ] Install dependencies: `npm install @failover/atom-store recoil`
- [ ] Setup RecoilRoot in application
- [ ] Initialize FailoverService with correct URL
- [ ] Implement useFailoverStatus hook in components
- [ ] Test failover banner display

### Testing

- [ ] Trigger test failover event
- [ ] Verify banner appears in application
- [ ] Check browser console for errors
- [ ] Test WebSocket reconnection
- [ ] Verify multiple apps can subscribe independently

## Ansible Configuration

### Installation

- [ ] Install Ansible: `pip install ansible`
- [ ] Install kafka-python: `pip install kafka-python`
- [ ] Configure Kafka bootstrap servers

### Testing

- [ ] Test Ansible playbook: `ansible-playbook trigger-failover.yml --check`
- [ ] Trigger test failover event
- [ ] Verify event appears in Kafka
- [ ] Check failover log file created

## End-to-End Testing

### Complete Flow Test

- [ ] **Retrieve API key**: `API_KEY=$(terraform output -raw update_api_key_value)`
- [ ] Trigger failover via Update API with API key
- [ ] Verify DynamoDB update: `aws dynamodb get-item ...`
- [ ] Monitor Read Flags Service logs
- [ ] Check Atom Store receives update
- [ ] Verify application displays failover banner
- [ ] Clear failover and verify banner disappears
- [ ] Test without API key (should fail with 403)
- [ ] Test with invalid API key (should fail with 403)

### Performance Testing

- [ ] Measure end-to-end latency (Ansible → Application)
- [ ] Test with multiple simultaneous failover events
- [ ] Verify system handles high message volume
- [ ] Check for memory leaks in long-running services
- [ ] Monitor CPU and memory usage

## Monitoring Setup

### CloudWatch

- [ ] Verify Lambda log groups created
- [ ] Check Lambda metrics in CloudWatch
- [ ] Set up CloudWatch alarms for errors
- [ ] Create custom dashboard for system overview

### Application Monitoring

- [ ] Monitor Kafka consumer lag
- [ ] Track DynamoDB read/write capacity
- [ ] Monitor Read Flags Service polling frequency
- [ ] Track Atom Store WebSocket connections
- [ ] Monitor application failover banner display rate

### Logging

- [ ] Configure centralized logging (optional)
- [ ] Set up log aggregation (ELK, Splunk, etc.)
- [ ] Create log retention policies
- [ ] Set up log-based alerts

## Security Hardening

### AWS

- [ ] Review IAM permissions (least privilege)
- [ ] Enable DynamoDB encryption at rest
- [ ] Configure VPC for Lambda (optional)
- [ ] Enable AWS CloudTrail for audit logging
- [ ] Rotate AWS access keys regularly

### Kafka

- [ ] Enable SASL/SSL authentication
- [ ] Configure ACLs for topic access
- [ ] Use encrypted connections
- [ ] Rotate Kafka credentials

### Atom Store

- [ ] Add authentication to API endpoints (if needed)
- [ ] Configure HTTPS/TLS
- [ ] Implement rate limiting
- [ ] Add request validation
- [ ] Enable CORS only for trusted origins

### Update API

- [ ] **API key authentication enabled** ✅
- [ ] Store API key securely (environment variables or secrets manager)
- [ ] Configure rate limiting (1000 req/s, 2000 burst) ✅
- [ ] Set usage quotas (1M req/month) ✅
- [ ] Monitor API Gateway metrics for auth failures
- [ ] Set up alarms for high 4XX error rates
- [ ] Document API key rotation procedure
- [ ] Test API key rotation process

### Network

- [ ] Configure firewalls
- [ ] Use private subnets where possible
- [ ] Implement network segmentation
- [ ] Enable VPC flow logs

## Documentation

- [ ] Document deployment procedures
- [ ] Create runbooks for common scenarios
- [ ] Document troubleshooting steps
- [ ] Create architecture diagrams
- [ ] Document API endpoints and formats
- [ ] Create user guides for applications

## Disaster Recovery

- [ ] Set up DynamoDB backups
- [ ] Document recovery procedures
- [ ] Test failover of Read Flags Service
- [ ] Test Atom Store high availability
- [ ] Create backup Kafka cluster (optional)
- [ ] Document rollback procedures

## Post-Deployment

- [ ] Notify stakeholders of deployment
- [ ] Schedule post-deployment review
- [ ] Monitor system for 24-48 hours
- [ ] Address any issues that arise
- [ ] Update documentation with lessons learned
- [ ] Plan for future enhancements

## Maintenance Tasks

### Daily

- [ ] Check CloudWatch for errors
- [ ] Monitor Kafka consumer lag
- [ ] Verify all services are running

### Weekly

- [ ] Review CloudWatch metrics
- [ ] Check DynamoDB capacity usage
- [ ] Review application logs
- [ ] Test failover trigger manually

### Monthly

- [ ] Review and optimize costs
- [ ] Update dependencies
- [ ] Review security configurations
- [ ] Test disaster recovery procedures
- [ ] Update documentation

## Rollback Plan

If deployment fails:

1. [ ] Stop Read Flags Service
2. [ ] Stop Atom Store Server
3. [ ] Remove Lambda event source mapping
4. [ ] Run `terraform destroy` (if needed)
5. [ ] Restore previous configuration
6. [ ] Document issues encountered
7. [ ] Plan remediation steps

## Success Criteria

- [ ] All Lambda functions deployed successfully
- [ ] DynamoDB table accessible and functional
- [ ] Kafka consumer processing events
- [ ] Read Flags Service polling DynamoDB
- [ ] Atom Store Server responding to requests
- [ ] Applications displaying failover status
- [ ] End-to-end latency < 30 seconds
- [ ] No errors in CloudWatch logs
- [ ] All monitoring and alerts configured
- [ ] Documentation complete and accurate

## Notes

Use this space to document any deployment-specific notes, issues, or customizations:

```
[Add your notes here]
```
