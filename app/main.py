from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.config import settings
from app.api.v1 import (
    auth, products, companies, categories, cart, orders,
    user, wishlist, offers, notifications, kyc, delivery, payments, stats
)
from app.api.v1 import admin_auth, admin_products, admin_orders, admin_users, admin_kyc, admin_companies, admin_categories, admin_offers, admin_analytics, admin_upload
from app.middleware.security import SecurityHeadersMiddleware, TimingMiddleware
import logging

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

# Security Middleware (add first)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(TimingMiddleware)

# CORS Middleware
if settings.ENVIRONMENT == "production":
    # In production, use specific origins
    origins = settings.ALLOWED_ORIGINS.split(",") if settings.ALLOWED_ORIGINS else []
    if not origins:
        logger.warning("No ALLOWED_ORIGINS set in production!")
else:
    # In development, allow all
    origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Process-Time"],
)


# Exception Handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors"""
    # Convert errors to JSON-serializable format
    def sanitize_error(error):
        """Convert error dict to JSON-serializable format"""
        if isinstance(error, dict):
            return {k: sanitize_error(v) for k, v in error.items()}
        elif isinstance(error, list):
            return [sanitize_error(item) for item in error]
        elif isinstance(error, bytes):
            return error.decode('utf-8', errors='replace')
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
                "details": sanitized_errors
            }
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    # Log the error
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": "Internal server error",
            "error": {
                "code": "SERVER_ERROR",
                "details": str(exc) if settings.DEBUG else "An error occurred"
            }
        }
    )


# Include Routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(products.router, prefix="/api/v1/products", tags=["Products"])
app.include_router(companies.router, prefix="/api/v1/companies", tags=["Companies"])
app.include_router(categories.router, prefix="/api/v1/categories", tags=["Categories"])
app.include_router(cart.router, prefix="/api/v1/cart", tags=["Cart"])
app.include_router(orders.router, prefix="/api/v1/orders", tags=["Orders"])
app.include_router(user.router, prefix="/api/v1/user", tags=["User"])
app.include_router(wishlist.router, prefix="/api/v1/wishlist", tags=["Wishlist"])
app.include_router(offers.router, prefix="/api/v1/offers", tags=["Offers"])
app.include_router(notifications.router, prefix="/api/v1/notifications", tags=["Notifications"])
app.include_router(kyc.router, prefix="/api/v1/kyc", tags=["KYC"])
app.include_router(delivery.router, prefix="/api/v1/delivery", tags=["Delivery"])
app.include_router(payments.router, prefix="/api/v1/payments", tags=["Payments"])
app.include_router(stats.router, prefix="/api/v1/stats", tags=["Statistics"])

# Admin Routers
app.include_router(admin_auth.router, prefix="/admin/auth", tags=["Admin Authentication"])
app.include_router(admin_products.router, prefix="/admin/products", tags=["Admin Products"])
app.include_router(admin_orders.router, prefix="/admin/orders", tags=["Admin Orders"])
app.include_router(admin_users.router, prefix="/admin/users", tags=["Admin Users"])
app.include_router(admin_kyc.router, prefix="/admin/kyc", tags=["Admin KYC"])
app.include_router(admin_companies.router, prefix="/admin", tags=["Admin Companies & Brands"])
app.include_router(admin_categories.router, prefix="/admin/categories", tags=["Admin Categories"])
app.include_router(admin_offers.router, prefix="/admin/offers", tags=["Admin Offers"])
app.include_router(admin_analytics.router, prefix="/admin/analytics", tags=["Admin Analytics"])
app.include_router(admin_upload.router, prefix="/admin/upload", tags=["Admin Upload"])


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

