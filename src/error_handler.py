#!/usr/bin/env python3
"""
Error Handler for MCP Browser

This module provides standardized error handling for the MCP Browser application.
"""

import enum
import logging
import traceback
import asyncio
import functools
from typing import Dict, List, Optional, Any, Callable, TypeVar, Union
from pydantic import BaseModel
from fastapi import HTTPException, status

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("error-handler")

class ErrorCode(enum.Enum):
    """Standard error codes for the application"""
    
    # Authentication errors (1000-1099)
    AUTH_INVALID_CREDENTIALS = 1000
    AUTH_TOKEN_EXPIRED = 1001
    AUTH_INVALID_TOKEN = 1002
    AUTH_INSUFFICIENT_PERMISSIONS = 1003
    AUTH_USER_DISABLED = 1004
    
    # Browser operation errors (2000-2099)
    BROWSER_NAVIGATION_FAILED = 2000
    BROWSER_TIMEOUT = 2001
    BROWSER_ELEMENT_NOT_FOUND = 2002
    BROWSER_EXECUTION_FAILED = 2003
    BROWSER_PAGE_CRASHED = 2004
    
    # Resource management errors (3000-3099)
    RESOURCE_NOT_FOUND = 3000
    RESOURCE_POOL_EXHAUSTED = 3001
    RESOURCE_ALREADY_EXISTS = 3002
    RESOURCE_LIMIT_EXCEEDED = 3003
    
    # Input validation errors (4000-4099)
    VALIDATION_ERROR = 4000
    INVALID_URL = 4001
    INVALID_SELECTOR = 4002
    INVALID_PARAMETER = 4003
    
    # System errors (5000-5099)
    INTERNAL_ERROR = 5000
    DEPENDENCY_ERROR = 5001
    NETWORK_ERROR = 5002
    DATABASE_ERROR = 5003

class ErrorDetail(BaseModel):
    """Detailed error information"""
    field: Optional[str] = None
    message: str
    code: Optional[str] = None

class ErrorResponse(BaseModel):
    """Standardized error response"""
    error_code: int
    message: str
    status_code: int
    details: Optional[List[ErrorDetail]] = None

# Map error codes to HTTP status codes
ERROR_STATUS_CODES = {
    # Authentication errors
    ErrorCode.AUTH_INVALID_CREDENTIALS: status.HTTP_401_UNAUTHORIZED,
    ErrorCode.AUTH_TOKEN_EXPIRED: status.HTTP_401_UNAUTHORIZED,
    ErrorCode.AUTH_INVALID_TOKEN: status.HTTP_401_UNAUTHORIZED,
    ErrorCode.AUTH_INSUFFICIENT_PERMISSIONS: status.HTTP_403_FORBIDDEN,
    ErrorCode.AUTH_USER_DISABLED: status.HTTP_403_FORBIDDEN,
    
    # Browser operation errors
    ErrorCode.BROWSER_NAVIGATION_FAILED: status.HTTP_400_BAD_REQUEST,
    ErrorCode.BROWSER_TIMEOUT: status.HTTP_408_REQUEST_TIMEOUT,
    ErrorCode.BROWSER_ELEMENT_NOT_FOUND: status.HTTP_404_NOT_FOUND,
    ErrorCode.BROWSER_EXECUTION_FAILED: status.HTTP_500_INTERNAL_SERVER_ERROR,
    ErrorCode.BROWSER_PAGE_CRASHED: status.HTTP_500_INTERNAL_SERVER_ERROR,
    
    # Resource management errors
    ErrorCode.RESOURCE_NOT_FOUND: status.HTTP_404_NOT_FOUND,
    ErrorCode.RESOURCE_POOL_EXHAUSTED: status.HTTP_503_SERVICE_UNAVAILABLE,
    ErrorCode.RESOURCE_ALREADY_EXISTS: status.HTTP_409_CONFLICT,
    ErrorCode.RESOURCE_LIMIT_EXCEEDED: status.HTTP_429_TOO_MANY_REQUESTS,
    
    # Input validation errors
    ErrorCode.VALIDATION_ERROR: status.HTTP_400_BAD_REQUEST,
    ErrorCode.INVALID_URL: status.HTTP_400_BAD_REQUEST,
    ErrorCode.INVALID_SELECTOR: status.HTTP_400_BAD_REQUEST,
    ErrorCode.INVALID_PARAMETER: status.HTTP_400_BAD_REQUEST,
    
    # System errors
    ErrorCode.INTERNAL_ERROR: status.HTTP_500_INTERNAL_SERVER_ERROR,
    ErrorCode.DEPENDENCY_ERROR: status.HTTP_502_BAD_GATEWAY,
    ErrorCode.NETWORK_ERROR: status.HTTP_503_SERVICE_UNAVAILABLE,
    ErrorCode.DATABASE_ERROR: status.HTTP_500_INTERNAL_SERVER_ERROR
}

class MCPBrowserException(Exception):
    """Custom exception for MCP Browser application"""
    
    def __init__(
        self, 
        error_code: ErrorCode,
        message: str = None,
        status_code: int = None,
        details: List[ErrorDetail] = None,
        original_exception: Exception = None
    ):
        """
        Initialize the exception
        
        Args:
            error_code: Error code from ErrorCode enum
            message: Error message
            status_code: HTTP status code (overrides the default for the error code)
            details: List of error details
            original_exception: The original exception that caused this error
        """
        self.error_code = error_code
        self.message = message or error_code.name
        self.status_code = status_code or ERROR_STATUS_CODES.get(
            error_code, status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        self.details = details or []
        self.original_exception = original_exception
        
        # Log the error with traceback if there was an original exception
        if original_exception:
            logger.error(
                f"Error {error_code.name}: {message}",
                exc_info=original_exception
            )
        else:
            logger.error(f"Error {error_code.name}: {message}")
            
        super().__init__(self.message)
    
    def to_response(self) -> ErrorResponse:
        """
        Convert the exception to a standardized error response
        
        Returns:
            ErrorResponse object
        """
        return ErrorResponse(
            error_code=self.error_code.value,
            message=self.message,
            status_code=self.status_code,
            details=self.details
        )
    
    def to_http_exception(self) -> HTTPException:
        """
        Convert the exception to an HTTPException
        
        Returns:
            HTTPException object
        """
        response = self.to_response()
        return HTTPException(
            status_code=self.status_code,
            detail=response.dict()
        )

class RetryConfig:
    """Configuration for retry mechanism"""
    
    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 30.0,
        backoff_factor: float = 2.0,
        retryable_errors: List[ErrorCode] = None
    ):
        """
        Initialize retry configuration
        
        Args:
            max_retries: Maximum number of retry attempts
            initial_delay: Initial delay in seconds before the first retry
            max_delay: Maximum delay in seconds between retries
            backoff_factor: Multiplier for the delay between retries
            retryable_errors: List of error codes that should be retried
        """
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.retryable_errors = retryable_errors or [
            ErrorCode.BROWSER_TIMEOUT,
            ErrorCode.NETWORK_ERROR,
            ErrorCode.RESOURCE_POOL_EXHAUSTED,
            ErrorCode.DEPENDENCY_ERROR
        ]

# Default retry configuration
DEFAULT_RETRY_CONFIG = RetryConfig()

# Type variable for return type
T = TypeVar('T')

async def with_retry(
    func: Callable[..., Any],
    *args,
    retry_config: RetryConfig = DEFAULT_RETRY_CONFIG,
    **kwargs
) -> Any:
    """
    Execute a function with retry logic
    
    Args:
        func: Function to execute
        *args: Positional arguments for the function
        retry_config: Retry configuration
        **kwargs: Keyword arguments for the function
        
    Returns:
        Result of the function
        
    Raises:
        MCPBrowserException: If all retries fail
    """
    retries = 0
    last_exception = None
    
    while retries <= retry_config.max_retries:
        try:
            return await func(*args, **kwargs)
        except MCPBrowserException as e:
            # Only retry for specified error codes
            if e.error_code not in retry_config.retryable_errors:
                raise
                
            last_exception = e
            retries += 1
            
            if retries > retry_config.max_retries:
                break
                
            # Calculate delay with exponential backoff
            delay = min(
                retry_config.initial_delay * (retry_config.backoff_factor ** (retries - 1)),
                retry_config.max_delay
            )
            
            logger.warning(
                f"Retry {retries}/{retry_config.max_retries} for error {e.error_code.name} "
                f"after {delay:.2f}s delay"
            )
            
            await asyncio.sleep(delay)
            
        except Exception as e:
            # Wrap unexpected exceptions
            error = MCPBrowserException(
                error_code=ErrorCode.INTERNAL_ERROR,
                message=f"Unexpected error: {str(e)}",
                original_exception=e
            )
            
            last_exception = error
            retries += 1
            
            if retries > retry_config.max_retries:
                break
                
            # Calculate delay with exponential backoff
            delay = min(
                retry_config.initial_delay * (retry_config.backoff_factor ** (retries - 1)),
                retry_config.max_delay
            )
            
            logger.warning(
                f"Retry {retries}/{retry_config.max_retries} for unexpected error "
                f"after {delay:.2f}s delay"
            )
            
            await asyncio.sleep(delay)
    
    # If we get here, all retries failed
    if last_exception:
        # Update the message to indicate retry failure
        if isinstance(last_exception, MCPBrowserException):
            last_exception.message = f"Failed after {retries} retries: {last_exception.message}"
        
        raise last_exception
    
    # This should not happen but just in case
    raise MCPBrowserException(
        error_code=ErrorCode.INTERNAL_ERROR,
        message=f"Failed after {retries} retries with no specific error"
    )

def handle_exceptions(func):
    """
    Decorator to handle exceptions in async functions
    
    Args:
        func: Async function to wrap
        
    Returns:
        Wrapped function
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except MCPBrowserException as e:
            # Convert to HTTP exception
            raise e.to_http_exception()
        except Exception as e:
            # Wrap unexpected exceptions
            error = MCPBrowserException(
                error_code=ErrorCode.INTERNAL_ERROR,
                message=f"Unexpected error: {str(e)}",
                original_exception=e
            )
            
            raise error.to_http_exception()
            
    return wrapper 