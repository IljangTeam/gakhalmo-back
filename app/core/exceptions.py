"""Custom exception classes for the application."""

from fastapi import HTTPException, status


class NotFoundError(HTTPException):
    """Resource not found exception (404)."""

    def __init__(self, detail: str = "Resource not found"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class ConflictError(HTTPException):
    """Resource conflict exception (409)."""

    def __init__(self, detail: str = "Resource conflict"):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)


class ForbiddenError(HTTPException):
    """Access forbidden exception (403)."""

    def __init__(self, detail: str = "Access forbidden"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class UnauthorizedError(HTTPException):
    """Authentication required/failed exception (401)."""

    def __init__(self, detail: str = "Authentication required"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class BadRequestError(HTTPException):
    """Invalid input exception (400)."""

    def __init__(self, detail: str = "Bad request"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class CapacityExceededError(HTTPException):
    """Meeting capacity exceeded exception (400)."""

    def __init__(self, detail: str = "Meeting capacity exceeded"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class AlreadyParticipantError(HTTPException):
    """User already participant exception (409)."""

    def __init__(self, detail: str = "User is already a participant"):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)
