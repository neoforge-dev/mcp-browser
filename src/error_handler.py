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

class ErrorCode(str, enum.Enum):
    """Error codes for MCP Browser exceptions"""
    
    # Resource Management Errors
    RESOURCE_POOL_EXHAUSTED = "RESOURCE_POOL_EXHAUSTED"
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    RESOURCE_LIMIT_EXCEEDED = "RESOURCE_LIMIT_EXCEEDED"
    RESOURCE_RECOVERY_FAILED = "RESOURCE_RECOVERY_FAILED"
    RESOURCE_CLEANUP_FAILED = "RESOURCE_CLEANUP_FAILED"
    RESOURCE_MONITOR_ERROR = "RESOURCE_MONITOR_ERROR"
    MAX_BROWSERS_REACHED = "MAX_BROWSERS_REACHED"
    POOL_SHUTTING_DOWN = "POOL_SHUTTING_DOWN"
    
    # Browser Management Errors
    BROWSER_INITIALIZATION_FAILED = "BROWSER_INITIALIZATION_FAILED"
    BROWSER_CLEANUP_FAILED = "BROWSER_CLEANUP_FAILED"
    BROWSER_RECOVERY_FAILED = "BROWSER_RECOVERY_FAILED"
    BROWSER_PROCESS_ERROR = "BROWSER_PROCESS_ERROR"
    BROWSER_NOT_INITIALIZED = "BROWSER_NOT_INITIALIZED"
    CONTEXT_CREATION_FAILED = "CONTEXT_CREATION_FAILED"
    CONTEXT_CLEANUP_FAILED = "CONTEXT_CLEANUP_FAILED"
    CONTEXT_RECOVERY_FAILED = "CONTEXT_RECOVERY_FAILED"
    
    # Page Management Errors
    PAGE_CREATION_FAILED = "PAGE_CREATION_FAILED"
    PAGE_NAVIGATION_FAILED = "PAGE_NAVIGATION_FAILED"
    PAGE_TIMEOUT = "PAGE_TIMEOUT"
    PAGE_ERROR = "PAGE_ERROR"
    
    # Network Errors
    NETWORK_ERROR = "NETWORK_ERROR"
    CONNECTION_ERROR = "CONNECTION_ERROR"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"
    
    # Authentication Errors
    AUTH_REQUIRED = "AUTH_REQUIRED"
    AUTH_FAILED = "AUTH_FAILED"
    AUTH_EXPIRED = "AUTH_EXPIRED"
    
    # Permission Errors
    PERMISSION_DENIED = "PERMISSION_DENIED"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    
    # General Errors
    INVALID_REQUEST = "INVALID_REQUEST"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"

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
    ErrorCode.AUTH_REQUIRED: status.HTTP_401_UNAUTHORIZED,
    ErrorCode.AUTH_FAILED: status.HTTP_401_UNAUTHORIZED,
    ErrorCode.AUTH_EXPIRED: status.HTTP_401_UNAUTHORIZED,
    
    # Browser operation errors
    ErrorCode.PAGE_NAVIGATION_FAILED: status.HTTP_400_BAD_REQUEST,
    ErrorCode.PAGE_TIMEOUT: status.HTTP_408_REQUEST_TIMEOUT,
    ErrorCode.PAGE_ERROR: status.HTTP_500_INTERNAL_SERVER_ERROR,
    ErrorCode.PAGE_CREATION_FAILED: status.HTTP_500_INTERNAL_SERVER_ERROR,
    
    # Resource management errors
    ErrorCode.RESOURCE_NOT_FOUND: status.HTTP_404_NOT_FOUND,
    ErrorCode.RESOURCE_POOL_EXHAUSTED: status.HTTP_503_SERVICE_UNAVAILABLE,
    ErrorCode.RESOURCE_LIMIT_EXCEEDED: status.HTTP_429_TOO_MANY_REQUESTS,
    ErrorCode.MAX_BROWSERS_REACHED: status.HTTP_429_TOO_MANY_REQUESTS,
    ErrorCode.POOL_SHUTTING_DOWN: status.HTTP_503_SERVICE_UNAVAILABLE,
    ErrorCode.RESOURCE_RECOVERY_FAILED: status.HTTP_500_INTERNAL_SERVER_ERROR,
    ErrorCode.RESOURCE_CLEANUP_FAILED: status.HTTP_500_INTERNAL_SERVER_ERROR,
    ErrorCode.RESOURCE_MONITOR_ERROR: status.HTTP_500_INTERNAL_SERVER_ERROR,
    
    # Browser operation errors
    ErrorCode.BROWSER_INITIALIZATION_FAILED: status.HTTP_500_INTERNAL_SERVER_ERROR,
    ErrorCode.BROWSER_NOT_INITIALIZED: status.HTTP_500_INTERNAL_SERVER_ERROR,
    ErrorCode.BROWSER_CLEANUP_FAILED: status.HTTP_500_INTERNAL_SERVER_ERROR,
    ErrorCode.BROWSER_RECOVERY_FAILED: status.HTTP_500_INTERNAL_SERVER_ERROR,
    ErrorCode.BROWSER_PROCESS_ERROR: status.HTTP_500_INTERNAL_SERVER_ERROR,
    ErrorCode.CONTEXT_CREATION_FAILED: status.HTTP_500_INTERNAL_SERVER_ERROR,
    ErrorCode.CONTEXT_CLEANUP_FAILED: status.HTTP_500_INTERNAL_SERVER_ERROR,
    ErrorCode.CONTEXT_RECOVERY_FAILED: status.HTTP_500_INTERNAL_SERVER_ERROR,
    
    # Input validation errors
    ErrorCode.INVALID_REQUEST: status.HTTP_400_BAD_REQUEST,
    
    # System errors
    ErrorCode.INTERNAL_ERROR: status.HTTP_500_INTERNAL_SERVER_ERROR,
    ErrorCode.NOT_IMPLEMENTED: status.HTTP_501_NOT_IMPLEMENTED,
    
    # Network errors
    ErrorCode.NETWORK_ERROR: status.HTTP_503_SERVICE_UNAVAILABLE,
    ErrorCode.CONNECTION_ERROR: status.HTTP_503_SERVICE_UNAVAILABLE,
    ErrorCode.TIMEOUT_ERROR: status.HTTP_408_REQUEST_TIMEOUT
}

class MCPBrowserException(Exception):
    """Custom exception for MCP Browser application"""
    
    def __init__(
        self,
        error_code: ErrorCode,
        message: str,
        original_exception: Optional[Exception] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the exception
        
        Args:
            error_code: Error code from ErrorCode enum
            message: Error message
            original_exception: The original exception that caused this error
            details: Additional details about the error
        """
        self.error_code = error_code
        self.message = message or error_code.name
        self.original_exception = original_exception
        self.details = details or {}
        
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
            error_code=ERROR_STATUS_CODES.get(self.error_code, status.HTTP_500_INTERNAL_SERVER_ERROR),
            message=self.message,
            status_code=ERROR_STATUS_CODES.get(self.error_code, status.HTTP_500_INTERNAL_SERVER_ERROR),
            details=[ErrorDetail(field="error_code", message=str(self.error_code))]
        )
    
    def to_http_exception(self) -> HTTPException:
        """
        Convert the exception to an HTTPException
        
        Returns:
            HTTPException object
        """
        response = self.to_response()
        return HTTPException(
            status_code=ERROR_STATUS_CODES.get(self.error_code, status.HTTP_500_INTERNAL_SERVER_ERROR),
            detail=response.dict()
        )

class RetryConfig:
    """Configuration for retry behavior"""
    
    def __init__(
        self,
        max_retries: int = 3,
        delay: float = 1.0,
        backoff: float = 2.0,
        exceptions: Optional[List[type]] = None
    ):
        """
        Initialize retry configuration
        
        Args:
            max_retries: Maximum number of retry attempts
            delay: Initial delay in seconds before the first retry
            backoff: Multiplier for the delay between retries
            exceptions: List of exception types that should be retried
        """
        self.max_retries = max_retries
        self.delay = delay
        self.backoff = backoff
        self.exceptions = exceptions or [Exception]

# Default retry configuration
DEFAULT_RETRY_CONFIG = RetryConfig()

# Type variable for return type
T = TypeVar('T')

def with_retry(config: Optional[RetryConfig] = None):
    """
    Decorator for retrying operations that may fail
    
    Args:
        config: Retry configuration. If None, uses DEFAULT_RETRY_CONFIG
    """
    if config is None:
        config = DEFAULT_RETRY_CONFIG
    
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            delay = config.delay
            
            for attempt in range(config.max_retries):
                try:
                    return await func(*args, **kwargs)
                except tuple(config.exceptions) as e:
                    last_exception = e
                    if attempt < config.max_retries - 1:
                        logger.warning(
                            f"Attempt {attempt + 1} failed, retrying in {delay:.1f}s: {str(e)}"
                        )
                        await asyncio.sleep(delay)
                        delay *= config.backoff
                    else:
                        logger.error(
                            f"All {config.max_retries} attempts failed: {str(e)}"
                        )
            
            raise last_exception
        
        return wrapper
    
    return decorator

def handle_exceptions(func: Callable):
    """
    Decorator for standardized exception handling
    
    Args:
        func: The function to wrap
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except MCPBrowserException as e:
            # Log the error with stack trace for debugging
            logger.error(
                f"MCPBrowserException: {e.error_code} - {e.message}",
                exc_info=True
            )
            
            # Convert to HTTP exception
            status_code = ERROR_STATUS_CODES.get(e.error_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            if e.error_code in [
                ErrorCode.AUTH_REQUIRED,
                ErrorCode.AUTH_FAILED,
                ErrorCode.AUTH_EXPIRED
            ]:
                status_code = status.HTTP_401_UNAUTHORIZED
            elif e.error_code in [
                ErrorCode.PERMISSION_DENIED,
                ErrorCode.RATE_LIMIT_EXCEEDED
            ]:
                status_code = status.HTTP_403_FORBIDDEN
            elif e.error_code in [
                ErrorCode.RESOURCE_NOT_FOUND,
                ErrorCode.PAGE_ERROR
            ]:
                status_code = status.HTTP_404_NOT_FOUND
            elif e.error_code in [
                ErrorCode.INVALID_REQUEST,
                ErrorCode.PAGE_NAVIGATION_FAILED
            ]:
                status_code = status.HTTP_400_BAD_REQUEST
            elif e.error_code in [
                ErrorCode.RESOURCE_POOL_EXHAUSTED,
                ErrorCode.RESOURCE_LIMIT_EXCEEDED
            ]:
                status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            
            raise HTTPException(
                status_code=status_code,
                detail={
                    "error_code": e.error_code,
                    "message": e.message,
                    "details": e.details
                }
            )
        except Exception as e:
            # Log unexpected errors
            logger.error("Unexpected error:", exc_info=True)
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error_code": ErrorCode.INTERNAL_ERROR,
                    "message": "An unexpected error occurred",
                    "details": {"error": str(e)}
                }
            )
    
    return wrapper 