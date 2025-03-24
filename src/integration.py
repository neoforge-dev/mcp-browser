#!/usr/bin/env python3
"""
Integration Module for MCP Browser

This module integrates BrowserPool, error handling, and authentication components.
"""

import os
import logging
import asyncio
import time
import uuid
from typing import Dict, List, Optional, Any, Set, Callable, AsyncGenerator
from datetime import datetime, timedelta

import jwt
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from contextlib import asynccontextmanager

# Import our components
from browser_pool import BrowserInstance, browser_pool, initialize_browser_pool, close_browser_pool
from error_handler import (
    MCPBrowserException, ErrorCode, RetryConfig, with_retry, handle_exceptions, DEFAULT_RETRY_CONFIG
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("integration")

# OAuth2 password bearer for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# JWT configuration
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "mcp-browser-default-secret-key")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.environ.get("REFRESH_TOKEN_EXPIRE_DAYS", 7))

# User models
class User(BaseModel):
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: Optional[bool] = None
    permissions: List[str] = []

# Fake database for demo
fake_users_db = {
    "admin": {
        "username": "admin",
        "full_name": "Administrator",
        "email": "admin@example.com",
        "disabled": False,
        "permissions": ["browser:full", "admin"]
    },
    "user": {
        "username": "user",
        "full_name": "Regular User",
        "email": "user@example.com",
        "disabled": False,
        "permissions": ["browser:basic"]
    }
}

class BrowserManager:
    """Manager for browser resources"""
    
    def __init__(self):
        """Initialize the browser manager"""
        self.session_contexts = {}  # Maps session IDs to context IDs
    
    async def initialize(self, max_browsers: int = 10, idle_timeout: int = 300):
        """
        Initialize the browser manager
        
        Args:
            max_browsers: Maximum number of concurrent browser instances
            idle_timeout: Time in seconds after which idle browsers are closed
        """
        await initialize_browser_pool(max_browsers, idle_timeout)
        logger.info(f"Browser manager initialized with max_browsers={max_browsers}")
    
    async def shutdown(self):
        """Shutdown the browser manager"""
        await close_browser_pool()
        logger.info("Browser manager shut down")
    
    async def create_browser_context(
        self, 
        session_id: str, 
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a browser context for a session
        
        Args:
            session_id: Session identifier
            user_id: User identifier
            
        Returns:
            Context information
        """
        try:
            # Get a browser from the pool
            browser_instance = await browser_pool.get_browser()
            
            # Create context ID
            context_id = str(uuid.uuid4())
            
            # Create the context
            context = await browser_instance.create_context(
                context_id,
                user_id=user_id
            )
            
            # Store the mapping
            self.session_contexts[session_id] = {
                "context_id": context_id,
                "browser_id": browser_instance.id,
                "created_at": time.time(),
                "user_id": user_id
            }
            
            logger.info(f"Created browser context {context_id} for session {session_id}")
            return context
            
        except Exception as e:
            logger.error(f"Error creating browser context: {str(e)}")
            raise MCPBrowserException(
                error_code=ErrorCode.RESOURCE_POOL_EXHAUSTED,
                message=f"Failed to create browser context: {str(e)}",
                original_exception=e
            )
    
    async def get_browser_context(self, session_id: str) -> Dict[str, Any]:
        """
        Get the browser context for a session
        
        Args:
            session_id: Session identifier
            
        Returns:
            Context information
        """
        session_info = self.session_contexts.get(session_id)
        if not session_info:
            raise MCPBrowserException(
                error_code=ErrorCode.RESOURCE_NOT_FOUND,
                message=f"No browser context found for session {session_id}"
            )
        
        return session_info
    
    async def close_browser_context(self, session_id: str):
        """
        Close the browser context for a session
        
        Args:
            session_id: Session identifier
        """
        session_info = self.session_contexts.get(session_id)
        if not session_info:
            logger.warning(f"No browser context found for session {session_id}")
            return
        
        context_id = session_info["context_id"]
        browser_id = session_info["browser_id"]
        
        try:
            # Get the browser instance
            browser = browser_pool.browsers.get(browser_id)
            if browser:
                # Close the context
                await browser.close_context(context_id)
            
            # Remove the session mapping
            del self.session_contexts[session_id]
            logger.info(f"Closed browser context for session {session_id}")
            
        except Exception as e:
            logger.error(f"Error closing browser context: {str(e)}")
            # Still remove the session mapping
            if session_id in self.session_contexts:
                del self.session_contexts[session_id]

class AuthManager:
    """Manager for authentication and authorization"""
    
    def __init__(self):
        """Initialize the auth manager"""
        pass
    
    async def get_user(self, username: str) -> Optional[User]:
        """
        Get a user by username
        
        Args:
            username: Username
            
        Returns:
            User object or None if not found
        """
        user_data = fake_users_db.get(username)
        if user_data:
            return User(**user_data)
        return None
    
    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """
        Authenticate a user
        
        Args:
            username: Username
            password: Password
            
        Returns:
            User object if authentication succeeds, None otherwise
        """
        # For demo, any password works
        user = await self.get_user(username)
        if not user:
            return None
        return user
    
    async def create_access_token(
        self, 
        data: Dict[str, Any], 
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create an access token
        
        Args:
            data: Claims to include in the token
            expires_delta: Token expiration time
            
        Returns:
            JWT token
        """
        to_encode = data.copy()
        
        # Set expiration
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            
        to_encode.update({"exp": expire})
        
        # Create the token
        encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        
        return encoded_jwt
    
    async def create_refresh_token(self, data: Dict[str, Any]) -> str:
        """
        Create a refresh token
        
        Args:
            data: Claims to include in the token
            
        Returns:
            JWT token
        """
        to_encode = data.copy()
        
        # Set expiration
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire, "refresh": True})
        
        # Create the token
        encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        
        return encoded_jwt
    
    async def decode_token(self, token: str) -> Dict[str, Any]:
        """
        Decode a JWT token
        
        Args:
            token: JWT token
            
        Returns:
            Token claims
            
        Raises:
            MCPBrowserException: If token is invalid
        """
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            raise MCPBrowserException(
                error_code=ErrorCode.AUTH_TOKEN_EXPIRED,
                message="Token has expired"
            )
        except jwt.InvalidTokenError:
            raise MCPBrowserException(
                error_code=ErrorCode.AUTH_INVALID_TOKEN,
                message="Invalid token"
            )
    
    async def get_current_user(self, token: str = Depends(oauth2_scheme)) -> User:
        """
        Get the current user from a token
        
        Args:
            token: JWT token
            
        Returns:
            User object
            
        Raises:
            HTTPException: If token is invalid or user not found
        """
        try:
            payload = await self.decode_token(token)
            username = payload.get("sub")
            if username is None:
                raise MCPBrowserException(
                    error_code=ErrorCode.AUTH_INVALID_TOKEN,
                    message="Token missing username"
                )
                
            user = await self.get_user(username)
            if user is None:
                raise MCPBrowserException(
                    error_code=ErrorCode.AUTH_INVALID_TOKEN,
                    message="User not found"
                )
                
            return user
            
        except MCPBrowserException as e:
            raise e.to_http_exception()
    
    async def get_current_active_user(self, current_user: User = Depends(get_current_user)) -> User:
        """
        Check if the current user is active
        
        Args:
            current_user: User object
            
        Returns:
            User object if active
            
        Raises:
            HTTPException: If user is disabled
        """
        if current_user.disabled:
            raise MCPBrowserException(
                error_code=ErrorCode.AUTH_USER_DISABLED,
                message="Inactive user"
            ).to_http_exception()
            
        return current_user
    
    def has_permission(self, user: User, required_permission: str) -> bool:
        """
        Check if a user has a permission
        
        Args:
            user: User object
            required_permission: Required permission
            
        Returns:
            True if user has permission, False otherwise
        """
        return required_permission in user.permissions or "admin" in user.permissions

# Create global instances
browser_manager = BrowserManager()
auth_manager = AuthManager()

def configure_app(app: FastAPI) -> FastAPI:
    """
    Configure the FastAPI app with lifespan event handlers
    
    Args:
        app: FastAPI app
        
    Returns:
        FastAPI app with lifespan configured
    """
    # Define lifespan context manager for this app
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        """Lifespan context manager for startup and shutdown events"""
        # Startup: Initialize services
        max_browsers = int(os.environ.get("MAX_BROWSERS", 10))
        idle_timeout = int(os.environ.get("IDLE_TIMEOUT", 300))
        
        await browser_manager.initialize(max_browsers, idle_timeout)
        
        logger.info("Integration services initialized")
        
        yield  # Run the application
        
        # Shutdown: Clean up resources
        await browser_manager.shutdown()
        
        logger.info("Integration services shut down")
    
    # Configure app with lifespan
    app.router.lifespan_context = lifespan
    
    return app

# Export components and functions
__all__ = [
    "browser_manager",
    "auth_manager",
    "configure_app",
    "with_retry",
    "handle_exceptions",
    "DEFAULT_RETRY_CONFIG"
] 