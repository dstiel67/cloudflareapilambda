#!/usr/bin/env python3
"""
Send a test failover event to Kafka.
Used for integration testing.
"""

import json
import sys
from datetime import datetime
from kafka import KafkaProducer

def send_test_event(bootstrap_servers='localhost:9092', topic='failover-events'):
    """Send a test failover event to Kafka"""
    
    # Create producer
    try:
        producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        print(f"✅ Connected to Kafka at {bootstrap_servers}")
    except Exception as e:
        print(f"❌ Failed to connect to Kafka: {e}")
        sys.exit(1)
    
    # Create test event
    event = {
        "event_type": "failover",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "applications": [
            {
                "app_id": "test-app-1",
                "failover_status": "Y",
                "reason": "Integration test"
            },
            {
                "app_id": "test-app-2",
                "failover_status": "Y",
                "reason": "Integration test"
            }
        ],
        "triggered_by": "test_script",
        "severity": "info"
    }
    
    # Send event
    try:
        future = producer.send(topic, event)
        result = future.get(timeout=10)
        
        print(f"✅ Event sent successfully!")
        print(f"   Topic: {topic}")
        print(f"   Partition: {result.partition}")
        print(f"   Offset: {result.offset}")
        print(f"\nEvent content:")
        print(json.dumps(event, indent=2))
        
    except Exception as e:
        print(f"❌ Failed to send event: {e}")
        sys.exit(1)
    finally:
        producer.close()

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Send test failover event to Kafka')
    parser.add_argument('--bootstrap-servers', default='localhost:9092',
                       help='Kafka bootstrap servers (default: localhost:9092)')
    parser.add_argument('--topic', default='failover-events',
                       help='Kafka topic (default: failover-events)')
    
    args = parser.parse_args()
    
    send_test_event(args.bootstrap_servers, args.topic)
