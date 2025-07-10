"""
Microsoft Graph API Custom Exceptions

This module provides specialized exception classes for handling various types of
Microsoft Graph API and Azure authentication errors. These exceptions follow
a hierarchical structure to allow for granular error handling and proper
error classification.

Author: DSP Development Team
Version: 1.0.0
"""

from typing import Optional, Dict, Any


class MicrosoftGraphException(Exception):
    """
    Base exception class for all Microsoft Graph API related errors.
    
    This exception serves as the parent class for all Microsoft Graph API
    specific exceptions, providing common attributes and methods for
    error handling and debugging.
    
    Attributes:
        message (str): Human-readable error message
        status_code (Optional[int]): HTTP status code if applicable
        error_code (Optional[str]): Microsoft-specific error code
        details (Optional[Dict[str, Any]]): Additional error details
    
    Example:
        >>> try:
        ...     # Some Graph API operation
        ...     pass
        ... except MicrosoftGraphException as e:
        ...     logger.error(f"Graph API error: {e.message}")
        ...     if e.status_code:
        ...         logger.error(f"HTTP Status: {e.status_code}")
    """
    
    def __init__(
        self, 
        message: str, 
        status_code: Optional[int] = None, 
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Initialize a Microsoft Graph API exception.
        
        Args:
            message: Human-readable error description
            status_code: HTTP status code from the API response
            error_code: Microsoft-specific error identifier
            details: Additional context or error details
        """
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert exception to dictionary for serialization.
        
        Returns:
            Dictionary representation of the exception
        """
        return {
            'message': self.message,
            'status_code': self.status_code,
            'error_code': self.error_code,
            'details': self.details,
            'exception_type': self.__class__.__name__
        }


class AzureAuthException(MicrosoftGraphException):
    """
    Exception for Azure Active Directory authentication errors.
    
    This exception is raised when authentication operations fail,
    including token acquisition, validation, or refresh operations.
    
    Attributes:
        auth_step (Optional[str]): The authentication step where the error occurred
    
    Example:
        >>> try:
        ...     token = get_access_token()
        ... except AzureAuthException as e:
        ...     if e.auth_step == "token_expired":
        ...         # Handle token expiration
        ...         pass
    """
    
    def __init__(
        self, 
        message: str, 
        auth_step: Optional[str] = None,
        status_code: Optional[int] = None,
        error_code: Optional[str] = None
    ) -> None:
        """
        Initialize an Azure authentication exception.
        
        Args:
            message: Human-readable error description
            auth_step: The authentication step where the error occurred
            status_code: HTTP status code if applicable
            error_code: Azure-specific error code
        """
        self.auth_step = auth_step
        super().__init__(message, status_code, error_code)


class TokenExpiredException(AzureAuthException):
    """
    Exception raised when an Azure access token has expired.
    
    This exception indicates that the current access token is no longer
    valid and needs to be refreshed or re-acquired.
    """
    
    def __init__(self, message: str = "Azure access token has expired") -> None:
        """
        Initialize a token expiration exception.
        
        Args:
            message: Custom error message (optional)
        """
        super().__init__(
            message=message, 
            auth_step="token_expired",
            status_code=401,
            error_code="TokenExpired"
        )


class InvalidTokenException(AzureAuthException):
    """
    Exception raised when an Azure access token is invalid or malformed.
    
    This exception indicates that the provided token is not valid,
    possibly due to corruption, wrong format, or unauthorized access.
    """
    
    def __init__(self, message: str = "Azure access token is invalid") -> None:
        """
        Initialize an invalid token exception.
        
        Args:
            message: Custom error message (optional)
        """
        super().__init__(
            message=message,
            auth_step="invalid_token",
            status_code=401,
            error_code="InvalidToken"
        )


class InsufficientPermissionsException(MicrosoftGraphException):
    """
    Exception raised when the application lacks required permissions.
    
    This exception indicates that the current user or application
    does not have sufficient permissions to perform the requested
    Microsoft Graph operation.
    """
    
    def __init__(
        self, 
        message: str = "Insufficient permissions for this Microsoft Graph operation",
        required_permission: Optional[str] = None
    ) -> None:
        """
        Initialize an insufficient permissions exception.
        
        Args:
            message: Custom error message (optional)
            required_permission: The specific permission that is missing
        """
        details = {}
        if required_permission:
            details['required_permission'] = required_permission
            
        super().__init__(
            message=message,
            status_code=403,
            error_code="Forbidden",
            details=details
        )


class RateLimitException(MicrosoftGraphException):
    """
    Exception raised when Microsoft Graph API rate limits are exceeded.
    
    This exception includes retry information to help implement
    proper backoff strategies.
    
    Attributes:
        retry_after (Optional[int]): Seconds to wait before retrying
    """
    
    def __init__(
        self, 
        message: str = "Microsoft Graph API rate limit exceeded", 
        retry_after: Optional[int] = None
    ) -> None:
        """
        Initialize a rate limit exception.
        
        Args:
            message: Custom error message (optional)
            retry_after: Number of seconds to wait before retrying
        """
        self.retry_after = retry_after
        details = {}
        if retry_after:
            details['retry_after'] = retry_after
            
        super().__init__(
            message=message,
            status_code=429,
            error_code="TooManyRequests",
            details=details
        )


class ResourceNotFoundException(MicrosoftGraphException):
    """
    Exception raised when a requested Microsoft Graph resource is not found.
    
    This exception indicates that the requested resource (user, group, etc.)
    does not exist or is not accessible with current permissions.
    
    Attributes:
        resource (Optional[str]): The type or identifier of the missing resource
    """
    
    def __init__(
        self, 
        message: str = "Requested Microsoft Graph resource not found", 
        resource: Optional[str] = None
    ) -> None:
        """
        Initialize a resource not found exception.
        
        Args:
            message: Custom error message (optional)
            resource: The type or identifier of the missing resource
        """
        self.resource = resource
        details = {}
        if resource:
            details['resource'] = resource
            
        super().__init__(
            message=message,
            status_code=404,
            error_code="ItemNotFound",
            details=details
        )


class BadRequestException(MicrosoftGraphException):
    """
    Exception raised when a request to Microsoft Graph API is malformed.
    
    This exception indicates that the request syntax, parameters,
    or content is invalid according to the API specification.
    """
    
    def __init__(
        self, 
        message: str = "Bad request to Microsoft Graph API",
        validation_errors: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Initialize a bad request exception.
        
        Args:
            message: Custom error message (optional)
            validation_errors: Dictionary of field validation errors
        """
        details = {}
        if validation_errors:
            details['validation_errors'] = validation_errors
            
        super().__init__(
            message=message,
            status_code=400,
            error_code="BadRequest",
            details=details
        )


class QuotaExceededException(MicrosoftGraphException):
    """
    Exception raised when Microsoft Graph API quotas are exceeded.
    
    This exception indicates that the application has exceeded
    its allocated quota for API calls or resource usage.
    """
    
    def __init__(
        self, 
        message: str = "Microsoft Graph API quota exceeded",
        quota_type: Optional[str] = None
    ) -> None:
        """
        Initialize a quota exceeded exception.
        
        Args:
            message: Custom error message (optional)
            quota_type: The type of quota that was exceeded
        """
        details = {}
        if quota_type:
            details['quota_type'] = quota_type
            
        super().__init__(
            message=message,
            status_code=429,
            error_code="QuotaExceeded",
            details=details
        )


class ServiceUnavailableException(MicrosoftGraphException):
    """
    Exception raised when Microsoft Graph services are temporarily unavailable.
    
    This exception indicates that the Microsoft Graph service is
    experiencing temporary issues and the request should be retried later.
    """
    
    def __init__(
        self, 
        message: str = "Microsoft Graph service temporarily unavailable",
        estimated_recovery_time: Optional[int] = None
    ) -> None:
        """
        Initialize a service unavailable exception.
        
        Args:
            message: Custom error message (optional)
            estimated_recovery_time: Estimated time until service recovery (seconds)
        """
        details = {}
        if estimated_recovery_time:
            details['estimated_recovery_time'] = estimated_recovery_time
            
        super().__init__(
            message=message,
            status_code=503,
            error_code="ServiceUnavailable",
            details=details
        )


# Exception mapping for HTTP status codes
EXCEPTION_MAPPING = {
    400: BadRequestException,
    401: InvalidTokenException,
    403: InsufficientPermissionsException,
    404: ResourceNotFoundException,
    429: RateLimitException,
    503: ServiceUnavailableException,
}


def create_exception_from_response(
    status_code: int, 
    message: str, 
    error_code: Optional[str] = None,
    **kwargs
) -> MicrosoftGraphException:
    """
    Factory function to create appropriate exception based on HTTP status code.
    
    Args:
        status_code: HTTP status code from the response
        message: Error message from the response
        error_code: Microsoft-specific error code
        **kwargs: Additional arguments for exception initialization
    
    Returns:
        Appropriate exception instance based on the status code
    
    Example:
        >>> exception = create_exception_from_response(
        ...     status_code=404,
        ...     message="User not found",
        ...     resource="user"
        ... )
        >>> isinstance(exception, ResourceNotFoundException)
        True
    """
    exception_class = EXCEPTION_MAPPING.get(status_code, MicrosoftGraphException)
    
    if status_code == 401 and error_code == "TokenExpired":
        return TokenExpiredException(message)
    
    return exception_class(message, **kwargs)
