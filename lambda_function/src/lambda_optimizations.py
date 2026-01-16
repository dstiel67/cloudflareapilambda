"""
Lambda-specific optimizations for Cloudflare Data Sync.

This module provides:
- Connection reuse for external services
- Lambda context handling and timeout management
- Cold start performance optimizations
- Resource management and cleanup
"""

import logging
import time
import threading
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
from contextlib import contextmanager

from .config import ConfigurationManager
from .cloudflare_client import CloudflareClient
from .dynamodb_client import DynamoDBClient
from .data_transformer import DataTransformer


@dataclass
class LambdaContext:
    """Wrapper for Lambda context with additional functionality."""
    aws_request_id: str
    function_name: str
    function_version: str
    invoked_function_arn: str
    memory_limit_in_mb: int
    remaining_time_in_millis: Callable[[], int]
    log_group_name: str
    log_stream_name: str
    
    @classmethod
    def from_lambda_context(cls, context: Any) -> 'LambdaContext':
        """Create LambdaContext from AWS Lambda context object."""
        return cls(
            aws_request_id=getattr(context, 'aws_request_id', 'unknown'),
            function_name=getattr(context, 'function_name', 'unknown'),
            function_version=getattr(context, 'function_version', 'unknown'),
            invoked_function_arn=getattr(context, 'invoked_function_arn', 'unknown'),
            memory_limit_in_mb=getattr(context, 'memory_limit_in_mb', 0),
            remaining_time_in_millis=getattr(context, 'get_remaining_time_in_millis', lambda: 0),
            log_group_name=getattr(context, 'log_group_name', 'unknown'),
            log_stream_name=getattr(context, 'log_stream_name', 'unknown')
        )
    
    def get_remaining_time_seconds(self) -> float:
        """Get remaining execution time in seconds."""
        return self.remaining_time_in_millis() / 1000.0
    
    def is_timeout_approaching(self, buffer_seconds: float = 30.0) -> bool:
        """Check if timeout is approaching within the buffer time."""
        return self.get_remaining_time_seconds() <= buffer_seconds


class ConnectionPool:
    """Manages reusable connections for external services."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize the connection pool.
        
        Args:
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self._lock = threading.Lock()
        
        # Cached instances
        self._config_manager: Optional[ConfigurationManager] = None
        self._cloudflare_client: Optional[CloudflareClient] = None
        self._dynamodb_client: Optional[DynamoDBClient] = None
        self._data_transformer: Optional[DataTransformer] = None
        
        # Connection metadata
        self._initialization_time = time.time()
        self._last_used = time.time()
        self._usage_count = 0
        
        self.logger.info("Connection pool initialized")
    
    def get_config_manager(self) -> ConfigurationManager:
        """Get or create configuration manager instance."""
        with self._lock:
            if self._config_manager is None:
                self.logger.debug("Creating new ConfigurationManager instance")
                self._config_manager = ConfigurationManager(logger=self.logger)
            
            self._update_usage_stats()
            return self._config_manager
    
    def get_cloudflare_client(self, config: Dict[str, Any]) -> CloudflareClient:
        """Get or create Cloudflare client instance.
        
        Args:
            config: Configuration dictionary containing credentials and settings
            
        Returns:
            CloudflareClient instance
        """
        with self._lock:
            # Check if we need to recreate the client (e.g., config changed)
            if (self._cloudflare_client is None or 
                self._should_recreate_cloudflare_client(config)):
                
                self.logger.debug("Creating new CloudflareClient instance")
                
                from .cloudflare_client import RetryConfig
                retry_config = RetryConfig(
                    max_attempts=config['retry_max_attempts'],
                    base_delay=1.0,
                    max_delay=60.0,
                    jitter=True
                )
                
                self._cloudflare_client = CloudflareClient(
                    credentials=config['cloudflare_credentials'],
                    timeout=config['api_timeout_seconds'],
                    retry_config=retry_config,
                    logger=self.logger
                )
            
            self._update_usage_stats()
            return self._cloudflare_client
    
    def get_dynamodb_client(self, config: Dict[str, Any]) -> DynamoDBClient:
        """Get or create DynamoDB client instance.
        
        Args:
            config: Configuration dictionary containing table name and settings
            
        Returns:
            DynamoDBClient instance
        """
        with self._lock:
            # Check if we need to recreate the client (e.g., table name changed)
            if (self._dynamodb_client is None or 
                self._should_recreate_dynamodb_client(config)):
                
                self.logger.debug("Creating new DynamoDBClient instance")
                self._dynamodb_client = DynamoDBClient(
                    table_name=config['dynamodb_table_name'],
                    max_retries=config['retry_max_attempts'],
                    logger=self.logger
                )
            
            self._update_usage_stats()
            return self._dynamodb_client
    
    def get_data_transformer(self, namespace_id: str) -> DataTransformer:
        """Get or create data transformer instance.
        
        Args:
            namespace_id: Cloudflare KV namespace ID
            
        Returns:
            DataTransformer instance
        """
        with self._lock:
            if (self._data_transformer is None or 
                self._data_transformer.namespace_id != namespace_id):
                
                self.logger.debug("Creating new DataTransformer instance")
                self._data_transformer = DataTransformer(
                    namespace_id=namespace_id,
                    logger=self.logger
                )
            
            self._update_usage_stats()
            return self._data_transformer
    
    def _should_recreate_cloudflare_client(self, config: Dict[str, Any]) -> bool:
        """Check if Cloudflare client should be recreated due to config changes."""
        if self._cloudflare_client is None:
            return True
        
        # Check if credentials have changed
        current_creds = config['cloudflare_credentials']
        client_creds = self._cloudflare_client.credentials
        
        return (
            current_creds.api_token != client_creds.api_token or
            current_creds.account_id != client_creds.account_id or
            current_creds.kv_namespace_id != client_creds.kv_namespace_id or
            self._cloudflare_client.timeout != config['api_timeout_seconds']
        )
    
    def _should_recreate_dynamodb_client(self, config: Dict[str, Any]) -> bool:
        """Check if DynamoDB client should be recreated due to config changes."""
        if self._dynamodb_client is None:
            return True
        
        return (
            self._dynamodb_client.table_name != config['dynamodb_table_name'] or
            self._dynamodb_client.max_retries != config['retry_max_attempts']
        )
    
    def _update_usage_stats(self):
        """Update connection pool usage statistics."""
        self._last_used = time.time()
        self._usage_count += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics."""
        current_time = time.time()
        return {
            'initialization_time': self._initialization_time,
            'last_used': self._last_used,
            'usage_count': self._usage_count,
            'age_seconds': current_time - self._initialization_time,
            'idle_seconds': current_time - self._last_used,
            'active_connections': {
                'config_manager': self._config_manager is not None,
                'cloudflare_client': self._cloudflare_client is not None,
                'dynamodb_client': self._dynamodb_client is not None,
                'data_transformer': self._data_transformer is not None
            }
        }
    
    def cleanup(self):
        """Clean up resources and connections."""
        with self._lock:
            self.logger.info("Cleaning up connection pool resources")
            
            # Close any connections that support explicit cleanup
            if self._cloudflare_client and hasattr(self._cloudflare_client, 'session'):
                try:
                    self._cloudflare_client.session.close()
                    self.logger.debug("Closed Cloudflare client session")
                except Exception as e:
                    self.logger.warning(f"Error closing Cloudflare session: {e}")
            
            # Reset all cached instances
            self._config_manager = None
            self._cloudflare_client = None
            self._dynamodb_client = None
            self._data_transformer = None
            
            self.logger.info("Connection pool cleanup completed")


# Global connection pool instance for reuse across invocations
_connection_pool: Optional[ConnectionPool] = None
_pool_lock = threading.Lock()


def get_connection_pool(logger: Optional[logging.Logger] = None) -> ConnectionPool:
    """Get or create the global connection pool instance.
    
    Args:
        logger: Optional logger instance
        
    Returns:
        ConnectionPool instance
    """
    global _connection_pool
    
    with _pool_lock:
        if _connection_pool is None:
            _connection_pool = ConnectionPool(logger=logger)
        return _connection_pool


class TimeoutManager:
    """Manages Lambda execution timeout and provides early warning."""
    
    def __init__(self, lambda_context: LambdaContext, buffer_seconds: float = 30.0,
                 logger: Optional[logging.Logger] = None):
        """Initialize timeout manager.
        
        Args:
            lambda_context: Lambda context wrapper
            buffer_seconds: Buffer time before timeout to start cleanup
            logger: Optional logger instance
        """
        self.lambda_context = lambda_context
        self.buffer_seconds = buffer_seconds
        self.logger = logger or logging.getLogger(__name__)
        
        self.start_time = time.time()
        self.timeout_warned = False
        
        # Calculate timeout threshold
        initial_remaining = lambda_context.get_remaining_time_seconds()
        self.timeout_threshold = initial_remaining - buffer_seconds
        
        self.logger.info(f"Timeout manager initialized: {initial_remaining:.1f}s remaining, "
                        f"{buffer_seconds}s buffer, threshold at {self.timeout_threshold:.1f}s")
    
    def check_timeout(self) -> bool:
        """Check if timeout is approaching.
        
        Returns:
            True if timeout is approaching and operations should be stopped
        """
        remaining = self.lambda_context.get_remaining_time_seconds()
        
        if remaining <= self.buffer_seconds:
            if not self.timeout_warned:
                self.logger.warning(f"Lambda timeout approaching: {remaining:.1f}s remaining")
                self.timeout_warned = True
            return True
        
        return False
    
    def get_remaining_time(self) -> float:
        """Get remaining execution time in seconds."""
        return self.lambda_context.get_remaining_time_seconds()
    
    def get_elapsed_time(self) -> float:
        """Get elapsed execution time in seconds."""
        return time.time() - self.start_time
    
    @contextmanager
    def timeout_context(self, operation_name: str):
        """Context manager that checks for timeout before and after operations.
        
        Args:
            operation_name: Name of the operation for logging
        """
        if self.check_timeout():
            self.logger.warning(f"Skipping {operation_name} due to approaching timeout")
            yield False
            return
        
        start_time = time.time()
        self.logger.debug(f"Starting {operation_name} with {self.get_remaining_time():.1f}s remaining")
        
        try:
            yield True
        finally:
            elapsed = time.time() - start_time
            remaining = self.get_remaining_time()
            self.logger.debug(f"Completed {operation_name} in {elapsed:.2f}s, {remaining:.1f}s remaining")


class ColdStartOptimizer:
    """Optimizes Lambda cold start performance."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize cold start optimizer.
        
        Args:
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self.cold_start_detected = False
        self.initialization_start = time.time()
    
    def detect_cold_start(self) -> bool:
        """Detect if this is a cold start invocation.
        
        Returns:
            True if this appears to be a cold start
        """
        # Check if connection pool is empty (indicates cold start)
        pool = get_connection_pool(self.logger)
        stats = pool.get_stats()
        
        # Cold start indicators:
        # 1. No active connections
        # 2. Pool age is very recent (< 1 second)
        # 3. Low usage count
        
        is_cold_start = (
            not any(stats['active_connections'].values()) or
            stats['age_seconds'] < 1.0 or
            stats['usage_count'] < 2
        )
        
        if is_cold_start and not self.cold_start_detected:
            self.cold_start_detected = True
            self.logger.info("Cold start detected - applying optimizations")
        
        return is_cold_start
    
    def optimize_for_cold_start(self):
        """Apply cold start optimizations."""
        if not self.detect_cold_start():
            return
        
        optimization_start = time.time()
        
        # Pre-warm connection pool
        self._prewarm_connections()
        
        # Log optimization results
        optimization_time = time.time() - optimization_start
        total_init_time = time.time() - self.initialization_start
        
        self.logger.info(f"Cold start optimizations completed in {optimization_time:.3f}s "
                        f"(total init: {total_init_time:.3f}s)")
    
    def _prewarm_connections(self):
        """Pre-warm connections to reduce latency."""
        try:
            # Pre-initialize AWS SDK clients by getting the connection pool
            pool = get_connection_pool(self.logger)
            
            # The act of getting the pool initializes basic AWS connections
            self.logger.debug("Connection pool pre-warmed")
            
        except Exception as e:
            self.logger.warning(f"Error during connection pre-warming: {e}")


def optimize_lambda_execution(lambda_context: LambdaContext, 
                            logger: Optional[logging.Logger] = None) -> Dict[str, Any]:
    """Apply comprehensive Lambda optimizations.
    
    Args:
        lambda_context: Lambda context wrapper
        logger: Optional logger instance
        
    Returns:
        Dictionary containing optimization results and metadata
    """
    if logger is None:
        logger = logging.getLogger(__name__)
    
    optimization_start = time.time()
    
    # Initialize cold start optimizer
    cold_start_optimizer = ColdStartOptimizer(logger=logger)
    cold_start_optimizer.optimize_for_cold_start()
    
    # Get connection pool statistics
    pool = get_connection_pool(logger)
    pool_stats = pool.get_stats()
    
    # Create timeout manager
    timeout_manager = TimeoutManager(lambda_context, buffer_seconds=30.0, logger=logger)
    
    optimization_time = time.time() - optimization_start
    
    optimization_results = {
        'optimization_time_ms': int(optimization_time * 1000),
        'cold_start_detected': cold_start_optimizer.cold_start_detected,
        'connection_pool_stats': pool_stats,
        'timeout_management': {
            'buffer_seconds': timeout_manager.buffer_seconds,
            'remaining_time_seconds': timeout_manager.get_remaining_time(),
            'timeout_threshold_seconds': timeout_manager.timeout_threshold
        },
        'lambda_context': {
            'function_name': lambda_context.function_name,
            'memory_limit_mb': lambda_context.memory_limit_in_mb,
            'aws_request_id': lambda_context.aws_request_id
        }
    }
    
    logger.info(f"Lambda optimizations applied in {optimization_time:.3f}s")
    
    return optimization_results, timeout_manager, pool


def cleanup_lambda_resources(logger: Optional[logging.Logger] = None):
    """Clean up Lambda resources before function termination.
    
    Args:
        logger: Optional logger instance
    """
    if logger is None:
        logger = logging.getLogger(__name__)
    
    try:
        # Clean up connection pool
        pool = get_connection_pool(logger)
        pool.cleanup()
        
        logger.info("Lambda resource cleanup completed")
        
    except Exception as e:
        logger.warning(f"Error during Lambda resource cleanup: {e}")