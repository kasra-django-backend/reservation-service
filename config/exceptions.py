"""
Custom exception handler for DRF.
Ensures consistent error response format across the API.
"""
import logging
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)


class DomainError(Exception):
    """Base class for domain-level errors."""
    code = "DOMAIN_ERROR"
    message = "A domain error occurred."
    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self, message=None, code=None):
        if message:
            self.message = message
        if code:
            self.code = code
        super().__init__(self.message)


class InsufficientStockError(DomainError):
    code = "INSUFFICIENT_STOCK"
    message = "Requested quantity is not available."
    status_code = status.HTTP_409_CONFLICT


class InvalidStateTransitionError(DomainError):
    code = "INVALID_STATE_TRANSITION"
    message = "This state transition is not allowed."
    status_code = status.HTTP_409_CONFLICT


class ReservationExpiredError(DomainError):
    code = "RESERVATION_EXPIRED"
    message = "This reservation has expired."
    status_code = status.HTTP_409_CONFLICT


class IdempotencyConflictError(DomainError):
    code = "IDEMPOTENCY_CONFLICT"
    message = "A request with this Idempotency-Key is already being processed."
    status_code = status.HTTP_409_CONFLICT


def custom_exception_handler(exc, context):
    """
    Wrap all errors in a consistent format:
    {
        "error": {
            "code": "...",
            "message": "..."
        }
    }
    """
    # Domain errors first
    if isinstance(exc, DomainError):
        logger.warning(f"Domain error: {exc.code} - {exc.message}")
        return Response(
            {"error": {"code": exc.code, "message": exc.message}},
            status=exc.status_code,
        )

    # DRF's default handler
    response = exception_handler(exc, context)

    if response is not None:
        code = "VALIDATION_ERROR"
        message = "Invalid input."

        if response.status_code == status.HTTP_401_UNAUTHORIZED:
            code = "UNAUTHORIZED"
            message = "Authentication credentials were not provided or are invalid."
        elif response.status_code == status.HTTP_403_FORBIDDEN:
            code = "FORBIDDEN"
            message = "You do not have permission to perform this action."
        elif response.status_code == status.HTTP_404_NOT_FOUND:
            code = "NOT_FOUND"
            message = "Resource not found."
        elif response.status_code == status.HTTP_400_BAD_REQUEST:
            message = response.data

        response.data = {"error": {"code": code, "message": message}}
        return response

    # Unknown exception — don't leak stack trace
    logger.exception("Unhandled exception in API")
    return Response(
        {"error": {"code": "INTERNAL_ERROR", "message": "An internal error occurred."}},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )