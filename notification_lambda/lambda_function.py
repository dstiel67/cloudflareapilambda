"""
AWS Lambda function for sending Server-Sent Events (SSE) notifications.

This function is triggered by DynamoDB Streams when the 'redirect-all-users-to-essentials' 
key is updated. It sends notifications to connected Angular web clients via SSE.
"""

import json
import logging
import boto3
import time
from typing import Dict, Any, List
from datetime import datetime, timezone

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
apigateway_management = None  # Will be initialized per request

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for DynamoDB Stream events.
    
    Processes DynamoDB Stream records and sends SSE notifications
    when 'redirect-all-users-to-essentials' key is updated.
    
    Args:
        event: DynamoDB Stream event data
        context: Lambda runtime context
        
    Returns:
        Dict containing processing results
    """
    logger.info(f"Processing DynamoDB Stream event with {len(event.get('Records', []))} records")
    
    processed_records = 0
    notifications_sent = 0
    errors = []
    
    try:
        # Process each DynamoDB Stream record
        for record in event.get('Records', []):
            try:
                processed_records += 1
                
                # Only process INSERT and MODIFY events
                event_name = record.get('eventName')
                if event_name not in ['INSERT', 'MODIFY']:
                    logger.debug(f"Skipping event type: {event_name}")
                    continue
                
                # Extract DynamoDB record data
                dynamodb_record = record.get('dynamodb', {})
                new_image = dynamodb_record.get('NewImage', {})
                
                # Check if this is the redirect-all-users-to-essentials key
                key_name = new_image.get('key_name', {}).get('S', '')
                if key_name != 'redirect-all-users-to-essentials':
                    logger.debug(f"Skipping non-target key: {key_name}")
                    continue
                
                logger.info(f"Processing update for key: {key_name}")
                
                # Extract the new value
                new_value = new_image.get('value', {}).get('S', '')
                retrieved_at = new_image.get('retrieved_at', {}).get('S', '')
                
                # Create notification payload
                notification = {
                    'type': 'redirect_status_update',
                    'data': {
                        'key': key_name,
                        'value': new_value,
                        'timestamp': retrieved_at or datetime.now(timezone.utc).isoformat(),
                        'event_type': event_name.lower()
                    },
                    'id': f"{int(time.time() * 1000)}",  # Unique event ID
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
                
                logger.info(f"Sending notification: {json.dumps(notification, default=str)}")
                
                # Send SSE notification
                success = await_send_sse_notification(notification)
                if success:
                    notifications_sent += 1
                else:
                    errors.append(f"Failed to send notification for key: {key_name}")
                
            except Exception as e:
                error_msg = f"Error processing record {processed_records}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
                continue
        
        # Log summary
        logger.info(f"Processing complete: {processed_records} records processed, "
                   f"{notifications_sent} notifications sent, {len(errors)} errors")
        
        # Return success response
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'DynamoDB Stream processing completed',
                'processed_records': processed_records,
                'notifications_sent': notifications_sent,
                'errors': errors
            })
        }
        
    except Exception as e:
        error_msg = f"Fatal error in lambda_handler: {str(e)}"
        logger.error(error_msg)
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'DynamoDB Stream processing failed',
                'error': error_msg,
                'processed_records': processed_records,
                'notifications_sent': notifications_sent
            })
        }


def await_send_sse_notification(notification: Dict[str, Any]) -> bool:
    """
    Send Server-Sent Event notification to connected clients.
    
    This function stores the notification in a DynamoDB table that serves
    as a message queue for SSE connections. The actual SSE endpoint will
    poll this table for new messages.
    
    Args:
        notification: Notification payload to send
        
    Returns:
        bool: True if notification was stored successfully
    """
    try:
        # Get the SSE messages table name from environment
        import os
        sse_table_name = os.environ.get('SSE_MESSAGES_TABLE_NAME', 'sse-messages')
        
        # Get DynamoDB table
        table = dynamodb.Table(sse_table_name)
        
        # Store notification with TTL (expire after 1 hour)
        ttl = int(time.time()) + 3600  # 1 hour from now
        
        item = {
            'message_id': notification['id'],
            'message_type': notification['type'],
            'payload': json.dumps(notification),
            'created_at': notification['timestamp'],
            'ttl': ttl,
            'delivered': False
        }
        
        # Put item in DynamoDB
        table.put_item(Item=item)
        
        logger.info(f"SSE notification stored with ID: {notification['id']}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to store SSE notification: {str(e)}")
        return False


def format_sse_message(notification: Dict[str, Any]) -> str:
    """
    Format notification as Server-Sent Event message.
    
    Args:
        notification: Notification payload
        
    Returns:
        str: Formatted SSE message
    """
    sse_message = f"id: {notification['id']}\n"
    sse_message += f"event: {notification['type']}\n"
    sse_message += f"data: {json.dumps(notification['data'])}\n\n"
    
    return sse_message