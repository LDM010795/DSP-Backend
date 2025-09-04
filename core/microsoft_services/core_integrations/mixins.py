"""
Microsoft Graph API Integration Mixins

This module provides thread-safe, production-ready mixins for integrating with
Microsoft Graph API. It implements read-only access patterns with comprehensive
error handling, automatic retry logic, and proper response processing.

The mixins follow the Single Responsibility Principle and provide clean
abstractions for Graph API operations while maintaining security through
read-only access restrictions.

Author: DSP Development Team
Version: 1.0.0
"""

import logging
from typing import Dict, Any, Optional, List
from functools import wraps
from time import sleep

import requests
from rest_framework.response import Response
from rest_framework import status

from .token_manager import azure_token_manager
from .exceptions import (
    MicrosoftGraphException,
    AzureAuthException,
    TokenExpiredException,
    InvalidTokenException,
    InsufficientPermissionsException,
    RateLimitException,
    ResourceNotFoundException,
    BadRequestException,
    ServiceUnavailableException,
)

logger = logging.getLogger(__name__)


def retry_on_rate_limit(max_retries: int = 3, base_delay: float = 1.0):
    """
    Decorator to automatically retry Graph API calls on rate limit errors.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds (will be exponentially increased)

    Returns:
        Decorated function with retry logic
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except RateLimitException as e:
                    last_exception = e
                    if attempt < max_retries:
                        # Use retry_after from response if available, otherwise exponential backoff
                        delay = (
                            e.retry_after
                            if e.retry_after
                            else base_delay * (2**attempt)
                        )
                        logger.warning(
                            f"Rate limit hit on attempt {attempt + 1}/{max_retries + 1}. "
                            f"Retrying in {delay}s..."
                        )
                        sleep(delay)
                    else:
                        logger.error(f"Rate limit exceeded after {max_retries} retries")
                        raise
                except (TokenExpiredException, InvalidTokenException):
                    # Don't retry on auth errors - they need manual intervention
                    raise

            # Should never reach here, but just in case
            raise last_exception

        return wrapper

    return decorator


class GraphAPIBaseMixin:
    """
    Base mixin for Microsoft Graph API integrations with comprehensive error handling.

    This mixin provides read-only access to Microsoft Graph API with automatic
    token management, retry logic, and proper error handling. It implements
    security best practices by restricting access to GET operations only.

    Attributes:
        GRAPH_BASE_URL (str): Base URL for Microsoft Graph API
        DEFAULT_TIMEOUT (int): Default request timeout in seconds
        MAX_RETRIES (int): Maximum retry attempts for rate-limited requests

    Example:
        >>> class UserService(GraphAPIBaseMixin):
        ...     def get_user(self, user_id: str) -> Dict[str, Any]:
        ...         return self.call_graph_api(f"users/{user_id}")
        ...
        >>> service = UserService()
        >>> user_data = service.get_user("user@domain.com")
    """

    GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
    DEFAULT_TIMEOUT = 30
    MAX_RETRIES = 3

    @retry_on_rate_limit(max_retries=3)
    def call_graph_api(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
        custom_headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Execute a read-only Microsoft Graph API call with comprehensive error handling.

        This method handles token acquisition, request formatting, response processing,
        and error handling for Microsoft Graph API calls. It automatically retries
        on rate limit errors and provides detailed error information.

        Args:
            endpoint: Graph API endpoint (e.g., 'me', 'users', 'organization')
            params: URL query parameters for the request
            timeout: Request timeout in seconds (uses default if None)
            custom_headers: Additional headers to include in the request

        Returns:
            Parsed JSON response from Microsoft Graph API

        Raises:
            AzureAuthException: Authentication or token-related errors
            MicrosoftGraphException: Graph API-specific errors
            RateLimitException: When rate limits are exceeded
            ResourceNotFoundException: When requested resource is not found
            InsufficientPermissionsException: When access is denied

        Example:
            >>> # Get current user information
            >>> user_info = self.call_graph_api("me")
            >>>
            >>> # Get users with filtering
            >>> users = self.call_graph_api(
            ...     "users",
            ...     params={"$filter": "startswith(displayName,'John')"}
            ... )
        """
        try:
            # 1. Acquire access token
            access_token = self._get_access_token()

            # 2. Prepare request
            url = self._build_url(endpoint)
            headers = self._build_headers(access_token, custom_headers)
            request_timeout = timeout or self.DEFAULT_TIMEOUT

            # 3. Execute request
            logger.debug(f"Making Graph API call: GET {endpoint}")
            response = self._execute_request(url, headers, params, request_timeout)

            # 4. Process response
            return self._process_response(response, endpoint)

        except AzureAuthException:
            # Re-raise authentication errors without modification
            raise
        except requests.exceptions.RequestException as e:
            logger.error(
                f"Graph API request failed for endpoint '{endpoint}': {str(e)}"
            )
            raise MicrosoftGraphException(
                f"Graph API request failed: {str(e)}",
                details={"endpoint": endpoint, "request_error": str(e)},
            )

    def call_graph_api_batch(
        self, requests_data: List[Dict[str, Any]], timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Execute multiple Graph API calls in a single batch request.

        This method allows efficient execution of multiple Graph API operations
        in a single HTTP request, reducing network overhead and improving performance.

        Args:
            requests_data: List of request objects for batch processing
            timeout: Request timeout in seconds

        Returns:
            Batch response containing individual request results

        Example:
            >>> batch_requests = [
            ...     {"id": "1", "method": "GET", "url": "/me"},
            ...     {"id": "2", "method": "GET", "url": "/organization"}
            ... ]
            >>> batch_response = self.call_graph_api_batch(batch_requests)
        """
        if not requests_data:
            raise ValueError("Batch requests data cannot be empty")

        # Validate batch request structure
        for req in requests_data:
            if not all(key in req for key in ["id", "method", "url"]):
                raise ValueError(
                    "Each batch request must have 'id', 'method', and 'url' fields"
                )
            if req["method"].upper() != "GET":
                raise ValueError("Only GET requests are allowed in batch operations")

        batch_payload = {"requests": requests_data}

        return self.call_graph_api(
            "$batch",
            params=None,
            timeout=timeout,
            custom_headers={"Content-Type": "application/json"},
        )

    def proxy_request(self, request, graph_path: str) -> Response:
        """
        Proxy Django HTTP requests to Microsoft Graph API with security restrictions.

        This method provides a secure proxy for forwarding Django requests to
        Microsoft Graph API. It enforces read-only access and provides proper
        error handling and response formatting.

        Args:
            request: Django HTTP request object
            graph_path: Graph API path extracted from the URL

        Returns:
            Django Response object with Graph API data or error information

        Security Notes:
            - Only GET requests are allowed
            - All query parameters are forwarded safely
            - Proper error handling prevents information leakage

        Example:
            >>> # In a Django view
            >>> def graph_proxy_view(request, path):
            ...     mixin = GraphAPIBaseMixin()
            ...     return mixin.proxy_request(request, path)
        """
        try:
            # Security: Only allow GET requests
            if request.method.upper() != "GET":
                return self._create_error_response(
                    error_message=f"Method {request.method} not allowed. Only GET requests supported.",
                    status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
                    details={"endpoint": graph_path, "method": request.method},
                )

            # Extract and validate query parameters
            params = self._extract_query_params(request)

            # Execute Graph API call
            result = self.call_graph_api(endpoint=graph_path, params=params)

            return Response(result, status=status.HTTP_200_OK)

        except TokenExpiredException:
            logger.warning(f"Token expired for endpoint {graph_path}")
            return self._create_error_response(
                error_message="Azure access token has expired",
                error_code="TokenExpired",
                status_code=status.HTTP_401_UNAUTHORIZED,
                details={"endpoint": graph_path},
            )
        except InsufficientPermissionsException as e:
            logger.warning(f"Insufficient permissions for endpoint {graph_path}")
            return self._create_error_response(
                error_message="Insufficient permissions for this resource",
                error_code="Forbidden",
                status_code=status.HTTP_403_FORBIDDEN,
                details={
                    "endpoint": graph_path,
                    "required_permission": e.details.get("required_permission"),
                },
            )
        except RateLimitException as e:
            logger.warning(f"Rate limit exceeded for endpoint {graph_path}")
            return self._create_error_response(
                error_message="Rate limit exceeded",
                error_code="TooManyRequests",
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                details={"endpoint": graph_path, "retry_after": e.retry_after},
            )
        except ResourceNotFoundException as e:
            logger.info(f"Resource not found: {graph_path}")
            return self._create_error_response(
                error_message="Requested resource not found",
                error_code="NotFound",
                status_code=status.HTTP_404_NOT_FOUND,
                details={"endpoint": graph_path, "resource": e.resource},
            )
        except (MicrosoftGraphException, AzureAuthException) as e:
            logger.error(f"Proxy request failed for {graph_path}: {str(e)}")
            return self._create_error_response(
                error_message=str(e),
                error_code=getattr(e, "error_code", "Unknown"),
                status_code=getattr(e, "status_code", status.HTTP_400_BAD_REQUEST),
                details={"endpoint": graph_path, "method": request.method},
            )

    def _get_access_token(self) -> str:
        """
        Get a valid access token from the token manager.

        Returns:
            Valid Azure AD access token

        Raises:
            AzureAuthException: If token acquisition fails
        """
        try:
            return azure_token_manager.get_access_token()
        except Exception as e:
            logger.error(f"Failed to acquire access token: {str(e)}")
            raise AzureAuthException(
                f"Token acquisition failed: {str(e)}", auth_step="token_acquisition"
            )

    def _build_url(self, endpoint: str) -> str:
        """
        Build the complete URL for a Graph API endpoint.

        Args:
            endpoint: API endpoint path

        Returns:
            Complete URL for the Graph API call
        """
        # Clean and normalize endpoint
        endpoint = endpoint.lstrip("/")
        if not endpoint:
            raise ValueError("Graph API endpoint cannot be empty")

        return f"{self.GRAPH_BASE_URL}/{endpoint}"

    def _build_headers(
        self, access_token: str, custom_headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, str]:
        """
        Build HTTP headers for Graph API requests.

        Args:
            access_token: Valid Azure AD access token
            custom_headers: Additional headers to include

        Returns:
            Complete headers dictionary for the request
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "DSP-Microsoft-Services/1.0.0",
        }

        # Add custom headers if provided
        if custom_headers:
            headers.update(custom_headers)

        return headers

    def _execute_request(
        self,
        url: str,
        headers: Dict[str, str],
        params: Optional[Dict[str, Any]],
        timeout: int,
    ) -> requests.Response:
        """
        Execute the HTTP request to Microsoft Graph API.

        Args:
            url: Complete URL for the request
            headers: HTTP headers
            params: Query parameters
            timeout: Request timeout

        Returns:
            HTTP response object

        Raises:
            requests.RequestException: For network-related errors
        """
        try:
            response = requests.get(
                url, headers=headers, params=params, timeout=timeout
            )
            return response
        except requests.exceptions.Timeout:
            raise MicrosoftGraphException(
                f"Graph API request timed out after {timeout}s",
                details={"timeout": timeout, "url": url},
            )
        except requests.exceptions.ConnectionError as e:
            raise MicrosoftGraphException(
                f"Failed to connect to Microsoft Graph API: {str(e)}",
                details={"connection_error": str(e), "url": url},
            )

    def _process_response(
        self, response: requests.Response, endpoint: str
    ) -> Dict[str, Any]:
        """
        Process and validate the Graph API response.

        Args:
            response: HTTP response from Graph API
            endpoint: Original endpoint for context

        Returns:
            Parsed JSON response data

        Raises:
            Appropriate Microsoft Graph exceptions based on response
        """
        try:
            response_data = response.json()
        except ValueError:
            # Handle non-JSON responses
            if response.status_code < 400:
                response_data = {
                    "message": "Success",
                    "status_code": response.status_code,
                }
            else:
                response_data = {"error": {"message": response.text or "Unknown error"}}

        # Handle error responses
        if response.status_code >= 400:
            self._handle_error_response(response, response_data, endpoint)

        logger.debug(
            f"Graph API call successful: {response.status_code} for {endpoint}"
        )
        return response_data

    def _handle_error_response(
        self, response: requests.Response, response_data: Dict[str, Any], endpoint: str
    ) -> None:
        """
        Handle and convert HTTP error responses to appropriate exceptions.

        Args:
            response: HTTP response object
            response_data: Parsed response data
            endpoint: Original endpoint for context

        Raises:
            Appropriate MicrosoftGraphException based on the error
        """
        error_info = response_data.get("error", {})
        error_message = error_info.get("message", f"HTTP {response.status_code}")
        error_code = error_info.get("code", "Unknown")

        logger.error(
            f"Graph API error for endpoint '{endpoint}': "
            f"{response.status_code} - {error_code}: {error_message}"
        )

        # Create appropriate exception based on status code and error details
        if response.status_code == 401:
            if (
                "token" in error_message.lower()
                or error_code == "InvalidAuthenticationToken"
            ):
                raise TokenExpiredException(error_message)
            else:
                raise InvalidTokenException(error_message)
        elif response.status_code == 403:
            # Extract permission information if available
            required_permission = error_info.get("requiredPermission")
            raise InsufficientPermissionsException(error_message, required_permission)
        elif response.status_code == 404:
            # Extract resource information from endpoint
            resource_type = endpoint.split("/")[0] if "/" in endpoint else endpoint
            raise ResourceNotFoundException(error_message, resource_type)
        elif response.status_code == 400:
            # Extract validation errors if available
            validation_errors = error_info.get("details", {})
            raise BadRequestException(error_message, validation_errors)
        elif response.status_code == 429:
            # Extract retry information
            retry_after = response.headers.get("Retry-After")
            retry_seconds = (
                int(retry_after) if retry_after and retry_after.isdigit() else None
            )
            raise RateLimitException(error_message, retry_after=retry_seconds)
        elif response.status_code == 503:
            # Extract recovery time if available
            retry_after = response.headers.get("Retry-After")
            recovery_time = (
                int(retry_after) if retry_after and retry_after.isdigit() else None
            )
            raise ServiceUnavailableException(error_message, recovery_time)
        else:
            # Generic Graph API exception for other errors
            raise MicrosoftGraphException(
                error_message,
                status_code=response.status_code,
                error_code=error_code,
                details={"endpoint": endpoint, "full_error": error_info},
            )

    def _extract_query_params(self, request) -> Optional[Dict[str, Any]]:
        """
        Safely extract query parameters from Django request.

        Args:
            request: Django HTTP request object

        Returns:
            Dictionary of query parameters or None
        """
        if hasattr(request, "GET") and request.GET:
            return dict(request.GET.items())
        return None

    def _create_error_response(
        self,
        error_message: str,
        status_code: int,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> Response:
        """
        Create a standardized error response for the proxy.

        Args:
            error_message: Human-readable error message
            status_code: HTTP status code
            error_code: Specific error code
            details: Additional error details

        Returns:
            Django Response object with error information
        """
        error_data = {
            "error": error_message,
            "error_code": error_code or "Unknown",
            "status_code": status_code,
        }

        if details:
            error_data.update(details)

        return Response(error_data, status=status_code)


class GraphAPIUserMixin(GraphAPIBaseMixin):
    """
    Specialized mixin for Microsoft Graph API user operations.

    This mixin provides convenient methods for common user-related
    Graph API operations with proper error handling and response formatting.
    """

    def get_user_by_id(self, user_id: str) -> Dict[str, Any]:
        """
        Get user information by user ID or email.

        Args:
            user_id: User ID or email address

        Returns:
            User information from Microsoft Graph
        """
        return self.call_graph_api(f"users/{user_id}")

    def get_user_groups(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get groups that a user belongs to.

        Args:
            user_id: User ID or email address

        Returns:
            List of groups the user belongs to
        """
        response = self.call_graph_api(f"users/{user_id}/memberOf")
        return response.get("value", [])

    def search_users(
        self, search_term: str, select_fields: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for users in the organization.

        Args:
            search_term: Search term for user lookup
            select_fields: Specific fields to return

        Returns:
            List of matching users
        """
        params = {
            "$filter": f"startswith(displayName,'{search_term}') or startswith(mail,'{search_term}')"
        }

        if select_fields:
            params["$select"] = ",".join(select_fields)

        response = self.call_graph_api("users", params=params)
        return response.get("value", [])
