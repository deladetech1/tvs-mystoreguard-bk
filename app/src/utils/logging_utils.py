"""
Logging utilities and helper functions for the application
"""
import asyncio
import time
import functools
from typing import Callable
from src.configs.logging import get_logger

class LogContext:
    """Context manager for structured logging with additional context"""
    
    def __init__(self, logger_name: str, operation: str, **context):
        self.logger = get_logger(logger_name)
        self.operation = operation
        self.context = context
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        self.logger.info(
            f"Starting {self.operation}",
            extra={
                "operation": self.operation,
                "extra_fields": {
                    "operation": self.operation,
                    **self.context
                }
            }
        )
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time if self.start_time else 0
        
        if exc_type is None:
            self.logger.info(
                f"Completed {self.operation}",
                extra={
                    "operation": self.operation,
                    "duration": duration,
                    "extra_fields": {
                        "operation": self.operation,
                        "duration": duration,
                        "status": "success",
                        **self.context
                    }
                }
            )
        else:
            self.logger.error(
                f"Failed {self.operation}: {str(exc_val)}",
                extra={
                    "operation": self.operation,
                    "duration": duration,
                    "error": str(exc_val),
                    "error_type": exc_type.__name__,
                    "extra_fields": {
                        "operation": self.operation,
                        "duration": duration,
                        "status": "error",
                        "error": str(exc_val),
                        "error_type": exc_type.__name__,
                        **self.context
                    }
                },
                exc_info=True
            )


def log_performance(operation_name: str = None):
    """Decorator to log function performance metrics"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            op_name = operation_name or f"{func.__module__}.{func.__name__}"
            logger = get_logger(func.__module__)
            
            start_time = time.time()
            logger.debug(f"Starting {op_name}")
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                logger.info(
                    f"Completed {op_name}",
                    extra={
                        "operation": op_name,
                        "duration": duration,
                        "extra_fields": {
                            "operation": op_name,
                            "duration": duration,
                            "status": "success"
                        }
                    }
                )
                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.error(
                    f"Failed {op_name}: {str(e)}",
                    extra={
                        "operation": op_name,
                        "duration": duration,
                        "error": str(e),
                        "extra_fields": {
                            "operation": op_name,
                            "duration": duration,
                            "status": "error",
                            "error": str(e)
                        }
                    },
                    exc_info=True
                )
                raise
        
        return wrapper
    return decorator


def log_async_performance(operation_name: str = None):
    """Decorator to log async function performance metrics"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            op_name = operation_name or f"{func.__module__}.{func.__name__}"
            logger = get_logger(func.__module__)
            
            start_time = time.time()
            logger.debug(f"Starting async {op_name}")
            
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                logger.info(
                    f"Completed async {op_name}",
                    extra={
                        "operation": op_name,
                        "duration": duration,
                        "extra_fields": {
                            "operation": op_name,
                            "duration": duration,
                            "status": "success"
                        }
                    }
                )
                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.error(
                    f"Failed async {op_name}: {str(e)}",
                    extra={
                        "operation": op_name,
                        "duration": duration,
                        "error": str(e),
                        "extra_fields": {
                            "operation": op_name,
                            "duration": duration,
                            "status": "error",
                            "error": str(e)
                        }
                    },
                    exc_info=True
                )
                raise
        
        return wrapper
    return decorator


def log_database_operation(operation: str, table: str = None, record_id: str = None):
    """Log database operations with structured data"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger("database")
            
            logger.debug(
                f"Database {operation}",
                extra={
                    "operation": operation,
                    "table": table,
                    "record_id": record_id,
                    "extra_fields": {
                        "operation": operation,
                        "table": table,
                        "record_id": record_id,
                        "type": "database_operation"
                    }
                }
            )
            
            try:
                result = func(*args, **kwargs)
                logger.info(
                    f"Database {operation} successful",
                    extra={
                        "operation": operation,
                        "table": table,
                        "record_id": record_id,
                        "extra_fields": {
                            "operation": operation,
                            "table": table,
                            "record_id": record_id,
                            "type": "database_operation",
                            "status": "success"
                        }
                    }
                )
                return result
            except Exception as e:
                logger.error(
                    f"Database {operation} failed: {str(e)}",
                    extra={
                        "operation": operation,
                        "table": table,
                        "record_id": record_id,
                        "error": str(e),
                        "extra_fields": {
                            "operation": operation,
                            "table": table,
                            "record_id": record_id,
                            "type": "database_operation",
                            "status": "error",
                            "error": str(e)
                        }
                    },
                    exc_info=True
                )
                raise
        
        return wrapper
    return decorator


def log_api_call(endpoint: str, method: str = "GET"):
    """Log API calls with request/response details (supports both sync and async functions)"""
    def decorator(func: Callable) -> Callable:
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                logger = get_logger("api")
                
                logger.debug(
                    f"API call: {method} {endpoint}",
                    extra={
                        "endpoint": endpoint,
                        "method": method,
                        "extra_fields": {
                            "endpoint": endpoint,
                            "method": method,
                            "type": "api_call"
                        }
                    }
                )
                
                try:
                    result = await func(*args, **kwargs)
                    logger.info(
                        f"API call successful: {method} {endpoint}",
                        extra={
                            "endpoint": endpoint,
                            "method": method,
                            "extra_fields": {
                                "endpoint": endpoint,
                                "method": method,
                                "type": "api_call",
                                "status": "success"
                            }
                        }
                    )
                    return result
                except Exception as e:
                    logger.error(
                        f"API call failed: {method} {endpoint} - {str(e)}",
                        extra={
                            "endpoint": endpoint,
                            "method": method,
                            "error": str(e),
                            "extra_fields": {
                                "endpoint": endpoint,
                                "method": method,
                                "type": "api_call",
                                "status": "error",
                                "error": str(e)
                            }
                        },
                        exc_info=True
                    )
                    raise
            
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                logger = get_logger("api")
                
                logger.debug(
                    f"API call: {method} {endpoint}",
                    extra={
                        "endpoint": endpoint,
                        "method": method,
                        "extra_fields": {
                            "endpoint": endpoint,
                            "method": method,
                            "type": "api_call"
                        }
                    }
                )
                
                try:
                    result = func(*args, **kwargs)
                    logger.info(
                        f"API call successful: {method} {endpoint}",
                        extra={
                            "endpoint": endpoint,
                            "method": method,
                            "extra_fields": {
                                "endpoint": endpoint,
                                "method": method,
                                "type": "api_call",
                                "status": "success"
                            }
                        }
                    )
                    return result
                except Exception as e:
                    logger.error(
                        f"API call failed: {method} {endpoint} - {str(e)}",
                        extra={
                            "endpoint": endpoint,
                            "method": method,
                            "error": str(e),
                            "extra_fields": {
                                "endpoint": endpoint,
                                "method": method,
                                "type": "api_call",
                                "status": "error",
                                "error": str(e)
                            }
                        },
                        exc_info=True
                    )
                    raise
            
            return sync_wrapper
    return decorator


def handle_controller_errors(response_model_class, success_message: str = "Operation successful"):
    """
    Decorator to handle errors in controllers and return custom response model
    
    Args:
        response_model_class: The response model class to return (e.g., Respons[SomeDto])
        success_message: Message to include in successful responses
    """
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)
            endpoint = getattr(func, '__name__', 'unknown_endpoint')
            
            try:
                result = await func(*args, **kwargs)
                
                # If result is already a response model, return it
                if hasattr(result, 'success') and hasattr(result, 'status_code'):
                    return result
                
                # If result is not a response model, wrap it
                if result is not None:
                    return response_model_class(
                        details=success_message,
                        data=[result] if not isinstance(result, list) else result,
                        success=True,
                        status_code=200
                    )
                else:
                    return response_model_class(
                        details=success_message,
                        data=[],
                        success=True,
                        status_code=200
                    )
                    
            except Exception as e:
                error_message = str(e)
                error_type = type(e).__name__
                
                # Log the error with full context
                logger.error(
                    f"Controller error in {endpoint}: {error_message}",
                    extra={
                        "endpoint": endpoint,
                        "error": error_message,
                        "error_type": error_type,
                        "extra_fields": {
                            "endpoint": endpoint,
                            "error": error_message,
                            "error_type": error_type,
                            "status": "error"
                        }
                    },
                    exc_info=True
                )
                
                # Return error response
                return response_model_class(
                    details=f"An error occurred: {error_message}",
                    error=error_message,
                    data=[],
                    success=False,
                    status_code=500
                )
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)
            endpoint = getattr(func, '__name__', 'unknown_endpoint')
            
            try:
                result = func(*args, **kwargs)
                
                # If result is already a response model, return it
                if hasattr(result, 'success') and hasattr(result, 'status_code'):
                    return result
                
                # If result is not a response model, wrap it
                if result is not None:
                    return response_model_class(
                        details=success_message,
                        data=[result] if not isinstance(result, list) else result,
                        success=True,
                        status_code=200
                    )
                else:
                    return response_model_class(
                        details=success_message,
                        data=[],
                        success=True,
                        status_code=200
                    )
                    
            except Exception as e:
                error_message = str(e)
                error_type = type(e).__name__
                
                # Log the error with full context
                logger.error(
                    f"Controller error in {endpoint}: {error_message}",
                    extra={
                        "endpoint": endpoint,
                        "error": error_message,
                        "error_type": error_type,
                        "extra_fields": {
                            "endpoint": endpoint,
                            "error": error_message,
                            "error_type": error_type,
                            "status": "error"
                        }
                    },
                    exc_info=True
                )
                
                # Return error response
                return response_model_class(
                    details=f"An error occurred: {error_message}",
                    error=error_message,
                    data=[],
                    success=False,
                    status_code=500
                )
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


class StructuredLogger:
    """Helper class for structured logging with consistent formatting"""
    
    def __init__(self, logger_name: str):
        self.logger = get_logger(logger_name)
    
    def log_event(self, event_type: str, message: str, **extra_fields):
        """Log an event with structured data"""
        self.logger.info(
            message,
            extra={
                "event_type": event_type,
                "extra_fields": {
                    "event_type": event_type,
                    **extra_fields
                }
            }
        )
    
    def log_error(self, event_type: str, message: str, error: Exception, **extra_fields):
        """Log an error with structured data"""
        self.logger.error(
            message,
            extra={
                "event_type": event_type,
                "error": str(error),
                "error_type": type(error).__name__,
                "extra_fields": {
                    "event_type": event_type,
                    "error": str(error),
                    "error_type": type(error).__name__,
                    **extra_fields
                }
            },
            exc_info=True
        )
    
    def log_metric(self, metric_name: str, value: float, unit: str = None, **extra_fields):
        """Log a metric with structured data"""
        self.logger.info(
            f"Metric: {metric_name} = {value}",
            extra={
                "metric_name": metric_name,
                "metric_value": value,
                "metric_unit": unit,
                "extra_fields": {
                    "metric_name": metric_name,
                    "metric_value": value,
                    "metric_unit": unit,
                    "type": "metric",
                    **extra_fields
                }
            }
        )


