# Ansible Failover Trigger

This directory contains Ansible playbooks for triggering failover events in the failover status management system.

## Prerequisites

- Ansible 2.9+
- Python 3.7+
- kafka-python library
- Access to Kafka cluster

## Installation

```bash
# Install Ansible
pip install ansible

# Install required Python packages
pip install kafka-python
```

## Configuration

Set the Kafka bootstrap servers:

```bash
export KAFKA_BOOTSTRAP_SERVERS="kafka.example.com:9092"
```

## Usage

### Trigger Failover

Activate failover for all configured apps:

```bash
ansible-playbook trigger-failover.yml
```

### Trigger Failover for Specific App

```bash
ansible-playbook trigger-failover.yml \
  -e "failover_apps=[{app_id: 'app1', failover_status: 'Y', reason: 'Scheduled maintenance'}]"
```

### Clear Failover

Deactivate failover:

```bash
ansible-playbook trigger-failover.yml \
  -e "failover_apps=[{app_id: 'app1', failover_status: 'N', reason: 'Maintenance complete'}]"
```

### Multiple Apps

```bash
ansible-playbook trigger-failover.yml \
  -e "failover_apps=[{app_id: 'app1', failover_status: 'Y', reason: 'Datacenter issue'}, {app_id: 'app2', failover_status: 'Y', reason: 'Datacenter issue'}]"
```

## Event Format

The playbook sends events to Kafka in this format:

```json
{
  "event_type": "failover",
  "timestamp": "2024-01-15T10:30:00Z",
  "applications": [
    {
      "app_id": "app1",
      "failover_status": "Y",
      "reason": "Primary datacenter unavailable"
    }
  ],
  "triggered_by": "ansible_monitoring",
  "severity": "critical"
}
```

## Integration with Monitoring

You can integrate this playbook with monitoring systems:

### Nagios/Icinga

```bash
# In your check command
if [ $SERVICE_STATE == "CRITICAL" ]; then
  ansible-playbook /path/to/trigger-failover.yml
fi
```

### Prometheus Alertmanager

Create a webhook receiver that calls the playbook.

### AWS CloudWatch

Use CloudWatch Events to trigger the playbook via Lambda or EC2.

## Logging

Failover events are logged to `/var/log/failover-events.log` for audit purposes.

## Troubleshooting

### Kafka Connection Issues

```bash
# Test Kafka connectivity
kafka-console-producer --broker-list $KAFKA_BOOTSTRAP_SERVERS --topic failover-events
```

### Python Package Issues

```bash
# Reinstall kafka-python
pip install --upgrade kafka-python
```

### Verify Event Delivery

```bash
# Monitor Kafka topic
kafka-console-consumer --bootstrap-server $KAFKA_BOOTSTRAP_SERVERS --topic failover-events --from-beginning
```
