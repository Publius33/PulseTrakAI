"""
Global Error Handler Middleware for PulseTrakAI™

Catches all unhandled exceptions and returns sanitized responses.
Logs full tracebacks internally with unique error IDs.

© PUBLIUS33™ — PulseTrakAI™ — All Rights Reserved.
"""
import logging
import uuid
import traceback
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class ErrorHandler:
    """Global error handler for FastAPI application."""
    
    @staticmethod
    def generate_error_id() -> str:
        """Generate unique error identifier."""
        return str(uuid.uuid4())
    
    @staticmethod
    def get_client_ip(request: Request) -> str:
        """Extract client IP from request."""
        if request.client:
            return request.client.host
        return "unknown"
    
    @staticmethod
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """Handle HTTPException (401, 403, 404, etc.)."""
        error_id = ErrorHandler.generate_error_id()
        client_ip = ErrorHandler.get_client_ip(request)
        
        logger.warning(
            f"HTTP Exception | "
            f"error_id={error_id} | "
            f"status={exc.status_code} | "
            f"detail={exc.detail} | "
            f"path={request.url.path} | "
            f"ip={client_ip}"
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "id": error_id,
                    "status": exc.status_code,
                    "message": exc.detail or "An error occurred",
                    "timestamp": logger.name
                }
            }
        )
    
    @staticmethod
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle Pydantic validation errors."""
        error_id = ErrorHandler.generate_error_id()
        client_ip = ErrorHandler.get_client_ip(request)
        
        # Extract validation errors
        validation_errors = []
        for error in exc.errors():
            validation_errors.append({
                "field": ".".join(str(x) for x in error["loc"][1:]),
                "message": error["msg"],
                "type": error["type"]
            })
        
        logger.warning(
            f"Validation Error | "
            f"error_id={error_id} | "
            f"path={request.url.path} | "
            f"ip={client_ip} | "
            f"errors={validation_errors}"
        )
        
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "id": error_id,
                    "status": 422,
                    "message": "Validation failed",
                    "details": validation_errors,
                    "timestamp": logger.name
                }
            }
        )
    
    @staticmethod
    async def generic_exception_handler(request: Request, exc: Exception):
        """Handle all unhandled exceptions."""
        error_id = ErrorHandler.generate_error_id()
        client_ip = ErrorHandler.get_client_ip(request)
        
        # Log full traceback internally
        tb = traceback.format_exc()
        
        logger.error(
            f"Unhandled Exception | "
            f"error_id={error_id} | "
            f"type={type(exc).__name__} | "
            f"path={request.url.path} | "
            f"method={request.method} | "
            f"ip={client_ip}\n"
            f"Traceback:\n{tb}"
        )
        
        # Return sanitized response (no stack trace to client)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "id": error_id,
                    "status": 500,
                    "message": "An internal server error occurred",
                    "detail": "The error has been logged and will be investigated",
                    "timestamp": logger.name
                }
            }
        )


def register_error_handlers(app):
    """Register all error handlers to FastAPI app."""
    from fastapi.exceptions import RequestValidationError
    from starlette.exceptions import HTTPException as StarletteHTTPException
    
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        return await ErrorHandler.http_exception_handler(request, exc)
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return await ErrorHandler.validation_exception_handler(request, exc)
    
    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        return await ErrorHandler.generic_exception_handler(request, exc)
    
    logger.info("Global error handlers registered")
