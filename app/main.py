from fastapi import FastAPI, Request, status, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.exceptions import RequestValidationError
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from app.config import settings
from app.database import engine
from app.core.exceptions import AppException
from app.api.route_registry import register_routes
from app.middleware.security import SecurityHeadersMiddleware, TimingMiddleware
import logging
from sqlalchemy import text

# Configure logging
if not settings.DEBUG:
    from app.utils.logging_config import root_logger
    logger = logging.getLogger(__name__)
else:
    logger = logging.getLogger(__name__)

# Determine docs URLs based on environment
docs_url = "/docs" if settings.DEBUG else None
redoc_url = "/redoc" if settings.DEBUG else None

app = FastAPI(
    title=settings.APP_NAME,
    description="B2B Grocery Mobile App Backend API",
    version=settings.APP_VERSION,
    docs_url=docs_url,
    redoc_url=redoc_url,
    openapi_url="/openapi.json" if settings.DEBUG else None
)

# Add security schemes to OpenAPI schema
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    from fastapi.openapi.utils import get_openapi
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # Add/Update security schemes to match FastAPI's OAuth2PasswordBearer
    if "components" not in openapi_schema:
        openapi_schema["components"] = {}
    if "securitySchemes" not in openapi_schema["components"]:
        openapi_schema["components"]["securitySchemes"] = {}
    
    # Define Bearer scheme for Swagger UI
    bearer_scheme = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": "Enter JWT token. Get token from /admin/auth/login (for admin) or /api/v1/auth/login (for users)"
    }
    
    # Add Bearer scheme
    openapi_schema["components"]["securitySchemes"]["Bearer"] = bearer_scheme
    
    # Also add OAuth2PasswordBearer to match what FastAPI generates
    openapi_schema["components"]["securitySchemes"]["OAuth2PasswordBearer"] = bearer_scheme
    
    # Update all endpoints to use Bearer instead of OAuth2PasswordBearer for Swagger UI
    for path, methods in openapi_schema.get("paths", {}).items():
        for method, operation in methods.items():
            if isinstance(operation, dict) and "security" in operation:
                for security in operation["security"]:
                    if "OAuth2PasswordBearer" in security:
                        # Add Bearer and keep OAuth2PasswordBearer for compatibility
                        security["Bearer"] = security["OAuth2PasswordBearer"]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi


def _validate_production_settings() -> None:
    if settings.ENVIRONMENT != "production":
        return

    if settings.SECRET_KEY == "change-me-in-production":
        raise RuntimeError("SECRET_KEY must be set to a strong non-default value in production.")

    origins = [o.strip() for o in (settings.ALLOWED_ORIGINS or "").split(",") if o.strip()]
    if not origins:
        raise RuntimeError("ALLOWED_ORIGINS must be configured in production.")


@app.on_event("startup")
def startup_validation() -> None:
    _validate_production_settings()

# Security Middleware (add first)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(TimingMiddleware)

# CORS Middleware
# Always check ALLOWED_ORIGINS first, regardless of environment
origins_str = settings.ALLOWED_ORIGINS or ""
origins = [origin.strip() for origin in origins_str.split(",") if origin.strip()] if origins_str else []

# If no origins specified, allow all (for development only)
if not origins:
    if settings.ENVIRONMENT == "production":
        raise RuntimeError("No ALLOWED_ORIGINS set in production.")
    logger.warning("No ALLOWED_ORIGINS set! Allowing all origins in non-production")
    origins = ["*"]
    allow_credentials = False  # Can't use "*" with credentials
else:
    # If specific origins are set, allow credentials
    allow_credentials = True
    logger.info(f"CORS: Allowing origins: {origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=allow_credentials,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["X-Process-Time"],
)


# Exception Handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic/validation errors with a consistent JSON shape."""

    # Convert errors to JSON-serializable format
    def sanitize_error(error):
        """Convert error dict to JSON-serializable format"""
        if isinstance(error, dict):
            return {k: sanitize_error(v) for k, v in error.items()}
        elif isinstance(error, list):
            return [sanitize_error(item) for item in error]
        elif isinstance(error, bytes):
            return error.decode("utf-8", errors="replace")
        elif isinstance(error, (str, int, float, bool, type(None))):
            return error
        else:
            return str(error)

    errors = exc.errors()
    sanitized_errors = sanitize_error(errors)

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "message": "Validation error",
            "error": {
                "code": "VALIDATION_ERROR",
                "details": sanitized_errors,
            },
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Normalize HTTPException responses so mobile apps always receive a
    top-level `message` field (and optional `error` details).
    """
    message = None
    error_payload = None

    # FastAPI commonly uses `detail` as a string or dict.
    if isinstance(exc.detail, str):
        message = exc.detail
    elif isinstance(exc.detail, dict):
        # If a custom handler already set `message`, prefer that.
        message = exc.detail.get("message") or exc.detail.get("detail") or "Request error"
        # Keep remaining keys under `error` for debugging if needed.
        error_payload = {k: v for k, v in exc.detail.items() if k != "message"}
    else:
        message = "Request error"
        error_payload = {"detail": str(exc.detail)}

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": message,
            "error": error_payload,
        },
        headers=exc.headers or {},
    )


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """Handle application exceptions with consistent JSON."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.message,
            "error": {"code": exc.code, "details": exc.details},
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unhandled exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": "Internal server error",
            "error": {
                "code": "SERVER_ERROR",
                "details": str(exc) if settings.DEBUG else "An error occurred",
            },
        },
    )


# Register all API, Admin, and Delivery routes (see app.api.route_registry)
register_routes(app)

# Serve uploaded files statically
uploads_dir = Path(settings.UPLOAD_DIR)
uploads_dir.mkdir(parents=True, exist_ok=True)

@app.get("/uploads/{file_path:path}")
async def serve_uploaded_file(file_path: str):
    """Serve uploaded files"""
    import mimetypes
    file_full_path = uploads_dir / file_path
    if file_full_path.exists() and file_full_path.is_file():
        # Determine content type from file extension
        content_type, _ = mimetypes.guess_type(str(file_full_path))
        if not content_type:
            # Default to image if we can't determine
            if file_full_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                content_type = 'image/jpeg' if file_full_path.suffix.lower() == '.jpg' else f'image/{file_full_path.suffix[1:].lower()}'
            else:
                content_type = 'application/octet-stream'
        
        return FileResponse(
            file_full_path,
            media_type=content_type,
            headers={
                "Cache-Control": "public, max-age=3600",
                "Access-Control-Allow-Origin": "*"
            }
        )
    else:
        return JSONResponse(
            status_code=404,
            content={"detail": "File not found"}
        )


@app.get("/")
def root():
    """Root endpoint"""
    return {
        "message": f"{settings.APP_NAME} is running",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": settings.APP_NAME
    }


@app.get("/live")
def liveness_check():
    return {"status": "alive", "service": settings.APP_NAME}


@app.get("/ready")
def readiness_check():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "not_ready",
                "service": settings.APP_NAME,
                "checks": {"database": "down"},
            },
        )
    return {"status": "ready", "service": settings.APP_NAME, "checks": {"database": "ok"}}

