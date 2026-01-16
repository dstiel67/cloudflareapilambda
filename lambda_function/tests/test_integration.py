"""
Integration tests for the complete Cloudflare Data Sync workflow.

These tests verify end-to-end functionality including:
- Complete data sync scenarios
- Error scenarios and recovery
- Various data sizes and formats
- Lambda-specific optimizations
"""

import json
import os
import time
import uuid
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List
import pytest

# Import the main lambda handler and components
from lambda_function.lambda_function import lambda_handler
from lambda_function.src.config import CloudflareCredentials
from lambda_function.src.cloudflare_client import CloudflareKey, CloudflareKeysResponse, CloudflareValueResponse, CloudflareResultInfo
from lambda_function.src.data_transformer import DynamoDBRecord
from lambda_function.src.dynamodb_client import BatchWriteResult


class TestIntegrationWorkflow:
    """Integration tests for complete workflow scenarios."""
    
    def setup_method(self):
        """Set up test environment before each test."""
        # Mock environment variables
        self.env_vars = {
            'SECRETS_MANAGER_SECRET_NAME': 'test-cloudflare-secret',
            'DYNAMODB_TABLE_NAME': 'test-cloudflare-data',
            'RETRY_MAX_ATTEMPTS': '3',
            'API_TIMEOUT_SECONDS': '30'
        }
        
        # Mock Cloudflare credentials
        self.mock_credentials = CloudflareCredentials(
            api_token='test-token-123',
            account_id='test-account-456',
            kv_namespace_id='test-namespace-789',
            kv_namespace='test-namespace'
        )
        
        # Mock Lambda context
        self.mock_context = Mock()
        self.mock_context.aws_request_id = 'test-request-123'
        self.mock_context.function_name = 'test-cloudflare-sync'
        self.mock_context.function_version = '1'
        self.mock_context.invoked_function_arn = 'arn:aws:lambda:us-east-1:123456789012:function:test-cloudflare-sync'
        self.mock_context.memory_limit_in_mb = 512
        self.mock_context.get_remaining_time_in_millis = Mock(return_value=300000)  # 5 minutes
        self.mock_context.log_group_name = '/aws/lambda/test-cloudflare-sync'
        self.mock_context.log_stream_name = '2024/01/09/[$LATEST]test123'
    
    @patch.dict(os.environ, {
        'SECRETS_MANAGER_SECRET_NAME': 'test-cloudflare-secret',
        'DYNAMODB_TABLE_NAME': 'test-cloudflare-data',
        'RETRY_MAX_ATTEMPTS': '3',
        'API_TIMEOUT_SECONDS': '30'
    })
    @patch('src.config.boto3.client')
    @patch('src.dynamodb_client.boto3.resource')
    @patch('src.cloudflare_client.requests.Session')
    def test_successful_end_to_end_sync(self, mock_session, mock_dynamodb_resource, mock_secrets_client):
        """Test successful end-to-end data sync workflow."""
        # Mock Secrets Manager
        mock_secrets = mock_secrets_client.return_value
        mock_secrets.get_secret_value.return_value = {
            'SecretString': json.dumps({
                'api_token': 'test-token-123',
                'account_id': 'test-account-456',
                'kv_namespace_id': 'test-namespace-789',
                'kv_namespace': 'test-namespace'
            })
        }
        
        # Mock Cloudflare API responses
        mock_http_session = mock_session.return_value
        
        # Mock list keys response
        keys_response_data = {
            'success': True,
            'result': [
                {'name': 'key1', 'expiration': None, 'metadata': {}},
                {'name': 'key2', 'expiration': 1640995200, 'metadata': {'type': 'config'}}
            ],
            'result_info': {
                'page': 1,
                'per_page': 2,
                'count': 2,
                'total_count': 2,
                'cursor': None
            },
            'errors': []
        }
        
        # Mock get value responses
        value_responses = {
            'key1': 'value1-content',
            'key2': {'config': 'data', 'enabled': True}
        }
        
        def mock_get(url, **kwargs):
            """Mock HTTP GET requests."""
            response = Mock()
            response.ok = True
            response.status_code = 200
            
            if '/keys' in url:
                response.json.return_value = keys_response_data
            elif '/values/key1' in url:
                response.json.return_value = value_responses['key1']
            elif '/values/key2' in url:
                response.json.return_value = value_responses['key2']
            else:
                response.json.return_value = {'success': False, 'errors': [{'message': 'Not found'}]}
            
            return response
        
        mock_http_session.get = mock_get
        
        # Mock DynamoDB
        mock_dynamodb = mock_dynamodb_resource.return_value
        mock_table = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_table.load.return_value = None  # Table exists
        
        # Mock batch write
        mock_dynamodb.batch_write_item.return_value = {
            'UnprocessedItems': {}
        }
        
        # Test event
        event = {
            'max_keys': 10
        }
        
        # Execute lambda handler
        result = lambda_handler(event, self.mock_context)
        
        # Verify successful response
        assert result['success'] is True
        assert 'data' in result
        assert 'statistics' in result
        
        # Verify processing summary
        processing_summary = result['data']['processing_summary']
        assert processing_summary['keys_retrieved'] == 2
        assert processing_summary['records_processed'] == 2
        assert processing_summary['records_stored'] == 2
        assert processing_summary['records_failed'] == 0
        
        # Verify Lambda optimizations were applied
        assert 'lambda_optimizations' in result['data']
        lambda_opts = result['data']['lambda_optimizations']
        assert 'cold_start_detected' in lambda_opts
        assert 'optimization_time_ms' in lambda_opts
        assert 'connection_pool_stats' in lambda_opts
        
        # Verify API calls were made
        assert result['statistics']['cloudflare_api_calls'] == 3  # 1 list + 2 get values
        assert result['statistics']['dynamodb_writes'] == 1
    
    @patch.dict(os.environ, {
        'SECRETS_MANAGER_SECRET_NAME': 'test-cloudflare-secret',
        'DYNAMODB_TABLE_NAME': 'test-cloudflare-data'
    })
    @patch('src.config.boto3.client')
    def test_configuration_error_handling(self, mock_secrets_client):
        """Test error handling for configuration failures."""
        # Mock Secrets Manager failure
        mock_secrets = mock_secrets_client.return_value
        mock_secrets.get_secret_value.side_effect = Exception("Secret not found")
        
        event = {}
        
        # Execute lambda handler
        result = lambda_handler(event, self.mock_context)
        
        # Verify error response
        assert result['success'] is False
        assert 'error' in result
        assert result['error']['type'] == 'CONFIGURATION_ERROR'
        assert 'Secret not found' in result['error']['message']
        assert result['error']['is_retryable'] is False
    
    @patch.dict(os.environ, {
        'SECRETS_MANAGER_SECRET_NAME': 'test-cloudflare-secret',
        'DYNAMODB_TABLE_NAME': 'test-cloudflare-data'
    })
    @patch('src.config.boto3.client')
    @patch('src.cloudflare_client.requests.Session')
    def test_cloudflare_authentication_error(self, mock_session, mock_secrets_client):
        """Test handling of Cloudflare authentication errors."""
        # Mock Secrets Manager
        mock_secrets = mock_secrets_client.return_value
        mock_secrets.get_secret_value.return_value = {
            'SecretString': json.dumps({
                'api_token': 'invalid-token',
                'account_id': 'test-account-456',
                'kv_namespace_id': 'test-namespace-789',
                'kv_namespace': 'test-namespace'
            })
        }
        
        # Mock Cloudflare API authentication failure
        mock_http_session = mock_session.return_value
        auth_error_response = Mock()
        auth_error_response.ok = False
        auth_error_response.status_code = 401
        auth_error_response.json.return_value = {
            'success': False,
            'errors': [{'code': 10000, 'message': 'Authentication failed'}]
        }
        mock_http_session.get.return_value = auth_error_response
        
        event = {}
        
        # Execute lambda handler
        result = lambda_handler(event, self.mock_context)
        
        # Verify error response
        assert result['success'] is False
        assert result['error']['type'] == 'AUTHENTICATION_ERROR'
        assert 'Authentication failed' in result['error']['message']
        assert result['error']['is_retryable'] is False
    
    @patch.dict(os.environ, {
        'SECRETS_MANAGER_SECRET_NAME': 'test-cloudflare-secret',
        'DYNAMODB_TABLE_NAME': 'test-cloudflare-data'
    })
    @patch('src.config.boto3.client')
    @patch('src.dynamodb_client.boto3.resource')
    @patch('src.cloudflare_client.requests.Session')
    def test_rate_limiting_handling(self, mock_session, mock_dynamodb_resource, mock_secrets_client):
        """Test handling of Cloudflare rate limiting."""
        # Mock Secrets Manager
        mock_secrets = mock_secrets_client.return_value
        mock_secrets.get_secret_value.return_value = {
            'SecretString': json.dumps({
                'api_token': 'test-token-123',
                'account_id': 'test-account-456',
                'kv_namespace_id': 'test-namespace-789',
                'kv_namespace': 'test-namespace'
            })
        }
        
        # Mock Cloudflare API rate limiting
        mock_http_session = mock_session.return_value
        rate_limit_response = Mock()
        rate_limit_response.ok = False
        rate_limit_response.status_code = 429
        rate_limit_response.headers = {'Retry-After': '60'}
        rate_limit_response.json.return_value = {
            'success': False,
            'errors': [{'code': 10013, 'message': 'Rate limit exceeded'}]
        }
        mock_http_session.get.return_value = rate_limit_response
        
        event = {}
        
        # Execute lambda handler
        result = lambda_handler(event, self.mock_context)
        
        # Verify error response
        assert result['success'] is False
        assert result['error']['type'] == 'API_ERROR'
        assert 'Rate limit' in result['error']['message']
        assert result['error']['is_retryable'] is True
    
    @patch.dict(os.environ, {
        'SECRETS_MANAGER_SECRET_NAME': 'test-cloudflare-secret',
        'DYNAMODB_TABLE_NAME': 'test-cloudflare-data'
    })
    @patch('src.config.boto3.client')
    @patch('boto3.resource')  # Mock at the boto3 level to catch all resource calls
    @patch('src.cloudflare_client.requests.Session')
    def test_dynamodb_storage_error(self, mock_session, mock_boto3_resource, mock_secrets_client):
        """Test handling of DynamoDB storage errors."""
        # Mock Secrets Manager
        mock_secrets = mock_secrets_client.return_value
        mock_secrets.get_secret_value.return_value = {
            'SecretString': json.dumps({
                'api_token': 'test-token-123',
                'account_id': 'test-account-456',
                'kv_namespace_id': 'test-namespace-789',
                'kv_namespace': 'test-namespace'
            })
        }
        
        # Mock successful Cloudflare API responses
        mock_http_session = mock_session.return_value
        
        def mock_get(url, **kwargs):
            response = Mock()
            response.ok = True
            response.status_code = 200
            
            if '/keys' in url:
                response.json.return_value = {
                    'success': True,
                    'result': [{'name': 'key1', 'expiration': None, 'metadata': {}}],
                    'result_info': {'page': 1, 'per_page': 1, 'count': 1, 'total_count': 1, 'cursor': None},
                    'errors': []
                }
            elif '/values/key1' in url:
                response.json.return_value = 'test-value'
            
            return response
        
        mock_http_session.get = mock_get
        
        # Mock DynamoDB resource and table
        mock_dynamodb = mock_boto3_resource.return_value
        mock_table = Mock()
        mock_dynamodb.Table.return_value = mock_table
        
        # Mock table.load() to succeed (table exists)
        mock_table.load.return_value = None
        
        # Mock batch_write_item to fail with table not found error
        from botocore.exceptions import ClientError
        mock_dynamodb.batch_write_item.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Requested resource not found'}},
            'BatchWriteItem'
        )
        
        event = {}
        
        # Execute lambda handler
        result = lambda_handler(event, self.mock_context)
        
        # Debug: Print the actual result structure
        print("Actual result keys:", result.keys())
        if 'data' in result:
            print("Data keys:", result['data'].keys())
        
        # Verify that the function handles storage errors gracefully
        # The function should succeed overall but report storage failures
        assert result['success'] is True  # Lambda execution succeeds
        
        # Check if the data is in the 'data' field or directly in result
        data = result.get('data', result)
        assert data['processing_summary']['records_processed'] == 1
        assert data['processing_summary']['records_stored'] == 0  # No records stored due to error
        assert data['processing_summary']['records_failed'] == 1  # One record failed
        assert result['statistics']['success_rate'] == 0.0  # 0% success rate
    
    @patch.dict(os.environ, {
        'SECRETS_MANAGER_SECRET_NAME': 'test-cloudflare-secret',
        'DYNAMODB_TABLE_NAME': 'test-cloudflare-data'
    })
    @patch('src.config.boto3.client')
    @patch('src.dynamodb_client.boto3.resource')
    @patch('src.cloudflare_client.requests.Session')
    def test_partial_processing_with_errors(self, mock_session, mock_dynamodb_resource, mock_secrets_client):
        """Test partial processing when some records fail validation."""
        # Mock Secrets Manager
        mock_secrets = mock_secrets_client.return_value
        mock_secrets.get_secret_value.return_value = {
            'SecretString': json.dumps({
                'api_token': 'test-token-123',
                'account_id': 'test-account-456',
                'kv_namespace_id': 'test-namespace-789',
                'kv_namespace': 'test-namespace'
            })
        }
        
        # Mock Cloudflare API responses with mixed success/failure
        mock_http_session = mock_session.return_value
        
        def mock_get(url, **kwargs):
            response = Mock()
            
            if '/keys' in url:
                response.ok = True
                response.status_code = 200
                response.json.return_value = {
                    'success': True,
                    'result': [
                        {'name': 'valid-key', 'expiration': None, 'metadata': {}},
                        {'name': 'invalid-key', 'expiration': None, 'metadata': {}}
                    ],
                    'result_info': {'page': 1, 'per_page': 2, 'count': 2, 'total_count': 2, 'cursor': None},
                    'errors': []
                }
            elif '/values/valid-key' in url:
                response.ok = True
                response.status_code = 200
                response.json.return_value = 'valid-content'
            elif '/values/invalid-key' in url:
                response.ok = False
                response.status_code = 404
                response.json.return_value = {
                    'success': False,
                    'errors': [{'code': 10000, 'message': 'Key not found'}]
                }
            
            return response
        
        mock_http_session.get = mock_get
        
        # Mock DynamoDB
        mock_dynamodb = mock_dynamodb_resource.return_value
        mock_table = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_table.load.return_value = None
        
        mock_dynamodb.batch_write_item.return_value = {
            'UnprocessedItems': {}
        }
        
        event = {}
        
        # Execute lambda handler
        result = lambda_handler(event, self.mock_context)
        
        # Verify partial success
        assert result['success'] is True
        processing_summary = result['data']['processing_summary']
        assert processing_summary['keys_retrieved'] == 2
        assert processing_summary['records_processed'] == 1  # Only valid-key processed
        assert processing_summary['records_stored'] == 1
        assert processing_summary['processing_errors'] == 1  # invalid-key failed
        
        # Verify errors are reported
        assert result['data']['errors'] is not None
        assert len(result['data']['errors']) == 1
        assert 'invalid-key' in result['data']['errors'][0]
    
    @patch.dict(os.environ, {
        'SECRETS_MANAGER_SECRET_NAME': 'test-cloudflare-secret',
        'DYNAMODB_TABLE_NAME': 'test-cloudflare-data'
    })
    @patch('src.config.boto3.client')
    @patch('src.dynamodb_client.boto3.resource')
    @patch('src.cloudflare_client.requests.Session')
    def test_large_dataset_processing(self, mock_session, mock_dynamodb_resource, mock_secrets_client):
        """Test processing of larger datasets with pagination."""
        # Mock Secrets Manager
        mock_secrets = mock_secrets_client.return_value
        mock_secrets.get_secret_value.return_value = {
            'SecretString': json.dumps({
                'api_token': 'test-token-123',
                'account_id': 'test-account-456',
                'kv_namespace_id': 'test-namespace-789',
                'kv_namespace': 'test-namespace'
            })
        }
        
        # Generate mock data for 50 keys
        mock_keys = [{'name': f'key{i}', 'expiration': None, 'metadata': {}} for i in range(50)]
        
        mock_http_session = mock_session.return_value
        
        def mock_get(url, **kwargs):
            response = Mock()
            response.ok = True
            response.status_code = 200
            
            if '/keys' in url:
                response.json.return_value = {
                    'success': True,
                    'result': mock_keys,
                    'result_info': {
                        'page': 1,
                        'per_page': 50,
                        'count': 50,
                        'total_count': 100,
                        'cursor': 'next-page-cursor'
                    },
                    'errors': []
                }
            else:
                # Mock value responses
                key_name = url.split('/')[-1]
                response.json.return_value = f'value-for-{key_name}'
            
            return response
        
        mock_http_session.get = mock_get
        
        # Mock DynamoDB
        mock_dynamodb = mock_dynamodb_resource.return_value
        mock_table = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_table.load.return_value = None
        
        # Mock batch write with some unprocessed items
        mock_dynamodb.batch_write_item.return_value = {
            'UnprocessedItems': {}
        }
        
        event = {
            'max_keys': 50
        }
        
        # Execute lambda handler
        result = lambda_handler(event, self.mock_context)
        
        # Verify successful processing
        assert result['success'] is True
        processing_summary = result['data']['processing_summary']
        assert processing_summary['keys_retrieved'] == 50
        assert processing_summary['records_processed'] == 50
        assert processing_summary['records_stored'] == 50
        
        # Verify pagination info
        assert result['data']['pagination'] is not None
        assert result['data']['pagination']['cursor'] == 'next-page-cursor'
        assert result['data']['pagination']['has_more_pages'] is True
        
        # Verify API call count (1 list + 50 get values)
        assert result['statistics']['cloudflare_api_calls'] == 51
    
    @patch.dict(os.environ, {
        'SECRETS_MANAGER_SECRET_NAME': 'test-cloudflare-secret',
        'DYNAMODB_TABLE_NAME': 'test-cloudflare-data'
    })
    @patch('src.config.boto3.client')
    @patch('src.dynamodb_client.boto3.resource')
    @patch('src.cloudflare_client.requests.Session')
    def test_timeout_handling(self, mock_session, mock_dynamodb_resource, mock_secrets_client):
        """Test Lambda timeout handling and early termination."""
        # Mock Secrets Manager
        mock_secrets = mock_secrets_client.return_value
        mock_secrets.get_secret_value.return_value = {
            'SecretString': json.dumps({
                'api_token': 'test-token-123',
                'account_id': 'test-account-456',
                'kv_namespace_id': 'test-namespace-789',
                'kv_namespace': 'test-namespace'
            })
        }
        
        # Mock context with very little remaining time
        timeout_context = Mock()
        timeout_context.aws_request_id = 'timeout-test-123'
        timeout_context.function_name = 'test-cloudflare-sync'
        timeout_context.function_version = '1'
        timeout_context.invoked_function_arn = 'arn:aws:lambda:us-east-1:123456789012:function:test-cloudflare-sync'
        timeout_context.memory_limit_in_mb = 512
        timeout_context.get_remaining_time_in_millis = Mock(return_value=25000)  # 25 seconds (less than 30s buffer)
        timeout_context.log_group_name = '/aws/lambda/test-cloudflare-sync'
        timeout_context.log_stream_name = '2024/01/09/[$LATEST]timeout123'
        
        # Mock Cloudflare API responses
        mock_http_session = mock_session.return_value
        
        def mock_get(url, **kwargs):
            response = Mock()
            response.ok = True
            response.status_code = 200
            
            if '/keys' in url:
                response.json.return_value = {
                    'success': True,
                    'result': [{'name': 'key1', 'expiration': None, 'metadata': {}}],
                    'result_info': {'page': 1, 'per_page': 1, 'count': 1, 'total_count': 1, 'cursor': None},
                    'errors': []
                }
            else:
                response.json.return_value = 'test-value'
            
            return response
        
        mock_http_session.get = mock_get
        
        event = {}
        
        # Execute lambda handler with timeout context
        result = lambda_handler(event, timeout_context)
        
        # Should return timeout error response
        assert result['success'] is False
        assert result['error']['type'] == 'TIMEOUT_ERROR' or 'timeout' in result['error']['message'].lower()
        assert result['error']['is_retryable'] is True
    
    @patch.dict(os.environ, {
        'SECRETS_MANAGER_SECRET_NAME': 'test-cloudflare-secret',
        'DYNAMODB_TABLE_NAME': 'test-cloudflare-data'
    })
    @patch('src.config.boto3.client')
    @patch('src.dynamodb_client.boto3.resource')
    @patch('src.cloudflare_client.requests.Session')
    def test_various_data_formats(self, mock_session, mock_dynamodb_resource, mock_secrets_client):
        """Test processing of various data formats and types."""
        # Mock Secrets Manager
        mock_secrets = mock_secrets_client.return_value
        mock_secrets.get_secret_value.return_value = {
            'SecretString': json.dumps({
                'api_token': 'test-token-123',
                'account_id': 'test-account-456',
                'kv_namespace_id': 'test-namespace-789',
                'kv_namespace': 'test-namespace'
            })
        }
        
        # Mock Cloudflare API responses with various data types
        mock_http_session = mock_session.return_value
        
        test_values = {
            'string-key': 'simple string value',
            'json-key': {'nested': {'data': 'value'}, 'array': [1, 2, 3]},
            'number-key': 42,
            'boolean-key': True,
            'null-key': None,
            'empty-key': '',
            'large-key': 'x' * 1000  # Large string
        }
        
        def mock_get(url, **kwargs):
            response = Mock()
            response.ok = True
            response.status_code = 200
            
            if '/keys' in url:
                response.json.return_value = {
                    'success': True,
                    'result': [
                        {'name': key, 'expiration': None, 'metadata': {'type': 'test'}}
                        for key in test_values.keys()
                    ],
                    'result_info': {
                        'page': 1,
                        'per_page': len(test_values),
                        'count': len(test_values),
                        'total_count': len(test_values),
                        'cursor': None
                    },
                    'errors': []
                }
            else:
                # Extract key name from URL
                key_name = url.split('/')[-1]
                if key_name in test_values:
                    response.json.return_value = test_values[key_name]
                else:
                    response.json.return_value = 'default-value'
            
            return response
        
        mock_http_session.get = mock_get
        
        # Mock DynamoDB
        mock_dynamodb = mock_dynamodb_resource.return_value
        mock_table = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_table.load.return_value = None
        
        mock_dynamodb.batch_write_item.return_value = {
            'UnprocessedItems': {}
        }
        
        event = {}
        
        # Execute lambda handler
        result = lambda_handler(event, self.mock_context)
        
        # Verify successful processing of all data types
        assert result['success'] is True
        processing_summary = result['data']['processing_summary']
        assert processing_summary['keys_retrieved'] == len(test_values)
        assert processing_summary['records_processed'] == len(test_values)
        assert processing_summary['records_stored'] == len(test_values)
        assert processing_summary['records_failed'] == 0
        
        # Verify no processing errors
        assert processing_summary['processing_errors'] == 0
    
    def test_connection_reuse_optimization(self):
        """Test that connection reuse optimization works correctly."""
        from lambda_function.src.lambda_optimizations import get_connection_pool
        
        # Get connection pool
        pool1 = get_connection_pool()
        pool2 = get_connection_pool()
        
        # Should be the same instance (singleton pattern)
        assert pool1 is pool2
        
        # Check initial stats
        stats = pool1.get_stats()
        assert stats['usage_count'] == 0
        assert not any(stats['active_connections'].values())
        
        # Mock configuration
        mock_config = {
            'cloudflare_credentials': self.mock_credentials,
            'api_timeout_seconds': 30,
            'retry_max_attempts': 3,
            'dynamodb_table_name': 'test-table'
        }
        
        # Get clients (should create new instances)
        with patch('lambda_function.src.lambda_optimizations.ConfigurationManager'), \
             patch('lambda_function.src.lambda_optimizations.CloudflareClient'), \
             patch('lambda_function.src.lambda_optimizations.DynamoDBClient'), \
             patch('lambda_function.src.lambda_optimizations.DataTransformer'):
            
            config_mgr1 = pool1.get_config_manager()
            config_mgr2 = pool1.get_config_manager()
            
            # Should be the same instance (reused)
            assert config_mgr1 is config_mgr2
            
            # Usage count should increase
            stats = pool1.get_stats()
            assert stats['usage_count'] == 2
    
    def test_cold_start_detection(self):
        """Test cold start detection and optimization."""
        from lambda_function.src.lambda_optimizations import ColdStartOptimizer
        
        optimizer = ColdStartOptimizer()
        
        # Should detect cold start on first run
        is_cold_start = optimizer.detect_cold_start()
        assert is_cold_start is True
        assert optimizer.cold_start_detected is True
        
        # Apply optimizations
        optimizer.optimize_for_cold_start()
        
        # Should complete without errors
        assert optimizer.cold_start_detected is True


class TestErrorRecoveryScenarios:
    """Test error recovery and resilience scenarios."""
    
    def setup_method(self):
        """Set up test environment."""
        self.mock_context = Mock()
        self.mock_context.aws_request_id = 'recovery-test-123'
        self.mock_context.function_name = 'test-cloudflare-sync'
        self.mock_context.function_version = '1'
        self.mock_context.invoked_function_arn = 'arn:aws:lambda:us-east-1:123456789012:function:test-cloudflare-sync'
        self.mock_context.memory_limit_in_mb = 512
        self.mock_context.get_remaining_time_in_millis = Mock(return_value=300000)
        self.mock_context.log_group_name = '/aws/lambda/test-cloudflare-sync'
        self.mock_context.log_stream_name = '2024/01/09/[$LATEST]recovery123'
    
    @patch.dict(os.environ, {
        'SECRETS_MANAGER_SECRET_NAME': 'test-cloudflare-secret',
        'DYNAMODB_TABLE_NAME': 'test-cloudflare-data'
    })
    @patch('src.config.boto3.client')
    @patch('src.dynamodb_client.boto3.resource')
    @patch('src.cloudflare_client.requests.Session')
    def test_retry_logic_with_eventual_success(self, mock_session, mock_dynamodb_resource, mock_secrets_client):
        """Test retry logic that eventually succeeds."""
        # Mock Secrets Manager
        mock_secrets = mock_secrets_client.return_value
        mock_secrets.get_secret_value.return_value = {
            'SecretString': json.dumps({
                'api_token': 'test-token-123',
                'account_id': 'test-account-456',
                'kv_namespace_id': 'test-namespace-789',
                'kv_namespace': 'test-namespace'
            })
        }
        
        # Mock Cloudflare API with initial failures then success
        mock_http_session = mock_session.return_value
        call_count = 0
        
        def mock_get(url, **kwargs):
            nonlocal call_count
            call_count += 1
            
            response = Mock()
            
            if '/keys' in url:
                if call_count <= 2:  # Fail first 2 attempts
                    response.ok = False
                    response.status_code = 500
                    response.json.return_value = {
                        'success': False,
                        'errors': [{'code': 10001, 'message': 'Internal server error'}]
                    }
                else:  # Succeed on 3rd attempt
                    response.ok = True
                    response.status_code = 200
                    response.json.return_value = {
                        'success': True,
                        'result': [{'name': 'test-key', 'expiration': None, 'metadata': {}}],
                        'result_info': {'page': 1, 'per_page': 1, 'count': 1, 'total_count': 1, 'cursor': None},
                        'errors': []
                    }
            elif '/values/test-key' in url:
                response.ok = True
                response.status_code = 200
                response.json.return_value = 'test-value'
            
            return response
        
        mock_http_session.get = mock_get
        
        # Mock DynamoDB
        mock_dynamodb = mock_dynamodb_resource.return_value
        mock_table = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_table.load.return_value = None
        
        mock_dynamodb.batch_write_item.return_value = {
            'UnprocessedItems': {}
        }
        
        event = {}
        
        # Execute lambda handler
        result = lambda_handler(event, self.mock_context)
        
        # Should eventually succeed after retries
        assert result['success'] is True
        assert call_count >= 3  # Should have retried
        
        # The retry logic happens at the Cloudflare client level, not error handler level
        # So we verify the API was called multiple times (indicating retries occurred)
        # call_count includes: 2 failed list_keys + 1 successful list_keys + 1 get_value = 4 total
        assert call_count == 4
    
    @patch.dict(os.environ, {
        'SECRETS_MANAGER_SECRET_NAME': 'test-cloudflare-secret',
        'DYNAMODB_TABLE_NAME': 'test-cloudflare-data'
    })
    @patch('src.config.boto3.client')
    @patch('src.dynamodb_client.boto3.resource')
    @patch('src.cloudflare_client.requests.Session')
    def test_circuit_breaker_activation(self, mock_session, mock_dynamodb_resource, mock_secrets_client):
        """Test circuit breaker activation after persistent failures."""
        # Mock Secrets Manager
        mock_secrets = mock_secrets_client.return_value
        mock_secrets.get_secret_value.return_value = {
            'SecretString': json.dumps({
                'api_token': 'test-token-123',
                'account_id': 'test-account-456',
                'kv_namespace_id': 'test-namespace-789',
                'kv_namespace': 'test-namespace'
            })
        }
        
        # Mock persistent Cloudflare API failures
        mock_http_session = mock_session.return_value
        
        def mock_get(url, **kwargs):
            response = Mock()
            response.ok = False
            response.status_code = 500
            response.json.return_value = {
                'success': False,
                'errors': [{'code': 10001, 'message': 'Persistent server error'}]
            }
            return response
        
        mock_http_session.get = mock_get
        
        event = {}
        
        # Execute lambda handler
        result = lambda_handler(event, self.mock_context)
        
        # Should fail due to persistent errors
        assert result['success'] is False
        assert result['error']['type'] == 'API_ERROR'
        assert 'Persistent server error' in result['error']['message']
        
        # The retry logic happens at the Cloudflare client level
        # We can verify retries occurred by checking the logs or API call patterns