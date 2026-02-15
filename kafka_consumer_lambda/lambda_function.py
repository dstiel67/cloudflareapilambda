"""
AWS Lambda function for processing Kafka failover events.

This function:
1. Consumes failover events from Kafka
2. Validates and transforms event data
3. Updates DynamoDB with new failover flags
"""

import json
import logging
import boto3
import os
from typing import Dict, Any, List
from datetime import datetime, timezone

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for Kafka failover events.
    
    Args:
        event: Kafka event data containing failover messages
        context: Lambda runtime context
        
    Returns:
        Dict containing processing results
    """
    logger.info("Kafka failover event received")
    
    try:
        # Get DynamoDB table
        table_name = os.environ.get('DYNAMODB_TABLE_NAME', 'failover-status')
        table = dynamodb.Table(table_name)
        
        # Process Kafka records
        records_processed = 0
        records_failed = 0
        
        # Kafka events come in as records
        for record in event.get('records', {}).values():
            for kafka_record in record:
                try:
                    # Decode Kafka message
                    message = decode_kafka_message(kafka_record)
                    
                    # Process failover event
                    process_failover_event(table, message)
                    records_processed += 1
                    
                except Exception as e:
                    logger.error(f"Error processing record: {str(e)}")
                    records_failed += 1
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'success': True,
                'records_processed': records_processed,
                'records_failed': records_failed
            })
        }
        
    except Exception as e:
        logger.error(f"Error in Kafka consumer: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'error': str(e)
            })
        }


def decode_kafka_message(kafka_record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Decode Kafka message from base64.
    
    Args:
        kafka_record: Kafka record with base64 encoded value
        
    Returns:
        Decoded message as dict
    """
    import base64
    
    # Kafka messages are base64 encoded
    encoded_value = kafka_record.get('value', '')
    decoded_value = base64.b64decode(encoded_value).decode('utf-8')
    
    # Parse JSON
    message = json.loads(decoded_value)
    
    logger.info(f"Decoded Kafka message: {message}")
    return message


def process_failover_event(table: Any, message: Dict[str, Any]) -> None:
    """
    Process failover event and update DynamoDB.
    
    Args:
        table: DynamoDB table resource
        message: Failover event message
    """
    event_type = message.get('event_type')
    timestamp = message.get('timestamp', datetime.now(timezone.utc).isoformat())
    applications = message.get('applications', [])
    triggered_by = message.get('triggered_by', 'unknown')
    
    logger.info(f"Processing {event_type} event for {len(applications)} applications")
    
    # Build update expression for all applications
    update_items = {}
    
    for app in applications:
        app_id = app.get('app_id')
        failover_status = app.get('failover_status', 'N')
        reason = app.get('reason', '')
        
        if not app_id:
            logger.warning(f"Skipping application without app_id: {app}")
            continue
        
        # Normalize app_id to match expected format
        failover_key = f"{app_id}_Failover"
        timestamp_key = f"{app_id}_LastUpdated"
        reason_key = f"{app_id}_Reason"
        
        update_items[failover_key] = failover_status
        update_items[timestamp_key] = timestamp
        update_items[reason_key] = reason
    
    # Add metadata
    update_items['LastUpdatedBy'] = triggered_by
    update_items['LastEventTimestamp'] = timestamp
    
    # Update DynamoDB
    # Using a single item with all flags as attributes
    try:
        table.put_item(
            Item={
                'pk': 'FAILOVER_STATUS',
                'sk': 'CURRENT',
                **update_items
            }
        )
        logger.info(f"Successfully updated DynamoDB with {len(applications)} failover flags")
        
    except Exception as e:
        logger.error(f"Error updating DynamoDB: {str(e)}")
        raise


def validate_failover_status(status: str) -> bool:
    """
    Validate failover status value.
    
    Args:
        status: Status value to validate
        
    Returns:
        True if valid, False otherwise
    """
    return status.upper() in ['Y', 'N', 'YES', 'NO', 'TRUE', 'FALSE', '1', '0']


def normalize_failover_status(status: str) -> str:
    """
    Normalize failover status to Y/N.
    
    Args:
        status: Status value to normalize
        
    Returns:
        Normalized status (Y or N)
    """
    status_upper = status.upper()
    
    if status_upper in ['Y', 'YES', 'TRUE', '1']:
        return 'Y'
    else:
        return 'N'
