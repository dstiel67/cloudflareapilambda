"""
AWS Lambda function for Server-Sent Events (SSE) endpoint.

This function provides an SSE endpoint for Angular web clients to receive
real-time notifications about redirect status updates.
"""

import json
import logging
import boto3
import time
from typing import Dict, Any, List, Generator
from datetime import datetime, timezone
import os

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for SSE endpoint.
    
    Handles SSE connection requests and streams notifications to clients.
    
    Args:
        event: API Gateway event data
        context: Lambda runtime context
        
    Returns:
        Dict containing SSE response
    """
    logger.info("SSE endpoint invoked")
    
    try:
        # Get request details
        http_method = event.get('httpMethod', 'GET')
        path = event.get('path', '')
        query_params = event.get('queryStringParameters') or {}
        
        logger.info(f"Request: {http_method} {path}")
        
        # Handle CORS preflight
        if http_method == 'OPTIONS':
            return create_cors_response()
        
        # Handle SSE connection
        if http_method == 'GET' and path.endswith('/events'):
            return handle_sse_connection(query_params, context)
        
        # Handle health check
        if http_method == 'GET' and path.endswith('/health'):
            return {
                'statusCode': 200,
                'headers': get_cors_headers(),
                'body': json.dumps({
                    'status': 'healthy',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
            }
        
        # Unknown endpoint
        return {
            'statusCode': 404,
            'headers': get_cors_headers(),
            'body': json.dumps({'error': 'Endpoint not found'})
        }
        
    except Exception as e:
        logger.error(f"Error in SSE handler: {str(e)}")
        return {
            'statusCode': 500,
            'headers': get_cors_headers(),
            'body': json.dumps({'error': 'Internal server error'})
        }


def handle_sse_connection(query_params: Dict[str, str], context: Any) -> Dict[str, Any]:
    """
    Handle Server-Sent Events connection.
    
    Args:
        query_params: Query parameters from the request
        context: Lambda context
        
    Returns:
        Dict containing SSE response
    """
    try:
        # Get client ID from query params (optional)
        client_id = query_params.get('client_id', f"client_{int(time.time())}")
        last_event_id = query_params.get('lastEventId', '0')
        
        logger.info(f"SSE connection for client: {client_id}, last_event_id: {last_event_id}")
        
        # Get messages from DynamoDB
        messages = get_pending_messages(last_event_id)
        
        # Format as SSE stream
        sse_data = format_sse_stream(messages, client_id)
        
        # Return SSE response
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'text/event-stream',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'GET,OPTIONS'
            },
            'body': sse_data
        }
        
    except Exception as e:
        logger.error(f"Error handling SSE connection: {str(e)}")
        return {
            'statusCode': 500,
            'headers': get_cors_headers(),
            'body': f"data: {json.dumps({'error': 'Connection failed'})}\n\n"
        }


def get_pending_messages(last_event_id: str) -> List[Dict[str, Any]]:
    """
    Get pending SSE messages from DynamoDB.
    
    Args:
        last_event_id: Last event ID received by client
        
    Returns:
        List of pending messages
    """
    try:
        # Get the SSE messages table name from environment
        sse_table_name = os.environ.get('SSE_MESSAGES_TABLE_NAME', 'sse-messages')
        table = dynamodb.Table(sse_table_name)
        
        # Scan for undelivered messages newer than last_event_id
        response = table.scan(
            FilterExpression='delivered = :delivered AND message_id > :last_id',
            ExpressionAttributeValues={
                ':delivered': False,
                ':last_id': last_event_id
            }
        )
        
        messages = response.get('Items', [])
        
        # Sort by message_id (timestamp-based)
        messages.sort(key=lambda x: x.get('message_id', '0'))
        
        logger.info(f"Found {len(messages)} pending messages")
        
        # Mark messages as delivered (optional - you might want to keep them for reconnections)
        for message in messages:
            try:
                table.update_item(
                    Key={'message_id': message['message_id']},
                    UpdateExpression='SET delivered = :delivered',
                    ExpressionAttributeValues={':delivered': True}
                )
            except Exception as e:
                logger.warning(f"Failed to mark message as delivered: {str(e)}")
        
        return messages
        
    except Exception as e:
        logger.error(f"Error getting pending messages: {str(e)}")
        return []


def format_sse_stream(messages: List[Dict[str, Any]], client_id: str) -> str:
    """
    Format messages as Server-Sent Events stream.
    
    Args:
        messages: List of messages to format
        client_id: Client identifier
        
    Returns:
        str: Formatted SSE stream
    """
    sse_stream = ""
    
    # Send initial connection message
    connection_msg = {
        'type': 'connection',
        'data': {
            'client_id': client_id,
            'connected_at': datetime.now(timezone.utc).isoformat(),
            'message': 'Connected to redirect status notifications'
        },
        'id': f"conn_{int(time.time() * 1000)}"
    }
    
    sse_stream += format_sse_message(connection_msg)
    
    # Add pending messages
    for message in messages:
        try:
            # Parse the stored payload
            payload = json.loads(message.get('payload', '{}'))
            sse_stream += format_sse_message(payload)
        except Exception as e:
            logger.error(f"Error formatting message: {str(e)}")
            continue
    
    # Send keep-alive message if no pending messages
    if not messages:
        keepalive_msg = {
            'type': 'keepalive',
            'data': {
                'timestamp': datetime.now(timezone.utc).isoformat()
            },
            'id': f"ka_{int(time.time() * 1000)}"
        }
        sse_stream += format_sse_message(keepalive_msg)
    
    return sse_stream


def format_sse_message(message: Dict[str, Any]) -> str:
    """
    Format a single message as SSE format.
    
    Args:
        message: Message to format
        
    Returns:
        str: Formatted SSE message
    """
    sse_message = f"id: {message.get('id', 'unknown')}\n"
    sse_message += f"event: {message.get('type', 'message')}\n"
    sse_message += f"data: {json.dumps(message.get('data', {}))}\n\n"
    
    return sse_message


def create_cors_response() -> Dict[str, Any]:
    """
    Create CORS preflight response.
    
    Returns:
        Dict containing CORS response
    """
    return {
        'statusCode': 200,
        'headers': get_cors_headers(),
        'body': ''
    }


def get_cors_headers() -> Dict[str, str]:
    """
    Get CORS headers for responses.
    
    Returns:
        Dict containing CORS headers
    """
    return {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
        'Access-Control-Allow-Methods': 'GET,OPTIONS',
        'Access-Control-Max-Age': '86400'
    }