"""
DynamoDB client for batch write operations.

This module handles:
- Batch write operations with error handling
- Retry logic for capacity errors and throttling
- Unprocessed items handling
- Storage accuracy tracking
"""

import time
import random
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from .data_transformer import DynamoDBRecord


@dataclass
class BatchWriteResult:
    """Result of a batch write operation."""
    successful_records: int
    failed_records: int
    unprocessed_items: List[Dict[str, Any]]
    errors: List[str]
    total_attempts: int
    execution_time_ms: int


class DynamoDBError(Exception):
    """Base exception for DynamoDB operations."""
    pass


class DynamoDBClient:
    """Manages all DynamoDB operations with proper error handling and retry logic."""
    
    # DynamoDB batch write limits
    MAX_BATCH_SIZE = 25
    MAX_ITEM_SIZE = 400 * 1024  # 400KB
    
    # Retry configuration
    DEFAULT_MAX_RETRIES = 3
    BASE_DELAY = 0.1  # 100ms base delay
    MAX_DELAY = 60.0  # 60 second max delay
    JITTER_RANGE = 0.1  # 10% jitter
    
    # Retryable error codes
    RETRYABLE_ERRORS = {
        'ProvisionedThroughputExceededException',
        'ThrottlingException',
        'InternalServerError',
        'ServiceUnavailable',
        'RequestLimitExceeded'
    }
    
    def __init__(self, table_name: str, max_retries: int = None, logger: Optional[logging.Logger] = None):
        """Initialize the DynamoDB client.
        
        Args:
            table_name: Name of the DynamoDB table
            max_retries: Maximum number of retry attempts (defaults to DEFAULT_MAX_RETRIES)
            logger: Optional logger instance
        """
        self.table_name = table_name
        self.max_retries = max_retries or self.DEFAULT_MAX_RETRIES
        self.logger = logger or logging.getLogger(__name__)
        
        # Initialize DynamoDB resources
        self._dynamodb_resource = None
        self._table = None
        
        # Statistics tracking
        self.reset_statistics()
    
    @property
    def dynamodb_resource(self):
        """Lazy initialization of DynamoDB resource."""
        if self._dynamodb_resource is None:
            try:
                self._dynamodb_resource = boto3.resource('dynamodb')
                self.logger.debug("DynamoDB resource initialized")
            except NoCredentialsError as e:
                self.logger.error("Failed to create DynamoDB resource: No AWS credentials found")
                raise DynamoDBError("AWS credentials not configured") from e
        return self._dynamodb_resource
    
    @property
    def table(self):
        """Lazy initialization of DynamoDB table."""
        if self._table is None:
            try:
                self._table = self.dynamodb_resource.Table(self.table_name)
                # Verify table exists by checking its status
                self._table.load()
                self.logger.debug(f"DynamoDB table '{self.table_name}' loaded successfully")
            except ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code == 'ResourceNotFoundException':
                    error_msg = f"DynamoDB table '{self.table_name}' not found"
                else:
                    error_msg = f"Failed to access DynamoDB table '{self.table_name}': {error_code}"
                self.logger.error(error_msg)
                raise DynamoDBError(error_msg) from e
        return self._table
    
    def reset_statistics(self):
        """Reset internal statistics tracking."""
        self.total_records_attempted = 0
        self.total_records_successful = 0
        self.total_records_failed = 0
        self.total_write_operations = 0
        self.total_retry_attempts = 0
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get current statistics for storage operations.
        
        Returns:
            Dictionary containing detailed operation statistics
        """
        success_rate = (
            self.total_records_successful / self.total_records_attempted 
            if self.total_records_attempted > 0 else 0.0
        )
        
        return {
            'total_records_attempted': self.total_records_attempted,
            'total_records_successful': self.total_records_successful,
            'total_records_failed': self.total_records_failed,
            'total_write_operations': self.total_write_operations,
            'total_retry_attempts': self.total_retry_attempts,
            'success_rate': round(success_rate, 4),
            'failure_rate': round(1.0 - success_rate, 4),
            'average_retries_per_operation': (
                self.total_retry_attempts / self.total_write_operations
                if self.total_write_operations > 0 else 0.0
            )
        }
    
    def get_operation_summary(self) -> str:
        """Get a human-readable summary of storage operations.
        
        Returns:
            Formatted string summarizing storage operation results
        """
        stats = self.get_statistics()
        
        summary = (
            f"Storage Operation Summary:\n"
            f"  Records Attempted: {stats['total_records_attempted']}\n"
            f"  Records Successful: {stats['total_records_successful']}\n"
            f"  Records Failed: {stats['total_records_failed']}\n"
            f"  Success Rate: {stats['success_rate']:.1%}\n"
            f"  Write Operations: {stats['total_write_operations']}\n"
            f"  Retry Attempts: {stats['total_retry_attempts']}"
        )
        
        return summary
    
    def validate_operation_accuracy(self, expected_records: int) -> bool:
        """Validate that storage operation reporting matches expected results.
        
        Args:
            expected_records: Expected number of records to be processed
            
        Returns:
            True if the accounting is accurate, False otherwise
        """
        actual_total = self.total_records_successful + self.total_records_failed
        
        if actual_total != expected_records:
            self.logger.error(
                f"Storage accuracy validation failed: "
                f"Expected {expected_records} records, but processed {actual_total} "
                f"({self.total_records_successful} successful + {self.total_records_failed} failed)"
            )
            return False
        
        if actual_total != self.total_records_attempted:
            self.logger.error(
                f"Internal accounting error: "
                f"Attempted {self.total_records_attempted} records, but "
                f"successful + failed = {actual_total}"
            )
            return False
        
        self.logger.debug(f"Storage accuracy validation passed: {actual_total} records processed as expected")
        return True
    
    def batch_write_records(self, records: List[DynamoDBRecord]) -> BatchWriteResult:
        """Perform batch write operations with error handling and retry logic.
        
        Args:
            records: List of DynamoDB records to write
            
        Returns:
            BatchWriteResult with operation statistics and any unprocessed items
            
        Raises:
            DynamoDBError: If all retry attempts are exhausted or non-retryable error occurs
        """
        start_time = time.time()
        
        if not records:
            self.logger.warning("No records provided for batch write")
            return BatchWriteResult(
                successful_records=0,
                failed_records=0,
                unprocessed_items=[],
                errors=[],
                total_attempts=0,
                execution_time_ms=0
            )
        
        self.logger.info(f"Starting batch write operation for {len(records)} records")
        self.total_records_attempted += len(records)
        
        # Convert records to DynamoDB items
        items = []
        conversion_errors = []
        
        for i, record in enumerate(records):
            try:
                item = self._record_to_dynamodb_item(record)
                items.append(item)
            except Exception as e:
                error_msg = f"Failed to convert record {i} (key: {record.key_name}): {str(e)}"
                conversion_errors.append(error_msg)
                self.logger.error(error_msg)
        
        if not items:
            error_msg = "No valid items to write after conversion"
            self.logger.error(error_msg)
            self.total_records_failed += len(records)
            return BatchWriteResult(
                successful_records=0,
                failed_records=len(records),
                unprocessed_items=[],
                errors=conversion_errors,
                total_attempts=0,
                execution_time_ms=int((time.time() - start_time) * 1000)
            )
        
        # Process items in batches
        successful_records = 0
        failed_records = len(records) - len(items)  # Records that failed conversion
        all_errors = conversion_errors.copy()
        total_attempts = 0
        
        # Split items into batches of MAX_BATCH_SIZE
        batches = [items[i:i + self.MAX_BATCH_SIZE] for i in range(0, len(items), self.MAX_BATCH_SIZE)]
        
        for batch_num, batch_items in enumerate(batches):
            self.logger.debug(f"Processing batch {batch_num + 1}/{len(batches)} with {len(batch_items)} items")
            
            try:
                batch_result = self._write_batch_with_retry(batch_items)
                successful_records += batch_result.successful_records
                failed_records += batch_result.failed_records
                all_errors.extend(batch_result.errors)
                total_attempts += batch_result.total_attempts
                
                # Handle any unprocessed items from this batch
                if batch_result.unprocessed_items:
                    self.logger.warning(f"Batch {batch_num + 1} has {len(batch_result.unprocessed_items)} unprocessed items")
                    # These will be counted as failed records
                    failed_records += len(batch_result.unprocessed_items)
                
            except DynamoDBError as e:
                error_msg = f"Batch {batch_num + 1} failed completely: {str(e)}"
                all_errors.append(error_msg)
                failed_records += len(batch_items)
                self.logger.error(error_msg)
        
        # Update statistics with accurate tracking
        self.total_records_successful += successful_records
        self.total_records_failed += failed_records
        self.total_write_operations += len(batches)
        
        # Validate that our accounting is accurate
        total_processed = successful_records + failed_records
        if total_processed != len(records):
            error_msg = (
                f"Storage accuracy error: Expected to process {len(records)} records, "
                f"but accounted for {total_processed} ({successful_records} successful + {failed_records} failed)"
            )
            self.logger.error(error_msg)
            all_errors.append(error_msg)
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        result = BatchWriteResult(
            successful_records=successful_records,
            failed_records=failed_records,
            unprocessed_items=[],  # All unprocessed items are already counted as failed
            errors=all_errors,
            total_attempts=total_attempts,
            execution_time_ms=execution_time_ms
        )
        
        self.logger.info(
            f"Batch write completed: {successful_records} successful, {failed_records} failed, "
            f"{execution_time_ms}ms execution time, accuracy validated: {total_processed == len(records)}"
        )
        
        return result
    
    def _write_batch_with_retry(self, items: List[Dict[str, Any]]) -> BatchWriteResult:
        """Write a single batch with retry logic for capacity errors and throttling.
        
        Args:
            items: List of DynamoDB items to write (max 25 items)
            
        Returns:
            BatchWriteResult for this batch
            
        Raises:
            DynamoDBError: If all retry attempts are exhausted
        """
        if len(items) > self.MAX_BATCH_SIZE:
            raise DynamoDBError(f"Batch size {len(items)} exceeds maximum {self.MAX_BATCH_SIZE}")
        
        unprocessed_items = items.copy()
        successful_records = 0
        errors = []
        attempt = 0
        
        while unprocessed_items and attempt <= self.max_retries:
            attempt += 1
            self.total_retry_attempts += 1 if attempt > 1 else 0
            
            try:
                # Prepare batch write request
                request_items = {
                    self.table_name: [
                        {'PutRequest': {'Item': item}} for item in unprocessed_items
                    ]
                }
                
                self.logger.debug(f"Batch write attempt {attempt}: {len(unprocessed_items)} items")
                
                # Execute batch write
                response = self.dynamodb_resource.batch_write_item(RequestItems=request_items)
                
                # Calculate successful records for this attempt
                items_in_this_attempt = len(unprocessed_items)
                unprocessed_items = response.get('UnprocessedItems', {}).get(self.table_name, [])
                unprocessed_count = len(unprocessed_items)
                successful_in_attempt = items_in_this_attempt - unprocessed_count
                successful_records += successful_in_attempt
                
                self.logger.debug(f"Attempt {attempt}: {successful_in_attempt} successful, {unprocessed_count} unprocessed")
                
                # If we have unprocessed items, we need to retry
                if unprocessed_items:
                    if attempt <= self.max_retries:
                        # Calculate delay for next retry
                        delay = self._calculate_retry_delay(attempt)
                        self.logger.info(f"Retrying {len(unprocessed_items)} unprocessed items in {delay:.2f}s")
                        time.sleep(delay)
                        
                        # Extract items from unprocessed response format
                        unprocessed_items = [item['PutRequest']['Item'] for item in unprocessed_items]
                    else:
                        error_msg = f"Max retries ({self.max_retries}) exceeded with {len(unprocessed_items)} unprocessed items"
                        errors.append(error_msg)
                        self.logger.error(error_msg)
                        break
                else:
                    # All items processed successfully
                    self.logger.debug(f"All items processed successfully in {attempt} attempts")
                    break
                    
            except ClientError as e:
                error_code = e.response['Error']['Code']
                error_message = e.response['Error']['Message']
                
                if error_code in self.RETRYABLE_ERRORS and attempt <= self.max_retries:
                    delay = self._calculate_retry_delay(attempt)
                    error_msg = f"Retryable error {error_code}: {error_message}. Retrying in {delay:.2f}s"
                    self.logger.warning(error_msg)
                    time.sleep(delay)
                    continue
                else:
                    error_msg = f"Non-retryable error or max retries exceeded: {error_code} - {error_message}"
                    errors.append(error_msg)
                    self.logger.error(error_msg)
                    raise DynamoDBError(error_msg) from e
                    
            except Exception as e:
                error_msg = f"Unexpected error during batch write: {str(e)}"
                errors.append(error_msg)
                self.logger.error(error_msg)
                raise DynamoDBError(error_msg) from e
        
        # Calculate final results
        failed_records = len(unprocessed_items)
        
        return BatchWriteResult(
            successful_records=successful_records,
            failed_records=failed_records,
            unprocessed_items=unprocessed_items,
            errors=errors,
            total_attempts=attempt,
            execution_time_ms=0  # Will be calculated by caller
        )
    
    def _calculate_retry_delay(self, attempt: int) -> float:
        """Calculate retry delay with exponential backoff and jitter.
        
        Args:
            attempt: Current attempt number (1-based)
            
        Returns:
            Delay in seconds
        """
        # Exponential backoff: base_delay * (2 ^ (attempt - 1))
        delay = self.BASE_DELAY * (2 ** (attempt - 1))
        
        # Cap at maximum delay
        delay = min(delay, self.MAX_DELAY)
        
        # Add jitter to avoid thundering herd
        jitter = delay * self.JITTER_RANGE * (2 * random.random() - 1)  # ±10% jitter
        delay += jitter
        
        # Ensure delay is positive
        return max(delay, 0.01)
    
    def _record_to_dynamodb_item(self, record: DynamoDBRecord) -> Dict[str, Any]:
        """Convert a DynamoDBRecord to a DynamoDB item format.
        
        Args:
            record: DynamoDB record to convert
            
        Returns:
            Dictionary in DynamoDB item format
            
        Raises:
            DynamoDBError: If conversion fails
        """
        try:
            item = {
                'pk': record.pk,
                'sk': record.sk,
                'key_name': record.key_name,
                'value': record.value,
                'metadata': record.metadata,
                'retrieved_at': record.retrieved_at,
                'source': record.source,
                'namespace_id': record.namespace_id,
                'data_version': record.data_version
            }
            
            # Add optional TTL field if present
            if record.ttl is not None:
                item['ttl'] = record.ttl
            
            # Validate item size
            item_size = self._estimate_item_size(item)
            if item_size > self.MAX_ITEM_SIZE:
                raise DynamoDBError(f"Item size ({item_size} bytes) exceeds DynamoDB limit ({self.MAX_ITEM_SIZE} bytes)")
            
            return item
            
        except Exception as e:
            error_msg = f"Failed to convert record to DynamoDB item: {str(e)}"
            raise DynamoDBError(error_msg) from e
    
    def _estimate_item_size(self, item: Dict[str, Any]) -> int:
        """Estimate the size of a DynamoDB item in bytes.
        
        Args:
            item: DynamoDB item to estimate size for
            
        Returns:
            Estimated size in bytes
        """
        # This is a rough estimation - actual DynamoDB encoding may differ
        size = 0
        
        for key, value in item.items():
            # Add key name size
            size += len(key.encode('utf-8'))
            
            # Add value size based on type
            if isinstance(value, str):
                size += len(value.encode('utf-8'))
            elif isinstance(value, (int, float)):
                size += 8  # Approximate size for numbers
            elif isinstance(value, bool):
                size += 1
            elif isinstance(value, dict):
                size += self._estimate_dict_size(value)
            elif isinstance(value, list):
                for list_item in value:
                    if isinstance(list_item, str):
                        size += len(list_item.encode('utf-8'))
                    else:
                        size += len(str(list_item).encode('utf-8'))
            elif value is None:
                size += 1  # Null values have minimal overhead
            else:
                size += len(str(value).encode('utf-8'))
        
        return size
    
    def _estimate_dict_size(self, data: Dict[str, Any]) -> int:
        """Estimate the size of a nested dictionary.
        
        Args:
            data: Dictionary to estimate size for
            
        Returns:
            Estimated size in bytes
        """
        size = 0
        for key, value in data.items():
            size += len(str(key).encode('utf-8'))
            
            if isinstance(value, str):
                size += len(value.encode('utf-8'))
            elif isinstance(value, (int, float)):
                size += 8
            elif isinstance(value, bool):
                size += 1
            elif isinstance(value, dict):
                size += self._estimate_dict_size(value)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, str):
                        size += len(item.encode('utf-8'))
                    else:
                        size += len(str(item).encode('utf-8'))
            elif value is None:
                size += 1
            else:
                size += len(str(value).encode('utf-8'))
        
        return size
    
    def handle_write_errors(self, unprocessed_items: List[Dict[str, Any]]) -> None:
        """Handle unprocessed items with exponential backoff retry.
        
        This method is called when batch_write_records returns unprocessed items.
        It attempts to write them with the same retry logic.
        
        Args:
            unprocessed_items: List of items that were not processed in previous batch write
            
        Raises:
            DynamoDBError: If retry attempts are exhausted
        """
        if not unprocessed_items:
            self.logger.debug("No unprocessed items to handle")
            return
        
        self.logger.info(f"Handling {len(unprocessed_items)} unprocessed items")
        
        try:
            # Extract items from DynamoDB unprocessed format if needed
            items = []
            for item in unprocessed_items:
                if isinstance(item, dict) and 'PutRequest' in item:
                    items.append(item['PutRequest']['Item'])
                else:
                    items.append(item)
            
            # Retry with the same logic as batch_write_records
            result = self._write_batch_with_retry(items)
            
            if result.failed_records > 0:
                error_msg = f"Failed to process {result.failed_records} unprocessed items after retry"
                self.logger.error(error_msg)
                raise DynamoDBError(error_msg)
            
            self.logger.info(f"Successfully processed {result.successful_records} previously unprocessed items")
            
        except Exception as e:
            error_msg = f"Failed to handle unprocessed items: {str(e)}"
            self.logger.error(error_msg)
            raise DynamoDBError(error_msg) from e
    
    def generate_operation_report(self, operation_context: str = "") -> Dict[str, Any]:
        """Generate a detailed report of storage operations for audit purposes.
        
        Args:
            operation_context: Optional context description for the report
            
        Returns:
            Dictionary containing detailed operation report
        """
        stats = self.get_statistics()
        
        report = {
            'operation_context': operation_context,
            'timestamp': time.time(),
            'table_name': self.table_name,
            'statistics': stats,
            'configuration': {
                'max_retries': self.max_retries,
                'max_batch_size': self.MAX_BATCH_SIZE,
                'max_item_size': self.MAX_ITEM_SIZE
            },
            'accuracy_validated': self.validate_operation_accuracy(self.total_records_attempted),
            'summary': self.get_operation_summary()
        }
        
        return report
    
    def log_operation_metrics(self, operation_context: str = ""):
        """Log detailed operation metrics for monitoring and debugging.
        
        Args:
            operation_context: Optional context description
        """
        stats = self.get_statistics()
        
        self.logger.info(
            f"DynamoDB Operation Metrics{' - ' + operation_context if operation_context else ''}:"
        )
        self.logger.info(f"  Table: {self.table_name}")
        self.logger.info(f"  Records Attempted: {stats['total_records_attempted']}")
        self.logger.info(f"  Records Successful: {stats['total_records_successful']}")
        self.logger.info(f"  Records Failed: {stats['total_records_failed']}")
        self.logger.info(f"  Success Rate: {stats['success_rate']:.1%}")
        self.logger.info(f"  Write Operations: {stats['total_write_operations']}")
        self.logger.info(f"  Total Retries: {stats['total_retry_attempts']}")
        
        if stats['total_write_operations'] > 0:
            avg_retries = stats['total_retry_attempts'] / stats['total_write_operations']
            self.logger.info(f"  Average Retries per Operation: {avg_retries:.2f}")
        
        # Validate and log accuracy
        accuracy_valid = self.validate_operation_accuracy(self.total_records_attempted)
        self.logger.info(f"  Accuracy Validation: {'PASSED' if accuracy_valid else 'FAILED'}")
    
    def clear_statistics(self):
        """Clear all statistics for a fresh start.
        
        This is useful when reusing the client for multiple operations
        and you want separate statistics for each operation.
        """
        self.logger.debug("Clearing DynamoDB client statistics")
        self.reset_statistics()