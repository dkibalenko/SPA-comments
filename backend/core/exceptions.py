class AppError(Exception):
    """Base exception for all application-level errors.

    All custom exceptions inherit from this, so callers can catch either the
    specific error or the broad AppError.
    """

    pass


class ValidationError(AppError):
    """Raised when input data fails business-rule validation.

    Distinct from DRF's serializer validation - this is raised inside the
    service/domain layer, not the HTTP layer.
    """

    pass


class NotFoundError(AppError):
    """Raised when a requested resource does not exist."""

    pass


class CaptchaError(AppError):
    """Raised when CAPTCHA token is invalid, expired, or answer is wrong."""

    pass


class UnsupportedFileTypeError(AppError):
    """Raised by AttachmentFactory when the uploaded file type is not allowed."""

    pass


class FileTooLargeError(AppError):
    """Raised when an uploaded file exceeds the allowed size limit."""

    pass
