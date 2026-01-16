"""
Tests for the ConfigurationManager class.
"""

import pytest
import os
import json
import logging
from unittest.mock import Mock, patch, MagicMock
from moto import mock_aws
import boto3

# Import the configuration module
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from config import ConfigurationManager, CloudflareCredentials, ConfigurationError


class TestConfigurationManager:
    """Test cases for ConfigurationManager class."""
    
    def test_configuration_manager_initialization(self):
        """Test that ConfigurationManager can be initialized."""
        # Act
        config_manager = ConfigurationManager()
        
        # Assert
        assert config_manager is not None
        assert config_manager.logger is not None
    
    def test_configuration_manager_with_custom_logger(self):
        """Test ConfigurationManager initialization with custom logger."""
        # Arrange
        custom_logger = logging.getLogger("test_logger")
        
        # Act
        config_manager = ConfigurationManager(logger=custom_logger)
        
        # Assert
        assert config_manager.logger is custom_logger
    
    @patch.dict(os.environ, {
        'SECRETS_MANAGER_SECRET_NAME': 'test-secret',
        'DYNAMODB_TABLE_NAME': 'test-table'
    })
    def test_load_environment_variables_success(self):
        """Test successful loading of required environment variables."""
        # Arrange
        config_manager = ConfigurationManager()
        
        # Act
        env_config = config_manager._load_environment_variables()
        
        # Assert
        assert env_config['secrets_manager_secret_name'] == 'test-secret'
        assert env_config['dynamodb_table_name'] == 'test-table'
        assert env_config['retry_max_attempts'] == 3  # default value
        assert env_config['api_timeout_seconds'] == 30  # default value
    
    @patch.dict(os.environ, {
        'SECRETS_MANAGER_SECRET_NAME': 'test-secret',
        'DYNAMODB_TABLE_NAME': 'test-table',
        'RETRY_MAX_ATTEMPTS': '5',
        'API_TIMEOUT_SECONDS': '60'
    })
    def test_load_environment_variables_with_optional_values(self):
        """Test loading environment variables with optional values provided."""
        # Arrange
        config_manager = ConfigurationManager()
        
        # Act
        env_config = config_manager._load_environment_variables()
        
        # Assert
        assert env_config['retry_max_attempts'] == 5
        assert env_config['api_timeout_seconds'] == 60
    
    def test_load_environment_variables_missing_required(self):
        """Test that missing required environment variables raise ConfigurationError."""
        # Arrange
        config_manager = ConfigurationManager()
        
        # Clear environment variables
        with patch.dict(os.environ, {}, clear=True):
            # Act & Assert
            with pytest.raises(ConfigurationError) as exc_info:
                config_manager._load_environment_variables()
            
            assert "Missing required environment variables" in str(exc_info.value)
    
    @mock_aws
    def test_get_cloudflare_credentials_success(self):
        """Test successful retrieval of Cloudflare credentials from Secrets Manager."""
        # Arrange
        secret_name = "test-cloudflare-secret"
        secret_value = {
            "api_token": "test-token",
            "account_id": "test-account",
            "kv_namespace_id": "test-namespace-id",
            "kv_namespace": "test-namespace"
        }
        
        # Create mock secret in Secrets Manager
        client = boto3.client('secretsmanager', region_name='us-east-1')
        client.create_secret(
            Name=secret_name,
            SecretString=json.dumps(secret_value)
        )
        
        config_manager = ConfigurationManager()
        
        # Act
        credentials = config_manager.get_cloudflare_credentials(secret_name)
        
        # Assert
        assert isinstance(credentials, CloudflareCredentials)
        assert credentials.api_token == "test-token"
        assert credentials.account_id == "test-account"
        assert credentials.kv_namespace_id == "test-namespace-id"
        assert credentials.kv_namespace == "test-namespace"
    
    @mock_aws
    def test_get_cloudflare_credentials_secret_not_found(self):
        """Test handling of non-existent secret."""
        # Arrange
        config_manager = ConfigurationManager()
        
        # Act & Assert
        with pytest.raises(ConfigurationError) as exc_info:
            config_manager.get_cloudflare_credentials("non-existent-secret")
        
        assert "Secret not found" in str(exc_info.value)
    
    @mock_aws
    def test_get_cloudflare_credentials_invalid_json(self):
        """Test handling of invalid JSON in secret."""
        # Arrange
        secret_name = "test-invalid-secret"
        
        # Create mock secret with invalid JSON
        client = boto3.client('secretsmanager', region_name='us-east-1')
        client.create_secret(
            Name=secret_name,
            SecretString="invalid json content"
        )
        
        config_manager = ConfigurationManager()
        
        # Act & Assert
        with pytest.raises(ConfigurationError) as exc_info:
            config_manager.get_cloudflare_credentials(secret_name)
        
        assert "Invalid JSON in secret" in str(exc_info.value)
    
    @mock_aws
    def test_get_cloudflare_credentials_missing_fields(self):
        """Test handling of missing required fields in secret."""
        # Arrange
        secret_name = "test-incomplete-secret"
        secret_value = {
            "api_token": "test-token",
            # Missing other required fields
        }
        
        # Create mock secret with incomplete data
        client = boto3.client('secretsmanager', region_name='us-east-1')
        client.create_secret(
            Name=secret_name,
            SecretString=json.dumps(secret_value)
        )
        
        config_manager = ConfigurationManager()
        
        # Act & Assert
        with pytest.raises(ConfigurationError) as exc_info:
            config_manager.get_cloudflare_credentials(secret_name)
        
        assert "Missing required fields in secret" in str(exc_info.value)
    @mock_aws
    @patch.dict(os.environ, {
        'SECRETS_MANAGER_SECRET_NAME': 'test-secret',
        'DYNAMODB_TABLE_NAME': 'test-table',
        'RETRY_MAX_ATTEMPTS': '5',
        'API_TIMEOUT_SECONDS': '45'
    })
    def test_load_config_complete_integration(self):
        """Test complete configuration loading integration."""
        # Arrange
        secret_name = "test-secret"
        secret_value = {
            "api_token": "test-token-123",
            "account_id": "test-account-456",
            "kv_namespace_id": "test-namespace-789",
            "kv_namespace": "test-namespace-name"
        }
        
        # Create mock secret in Secrets Manager
        client = boto3.client('secretsmanager', region_name='us-east-1')
        client.create_secret(
            Name=secret_name,
            SecretString=json.dumps(secret_value)
        )
        
        config_manager = ConfigurationManager()
        
        # Act
        config = config_manager.load_config()
        
        # Assert
        assert config['secrets_manager_secret_name'] == 'test-secret'
        assert config['dynamodb_table_name'] == 'test-table'
        assert config['retry_max_attempts'] == 5
        assert config['api_timeout_seconds'] == 45
        
        credentials = config['cloudflare_credentials']
        assert isinstance(credentials, CloudflareCredentials)
        assert credentials.api_token == "test-token-123"
        assert credentials.account_id == "test-account-456"
        assert credentials.kv_namespace_id == "test-namespace-789"
        assert credentials.kv_namespace == "test-namespace-name"
    
    def test_config_caching(self):
        """Test that configuration is cached after first load."""
        # Arrange
        config_manager = ConfigurationManager()
        
        # Mock the _load_environment_variables and get_cloudflare_credentials methods
        with patch.object(config_manager, '_load_environment_variables') as mock_env, \
             patch.object(config_manager, 'get_cloudflare_credentials') as mock_creds:
            
            mock_env.return_value = {
                'secrets_manager_secret_name': 'test-secret',
                'dynamodb_table_name': 'test-table',
                'retry_max_attempts': 3,
                'api_timeout_seconds': 30
            }
            mock_creds.return_value = CloudflareCredentials(
                api_token="test-token",
                account_id="test-account",
                kv_namespace_id="test-namespace-id",
                kv_namespace="test-namespace"
            )
            
            # Act - Load config twice
            config1 = config_manager.load_config()
            config2 = config_manager.load_config()
            
            # Assert - Methods should only be called once due to caching
            mock_env.assert_called_once()
            mock_creds.assert_called_once()
            assert config1 is config2  # Same object reference due to caching