"""
Data transformation and validation for Cloudflare to DynamoDB.

This module handles:
- Cloudflare to DynamoDB data transformation
- Data type validation for DynamoDB compatibility
- Metadata generation (timestamps, source info)
- Comprehensive data validation with graceful error handling
"""

import json
import logging
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Dict, Any, Optional, List, Union
from decimal import Decimal

from .cloudflare_client import CloudflareKey


@dataclass
class DynamoDBRecord:
    """Represents a record to be stored in DynamoDB."""
    pk: str  # Primary key: f"cf_kv#{key}"
    sk: str  # Sort key: ISO timestamp
    key_name: str  # Original Cloudflare key
    value: str  # Cloudflare value (stored as string)
    metadata: Dict[str, Any]  # Cloudflare metadata (expiration, etc.)
    retrieved_at: str  # ISO timestamp when retrieved
    ttl: Optional[int]  # DynamoDB TTL (optional)
    source: str  # Always "cloudflare_kv"
    namespace_id: str  # Cloudflare namespace ID
    data_version: str  # Schema version for future compatibility


class DataValidationError(Exception):
    """Raised when data validation fails."""
    pass


class DataTransformer:
    """Transforms and validates data between Cloudflare and DynamoDB formats."""
    
    DATA_VERSION = "1.0"
    SOURCE = "cloudflare_kv"
    MAX_DYNAMODB_ITEM_SIZE = 400 * 1024  # 400KB limit for DynamoDB items
    
    def __init__(self, namespace_id: str, logger: Optional[logging.Logger] = None):
        """Initialize the data transformer.
        
        Args:
            namespace_id: Cloudflare KV namespace ID
            logger: Optional logger instance
        """
        self.namespace_id = namespace_id
        self.logger = logger or logging.getLogger(__name__)
        
    def transform_kv_record(self, key: str, value: Any, cloudflare_key_metadata: Optional[CloudflareKey] = None) -> DynamoDBRecord:
        """Transform Cloudflare KV data to DynamoDB format.
        
        Args:
            key: Cloudflare key name
            value: Cloudflare value (any type)
            cloudflare_key_metadata: Optional CloudflareKey object with metadata
            
        Returns:
            DynamoDBRecord ready for DynamoDB storage
            
        Raises:
            DataValidationError: If transformation fails due to invalid data
        """
        try:
            # Generate timestamps
            now = datetime.now(timezone.utc)
            iso_timestamp = now.isoformat()
            
            # Create primary and sort keys
            pk = f"cf_kv#{key}"
            sk = iso_timestamp
            
            # Convert value to string for consistent storage
            if value is None:
                value_str = ""
                self.logger.debug(f"Null value for key {key}, storing as empty string")
            elif isinstance(value, str):
                value_str = value
            else:
                # Convert non-string values to JSON
                try:
                    value_str = json.dumps(value, default=str)
                    self.logger.debug(f"Converted non-string value to JSON for key {key}")
                except (TypeError, ValueError) as e:
                    # Fallback to string representation
                    value_str = str(value)
                    self.logger.warning(f"Failed to JSON serialize value for key {key}, using string representation: {e}")
            
            # Process metadata
            metadata = {}
            ttl = None
            
            if cloudflare_key_metadata:
                # Include Cloudflare metadata
                if cloudflare_key_metadata.metadata:
                    metadata.update(cloudflare_key_metadata.metadata)
                
                # Handle expiration for DynamoDB TTL
                if cloudflare_key_metadata.expiration:
                    ttl = cloudflare_key_metadata.expiration
                    metadata['cloudflare_expiration'] = cloudflare_key_metadata.expiration
            
            # Add transformation metadata
            metadata.update({
                'transformed_at': iso_timestamp,
                'original_type': type(value).__name__,
                'value_length': len(value_str)
            })
            
            # Create DynamoDB record
            record = DynamoDBRecord(
                pk=pk,
                sk=sk,
                key_name=key,
                value=value_str,
                metadata=metadata,
                retrieved_at=iso_timestamp,
                ttl=ttl,
                source=self.SOURCE,
                namespace_id=self.namespace_id,
                data_version=self.DATA_VERSION
            )
            
            self.logger.debug(f"Transformed record for key {key}: pk={pk}, value_length={len(value_str)}")
            return record
            
        except Exception as e:
            error_msg = f"Failed to transform record for key {key}: {str(e)}"
            self.logger.error(error_msg)
            raise DataValidationError(error_msg) from e
    
    def validate_record(self, record: DynamoDBRecord) -> bool:
        """Validate record structure and data types for DynamoDB compatibility.
        
        Args:
            record: DynamoDB record to validate
            
        Returns:
            True if record is valid
            
        Raises:
            DataValidationError: If validation fails
        """
        try:
            # Validate required fields
            required_fields = ['pk', 'sk', 'key_name', 'value', 'retrieved_at', 'source', 'namespace_id', 'data_version']
            for field in required_fields:
                if not hasattr(record, field) or getattr(record, field) is None:
                    raise DataValidationError(f"Missing required field: {field}")
            
            # Validate data types
            if not isinstance(record.pk, str) or not record.pk:
                raise DataValidationError("Primary key (pk) must be a non-empty string")
            
            if not isinstance(record.sk, str) or not record.sk:
                raise DataValidationError("Sort key (sk) must be a non-empty string")
            
            if not isinstance(record.key_name, str) or not record.key_name:
                raise DataValidationError("Key name must be a non-empty string")
            
            if not isinstance(record.value, str):
                raise DataValidationError("Value must be a string")
            
            if not isinstance(record.metadata, dict):
                raise DataValidationError("Metadata must be a dictionary")
            
            if not isinstance(record.source, str) or record.source != self.SOURCE:
                raise DataValidationError(f"Source must be '{self.SOURCE}'")
            
            if not isinstance(record.namespace_id, str) or not record.namespace_id:
                raise DataValidationError("Namespace ID must be a non-empty string")
            
            if not isinstance(record.data_version, str) or not record.data_version:
                raise DataValidationError("Data version must be a non-empty string")
            
            # Validate optional TTL field
            if record.ttl is not None and not isinstance(record.ttl, int):
                raise DataValidationError("TTL must be an integer or None")
            
            # Validate DynamoDB constraints
            self._validate_dynamodb_constraints(record)
            
            self.logger.debug(f"Record validation passed for key {record.key_name}")
            return True
            
        except DataValidationError:
            raise
        except Exception as e:
            error_msg = f"Unexpected error during validation for key {record.key_name}: {str(e)}"
            self.logger.error(error_msg)
            raise DataValidationError(error_msg) from e
    
    def _validate_dynamodb_constraints(self, record: DynamoDBRecord) -> None:
        """Validate DynamoDB-specific constraints.
        
        Args:
            record: Record to validate
            
        Raises:
            DataValidationError: If DynamoDB constraints are violated
        """
        # Calculate approximate item size
        item_size = self._estimate_item_size(record)
        if item_size > self.MAX_DYNAMODB_ITEM_SIZE:
            raise DataValidationError(f"Record size ({item_size} bytes) exceeds DynamoDB limit ({self.MAX_DYNAMODB_ITEM_SIZE} bytes)")
        
        # Validate key lengths (DynamoDB has limits)
        if len(record.pk.encode('utf-8')) > 2048:
            raise DataValidationError("Primary key exceeds DynamoDB 2KB limit")
        
        if len(record.sk.encode('utf-8')) > 1024:
            raise DataValidationError("Sort key exceeds DynamoDB 1KB limit")
        
        # Validate metadata for DynamoDB compatibility
        self._validate_metadata_for_dynamodb(record.metadata)
    
    def _estimate_item_size(self, record: DynamoDBRecord) -> int:
        """Estimate the size of a DynamoDB item in bytes.
        
        Args:
            record: Record to estimate size for
            
        Returns:
            Estimated size in bytes
        """
        # This is a rough estimation - actual DynamoDB encoding may differ
        size = 0
        
        # String attributes
        for attr in ['pk', 'sk', 'key_name', 'value', 'retrieved_at', 'source', 'namespace_id', 'data_version']:
            value = getattr(record, attr)
            if value:
                size += len(attr.encode('utf-8')) + len(str(value).encode('utf-8'))
        
        # TTL (number attribute)
        if record.ttl is not None:
            size += len('ttl'.encode('utf-8')) + 8  # Approximate size for number
        
        # Metadata (map attribute)
        size += len('metadata'.encode('utf-8'))
        size += self._estimate_dict_size(record.metadata)
        
        return size
    
    def _estimate_dict_size(self, data: Dict[str, Any]) -> int:
        """Estimate the size of a dictionary when stored in DynamoDB.
        
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
                size += 8  # Approximate size for numbers
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
            else:
                size += len(str(value).encode('utf-8'))
        
        return size
    
    def _validate_metadata_for_dynamodb(self, metadata: Dict[str, Any]) -> None:
        """Validate metadata dictionary for DynamoDB compatibility.
        
        Args:
            metadata: Metadata dictionary to validate
            
        Raises:
            DataValidationError: If metadata contains incompatible types
        """
        def validate_value(value: Any, path: str = "") -> None:
            """Recursively validate values in the metadata."""
            if value is None:
                return  # None/null values are allowed
            
            if isinstance(value, (str, int, float, bool)):
                return  # Basic types are allowed
            
            if isinstance(value, dict):
                for key, val in value.items():
                    if not isinstance(key, str):
                        raise DataValidationError(f"Dictionary keys must be strings at path: {path}.{key}")
                    validate_value(val, f"{path}.{key}")
                return
            
            if isinstance(value, list):
                for i, item in enumerate(value):
                    validate_value(item, f"{path}[{i}]")
                return
            
            # Convert other types to strings
            if not isinstance(value, (str, int, float, bool, dict, list, type(None))):
                self.logger.warning(f"Converting unsupported type {type(value)} to string at path: {path}")
        
        try:
            validate_value(metadata, "metadata")
        except Exception as e:
            raise DataValidationError(f"Metadata validation failed: {str(e)}") from e
    
    def handle_missing_or_null_values(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle missing or null values gracefully in API response data.
        
        Args:
            data: Raw data from API response
            
        Returns:
            Processed data with null values handled
        """
        processed_data = {}
        
        for key, value in data.items():
            if value is None:
                # Log null values but don't fail
                self.logger.debug(f"Null value found for field: {key}")
                processed_data[key] = None
            elif isinstance(value, dict):
                # Recursively handle nested dictionaries
                processed_data[key] = self.handle_missing_or_null_values(value)
            elif isinstance(value, list):
                # Handle lists with potential null values
                processed_data[key] = [
                    self.handle_missing_or_null_values(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                processed_data[key] = value
        
        return processed_data
    
    def validate_api_response_fields(self, response_data: Dict[str, Any], required_fields: List[str]) -> bool:
        """Validate that required fields are present in API response.
        
        Args:
            response_data: API response data to validate
            required_fields: List of required field names
            
        Returns:
            True if all required fields are present
            
        Raises:
            DataValidationError: If required fields are missing
        """
        missing_fields = []
        
        for field in required_fields:
            if field not in response_data:
                missing_fields.append(field)
        
        if missing_fields:
            error_msg = f"Missing required fields in API response: {', '.join(missing_fields)}"
            self.logger.error(error_msg)
            raise DataValidationError(error_msg)
        
        self.logger.debug(f"API response validation passed for fields: {required_fields}")
        return True
    
    def validate_and_process_batch(self, records: List[DynamoDBRecord], skip_invalid: bool = True) -> List[DynamoDBRecord]:
        """Validate a batch of records and optionally skip invalid ones.
        
        Args:
            records: List of DynamoDB records to validate
            skip_invalid: If True, skip invalid records and continue; if False, raise on first invalid record
            
        Returns:
            List of valid records
            
        Raises:
            DataValidationError: If skip_invalid is False and any record is invalid
        """
        valid_records = []
        validation_errors = []
        
        for i, record in enumerate(records):
            try:
                if self.validate_record(record):
                    valid_records.append(record)
            except DataValidationError as e:
                error_msg = f"Record {i} validation failed: {str(e)}"
                validation_errors.append(error_msg)
                
                if skip_invalid:
                    self.logger.warning(f"Skipping invalid record {i}: {str(e)}")
                    continue
                else:
                    self.logger.error(error_msg)
                    raise DataValidationError(error_msg) from e
        
        if validation_errors:
            self.logger.info(f"Batch validation completed: {len(valid_records)} valid, {len(validation_errors)} invalid records")
            if validation_errors and skip_invalid:
                # Log summary of validation errors without failing
                self.logger.warning(f"Validation errors encountered: {len(validation_errors)} records skipped")
        else:
            self.logger.debug(f"All {len(records)} records in batch passed validation")
        
        return valid_records
    
    def sanitize_for_dynamodb(self, value: Any) -> Any:
        """Sanitize a value for DynamoDB storage by converting unsupported types.
        
        Args:
            value: Value to sanitize
            
        Returns:
            Sanitized value compatible with DynamoDB
        """
        if value is None:
            return None
        
        if isinstance(value, (str, int, float, bool)):
            return value
        
        if isinstance(value, dict):
            return {k: self.sanitize_for_dynamodb(v) for k, v in value.items()}
        
        if isinstance(value, list):
            return [self.sanitize_for_dynamodb(item) for item in value]
        
        if isinstance(value, Decimal):
            return float(value)
        
        # Convert other types to string
        self.logger.debug(f"Converting unsupported type {type(value)} to string")
        return str(value)
    
    def log_validation_error(self, error: Exception, context: str, record_key: Optional[str] = None) -> None:
        """Log validation errors with appropriate context without failing the operation.
        
        Args:
            error: The validation error that occurred
            context: Context description (e.g., "API response validation", "record transformation")
            record_key: Optional key name for record-specific errors
        """
        if record_key:
            error_msg = f"Validation error for key '{record_key}' during {context}: {str(error)}"
        else:
            error_msg = f"Validation error during {context}: {str(error)}"
        
        self.logger.warning(error_msg)
        
        # Log additional details for debugging
        if hasattr(error, '__cause__') and error.__cause__:
            self.logger.debug(f"Underlying cause: {str(error.__cause__)}")
    
    def create_error_record(self, key: str, error: Exception, original_value: Any = None) -> Dict[str, Any]:
        """Create an error record for failed transformations to track issues.
        
        Args:
            key: The key that failed transformation
            error: The error that occurred
            original_value: The original value that failed (optional)
            
        Returns:
            Dictionary containing error information
        """
        now = datetime.now(timezone.utc).isoformat()
        
        error_record = {
            'key_name': key,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'timestamp': now,
            'namespace_id': self.namespace_id,
            'source': self.SOURCE
        }
        
        if original_value is not None:
            error_record['original_value_type'] = type(original_value).__name__
            # Only include original value if it's small and safe to log
            if isinstance(original_value, (str, int, float, bool)) and len(str(original_value)) < 100:
                error_record['original_value_sample'] = str(original_value)[:100]
        
        return error_record