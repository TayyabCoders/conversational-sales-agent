from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
import structlog
import traceback
import os

logger = structlog.get_logger(__name__)

def create_error_response(success: bool, code: str, message: str, details: dict = None, status_code: int = 500):
    """Create standardized error response."""
    response_data = {
        "success": success,
        "error": {
            "code": code,
            "message": message,
            "details": details or {}
        }
    }
    
    # Add stack trace in development mode
    if os.getenv("DEBUG", "false").lower() == "true" and details and "traceback" in details:
        response_data["error"]["traceback"] = details["traceback"]
    
    return JSONResponse(
        status_code=status_code,
        content=response_data
    )

async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all for any unhandled exceptions."""
    logger.error(
        "Unhandled exception occurred",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        traceback=traceback.format_exc()
    )
    
    # Include traceback in development
    details = {}
    if os.getenv("DEBUG", "false").lower() == "true":
        details["traceback"] = traceback.format_exc()
    
    return create_error_response(
        success=False,
        code="INTERNAL_SERVER_ERROR",
        message="An unexpected error occurred internal to the server.",
        details=details,
        status_code=500
    )

async def http_exception_handler(request: Request, exc: HTTPException):
    """Handler for standard FastAPI/Starlette HTTPExceptions."""
    logger.warning(
        "HTTP exception occurred",
        path=request.url.path,
        method=request.method,
        status_code=exc.status_code,
        detail=exc.detail
    )
    return create_error_response(
        success=False,
        code=f"HTTP_{exc.status_code}",
        message=str(exc.detail),
        status_code=exc.status_code
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handler for Pydantic validation errors (422)."""
    logger.warning(
        "Validation error occurred",
        path=request.url.path,
        method=request.method,
        errors=exc.errors()
    )
    return create_error_response(
        success=False,
        code="VALIDATION_ERROR",
        message="Request validation failed.",
        details={"errors": exc.errors()},
        status_code=422
    )

async def database_integrity_error_handler(request: Request, exc: IntegrityError):
    """Handler for database integrity errors (unique constraints, foreign keys)."""
    error_message = str(exc.orig) if hasattr(exc, 'orig') else str(exc)
    
    logger.warning(
        "Database integrity error",
        path=request.url.path,
        method=request.method,
        error=error_message
    )
    
    # Parse common integrity errors
    if "unique constraint" in error_message.lower() or "duplicate" in error_message.lower():
        return create_error_response(
            success=False,
            code="CONFLICT",
            message="Duplicate entry found. The resource already exists.",
            details={"error": error_message} if os.getenv("DEBUG", "false").lower() == "true" else {},
            status_code=409
        )
    elif "foreign key constraint" in error_message.lower():
        return create_error_response(
            success=False,
            code="FOREIGN_KEY_CONSTRAINT",
            message="Foreign key constraint failed. Referenced resource does not exist.",
            details={"error": error_message} if os.getenv("DEBUG", "false").lower() == "true" else {},
            status_code=400
        )
    else:
        return create_error_response(
            success=False,
            code="DATABASE_ERROR",
            message="Database integrity error occurred.",
            details={"error": error_message} if os.getenv("DEBUG", "false").lower() == "true" else {},
            status_code=400
        )

async def database_error_handler(request: Request, exc: SQLAlchemyError):
    """Handler for general SQLAlchemy errors."""
    logger.error(
        "Database error occurred",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        traceback=traceback.format_exc()
    )
    
    details = {}
    if os.getenv("DEBUG", "false").lower() == "true":
        details["error"] = str(exc)
        details["traceback"] = traceback.format_exc()
    
    return create_error_response(
        success=False,
        code="DATABASE_ERROR",
        message="A database error occurred.",
        details=details,
        status_code=500
    )

async def not_found_handler(request: Request, exc: Exception):
    """Handler for 404 Not Found errors."""
    logger.info(
        "Route not found",
        path=request.url.path,
        method=request.method
    )
    return create_error_response(
        success=False,
        code="NOT_FOUND",
        message=f"Route {request.method} {request.url.path} not found",
        status_code=404
    )

def setup_exception_handlers(app):
    """Register all exception handlers with the FastAPI app."""
    # Specific handlers first (more specific to less specific)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(IntegrityError, database_integrity_error_handler)
    app.add_exception_handler(SQLAlchemyError, database_error_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    
    # Generic handler last
    app.add_exception_handler(Exception, global_exception_handler)

