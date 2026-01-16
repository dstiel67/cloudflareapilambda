"""
AWS Lambda function for syncing Cloudflare KV data to DynamoDB.

This module provides the main entry point for the Lambda function that:
1. Retrieves Cloudflare API credentials from AWS Secrets Manager
2. Fetches data from Cloudflare KV API
3. Transforms and stores the data in DynamoDB
4. Returns execution summary with metrics
"""

import json
import logging
import time
import uuid
from typing import Dict, Any, List, Optional

# Import our components
from src.config import ConfigurationManager, ConfigurationError
from src.cloudflare_client import (
    CloudflareClient, CloudflareAPIError, CloudflareAuthenticationError, 
    CloudflareRateLimitError, RetryConfig
)
from src.data_transformer import DataTransformer, DataValidationError
from src.dynamodb_client import DynamoDBClient, DynamoDBError
from src.error_handler import ErrorHandler, ErrorContext, ErrorCategory
from src.lambda_optimizations import (
    LambdaContext, optimize_lambda_execution, cleanup_lambda_resources,
    get_connection_pool
)

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler function for Cloudflare data sync.
    
    Fetches a specific key from Cloudflare KV and stores it in DynamoDB.
    
    Includes Lambda-specific optimizations:
    - Connection reuse across invocations
    - Cold start performance optimization
    - Timeout management and early termination
    - Resource cleanup on completion
    
    Args:
        event: Lambda event data (can contain optional parameters)
            - key_name: Specific key to fetch (default: 'redirect-all-users-to-essentials')
        context: Lambda runtime context
        
    Returns:
        Dict containing execution results and comprehensive metrics
        
    Requirements: All requirements integrated, Performance and reliability
    """
    # Generate unique request ID for tracking
    request_id = str(uuid.uuid4())
    
    # Initialize error handler for comprehensive logging and statistics
    error_handler = ErrorHandler(logger=logger, request_id=request_id)
    
    # Wrap Lambda context for enhanced functionality
    lambda_context = LambdaContext.from_lambda_context(context)
    
    try:
        # Apply Lambda-specific optimizations
        optimization_results, timeout_manager, connection_pool = optimize_lambda_execution(
            lambda_context, logger
        )
        
        error_handler.log_operation_start("lambda_execution", "main", {
            "event": event,
            "context_request_id": lambda_context.aws_request_id,
            "remaining_time_ms": lambda_context.remaining_time_in_millis(),
            "memory_limit_mb": lambda_context.memory_limit_in_mb,
            "cold_start_detected": optimization_results['cold_start_detected'],
            "optimization_time_ms": optimization_results['optimization_time_ms']
        })
        
        logger.info(f"Starting Cloudflare KV Data Sync | Request ID: {request_id}")
        logger.info(f"Lambda optimizations: Cold start: {optimization_results['cold_start_detected']}, "
                   f"Optimization time: {optimization_results['optimization_time_ms']}ms")
        logger.info(f"Event: {json.dumps(event, default=str)}")
        
        # Extract key name from event (default to specific key)
        key_name = event.get('key_name', 'redirect-all-users-to-essentials')
        logger.info(f"Fetching specific key: {key_name}")
        
        # Step 1: Load configuration with connection reuse
        logger.info("Step 1: Loading configuration")
        error_handler.log_operation_start("load_configuration", "config_manager")
        
        with timeout_manager.timeout_context("load_configuration") as should_continue:
            if not should_continue:
                return error_handler.create_error_response({
                    'category': 'timeout',
                    'message': 'Lambda timeout approached during configuration loading',
                    'is_retryable': True
                })
            
            try:
                config_manager = connection_pool.get_config_manager()
                config = config_manager.load_config()
                
                error_handler.log_operation_end("load_configuration", "config_manager", True, {
                    "secrets_loaded": True,
                    "environment_vars_loaded": True,
                    "connection_reused": config_manager is connection_pool._config_manager
                })
                
            except ConfigurationError as e:
                error_context = error_handler.create_error_context(
                    "load_configuration", "config_manager",
                    {"configuration_source": "environment_and_secrets_manager"}
                )
                error_info = error_handler.handle_configuration_error(e, error_context)
                return error_handler.create_error_response(error_info)
        
        # Step 2: Initialize Cloudflare API client with connection reuse
        logger.info("Step 2: Initializing Cloudflare API client")
        error_handler.log_operation_start("initialize_cloudflare_client", "cloudflare_client")
        
        with timeout_manager.timeout_context("initialize_cloudflare_client") as should_continue:
            if not should_continue:
                return error_handler.create_error_response({
                    'category': 'timeout',
                    'message': 'Lambda timeout approaching during Cloudflare client initialization',
                    'is_retryable': True
                })
            
            try:
                cloudflare_client = connection_pool.get_cloudflare_client(config)
                
                error_handler.log_operation_end("initialize_cloudflare_client", "cloudflare_client", True, {
                    "namespace_id": config['cloudflare_credentials'].kv_namespace_id,
                    "timeout": config['api_timeout_seconds'],
                    "max_retries": config['retry_max_attempts'],
                    "connection_reused": cloudflare_client is connection_pool._cloudflare_client
                })
                
            except Exception as e:
                error_context = error_handler.create_error_context(
                    "initialize_cloudflare_client", "cloudflare_client",
                    {"credentials_source": "secrets_manager"}
                )
                error_info = error_handler.handle_configuration_error(e, error_context)
                return error_handler.create_error_response(error_info)
        
        # Step 3: Initialize data transformer with connection reuse
        logger.info("Step 3: Initializing data transformer")
        data_transformer = connection_pool.get_data_transformer(
            config['cloudflare_credentials'].kv_namespace_id
        )
        
        # Step 4: Initialize DynamoDB client with connection reuse
        logger.info("Step 4: Initializing DynamoDB client")
        error_handler.log_operation_start("initialize_dynamodb_client", "dynamodb_client")
        
        with timeout_manager.timeout_context("initialize_dynamodb_client") as should_continue:
            if not should_continue:
                return error_handler.create_error_response({
                    'category': 'timeout',
                    'message': 'Lambda timeout approaching during DynamoDB client initialization',
                    'is_retryable': True
                })
            
            try:
                dynamodb_client = connection_pool.get_dynamodb_client(config)
                
                error_handler.log_operation_end("initialize_dynamodb_client", "dynamodb_client", True, {
                    "table_name": config['dynamodb_table_name'],
                    "max_retries": config['retry_max_attempts'],
                    "connection_reused": dynamodb_client is connection_pool._dynamodb_client
                })
                
            except DynamoDBError as e:
                error_context = error_handler.create_error_context(
                    "initialize_dynamodb_client", "dynamodb_client",
                    {"table_name": config['dynamodb_table_name']}
                )
                error_info = error_handler.handle_storage_error(e, error_context, is_retryable=False)
                return error_handler.create_error_response(error_info)
        
        # Step 5: Fetch specific key value from Cloudflare KV with timeout management
        logger.info(f"Step 5: Fetching key '{key_name}' from Cloudflare KV")
        error_handler.log_operation_start("fetch_cloudflare_value", "cloudflare_client")
        
        with timeout_manager.timeout_context("fetch_cloudflare_value") as should_continue:
            if not should_continue:
                return error_handler.create_error_response({
                    'category': 'timeout',
                    'message': 'Lambda timeout approaching during value fetching',
                    'is_retryable': True
                })
            
            try:
                # Fetch value directly for the specific key
                value_response = cloudflare_client.get_value(key_name)
                error_handler.update_statistics(cloudflare_api_calls=1)
                
                if not value_response.success or value_response.errors:
                    error_msg = f"Cloudflare API returned errors for key '{key_name}': {[e.message for e in value_response.errors]}"
                    raise CloudflareAPIError(error_msg, errors=value_response.errors)
                
                logger.info(f"Successfully retrieved value for key '{key_name}'")
                
                error_handler.log_operation_end("fetch_cloudflare_value", "cloudflare_client", True, {
                    "key_name": key_name,
                    "value_retrieved": True
                })
                
            except CloudflareAuthenticationError as e:
                error_context = error_handler.create_error_context(
                    "fetch_cloudflare_value", "cloudflare_client",
                    {"namespace_id": config['cloudflare_credentials'].kv_namespace_id, "key_name": key_name}
                )
                error_info = error_handler.handle_authentication_error(e, error_context)
                return error_handler.create_error_response(error_info)
                
            except (CloudflareAPIError, CloudflareRateLimitError) as e:
                error_context = error_handler.create_error_context(
                    "fetch_cloudflare_value", "cloudflare_client",
                    {"namespace_id": config['cloudflare_credentials'].kv_namespace_id, "key_name": key_name}
                )
                is_retryable = isinstance(e, CloudflareRateLimitError) or (hasattr(e, 'status_code') and e.status_code >= 500)
                error_info = error_handler.handle_api_error(e, error_context, is_retryable=is_retryable)
                return error_handler.create_error_response(error_info)
        
        # Step 6: Transform data with timeout management
        logger.info("Step 6: Transforming data")
        error_handler.log_operation_start("transform_data", "data_processing")
        
        with timeout_manager.timeout_context("transform_data") as should_continue:
            if not should_continue:
                return error_handler.create_error_response({
                    'category': 'timeout',
                    'message': 'Lambda timeout approaching during data transformation',
                    'is_retryable': True
                })
            
            try:
                # Transform data for DynamoDB (create a mock CloudflareKey object)
                from src.cloudflare_client import CloudflareKey
                cloudflare_key = CloudflareKey(name=key_name, expiration=None, metadata={})
                
                record = data_transformer.transform_kv_record(
                    key=key_name,
                    value=value_response.result,
                    cloudflare_key_metadata=cloudflare_key
                )
                
                # Validate record
                if not data_transformer.validate_record(record):
                    raise DataValidationError(f"Record validation failed for key '{key_name}'")
                
                error_handler.update_statistics(records_processed=1)
                
                logger.info(f"Successfully transformed data for key '{key_name}'")
                
                error_handler.log_operation_end("transform_data", "data_processing", True, {
                    "key_name": key_name,
                    "record_valid": True
                })
                
            except DataValidationError as e:
                error_context = error_handler.create_error_context(
                    "transform_data", "data_processing",
                    {"key_name": key_name}
                )
                error_msg = f"Data validation error for key '{key_name}': {str(e)}"
                logger.error(error_msg)
                return error_handler.create_error_response({
                    'category': 'data_validation',
                    'message': error_msg,
                    'is_retryable': False
                })
                
            except Exception as e:
                error_msg = f"Unexpected error transforming key '{key_name}': {str(e)}"
                logger.error(error_msg)
                return error_handler.create_error_response({
                    'category': 'unknown',
                    'message': error_msg,
                    'is_retryable': False
                })
        
        # Step 7: Store record in DynamoDB with timeout management
        logger.info("Step 7: Storing record in DynamoDB")
        error_handler.log_operation_start("store_record", "dynamodb_client")
        
        with timeout_manager.timeout_context("store_record") as should_continue:
            if not should_continue:
                logger.warning("Skipping DynamoDB storage due to approaching timeout")
                # Return partial success response
                response_data = {
                    "message": "Cloudflare data sync partially completed - timeout approaching",
                    "key_name": key_name,
                    "processing_summary": {
                        "key_retrieved": True,
                        "record_processed": True,
                        "record_stored": False,
                        "timeout_occurred": True
                    }
                }
                return error_handler.create_success_response(response_data)
            
            try:
                # Store single record
                batch_result = dynamodb_client.batch_write_records([record])
                error_handler.update_statistics(
                    dynamodb_writes=1,
                    records_stored=batch_result.successful_records
                )
                
                logger.info(f"Storage completed: {batch_result.successful_records} successful, {batch_result.failed_records} failed")
                
                error_handler.log_operation_end("store_record", "dynamodb_client", True, {
                    "key_name": key_name,
                    "record_stored": batch_result.successful_records > 0,
                    "storage_errors": len(batch_result.errors)
                })
                
            except DynamoDBError as e:
                error_context = error_handler.create_error_context(
                    "store_record", "dynamodb_client",
                    {"key_name": key_name}
                )
                error_info = error_handler.handle_storage_error(e, error_context, is_retryable=True)
                return error_handler.create_error_response(error_info)
        
        # Step 8: Generate final response with optimization metrics
        error_handler.log_operation_end("lambda_execution", "main", True)
        
        # Create success response with comprehensive statistics
        response_data = {
            "message": f"Cloudflare data sync completed successfully for key '{key_name}'",
            "key_name": key_name,
            "processing_summary": {
                "key_retrieved": True,
                "record_processed": True,
                "record_stored": batch_result.successful_records > 0 if 'batch_result' in locals() else False,
                "record_failed": batch_result.failed_records > 0 if 'batch_result' in locals() else False
            },
            "lambda_optimizations": {
                "cold_start_detected": optimization_results['cold_start_detected'],
                "optimization_time_ms": optimization_results['optimization_time_ms'],
                "connection_pool_stats": optimization_results['connection_pool_stats'],
                "timeout_management": {
                    "timeout_warned": timeout_manager.timeout_warned,
                    "remaining_time_seconds": timeout_manager.get_remaining_time(),
                    "elapsed_time_seconds": timeout_manager.get_elapsed_time()
                }
            }
        }
        
        # Log final summary
        error_handler.log_final_summary()
        
        return error_handler.create_success_response(response_data)
        
    except Exception as e:
        # Handle any unexpected errors
        error_context = error_handler.create_error_context(
            "lambda_execution", "main",
            {"unexpected_error": True, "error_type": type(e).__name__}
        )
        
        # Log the full exception for debugging
        logger.error(f"Unexpected error in lambda_handler: {str(e)}", exc_info=True)
        
        # Create generic error response
        error_info = {
            'category': ErrorCategory.UNKNOWN.value,
            'type': type(e).__name__,
            'message': str(e),
            'timestamp': error_context.timestamp,
            'operation': error_context.operation,
            'component': error_context.component,
            'request_id': request_id,
            'is_retryable': False,
            'severity': 'critical'
        }
        
        error_handler.log_operation_end("lambda_execution", "main", False, {
            "error": str(e),
            "error_type": type(e).__name__
        })
        
        error_handler.log_final_summary()
        
        return error_handler.create_error_response(error_info)
    
    finally:
        # Clean up resources before function termination
        try:
            cleanup_lambda_resources(logger)
        except Exception as cleanup_error:
            logger.warning(f"Error during resource cleanup: {cleanup_error}")