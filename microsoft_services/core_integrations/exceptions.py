"""
Microsoft Graph API Custom Exceptions
Spezifische Exceptions für verschiedene Graph API Fehlertypen
"""

class MicrosoftGraphException(Exception):
    """
    Basis Exception für alle Microsoft Graph API Fehler
    """
    
    def __init__(self, message: str, status_code: int = None, error_code: str = None):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(self.message)

class AzureAuthException(MicrosoftGraphException):
    """
    Exception für Azure Authentication Fehler
    """
    
    def __init__(self, message: str, auth_step: str = None):
        self.auth_step = auth_step
        super().__init__(message)

class TokenExpiredException(AzureAuthException):
    """
    Exception für abgelaufene Access Tokens
    """
    
    def __init__(self, message: str = "Azure access token has expired"):
        super().__init__(message, auth_step="token_expired")

class InvalidTokenException(AzureAuthException):
    """
    Exception für ungültige Access Tokens
    """
    
    def __init__(self, message: str = "Azure access token is invalid"):
        super().__init__(message, auth_step="invalid_token")

class InsufficientPermissionsException(MicrosoftGraphException):
    """
    Exception für fehlende Berechtigungen
    """
    
    def __init__(self, message: str = "Insufficient permissions for this Microsoft Graph operation"):
        super().__init__(message, status_code=403, error_code="Forbidden")

class RateLimitException(MicrosoftGraphException):
    """
    Exception für Rate Limiting (zu viele Requests)
    """
    
    def __init__(self, message: str = "Microsoft Graph API rate limit exceeded", retry_after: int = None):
        self.retry_after = retry_after
        super().__init__(message, status_code=429, error_code="TooManyRequests")

class ResourceNotFoundException(MicrosoftGraphException):
    """
    Exception für nicht gefundene Ressourcen
    """
    
    def __init__(self, message: str = "Requested Microsoft Graph resource not found", resource: str = None):
        self.resource = resource
        super().__init__(message, status_code=404, error_code="ItemNotFound")

class BadRequestException(MicrosoftGraphException):
    """
    Exception für fehlerhafte Graph API Requests
    """
    
    def __init__(self, message: str = "Bad request to Microsoft Graph API"):
        super().__init__(message, status_code=400, error_code="BadRequest")

class QuotaExceededException(MicrosoftGraphException):
    """
    Exception für überschrittene API Quotas
    """
    
    def __init__(self, message: str = "Microsoft Graph API quota exceeded"):
        super().__init__(message, status_code=429, error_code="QuotaExceeded")

class ServiceUnavailableException(MicrosoftGraphException):
    """
    Exception für temporär nicht verfügbare Microsoft Services
    """
    
    def __init__(self, message: str = "Microsoft Graph service temporarily unavailable"):
        super().__init__(message, status_code=503, error_code="ServiceUnavailable")
