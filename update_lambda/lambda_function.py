"""
AWS Lambda function for updating redirect status in DynamoDB.

This function provides an API endpoint to update the 'redirect-all-users-to-essentials' 
status in DynamoDB, which triggers notifications to connected web clients via SSE.
"""

import json
import logging
import boto3
import time
from typing import Dict, Any
from datetime import datetime, timezone
import os

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for updating redirect status.
    
    Handles HTTP requests to update the redirect status in DynamoDB.
    
    Args:
        event: API Gateway event data
        context: Lambda runtime context
        
    Returns:
        Dict containing API Gateway response
    """
    logger.info("Update redirect status endpoint invoked")
    
    try:
        # Get request details
        http_method = event.get('httpMethod', 'POST')
        path = event.get('path', '')
        body = event.get('body', '{}')
        
        logger.info(f"Request: {http_method} {path}")
        
        # Handle CORS preflight
        if http_method == 'OPTIONS':
            return create_cors_response()
        
        # Handle redirect status update
        if http_method == 'POST' and path.endswith('/redirect-status'):
            return handle_update_redirect_status(body)
        
        # Handle GET request to retrieve current status
        if http_method == 'GET' and path.endswith('/redirect-status'):
            return handle_get_redirect_status()
        
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
        logger.error(f"Error in update handler: {str(e)}")
        return {
            'statusCode': 500,
            'headers': get_cors_headers(),
            'body': json.dumps({'error': 'Internal server error', 'message': str(e)})
        }


def handle_update_redirect_status(body: str) -> Dict[str, Any]:
    """
    Handle redirect status update request.
    
    Args:
        body: JSON request body
        
    Returns:
        Dict containing API Gateway response
    """
    try:
        # Parse request body
        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            return {
                'statusCode': 400,
                'headers': get_cors_headers(),
                'body': json.dumps({'error': 'Invalid JSON in request body'})
            }
        
        # Get the new redirect status value
        new_value = data.get('value', '').upper()
        
        # Validate the value
        if new_value not in ['ON', 'OFF']:
            return {
                'statusCode': 400,
                'headers': get_cors_headers(),
                'body': json.dumps({
                    'error': 'Invalid value',
                    'message': 'Value must be either "ON" or "OFF"'
                })
            }
        
        # Get optional metadata
        updated_by = data.get('updated_by', 'api')
        reason = data.get('reason', '')
        
        logger.info(f"Updating redirect status to: {new_value} (by: {updated_by})")
        
        # Get DynamoDB table
        table_name = os.environ.get('DYNAMODB_TABLE_NAME', 'cloudflare-kv-data-with-stream')
        table = dynamodb.Table(table_name)
        
        # Create timestamp
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Prepare the item
        item = {
            'pk': 'cf_kv#redirect-all-users-to-essentials',
            'sk': timestamp,
            'key_name': 'redirect-all-users-to-essentials',
            'value': new_value,
            'retrieved_at': timestamp,
            'updated_at': timestamp,
            'updated_by': updated_by,
            'source': 'api',
            'data_version': '1.0',
            'namespace_id': 'direct-update',
            'metadata': {
                'transformed_at': timestamp,
                'original_type': 'str',
                'value_length': len(new_value),
                'reason': reason
            }
        }
        
        # Put item in DynamoDB (this will trigger the Stream)
        table.put_item(Item=item)
        
        logger.info(f"Successfully updated redirect status to: {new_value}")
        
        # Return success response
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps({
                'success': True,
                'message': f'Redirect status updated to {new_value}',
                'data': {
                    'key': 'redirect-all-users-to-essentials',
                    'value': new_value,
                    'timestamp': timestamp,
                    'updated_by': updated_by
                }
            })
        }
        
    except Exception as e:
        logger.error(f"Error updating redirect status: {str(e)}")
        return {
            'statusCode': 500,
            'headers': get_cors_headers(),
            'body': json.dumps({
                'error': 'Failed to update redirect status',
                'message': str(e)
            })
        }


def handle_get_redirect_status() -> Dict[str, Any]:
    """
    Handle get redirect status request.
    
    Returns:
        Dict containing API Gateway response with current status
    """
    try:
        # Get DynamoDB table
        table_name = os.environ.get('DYNAMODB_TABLE_NAME', 'cloudflare-kv-data-with-stream')
        table = dynamodb.Table(table_name)
        
        # Query for the most recent redirect status
        response = table.query(
            KeyConditionExpression='pk = :pk',
            ExpressionAttributeValues={
                ':pk': 'cf_kv#redirect-all-users-to-essentials'
            },
            ScanIndexForward=False,  # Sort descending (newest first)
            Limit=1
        )
        
        items = response.get('Items', [])
        
        if not items:
            return {
                'statusCode': 404,
                'headers': get_cors_headers(),
                'body': json.dumps({
                    'error': 'Redirect status not found',
                    'message': 'No redirect status has been set yet'
                })
            }
        
        item = items[0]
        
        # Return current status
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps({
                'success': True,
                'data': {
                    'key': item.get('key_name'),
                    'value': item.get('value'),
                    'timestamp': item.get('updated_at') or item.get('retrieved_at'),
                    'updated_by': item.get('updated_by', 'unknown'),
                    'source': item.get('source', 'unknown')
                }
            })
        }
        
    except Exception as e:
        logger.error(f"Error getting redirect status: {str(e)}")
        return {
            'statusCode': 500,
            'headers': get_cors_headers(),
            'body': json.dumps({
                'error': 'Failed to get redirect status',
                'message': str(e)
            })
        }


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
        'Access-Control-Allow-Methods': 'GET,POST,PUT,OPTIONS',
        'Access-Control-Max-Age': '86400',
        'Content-Type': 'application/json'
    }