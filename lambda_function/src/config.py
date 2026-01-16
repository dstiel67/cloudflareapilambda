"""
Configuration management for Cloudflare Data Sync Lambda function.

This module handles:
- Environment variable loading and validation
- AWS Secrets Manager credential retrieval
- Configuration error handling and logging
"""

import os
import json
import logging
from dataclasses import dataclass
from typing import Dict, Any, Optional
import boto3
from botocore.exceptions import ClientError, NoCredentialsError


@dataclass
class CloudflareCredentials:
    """Cloudflare API credentials retrieved from Secrets Manager."""
    api_token: str
    account_id: str
    kv_namespace_id: str
    kv_namespace: str


class ConfigurationError(Exception):
    """Raised when configuration loading fails."""
    pass


class ConfigurationManager:
    """Manages configuration from environment variables and AWS Secrets Manager."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize the configuration manager.
        
        Args:
            logger: Optional logger instance. If not provided, creates a new one.
        """
        self.logger = logger or logging.getLogger(__name__)
        self._secrets_client = None
        self._config_cache = None
    
    @property
    def secrets_client(self):
        """Lazy initialization of Secrets Manager client."""
        if self._secrets_client is None:
            try:
                self._secrets_client = boto3.client('secretsmanager')
            except NoCredentialsError as e:
                self.logger.error("Failed to create Secrets Manager client: No AWS credentials found")
                raise ConfigurationError("AWS credentials not configured") from e
        return self._secrets_client
    
    def load_config(self) -> Dict[str, Any]:
        """Load complete configuration from environment variables and Secrets Manager.
        
        Returns:
            Dictionary containing all configuration values.
            
        Raises:
            ConfigurationError: If required configuration is missing or invalid.
        """
        if self._config_cache is not None:
            return self._config_cache
            
        self.logger.info("Loading configuration from environment variables and Secrets Manager")
        
        try:
            # Load environment variables
            env_config = self._load_environment_variables()
            
            # Load Cloudflare credentials from Secrets Manager
            cloudflare_creds = self.get_cloudflare_credentials(env_config['secrets_manager_secret_name'])
            
            # Combine configuration
            config = {
                **env_config,
                'cloudflare_credentials': cloudflare_creds
            }
            
            self._config_cache = config
            self.logger.info("Configuration loaded successfully")
            return config
            
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {str(e)}")
            raise ConfigurationError(f"Configuration loading failed: {str(e)}") from e
    
    def _load_environment_variables(self) -> Dict[str, Any]:
        """Load and validate required environment variables.
        
        Returns:
            Dictionary of environment variable values.
            
        Raises:
            ConfigurationError: If required environment variables are missing.
        """
        required_vars = {
            'SECRETS_MANAGER_SECRET_NAME': 'secrets_manager_secret_name',
            'DYNAMODB_TABLE_NAME': 'dynamodb_table_name'
        }
        
        optional_vars = {
            'RETRY_MAX_ATTEMPTS': ('retry_max_attempts', int, 3),
            'API_TIMEOUT_SECONDS': ('api_timeout_seconds', int, 30)
        }
        
        config = {}
        missing_vars = []
        
        # Check required variables
        for env_var, config_key in required_vars.items():
            value = os.environ.get(env_var)
            if not value:
                missing_vars.append(env_var)
            else:
                config[config_key] = value
                self.logger.debug(f"Loaded required environment variable: {env_var}")
        
        if missing_vars:
            error_msg = f"Missing required environment variables: {', '.join(missing_vars)}"
            self.logger.error(error_msg)
            raise ConfigurationError(error_msg)
        
        # Load optional variables with defaults
        for env_var, (config_key, var_type, default_value) in optional_vars.items():
            value = os.environ.get(env_var)
            if value:
                try:
                    config[config_key] = var_type(value)
                    self.logger.debug(f"Loaded optional environment variable: {env_var}={value}")
                except ValueError as e:
                    self.logger.warning(f"Invalid value for {env_var}: {value}, using default: {default_value}")
                    config[config_key] = default_value
            else:
                config[config_key] = default_value
                self.logger.debug(f"Using default value for {env_var}: {default_value}")
        
        return config
    
    def get_cloudflare_credentials(self, secret_name: str) -> CloudflareCredentials:
        """Retrieve Cloudflare credentials from AWS Secrets Manager.
        
        Args:
            secret_name: Name of the secret in Secrets Manager.
            
        Returns:
            CloudflareCredentials object with API credentials.
            
        Raises:
            ConfigurationError: If secret retrieval or parsing fails.
        """
        self.logger.info(f"Retrieving Cloudflare credentials from Secrets Manager: {secret_name}")
        
        try:
            response = self.secrets_client.get_secret_value(SecretId=secret_name)
            secret_string = response['SecretString']
            
            # Parse the JSON secret
            try:
                secret_data = json.loads(secret_string)
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse secret JSON: {str(e)}")
                raise ConfigurationError(f"Invalid JSON in secret {secret_name}") from e
            
            # Validate required fields
            required_fields = ['api_token', 'account_id', 'kv_namespace_id', 'kv_namespace']
            missing_fields = [field for field in required_fields if not secret_data.get(field)]
            
            if missing_fields:
                error_msg = f"Missing required fields in secret {secret_name}: {', '.join(missing_fields)}"
                self.logger.error(error_msg)
                raise ConfigurationError(error_msg)
            
            credentials = CloudflareCredentials(
                api_token=secret_data['api_token'],
                account_id=secret_data['account_id'],
                kv_namespace_id=secret_data['kv_namespace_id'],
                kv_namespace=secret_data['kv_namespace']
            )
            
            self.logger.info("Cloudflare credentials retrieved successfully")
            return credentials
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ResourceNotFoundException':
                error_msg = f"Secret not found: {secret_name}"
            elif error_code == 'AccessDeniedException':
                error_msg = f"Access denied to secret: {secret_name}"
            else:
                error_msg = f"AWS error retrieving secret {secret_name}: {error_code}"
            
            self.logger.error(error_msg)
            raise ConfigurationError(error_msg) from e
        
        except Exception as e:
            error_msg = f"Unexpected error retrieving secret {secret_name}: {str(e)}"
            self.logger.error(error_msg)
            raise ConfigurationError(error_msg) from e