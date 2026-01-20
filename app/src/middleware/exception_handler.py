"""
FastAPI exception handler for custom response exceptions
"""
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from src.entities.shared.sh_response import ResponseException
from src.configs.logging import get_logger

logger = get_logger("exception_handler")


async def response_exception_handler(request: Request, exc: ResponseException) -> JSONResponse:
    """
    Handle ResponseException and return the custom response model as JSON
    """
    logger.info(
        f"Handling ResponseException: {exc.message}",
        extra={
            "extra_fields": {
                "endpoint": str(request.url),
                "method": request.method,
                "error": exc.message,
                "status_code": exc.response.status_code
            }
        }
    )
    
    # Return the response model as JSON with the appropriate status code
    return JSONResponse(
        status_code=exc.response.status_code,
        content=exc.response.model_dump()
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Handle HTTPException and return proper error response with the exception detail.
    This ensures that location permission errors and other HTTPExceptions are properly returned.
    """
    logger.warning(
        f"HTTPException: {exc.detail}",
        extra={
            "extra_fields": {
                "endpoint": str(request.url),
                "method": request.method,
                "error": exc.detail,
                "status_code": exc.status_code
            }
        }
    )
    
    # Return HTTPException details in FastAPI's default format
    # This ensures the detail message is directly accessible to clients
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle generic exceptions and return a standardized error response.
    
    Note: HTTPException and ResponseException are handled by their specific handlers
    and should not reach this handler due to FastAPI's exception handling order.
    """
    # Re-raise HTTPException and ResponseException to let their handlers process them
    # This is a safety check, though FastAPI should handle this automatically
    if isinstance(exc, HTTPException):
        raise exc
    if isinstance(exc, ResponseException):
        raise exc
    
    logger.error(
        f"Unhandled exception: {str(exc)}",
        extra={
            "extra_fields": {
                "endpoint": str(request.url),
                "method": request.method,
                "error": str(exc),
                "error_type": type(exc).__name__
            }
        },
        exc_info=True
    )
    
    # Return a generic error response
    error_response = {
        "details": "An unexpected error occurred",
        "error": str(exc),
        "data": [],
        "status_code": 500,
        "success": False
    }
    
    return JSONResponse(
        status_code=500,
        content=error_response
    )
