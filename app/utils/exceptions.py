class AppError(Exception):
    """Base application error mapped to an HTTP status by the global handler."""

    status_code = 500
    detail = "Internal server error"

    def __init__(self, detail: str | None = None):
        if detail:
            self.detail = detail
        super().__init__(self.detail)


class NotFoundError(AppError):
    status_code = 404
    detail = "Resource not found"


class ForbiddenError(AppError):
    status_code = 403
    detail = "You do not have permission to perform this action"


class UnauthorizedError(AppError):
    status_code = 401
    detail = "Not authenticated"


class ConflictError(AppError):
    status_code = 409
    detail = "Resource conflict"


class ValidationAppError(AppError):
    status_code = 422
    detail = "Validation error"
