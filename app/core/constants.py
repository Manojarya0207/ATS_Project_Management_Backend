"""Application-wide constants: error codes, header names, and shared limits.

Keeping these in one module prevents magic strings from drifting across
modules and gives API consumers a stable, documented error-code vocabulary.
"""

from __future__ import annotations

from enum import StrEnum


class ErrorCode(StrEnum):
    """Machine-readable error codes returned in the ``errors[].code`` field."""

    # Generic
    internal_error = "INTERNAL_ERROR"
    validation_error = "VALIDATION_ERROR"
    not_found = "NOT_FOUND"
    conflict = "CONFLICT"
    stale_version = "STALE_VERSION"
    rate_limited = "RATE_LIMITED"

    # Auth
    unauthorized = "UNAUTHORIZED"
    forbidden = "FORBIDDEN"
    invalid_credentials = "INVALID_CREDENTIALS"
    invalid_token = "INVALID_TOKEN"
    token_reuse_detected = "TOKEN_REUSE_DETECTED"
    inactive_account = "INACTIVE_ACCOUNT"
    weak_password = "WEAK_PASSWORD"

    # Domain
    duplicate_email = "DUPLICATE_EMAIL"
    already_member = "ALREADY_MEMBER"
    file_too_large = "FILE_TOO_LARGE"


# --- HTTP headers -----------------------------------------------------------
REQUEST_ID_HEADER = "X-Request-ID"
CORRELATION_ID_HEADER = "X-Correlation-ID"
PROCESS_TIME_HEADER = "X-Process-Time"

# --- Pagination -------------------------------------------------------------
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# --- Kanban -----------------------------------------------------------------
POSITION_STEP = 1000.0
