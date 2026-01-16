"""
Cloudflare API client for KV operations.

This module handles:
- API authentication using Bearer token
- List keys and get value operations
- Request timeout and error handling
- Retry logic and rate limiting
"""

import logging
import time
import random
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Union, Callable
from enum import Enum
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import CloudflareCredentials


@dataclass
class CloudflareKey:
    """Represents a Cloudflare KV key with metadata."""
    name: str
    expiration: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class CloudflareResultInfo:
    """Pagination and result information from Cloudflare API."""
    page: int
    per_page: int
    count: int
    total_count: int
    cursor: Optional[str] = None


@dataclass
class CloudflareError:
    """Represents an error from Cloudflare API."""
    code: int
    message: str


@dataclass
class CloudflareKeysResponse:
    """Response from Cloudflare list keys API."""
    success: bool
    result: List[CloudflareKey]
    result_info: CloudflareResultInfo
    errors: List[CloudflareError]


@dataclass
class CloudflareValueResponse:
    """Response from Cloudflare get value API."""
    success: bool
    result: Any
    errors: List[CloudflareError]


class CloudflareAPIError(Exception):
    """Raised when Cloudflare API returns an error."""
    def __init__(self, message: str, status_code: int = None, errors: List[CloudflareError] = None):
        super().__init__(message)
        self.status_code = status_code
        self.errors = errors or []


class CloudflareAuthenticationError(CloudflareAPIError):
    """Raised when authentication with Cloudflare API fails."""
    pass


class CloudflareRateLimitError(CloudflareAPIError):
    """Raised when Cloudflare API rate limit is exceeded."""
    def __init__(self, message: str, retry_after: int = None):
        super().__init__(message, status_code=429)
        self.retry_after = retry_after


class CircuitBreakerState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Circuit breaker implementation for handling persistent failures."""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60, logger: Optional[logging.Logger] = None):
        """Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of consecutive failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            logger: Optional logger instance
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.logger = logger or logging.getLogger(__name__)
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitBreakerState.CLOSED
        self.success_count = 0
    
    def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection.
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            CloudflareAPIError: If circuit is open or function fails
        """
        if self.state == CircuitBreakerState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitBreakerState.HALF_OPEN
                self.logger.info("Circuit breaker moving to HALF_OPEN state")
            else:
                raise CloudflareAPIError("Circuit breaker is OPEN - too many recent failures")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.last_failure_time is None:
            return True
        return time.time() - self.last_failure_time >= self.recovery_timeout
    
    def _on_success(self):
        """Handle successful operation."""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= 3:  # Reset after 3 successful operations
                self.state = CircuitBreakerState.CLOSED
                self.failure_count = 0
                self.success_count = 0
                self.logger.info("Circuit breaker reset to CLOSED state")
        else:
            self.failure_count = 0
    
    def _on_failure(self):
        """Handle failed operation."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        self.success_count = 0
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN
            self.logger.warning(f"Circuit breaker opened after {self.failure_count} failures")


class RetryConfig:
    """Configuration for retry logic."""
    
    def __init__(self, max_attempts: int = 3, base_delay: float = 1.0, max_delay: float = 60.0, jitter: bool = True):
        """Initialize retry configuration.
        
        Args:
            max_attempts: Maximum number of retry attempts
            base_delay: Base delay in seconds for exponential backoff
            max_delay: Maximum delay in seconds
            jitter: Whether to add random jitter to delays
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter = jitter


class CloudflareClient:
    """Client for interacting with Cloudflare KV API with retry logic and circuit breaker."""
    
    BASE_URL = "https://api.cloudflare.com/client/v4"
    
    def __init__(self, credentials: CloudflareCredentials, timeout: int = 30, 
                 retry_config: Optional[RetryConfig] = None, logger: Optional[logging.Logger] = None):
        """Initialize the Cloudflare client.
        
        Args:
            credentials: Cloudflare API credentials
            timeout: Request timeout in seconds
            retry_config: Retry configuration, uses defaults if not provided
            logger: Optional logger instance
        """
        self.credentials = credentials
        self.timeout = timeout
        self.retry_config = retry_config or RetryConfig()
        self.logger = logger or logging.getLogger(__name__)
        
        # Initialize circuit breaker
        self.circuit_breaker = CircuitBreaker(logger=self.logger)
        
        # Create session with authentication headers
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {credentials.api_token}',
            'Content-Type': 'application/json'
        })
        
        # Configure retry strategy for non-rate-limit errors
        retry_strategy = Retry(
            total=0,  # We'll handle retries manually for better control
            backoff_factor=0,
            status_forcelist=[]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        self.logger.info(f"CloudflareClient initialized for namespace: {credentials.kv_namespace}")
    
    def list_keys(self, cursor: Optional[str] = None, limit: int = 1000) -> CloudflareKeysResponse:
        """List keys in the KV namespace with retry logic.
        
        Args:
            cursor: Pagination cursor for continuing from previous request
            limit: Maximum number of keys to return (max 1000)
            
        Returns:
            CloudflareKeysResponse with keys and pagination info
            
        Raises:
            CloudflareAPIError: If the API request fails after retries
            CloudflareAuthenticationError: If authentication fails
            CloudflareRateLimitError: If rate limit is exceeded
        """
        def _make_request():
            url = f"{self.BASE_URL}/accounts/{self.credentials.account_id}/storage/kv/namespaces/{self.credentials.kv_namespace_id}/keys"
            
            params = {'limit': min(limit, 1000)}  # Cloudflare max is 1000
            if cursor:
                params['cursor'] = cursor
            
            self.logger.debug(f"Listing keys with params: {params}")
            
            try:
                response = self.session.get(url, params=params, timeout=self.timeout)
                return self._handle_response(response, self._parse_keys_response)
                
            except requests.exceptions.Timeout:
                error_msg = f"Request timeout after {self.timeout} seconds"
                self.logger.error(error_msg)
                raise CloudflareAPIError(error_msg)
                
            except requests.exceptions.RequestException as e:
                error_msg = f"Network error during list_keys: {str(e)}"
                self.logger.error(error_msg)
                raise CloudflareAPIError(error_msg)
        
        return self._execute_with_retry_and_circuit_breaker(_make_request)
    
    def get_value(self, key: str) -> CloudflareValueResponse:
        """Get value for a specific key from KV namespace with retry logic.
        
        Args:
            key: The key to retrieve
            
        Returns:
            CloudflareValueResponse with the value
            
        Raises:
            CloudflareAPIError: If the API request fails after retries
            CloudflareAuthenticationError: If authentication fails
            CloudflareRateLimitError: If rate limit is exceeded
        """
        def _make_request():
            url = f"{self.BASE_URL}/accounts/{self.credentials.account_id}/storage/kv/namespaces/{self.credentials.kv_namespace_id}/values/{key}"
            
            self.logger.debug(f"Getting value for key: {key}")
            
            try:
                response = self.session.get(url, timeout=self.timeout)
                return self._handle_response(response, self._parse_value_response)
                
            except requests.exceptions.Timeout:
                error_msg = f"Request timeout after {self.timeout} seconds for key: {key}"
                self.logger.error(error_msg)
                raise CloudflareAPIError(error_msg)
                
            except requests.exceptions.RequestException as e:
                error_msg = f"Network error during get_value for key {key}: {str(e)}"
                self.logger.error(error_msg)
                raise CloudflareAPIError(error_msg)
        
        return self._execute_with_retry_and_circuit_breaker(_make_request)
    
    def _execute_with_retry_and_circuit_breaker(self, func: Callable) -> Union[CloudflareKeysResponse, CloudflareValueResponse]:
        """Execute function with retry logic and circuit breaker protection.
        
        Args:
            func: Function to execute
            
        Returns:
            Function result
            
        Raises:
            CloudflareAPIError: If all retries are exhausted or circuit is open
        """
        def _execute_with_retries():
            last_exception = None
            
            for attempt in range(self.retry_config.max_attempts):
                try:
                    return func()
                    
                except CloudflareAuthenticationError:
                    # Don't retry authentication errors
                    raise
                    
                except CloudflareRateLimitError as e:
                    # Handle rate limiting with specific retry delay
                    if attempt < self.retry_config.max_attempts - 1:
                        retry_delay = e.retry_after or 60
                        self.logger.warning(f"Rate limited, waiting {retry_delay} seconds before retry {attempt + 1}")
                        time.sleep(retry_delay)
                        continue
                    raise
                    
                except CloudflareAPIError as e:
                    last_exception = e
                    
                    # Don't retry client errors (4xx except 429)
                    if e.status_code and 400 <= e.status_code < 500 and e.status_code != 429:
                        raise
                    
                    # Calculate retry delay with exponential backoff and jitter
                    if attempt < self.retry_config.max_attempts - 1:
                        delay = self._calculate_retry_delay(attempt)
                        self.logger.warning(f"API error (attempt {attempt + 1}), retrying in {delay:.2f} seconds: {str(e)}")
                        time.sleep(delay)
                        continue
                    
                    # Last attempt failed
                    raise
            
            # All retries exhausted
            if last_exception:
                raise last_exception
            else:
                raise CloudflareAPIError("All retry attempts exhausted")
        
        return self.circuit_breaker.call(_execute_with_retries)
    
    def _calculate_retry_delay(self, attempt: int) -> float:
        """Calculate retry delay with exponential backoff and optional jitter.
        
        Args:
            attempt: Current attempt number (0-based)
            
        Returns:
            Delay in seconds
        """
        # Exponential backoff: base_delay * (2 ^ attempt)
        delay = self.retry_config.base_delay * (2 ** attempt)
        
        # Cap at max_delay
        delay = min(delay, self.retry_config.max_delay)
        
        # Add jitter if enabled
        if self.retry_config.jitter:
            # Add random jitter up to 25% of the delay
            jitter = delay * 0.25 * random.random()
            delay += jitter
        
        return delay
    
    def _handle_response(self, response: requests.Response, parser_func) -> Union[CloudflareKeysResponse, CloudflareValueResponse]:
        """Handle HTTP response and parse according to the provided parser function.
        
        Args:
            response: HTTP response object
            parser_func: Function to parse the response JSON
            
        Returns:
            Parsed response object
            
        Raises:
            CloudflareAuthenticationError: If authentication fails (401, 403)
            CloudflareRateLimitError: If rate limit exceeded (429)
            CloudflareAPIError: For other API errors
        """
        self.logger.debug(f"Response status: {response.status_code}, Content-Type: {response.headers.get('Content-Type', 'unknown')}")
        
        # Handle authentication errors
        if response.status_code in (401, 403):
            error_msg = f"Authentication failed: {response.status_code}"
            try:
                error_data = response.json()
                if 'errors' in error_data and error_data['errors']:
                    error_msg += f" - {error_data['errors'][0].get('message', '')}"
            except:
                pass
            self.logger.error(error_msg)
            raise CloudflareAuthenticationError(error_msg, status_code=response.status_code)
        
        # Handle rate limiting
        if response.status_code == 429:
            retry_after = int(response.headers.get('Retry-After', 60))
            error_msg = f"Rate limit exceeded, retry after {retry_after} seconds"
            self.logger.warning(error_msg)
            raise CloudflareRateLimitError(error_msg, retry_after=retry_after)
        
        # Handle other HTTP errors
        if not response.ok:
            try:
                error_data = response.json()
                errors = [CloudflareError(code=err.get('code', 0), message=err.get('message', '')) 
                         for err in error_data.get('errors', [])]
                error_msg = f"API error {response.status_code}: {error_data.get('errors', [{}])[0].get('message', 'Unknown error')}"
            except (ValueError, KeyError):
                errors = []
                error_msg = f"HTTP error {response.status_code}: {response.text[:200]}"
            
            self.logger.error(error_msg)
            raise CloudflareAPIError(error_msg, status_code=response.status_code, errors=errors)
        
        # Parse successful response
        try:
            # For value responses, check content type
            content_type = response.headers.get('Content-Type', '')
            
            # If it's not JSON, return raw content
            if 'application/json' not in content_type and parser_func == self._parse_value_response:
                self.logger.debug(f"Non-JSON response, returning raw content (length: {len(response.content)})")
                return CloudflareValueResponse(
                    success=True,
                    result=response.text,
                    errors=[]
                )
            
            # Try to parse as JSON
            json_data = response.json()
            return parser_func(json_data)
            
        except ValueError as e:
            # JSON parsing failed
            error_msg = f"Failed to parse API response as JSON: {str(e)}. Response text: {response.text[:200]}"
            self.logger.error(error_msg)
            
            # For value endpoint, return raw text as fallback
            if parser_func == self._parse_value_response:
                self.logger.info("Returning raw response text as value")
                return CloudflareValueResponse(
                    success=True,
                    result=response.text,
                    errors=[]
                )
            
            raise CloudflareAPIError(error_msg)
            
        except KeyError as e:
            error_msg = f"Failed to parse API response structure: {str(e)}"
            self.logger.error(error_msg)
            raise CloudflareAPIError(error_msg)
    
    def _parse_keys_response(self, data: Dict[str, Any]) -> CloudflareKeysResponse:
        """Parse list keys API response.
        
        Args:
            data: JSON response data
            
        Returns:
            CloudflareKeysResponse object
        """
        # Parse errors
        errors = [CloudflareError(code=err.get('code', 0), message=err.get('message', '')) 
                 for err in data.get('errors', [])]
        
        # Parse result info
        result_info_data = data.get('result_info', {})
        result_info = CloudflareResultInfo(
            page=result_info_data.get('page', 1),
            per_page=result_info_data.get('per_page', 0),
            count=result_info_data.get('count', 0),
            total_count=result_info_data.get('total_count', 0),
            cursor=result_info_data.get('cursor')
        )
        
        # Parse keys
        keys = []
        for key_data in data.get('result', []):
            key = CloudflareKey(
                name=key_data['name'],
                expiration=key_data.get('expiration'),
                metadata=key_data.get('metadata')
            )
            keys.append(key)
        
        return CloudflareKeysResponse(
            success=data.get('success', False),
            result=keys,
            result_info=result_info,
            errors=errors
        )
    
    def _parse_value_response(self, data: Any) -> CloudflareValueResponse:
        """Parse get value API response.
        
        Note: KV values endpoint returns the raw value, not JSON wrapped.
        For JSON responses, we need to check if it's a Cloudflare error format.
        
        Args:
            data: Response data (could be raw value or error JSON)
            
        Returns:
            CloudflareValueResponse object
        """
        # Check if this is a Cloudflare error response (JSON format)
        if isinstance(data, dict) and 'success' in data:
            errors = [CloudflareError(code=err.get('code', 0), message=err.get('message', '')) 
                     for err in data.get('errors', [])]
            return CloudflareValueResponse(
                success=data.get('success', False),
                result=data.get('result'),
                errors=errors
            )
        
        # This is a raw value response
        return CloudflareValueResponse(
            success=True,
            result=data,
            errors=[]
        )