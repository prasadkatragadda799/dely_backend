"""
Application-level exceptions for consistent error handling.
Use these in services; API layer can map them to HTTP responses.
"""
from typing import Any, Optional, Dict


class AppException(Exception):
    """Base exception for application errors."""

    def __init__(
        self,
        message: str = "An error occurred",
        code: str = "APP_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class NotFoundError(AppException):
    """Resource not found (maps to 404)."""

    def __init__(self, message: str = "Resource not found", resource: Optional[str] = None, **kwargs: Any):
        details = kwargs.pop("details", {})
        if resource:
            details["resource"] = resource
        super().__init__(
            message=message,
            code="NOT_FOUND",
            status_code=404,
            details=details,
            **kwargs,
        )


class ValidationError(AppException):
    """Validation / bad request (maps to 400)."""

    def __init__(self, message: str = "Validation error", details: Optional[Dict[str, Any]] = None, **kwargs: Any):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=400,
            details=details or {},
            **kwargs,
        )


class ForbiddenError(AppException):
    """Forbidden / insufficient permissions (maps to 403)."""

    def __init__(self, message: str = "Forbidden", **kwargs: Any):
        super().__init__(
            message=message,
            code="FORBIDDEN",
            status_code=403,
            **kwargs,
        )


class ConflictError(AppException):
    """Conflict / duplicate resource (maps to 409)."""

    def __init__(self, message: str = "Resource conflict", **kwargs: Any):
        super().__init__(
            message=message,
            code="CONFLICT",
            status_code=409,
            **kwargs,
        )
