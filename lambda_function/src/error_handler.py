"""
Error handling and logging for Cloudflare Data Sync.

This module handles:
- Categorized error handling (config, auth, API, storage)
- Comprehensive audit logging for all operations
- Execution statistics and timing information
- Structured logging with consistent formatting
"""

import logging
import time
import traceback
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Union
from enum import Enum


class ErrorCategory(Enum):
    """Categories of errors for structured handling."""
    CONFIGURATION = "configuration"
    AUTHENTICATION = "authentication"
    API = "api"
    STORAGE = "storage"
    DATA_VALIDATION = "data_validation"
    NETWORK = "network"
    UNKNOWN = "unknown"


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ErrorContext:
    """Context information for error handling."""
    operation: str
    component: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    request_id: Optional[str] = None
    additional_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionStatistics:
    """Statistics for tracking execution metrics."""
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    execution_time_ms: Optional[int] = None
    
    # Operation counters
    cloudflare_api_calls: int = 0
    dynamodb_writes: int = 0
    records_processed: int = 0
    records_stored: int = 0
    records_failed: int = 0
    
    # Error counters by category
    configuration_errors: int = 0
    authentication_errors: int = 0
    api_errors: int = 0
    storage_errors: int = 0
    data_validation_errors: int = 0
    network_errors: int = 0
    unknown_errors: int = 0
    
    # Retry statistics
    total_retries: int = 0
    successful_retries: int = 0
    failed_retries: int = 0
    
    def finish_execution(self):
        """Mark execution as finished and calculate timing."""
        self.end_time = time.time()
        self.execution_time_ms = int((self.end_time - self.start_time) * 1000)
    
    def increment_error_count(self, category: ErrorCategory):
        """Increment error count for the specified category."""
        if category == ErrorCategory.CONFIGURATION:
            self.configuration_errors += 1
        elif category == ErrorCategory.AUTHENTICATION:
            self.authentication_errors += 1
        elif category == ErrorCategory.API:
            self.api_errors += 1
        elif category == ErrorCategory.STORAGE:
            self.storage_errors += 1
        elif category == ErrorCategory.DATA_VALIDATION:
            self.data_validation_errors += 1
        elif category == ErrorCategory.NETWORK:
            self.network_errors += 1
        else:
            self.unknown_errors += 1
    
    def get_total_errors(self) -> int:
        """Get total number of errors across all categories."""
        return (
            self.configuration_errors + self.authentication_errors + 
            self.api_errors + self.storage_errors + self.data_validation_errors +
            self.network_errors + self.unknown_errors
        )
    
    def get_success_rate(self) -> float:
        """Calculate success rate for processed records."""
        if self.records_processed == 0:
            return 0.0
        return self.records_stored / self.records_processed
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert statistics to dictionary format."""
        return {
            'execution_time_ms': self.execution_time_ms,
            'cloudflare_api_calls': self.cloudflare_api_calls,
            'dynamodb_writes': self.dynamodb_writes,
            'records_processed': self.records_processed,
            'records_stored': self.records_stored,
            'records_failed': self.records_failed,
            'success_rate': round(self.get_success_rate(), 4),
            'total_errors': self.get_total_errors(),
            'error_breakdown': {
                'configuration_errors': self.configuration_errors,
                'authentication_errors': self.authentication_errors,
                'api_errors': self.api_errors,
                'storage_errors': self.storage_errors,
                'data_validation_errors': self.data_validation_errors,
                'network_errors': self.network_errors,
                'unknown_errors': self.unknown_errors
            },
            'retry_statistics': {
                'total_retries': self.total_retries,
                'successful_retries': self.successful_retries,
                'failed_retries': self.failed_retries,
                'retry_success_rate': (
                    self.successful_retries / self.total_retries 
                    if self.total_retries > 0 else 0.0
                )
            }
        }


class ErrorHandler:
    """Centralized error handling and structured logging for the Lambda function."""
    
    def __init__(self, logger: Optional[logging.Logger] = None, request_id: Optional[str] = None):
        """Initialize the error handler.
        
        Args:
            logger: Optional logger instance. If not provided, creates a new one.
            request_id: Optional request ID for tracking operations across components.
        """
        self.logger = logger or logging.getLogger(__name__)
        self.request_id = request_id
        self.statistics = ExecutionStatistics()
        self.audit_log: List[Dict[str, Any]] = []
        
        # Configure structured logging format
        self._configure_logging()
        
        # Log initialization
        self.log_audit_event(
            event_type="error_handler_initialized",
            details={"request_id": self.request_id}
        )
    
    def _configure_logging(self):
        """Configure structured logging format for consistent output."""
        # Create a custom formatter for structured logging
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Apply formatter to all handlers if not already configured
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
        else:
            # Update existing handlers with our formatter
            for handler in self.logger.handlers:
                if not handler.formatter:
                    handler.setFormatter(formatter)
    
    def handle_configuration_error(self, error: Exception, context: ErrorContext) -> Dict[str, Any]:
        """Handle configuration-related errors.
        
        Args:
            error: The configuration error that occurred
            context: Context information about the error
            
        Returns:
            Structured error information
        """
        return self._handle_categorized_error(
            error=error,
            category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.CRITICAL,
            context=context,
            is_retryable=False
        )
    
    def handle_authentication_error(self, error: Exception, context: ErrorContext) -> Dict[str, Any]:
        """Handle authentication-related errors.
        
        Args:
            error: The authentication error that occurred
            context: Context information about the error
            
        Returns:
            Structured error information
        """
        return self._handle_categorized_error(
            error=error,
            category=ErrorCategory.AUTHENTICATION,
            severity=ErrorSeverity.HIGH,
            context=context,
            is_retryable=False
        )
    
    def handle_api_error(self, error: Exception, context: ErrorContext, 
                        is_retryable: bool = True) -> Dict[str, Any]:
        """Handle API-related errors.
        
        Args:
            error: The API error that occurred
            context: Context information about the error
            is_retryable: Whether this error can be retried
            
        Returns:
            Structured error information
        """
        # Determine severity based on error type and retryability
        severity = ErrorSeverity.MEDIUM if is_retryable else ErrorSeverity.HIGH
        
        return self._handle_categorized_error(
            error=error,
            category=ErrorCategory.API,
            severity=severity,
            context=context,
            is_retryable=is_retryable
        )
    
    def handle_storage_error(self, error: Exception, context: ErrorContext,
                           is_retryable: bool = True) -> Dict[str, Any]:
        """Handle storage-related errors.
        
        Args:
            error: The storage error that occurred
            context: Context information about the error
            is_retryable: Whether this error can be retried
            
        Returns:
            Structured error information
        """
        severity = ErrorSeverity.MEDIUM if is_retryable else ErrorSeverity.HIGH
        
        return self._handle_categorized_error(
            error=error,
            category=ErrorCategory.STORAGE,
            severity=severity,
            context=context,
            is_retryable=is_retryable
        )
    
    def handle_data_validation_error(self, error: Exception, context: ErrorContext) -> Dict[str, Any]:
        """Handle data validation errors.
        
        Args:
            error: The validation error that occurred
            context: Context information about the error
            
        Returns:
            Structured error information
        """
        return self._handle_categorized_error(
            error=error,
            category=ErrorCategory.DATA_VALIDATION,
            severity=ErrorSeverity.LOW,
            context=context,
            is_retryable=False
        )
    
    def handle_network_error(self, error: Exception, context: ErrorContext) -> Dict[str, Any]:
        """Handle network-related errors.
        
        Args:
            error: The network error that occurred
            context: Context information about the error
            
        Returns:
            Structured error information
        """
        return self._handle_categorized_error(
            error=error,
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.MEDIUM,
            context=context,
            is_retryable=True
        )
    
    def _handle_categorized_error(self, error: Exception, category: ErrorCategory,
                                severity: ErrorSeverity, context: ErrorContext,
                                is_retryable: bool) -> Dict[str, Any]:
        """Handle an error with categorization and structured logging.
        
        Args:
            error: The error that occurred
            category: Error category
            severity: Error severity level
            context: Context information
            is_retryable: Whether the error can be retried
            
        Returns:
            Structured error information
        """
        # Update statistics
        self.statistics.increment_error_count(category)
        
        # Create structured error information
        error_info = {
            'error_id': f"{category.value}_{int(time.time() * 1000)}",
            'category': category.value,
            'severity': severity.value,
            'type': type(error).__name__,
            'message': str(error),
            'is_retryable': is_retryable,
            'timestamp': context.timestamp,
            'operation': context.operation,
            'component': context.component,
            'request_id': context.request_id or self.request_id,
            'additional_data': context.additional_data
        }
        
        # Add stack trace for high severity errors
        if severity in (ErrorSeverity.HIGH, ErrorSeverity.CRITICAL):
            error_info['stack_trace'] = traceback.format_exc()
        
        # Log the error with appropriate level
        log_level = self._get_log_level_for_severity(severity)
        log_message = self._format_error_log_message(error_info)
        
        self.logger.log(log_level, log_message)
        
        # Add to audit log
        self.log_audit_event(
            event_type="error_handled",
            details=error_info
        )
        
        return error_info
    
    def _get_log_level_for_severity(self, severity: ErrorSeverity) -> int:
        """Get logging level for error severity.
        
        Args:
            severity: Error severity level
            
        Returns:
            Logging level constant
        """
        severity_to_level = {
            ErrorSeverity.LOW: logging.INFO,
            ErrorSeverity.MEDIUM: logging.WARNING,
            ErrorSeverity.HIGH: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL
        }
        return severity_to_level.get(severity, logging.ERROR)
    
    def _format_error_log_message(self, error_info: Dict[str, Any]) -> str:
        """Format error information for logging.
        
        Args:
            error_info: Structured error information
            
        Returns:
            Formatted log message
        """
        return (
            f"[{error_info['category'].upper()}] {error_info['type']}: {error_info['message']} "
            f"| Operation: {error_info['operation']} | Component: {error_info['component']} "
            f"| Retryable: {error_info['is_retryable']} | ID: {error_info['error_id']}"
        )
    
    def log_audit_event(self, event_type: str, details: Dict[str, Any] = None):
        """Log an audit event for comprehensive operation tracking.
        
        Args:
            event_type: Type of event being logged
            details: Additional event details
        """
        audit_entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'event_type': event_type,
            'request_id': self.request_id,
            'details': details or {}
        }
        
        self.audit_log.append(audit_entry)
        
        # Log audit events at INFO level for comprehensive tracking
        self.logger.info(f"AUDIT: {event_type} | Request: {self.request_id} | Details: {details}")
    
    def log_operation_start(self, operation: str, component: str, details: Dict[str, Any] = None):
        """Log the start of an operation.
        
        Args:
            operation: Name of the operation starting
            component: Component performing the operation
            details: Additional operation details
        """
        self.log_audit_event(
            event_type="operation_start",
            details={
                'operation': operation,
                'component': component,
                'start_time': time.time(),
                **(details or {})
            }
        )
    
    def log_operation_end(self, operation: str, component: str, success: bool, 
                         details: Dict[str, Any] = None):
        """Log the end of an operation.
        
        Args:
            operation: Name of the operation ending
            component: Component that performed the operation
            success: Whether the operation was successful
            details: Additional operation details
        """
        self.log_audit_event(
            event_type="operation_end",
            details={
                'operation': operation,
                'component': component,
                'success': success,
                'end_time': time.time(),
                **(details or {})
            }
        )
    
    def log_retry_attempt(self, operation: str, attempt: int, max_attempts: int, 
                         error: Exception = None):
        """Log a retry attempt.
        
        Args:
            operation: Operation being retried
            attempt: Current attempt number
            max_attempts: Maximum number of attempts
            error: Error that triggered the retry (optional)
        """
        self.statistics.total_retries += 1
        
        details = {
            'operation': operation,
            'attempt': attempt,
            'max_attempts': max_attempts,
            'retry_reason': str(error) if error else 'Unknown'
        }
        
        self.log_audit_event(event_type="retry_attempt", details=details)
        
        self.logger.warning(
            f"RETRY: {operation} (attempt {attempt}/{max_attempts}) | "
            f"Reason: {details['retry_reason']}"
        )
    
    def log_retry_success(self, operation: str, final_attempt: int):
        """Log successful retry completion.
        
        Args:
            operation: Operation that succeeded after retry
            final_attempt: Final attempt number that succeeded
        """
        self.statistics.successful_retries += 1
        
        self.log_audit_event(
            event_type="retry_success",
            details={
                'operation': operation,
                'final_attempt': final_attempt
            }
        )
        
        self.logger.info(f"RETRY SUCCESS: {operation} succeeded on attempt {final_attempt}")
    
    def log_retry_failure(self, operation: str, final_attempt: int, final_error: Exception):
        """Log retry failure after all attempts exhausted.
        
        Args:
            operation: Operation that failed after all retries
            final_attempt: Final attempt number
            final_error: Final error that caused failure
        """
        self.statistics.failed_retries += 1
        
        self.log_audit_event(
            event_type="retry_failure",
            details={
                'operation': operation,
                'final_attempt': final_attempt,
                'final_error': str(final_error)
            }
        )
        
        self.logger.error(
            f"RETRY FAILURE: {operation} failed after {final_attempt} attempts | "
            f"Final error: {str(final_error)}"
        )
    
    def update_statistics(self, **kwargs):
        """Update execution statistics.
        
        Args:
            **kwargs: Statistics to update (e.g., cloudflare_api_calls=1)
        """
        for key, value in kwargs.items():
            if hasattr(self.statistics, key):
                current_value = getattr(self.statistics, key)
                setattr(self.statistics, key, current_value + value)
            else:
                self.logger.warning(f"Unknown statistic key: {key}")
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """Get comprehensive execution summary with statistics and audit log.
        
        Returns:
            Dictionary containing execution summary
        """
        # Ensure execution timing is calculated
        if self.statistics.end_time is None:
            self.statistics.finish_execution()
        
        return {
            'request_id': self.request_id,
            'statistics': self.statistics.to_dict(),
            'audit_log_entries': len(self.audit_log),
            'execution_summary': {
                'total_operations': len([entry for entry in self.audit_log 
                                       if entry['event_type'] in ['operation_start', 'operation_end']]),
                'errors_encountered': self.statistics.get_total_errors(),
                'retries_performed': self.statistics.total_retries,
                'overall_success': self.statistics.get_total_errors() == 0
            }
        }
    
    def log_final_summary(self):
        """Log final execution summary for audit purposes."""
        summary = self.get_execution_summary()
        
        self.logger.info("=" * 80)
        self.logger.info("EXECUTION SUMMARY")
        self.logger.info("=" * 80)
        self.logger.info(f"Request ID: {summary['request_id']}")
        self.logger.info(f"Execution Time: {summary['statistics']['execution_time_ms']}ms")
        self.logger.info(f"Records Processed: {summary['statistics']['records_processed']}")
        self.logger.info(f"Records Stored: {summary['statistics']['records_stored']}")
        self.logger.info(f"Success Rate: {summary['statistics']['success_rate']:.1%}")
        self.logger.info(f"Total Errors: {summary['statistics']['total_errors']}")
        self.logger.info(f"API Calls: {summary['statistics']['cloudflare_api_calls']}")
        self.logger.info(f"DynamoDB Writes: {summary['statistics']['dynamodb_writes']}")
        self.logger.info(f"Retries: {summary['statistics']['retry_statistics']['total_retries']}")
        self.logger.info(f"Audit Log Entries: {summary['audit_log_entries']}")
        self.logger.info(f"Overall Success: {summary['execution_summary']['overall_success']}")
        self.logger.info("=" * 80)
        
        # Log detailed error breakdown if there were errors
        if summary['statistics']['total_errors'] > 0:
            self.logger.info("ERROR BREAKDOWN:")
            for error_type, count in summary['statistics']['error_breakdown'].items():
                if count > 0:
                    self.logger.info(f"  {error_type}: {count}")
        
        # Add final audit entry
        self.log_audit_event(
            event_type="execution_completed",
            details=summary
        )
    
    def get_audit_log(self) -> List[Dict[str, Any]]:
        """Get complete audit log for external processing.
        
        Returns:
            List of audit log entries
        """
        return self.audit_log.copy()
    
    def create_error_context(self, operation: str, component: str, 
                           additional_data: Dict[str, Any] = None) -> ErrorContext:
        """Create an error context for consistent error handling.
        
        Args:
            operation: Name of the operation
            component: Component where the error occurred
            additional_data: Additional context data
            
        Returns:
            ErrorContext object
        """
        return ErrorContext(
            operation=operation,
            component=component,
            request_id=self.request_id,
            additional_data=additional_data or {}
        )
    
    def create_error_response(self, error_info: Dict[str, Any], 
                            http_status_code: int = None) -> Dict[str, Any]:
        """Create a standardized error response structure.
        
        Args:
            error_info: Structured error information from error handling
            http_status_code: HTTP status code (will be determined if not provided)
            
        Returns:
            Standardized error response dictionary
        """
        # Determine HTTP status code if not provided
        if http_status_code is None:
            http_status_code = self._map_error_to_http_status(error_info)
        
        # Create standardized error response
        error_response = {
            "success": False,
            "error": {
                "type": error_info.get('category', 'unknown').upper() + "_ERROR",
                "message": self._create_actionable_error_message(error_info),
                "details": error_info.get('message', 'Unknown error occurred'),
                "timestamp": error_info.get('timestamp', datetime.now(timezone.utc).isoformat()),
                "request_id": error_info.get('request_id', self.request_id),
                "error_id": error_info.get('error_id'),
                "is_retryable": error_info.get('is_retryable', False)
            },
            "statistics": self.statistics.to_dict(),
            "http_status_code": http_status_code
        }
        
        # Add additional context for debugging if available
        if error_info.get('additional_data'):
            error_response["error"]["context"] = error_info['additional_data']
        
        # Add retry guidance for retryable errors
        if error_info.get('is_retryable'):
            error_response["error"]["retry_guidance"] = self._get_retry_guidance(error_info)
        
        return error_response
    
    def create_success_response(self, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create a standardized success response structure.
        
        Args:
            data: Optional additional data to include in response
            
        Returns:
            Standardized success response dictionary
        """
        # Ensure execution timing is calculated
        if self.statistics.end_time is None:
            self.statistics.finish_execution()
        
        success_response = {
            "success": True,
            "data": data or {},
            "statistics": self.statistics.to_dict(),
            "request_id": self.request_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        return success_response
    
    def _map_error_to_http_status(self, error_info: Dict[str, Any]) -> int:
        """Map error category and type to appropriate HTTP status code.
        
        Args:
            error_info: Structured error information
            
        Returns:
            HTTP status code
        """
        category = error_info.get('category', 'unknown')
        error_type = error_info.get('type', '')
        severity = error_info.get('severity', 'medium')
        
        # Configuration errors
        if category == ErrorCategory.CONFIGURATION.value:
            return 500  # Internal Server Error
        
        # Authentication errors
        if category == ErrorCategory.AUTHENTICATION.value:
            if 'unauthorized' in error_type.lower() or 'auth' in error_type.lower():
                return 401  # Unauthorized
            else:
                return 403  # Forbidden
        
        # API errors - map based on common HTTP error patterns
        if category == ErrorCategory.API.value:
            if 'timeout' in error_type.lower() or 'network' in error_type.lower():
                return 504  # Gateway Timeout
            elif 'rate' in error_type.lower() or 'limit' in error_type.lower():
                return 429  # Too Many Requests
            elif 'not found' in error_type.lower():
                return 404  # Not Found
            elif 'bad request' in error_type.lower() or 'invalid' in error_type.lower():
                return 400  # Bad Request
            else:
                return 502  # Bad Gateway
        
        # Storage errors
        if category == ErrorCategory.STORAGE.value:
            if 'capacity' in error_type.lower() or 'throttl' in error_type.lower():
                return 503  # Service Unavailable
            elif 'not found' in error_type.lower():
                return 404  # Not Found
            else:
                return 500  # Internal Server Error
        
        # Data validation errors
        if category == ErrorCategory.DATA_VALIDATION.value:
            return 422  # Unprocessable Entity
        
        # Network errors
        if category == ErrorCategory.NETWORK.value:
            return 503  # Service Unavailable
        
        # Default based on severity
        if severity == ErrorSeverity.CRITICAL.value:
            return 500  # Internal Server Error
        elif severity == ErrorSeverity.HIGH.value:
            return 500  # Internal Server Error
        elif severity == ErrorSeverity.MEDIUM.value:
            return 503  # Service Unavailable
        else:
            return 400  # Bad Request
    
    def _create_actionable_error_message(self, error_info: Dict[str, Any]) -> str:
        """Create an actionable error message that provides guidance to users.
        
        Args:
            error_info: Structured error information
            
        Returns:
            Actionable error message
        """
        category = error_info.get('category', 'unknown')
        error_type = error_info.get('type', '')
        original_message = error_info.get('message', 'Unknown error occurred')
        
        # Configuration errors
        if category == ErrorCategory.CONFIGURATION.value:
            if 'environment' in original_message.lower():
                return f"Configuration error: {original_message}. Please check your environment variables and ensure all required values are set."
            elif 'secret' in original_message.lower():
                return f"Configuration error: {original_message}. Please verify your AWS Secrets Manager configuration and permissions."
            else:
                return f"Configuration error: {original_message}. Please check your Lambda function configuration."
        
        # Authentication errors
        if category == ErrorCategory.AUTHENTICATION.value:
            return f"Authentication failed: {original_message}. Please verify your Cloudflare API credentials in AWS Secrets Manager."
        
        # API errors
        if category == ErrorCategory.API.value:
            if 'rate' in original_message.lower() or 'limit' in original_message.lower():
                return f"API rate limit exceeded: {original_message}. The operation will be retried automatically with exponential backoff."
            elif 'timeout' in original_message.lower():
                return f"API request timeout: {original_message}. Please check network connectivity and Cloudflare API status."
            elif 'network' in original_message.lower():
                return f"Network error: {original_message}. Please check network connectivity and try again."
            else:
                return f"Cloudflare API error: {original_message}. Please check the Cloudflare API status and your request parameters."
        
        # Storage errors
        if category == ErrorCategory.STORAGE.value:
            if 'capacity' in original_message.lower() or 'throttl' in original_message.lower():
                return f"DynamoDB capacity error: {original_message}. The operation will be retried automatically."
            elif 'table' in original_message.lower():
                return f"DynamoDB table error: {original_message}. Please verify your DynamoDB table configuration and permissions."
            else:
                return f"Storage error: {original_message}. Please check your DynamoDB configuration and AWS permissions."
        
        # Data validation errors
        if category == ErrorCategory.DATA_VALIDATION.value:
            return f"Data validation error: {original_message}. The invalid data will be skipped and processing will continue."
        
        # Network errors
        if category == ErrorCategory.NETWORK.value:
            return f"Network connectivity error: {original_message}. Please check network connectivity and try again."
        
        # Default actionable message
        return f"{original_message}. Please check the logs for more details and contact support if the issue persists."
    
    def _get_retry_guidance(self, error_info: Dict[str, Any]) -> Dict[str, Any]:
        """Get retry guidance for retryable errors.
        
        Args:
            error_info: Structured error information
            
        Returns:
            Retry guidance information
        """
        category = error_info.get('category', 'unknown')
        
        guidance = {
            "recommended_action": "retry",
            "retry_delay_seconds": 1,
            "max_retries": 3,
            "backoff_strategy": "exponential"
        }
        
        # Customize guidance based on error category
        if category == ErrorCategory.API.value:
            if 'rate' in error_info.get('message', '').lower():
                guidance.update({
                    "retry_delay_seconds": 60,
                    "max_retries": 5,
                    "backoff_strategy": "exponential_with_jitter",
                    "notes": "Rate limit errors require longer delays between retries"
                })
            else:
                guidance.update({
                    "retry_delay_seconds": 2,
                    "max_retries": 3,
                    "notes": "API errors are typically transient and resolve quickly"
                })
        
        elif category == ErrorCategory.STORAGE.value:
            guidance.update({
                "retry_delay_seconds": 1,
                "max_retries": 5,
                "backoff_strategy": "exponential_with_jitter",
                "notes": "Storage capacity errors usually resolve within a few seconds"
            })
        
        elif category == ErrorCategory.NETWORK.value:
            guidance.update({
                "retry_delay_seconds": 5,
                "max_retries": 3,
                "notes": "Network errors may require longer delays to allow connectivity to restore"
            })
        
        return guidance