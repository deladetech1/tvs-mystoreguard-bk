import time
import uuid
from typing import Callable
from fastapi import Request, Response
from fastapi.responses import StreamingResponse
from starlette.middleware.base import BaseHTTPMiddleware
from src.configs.logging import get_logger


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests and responses"""
    
    def __init__(self, app, logger_name: str = "http"):
        super().__init__(app)
        self.logger = get_logger(logger_name)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        
        # Start timing
        start_time = time.time()
        
        # Log request
        self._log_request(request, request_id)
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Log response
            self._log_response(request, response, process_time, request_id)
            
            return response
            
        except Exception as e:
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Log error
            self._log_error(request, e, process_time, request_id)
            
            # Re-raise the exception
            raise
    
    def _log_request(self, request: Request, request_id: str):
        """Log incoming request details"""
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        
        # Get request body for POST/PUT/PATCH requests (be careful with large bodies)
        body = None
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                # Only log body for small requests (< 1KB)
                if request.headers.get("content-length", "0") < "1024":
                    # Note: We can't await here since this is not an async function
                    # The body will be consumed by FastAPI before reaching this point
                    body = "<request body available but not logged in sync context>"
            except Exception:
                body = "<unable to read body>"
        
        self.logger.info(
            f"Request started",
            extra={
                "request_id": request_id,
                "method": request.method,
                "url": str(request.url),
                "path": request.url.path,
                "query_params": dict(request.query_params),
                "client_ip": client_ip,
                "user_agent": user_agent,
                "headers": dict(request.headers),
                "body": body,
                "extra_fields": {
                    "request_id": request_id,
                    "method": request.method,
                    "url": str(request.url),
                    "path": request.url.path,
                    "client_ip": client_ip,
                    "user_agent": user_agent
                }
            }
        )
    
    def _log_response(self, request: Request, response: Response, process_time: float, request_id: str):
        """Log response details"""
        status_code = response.status_code
        
        # Determine log level based on status code
        if status_code >= 500:
            log_level = "error"
        elif status_code >= 400:
            log_level = "warning"
        else:
            log_level = "info"
        
        # Get response body for small responses
        response_body = None
        if hasattr(response, 'body') and response.body:
            try:
                # Only log body for small responses (< 1KB)
                if len(response.body) < 1024:
                    response_body = response.body.decode("utf-8", errors="ignore")
            except Exception:
                response_body = "<unable to read response body>"
        
        # Log the response
        getattr(self.logger, log_level)(
            f"Request completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": status_code,
                "process_time": round(process_time, 4),
                "response_headers": dict(response.headers),
                "response_body": response_body,
                "extra_fields": {
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": status_code,
                    "process_time": round(process_time, 4)
                }
            }
        )
    
    def _log_error(self, request: Request, error: Exception, process_time: float, request_id: str):
        """Log error details"""
        self.logger.error(
            f"Request failed: {str(error)}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "error": str(error),
                "error_type": type(error).__name__,
                "process_time": round(process_time, 4),
                "extra_fields": {
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "error": str(error),
                    "error_type": type(error).__name__,
                    "process_time": round(process_time, 4)
                }
            },
            exc_info=True
        )


class SecurityLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging security-related events"""
    
    def __init__(self, app, logger_name: str = "security"):
        super().__init__(app)
        self.logger = get_logger(logger_name)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check for suspicious patterns
        self._check_suspicious_activity(request)
        
        # Process request
        response = await call_next(request)
        
        # Log security events based on response
        self._log_security_events(request, response)
        
        return response
    
    def _check_suspicious_activity(self, request: Request):
        """Check for suspicious request patterns"""
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "")
        path = request.url.path
        
        # Check for common attack patterns
        suspicious_patterns = [
            "..",  # Path traversal
            "script",  # XSS attempts
            "union",  # SQL injection
            "select",  # SQL injection
            "drop",  # SQL injection
            "delete",  # SQL injection
            "insert",  # SQL injection
            "update",  # SQL injection
            "exec",  # Command injection
            "eval",  # Code injection
        ]
        
        for pattern in suspicious_patterns:
            if pattern in path.lower() or pattern in user_agent.lower():
                self.logger.warning(
                    f"Suspicious activity detected",
                    extra={
                        "client_ip": client_ip,
                        "user_agent": user_agent,
                        "path": path,
                        "pattern": pattern,
                        "extra_fields": {
                            "client_ip": client_ip,
                            "user_agent": user_agent,
                            "path": path,
                            "pattern": pattern,
                            "event_type": "suspicious_activity"
                        }
                    }
                )
                break
    
    def _log_security_events(self, request: Request, response: Response):
        """Log security-related events based on response"""
        client_ip = request.client.host if request.client else "unknown"
        status_code = response.status_code
        
        # Log authentication failures
        if status_code == 401:
            self.logger.warning(
                f"Authentication failed",
                extra={
                    "client_ip": client_ip,
                    "path": request.url.path,
                    "method": request.method,
                    "status_code": status_code,
                    "extra_fields": {
                        "client_ip": client_ip,
                        "path": request.url.path,
                        "method": request.method,
                        "status_code": status_code,
                        "event_type": "auth_failure"
                    }
                }
            )
        
        # Log authorization failures
        elif status_code == 403:
            self.logger.warning(
                f"Authorization failed",
                extra={
                    "client_ip": client_ip,
                    "path": request.url.path,
                    "method": request.method,
                    "status_code": status_code,
                    "extra_fields": {
                        "client_ip": client_ip,
                        "path": request.url.path,
                        "method": request.method,
                        "status_code": status_code,
                        "event_type": "authz_failure"
                    }
                }
            )
        
        # Log server errors (potential security issues)
        elif status_code >= 500:
            self.logger.error(
                f"Server error - potential security issue",
                extra={
                    "client_ip": client_ip,
                    "path": request.url.path,
                    "method": request.method,
                    "status_code": status_code,
                    "extra_fields": {
                        "client_ip": client_ip,
                        "path": request.url.path,
                        "method": request.method,
                        "status_code": status_code,
                        "event_type": "server_error"
                    }
                }
            )
