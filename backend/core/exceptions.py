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
