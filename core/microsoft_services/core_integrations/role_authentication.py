"""
Microsoft Graph API Role Authentication System

This module provides a production-ready role authentication system that maps
Microsoft Azure AD group memberships to Django user roles and permissions.
The system is designed to be generic and configurable for different applications
while maintaining security and auditability.

The role authentication system follows these principles:
- Separation of Concerns: Clear separation between role mapping and user management
- Single Responsibility: Each method has a specific, well-defined purpose
- Configuration-driven: Role mappings are configurable and extensible
- Audit Trail: Comprehensive logging for security and debugging

Author: DSP Development Team
Version: 1.0.0
"""

import logging
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from functools import lru_cache

from django.conf import settings
from django.core.cache import cache

from .mixins import GraphAPIBaseMixin
from .exceptions import MicrosoftGraphException, ResourceNotFoundException

logger = logging.getLogger(__name__)


class RoleLevel(Enum):
    """
    Enumeration of available role levels in order of privilege.
    
    Higher values indicate higher privilege levels.
    """
    USER = 1
    MODERATOR = 2
    STAFF = 3
    ADMINISTRATOR = 4


@dataclass
class RoleConfiguration:
    """
    Configuration object for a user role.
    
    Attributes:
        role_name: Human-readable name of the role
        level: Role privilege level
        is_staff: Django staff permission
        is_superuser: Django superuser permission
        description: Description of the role's purpose
        permissions: Set of custom permissions for the role
    """
    role_name: str
    level: RoleLevel
    is_staff: bool = False
    is_superuser: bool = False
    description: str = ""
    permissions: Set[str] = field(default_factory=set)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert role configuration to dictionary for serialization."""
        return {
            'role_name': self.role_name,
            'level': self.level.name,
            'level_value': self.level.value,
            'is_staff': self.is_staff,
            'is_superuser': self.is_superuser,
            'description': self.description,
            'permissions': list(self.permissions)
        }


@dataclass
class RoleAssignmentResult:
    """
    Result object for role assignment operations.
    
    Attributes:
        success: Whether the role assignment was successful
        role_config: The assigned role configuration
        groups: List of Microsoft groups the user belongs to
        error_message: Error message if assignment failed
        assignment_reason: Reason for the specific role assignment
    """
    success: bool
    role_config: Optional[RoleConfiguration] = None
    groups: List[str] = field(default_factory=list)
    error_message: Optional[str] = None
    assignment_reason: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for serialization."""
        return {
            'success': self.success,
            'role_config': self.role_config.to_dict() if self.role_config else None,
            'groups': self.groups,
            'error_message': self.error_message,
            'assignment_reason': self.assignment_reason
        }


class RoleAuthenticator:
    """
    Production-ready role authenticator for Microsoft Graph API integration.
    
    This class provides comprehensive role management by mapping Microsoft Azure AD
    group memberships to Django user roles and permissions. It supports configurable
    role hierarchies, caching for performance, and comprehensive audit logging.
    
    Key Features:
    - Configurable role mappings with hierarchy support
    - Automatic caching of group memberships for performance
    - Comprehensive error handling and logging
    - Support for custom role configurations
    - Audit trail for security compliance
    
    Example:
        >>> authenticator = RoleAuthenticator()
        >>> result = authenticator.get_user_role_from_microsoft("user@domain.com")
        >>> if result.success:
        ...     print(f"User role: {result.role_config.role_name}")
        ... else:
        ...     print(f"Role assignment failed: {result.error_message}")
    """
    
    def __init__(self, custom_role_mappings: Optional[Dict[str, RoleConfiguration]] = None):
        """
        Initialize the role authenticator with role configurations.
        
        Args:
            custom_role_mappings: Custom role mappings to override defaults
        """
        self.graph_mixin = GraphAPIBaseMixin()
        self._role_mappings = self._initialize_role_mappings(custom_role_mappings)
        self._cache_timeout = getattr(settings, 'ROLE_CACHE_TIMEOUT', 300)  # 5 minutes
        
        logger.info(f"RoleAuthenticator initialized with {len(self._role_mappings)} role mappings")
    
    def _initialize_role_mappings(
        self, 
        custom_mappings: Optional[Dict[str, RoleConfiguration]] = None
    ) -> Dict[str, RoleConfiguration]:
        """
        Initialize role mappings with defaults and custom overrides.
        
        Args:
            custom_mappings: Custom role configurations to use
        
        Returns:
            Complete role mappings dictionary
        """
        # Default role configurations
        default_mappings = {
            'Admin': RoleConfiguration(
                role_name='Administrator',
                level=RoleLevel.ADMINISTRATOR,
                is_staff=True,
                is_superuser=True,
                description='Full system administrator with all permissions',
                permissions={'admin.access', 'user.manage', 'content.manage', 'system.configure'}
            ),
            'Staff': RoleConfiguration(
                role_name='Staff',
                level=RoleLevel.STAFF,
                is_staff=True,
                is_superuser=False,
                description='Staff member with content management permissions',
                permissions={'content.manage', 'user.view', 'reports.view'}
            ),
            'Moderator': RoleConfiguration(
                role_name='Moderator',
                level=RoleLevel.MODERATOR,
                is_staff=True,
                is_superuser=False,
                description='Content moderator with limited management permissions',
                permissions={'content.moderate', 'user.view'}
            ),
            'default': RoleConfiguration(
                role_name='User',
                level=RoleLevel.USER,
                is_staff=False,
                is_superuser=False,
                description='Standard authenticated user',
                permissions={'content.view'}
            )
        }
        
        # Apply custom mappings if provided
        if custom_mappings:
            default_mappings.update(custom_mappings)
        
        # Load from Django settings if available
        settings_mappings = getattr(settings, 'MICROSOFT_ROLE_MAPPINGS', {})
        if settings_mappings:
            for group_name, config_dict in settings_mappings.items():
                default_mappings[group_name] = RoleConfiguration(**config_dict)
        
        return default_mappings
    
    def get_user_role_from_microsoft(self, user_email: str) -> RoleAssignmentResult:
        """
        Determine user role based on Microsoft Azure AD group memberships.
        
        This method performs the complete role assignment process:
        1. Validate user email format
        2. Retrieve user from Microsoft Graph API
        3. Get user's group memberships
        4. Map groups to roles based on hierarchy
        5. Return detailed assignment result
        
        Args:
            user_email: Email address of the user to process
        
        Returns:
            Detailed role assignment result with success status and role information
        
        Example:
            >>> result = authenticator.get_user_role_from_microsoft("john@company.com")
            >>> if result.success:
            ...     print(f"Role: {result.role_config.role_name}")
            ...     print(f"Groups: {', '.join(result.groups)}")
            ... else:
            ...     print(f"Error: {result.error_message}")
        """
        try:
            # 1. Validate input
            if not self._validate_email_format(user_email):
                return RoleAssignmentResult(
                    success=False,
                    error_message=f"Invalid email format: {user_email}"
                )
            
            # 2. Get user ID from Microsoft Graph API
            user_id = self._get_user_id_by_email(user_email)
            if not user_id:
                return RoleAssignmentResult(
                    success=False,
                    error_message=f"User {user_email} not found in Microsoft organization"
                )
            
            # 3. Get user's group memberships (with caching)
            user_groups = self._get_user_groups_cached(user_id, user_email)
            if user_groups is None:
                return RoleAssignmentResult(
                    success=False,
                    error_message=f"Could not retrieve group memberships for {user_email}"
                )
            
            # 4. Determine role based on group memberships
            role_config, assignment_reason = self._determine_role_from_groups(user_groups)
            
            # 5. Log successful role assignment
            logger.info(
                f"Role assignment successful for {user_email}: "
                f"{role_config.role_name} (Groups: {user_groups}, Reason: {assignment_reason})"
            )
            
            return RoleAssignmentResult(
                success=True,
                role_config=role_config,
                groups=user_groups,
                assignment_reason=assignment_reason
            )
            
        except Exception as e:
            logger.error(f"Role assignment failed for {user_email}: {str(e)}", exc_info=True)
            return RoleAssignmentResult(
                success=False,
                error_message=f"Role assignment error: {str(e)}",
                groups=[]
            )
    
    def _validate_email_format(self, email: str) -> bool:
        """
        Validate email format using basic rules.
        
        Args:
            email: Email address to validate
        
        Returns:
            True if email format is valid
        """
        if not email or '@' not in email:
            return False
        
        parts = email.split('@')
        if len(parts) != 2 or not parts[0] or not parts[1]:
            return False
        
        return True
    
    def _get_user_id_by_email(self, email: str) -> Optional[str]:
        """
        Retrieve Microsoft Graph user ID by email address.
        
        Args:
            email: User's email address
        
        Returns:
            Microsoft Graph user ID or None if not found
        """
        try:
            # Use cache for user ID lookups
            cache_key = f"ms_user_id:{email}"
            cached_user_id = cache.get(cache_key)
            if cached_user_id:
                logger.debug(f"Using cached user ID for {email}")
                return cached_user_id
            
            # Search for user by email
            user_filter = f"mail eq '{email}' or userPrincipalName eq '{email}'"
            search_query = f"users?$filter={user_filter}&$select=id,displayName"
            
            response = self.graph_mixin.call_graph_api(search_query)
            users = response.get('value', [])
            
            if users:
                user_id = users[0].get('id')
                # Cache user ID for future lookups
                cache.set(cache_key, user_id, timeout=self._cache_timeout)
                return user_id
            
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving user ID for {email}: {str(e)}")
            return None
    
    def _get_user_groups_cached(self, user_id: str, user_email: str) -> Optional[List[str]]:
        """
        Get user's group memberships with caching support.
        
        Args:
            user_id: Microsoft Graph user ID
            user_email: User's email for logging
        
        Returns:
            List of group display names or None if error
        """
        # Try cache first
        cache_key = f"ms_user_groups:{user_id}"
        cached_groups = cache.get(cache_key)
        if cached_groups is not None:
            logger.debug(f"Using cached groups for {user_email}")
            return cached_groups
        
        # Fetch from Microsoft Graph API
        groups = self._get_user_groups(user_id)
        if groups is not None:
            # Cache the groups
            cache.set(cache_key, groups, timeout=self._cache_timeout)
            logger.debug(f"Cached groups for {user_email}: {groups}")
        
        return groups
    
    def _get_user_groups(self, user_id: str) -> Optional[List[str]]:
        """
        Retrieve user's group memberships from Microsoft Graph API.
        
        Args:
            user_id: Microsoft Graph user ID
        
        Returns:
            List of group display names or None if error
        """
        try:
            # Get user's group memberships
            groups_query = f"users/{user_id}/memberOf?$select=displayName,id,securityEnabled"
            response = self.graph_mixin.call_graph_api(groups_query)
            
            groups = response.get('value', [])
            
            # Filter for security-enabled groups and extract display names
            group_names = []
            for group in groups:
                if group.get('securityEnabled', True):  # Include security groups
                    display_name = group.get('displayName')
                    if display_name:
                        group_names.append(display_name)
            
            return group_names
            
        except ResourceNotFoundException:
            logger.warning(f"User {user_id} not found when retrieving groups")
            return []
        except Exception as e:
            logger.error(f"Error retrieving groups for user {user_id}: {str(e)}")
            return None
    
    def _determine_role_from_groups(self, user_groups: List[str]) -> Tuple[RoleConfiguration, str]:
        """
        Determine the highest privilege role based on group memberships.
        
        Args:
            user_groups: List of Microsoft groups the user belongs to
        
        Returns:
            Tuple of (role_configuration, assignment_reason)
        """
        assigned_role = None
        highest_level = RoleLevel.USER
        assignment_reason = "default assignment"
        
        # Check each group against role mappings
        for group_name in user_groups:
            if group_name in self._role_mappings:
                role_config = self._role_mappings[group_name]
                
                # Assign highest privilege role found
                if role_config.level.value > highest_level.value:
                    assigned_role = role_config
                    highest_level = role_config.level
                    assignment_reason = f"member of '{group_name}' group"
        
        # Return assigned role or default
        if assigned_role:
            return assigned_role, assignment_reason
        else:
            return self._role_mappings['default'], "no matching groups, using default role"
    
    def invalidate_user_cache(self, user_email: str) -> bool:
        """
        Invalidate cached data for a specific user.
        
        Args:
            user_email: Email of the user to invalidate cache for
        
        Returns:
            True if cache was invalidated, False if no cache existed
        """
        try:
            # Get user ID to clear group cache
            user_id = self._get_user_id_by_email(user_email)
            
            cache_keys = [
                f"ms_user_id:{user_email}",
                f"ms_user_groups:{user_id}" if user_id else None
            ]
            
            invalidated = False
            for cache_key in cache_keys:
                if cache_key and cache.get(cache_key):
                    cache.delete(cache_key)
                    invalidated = True
            
            if invalidated:
                logger.info(f"Cache invalidated for user: {user_email}")
            
            return invalidated
            
        except Exception as e:
            logger.error(f"Error invalidating cache for {user_email}: {str(e)}")
            return False
    
    def get_role_hierarchy(self) -> Dict[str, Any]:
        """
        Get the complete role hierarchy configuration.
        
        Returns:
            Dictionary containing role hierarchy information
        """
        hierarchy = {}
        
        for group_name, role_config in self._role_mappings.items():
            if group_name != 'default':  # Exclude default role from hierarchy
                hierarchy[group_name] = role_config.to_dict()
        
        # Add default role separately
        hierarchy['_default'] = self._role_mappings['default'].to_dict()
        
        return {
            'roles': hierarchy,
            'hierarchy_levels': [level.name for level in RoleLevel],
            'total_roles': len(self._role_mappings) - 1,  # Exclude default
            'cache_timeout': self._cache_timeout
        }
    
    def validate_role_configuration(self) -> Dict[str, Any]:
        """
        Validate the current role configuration and test Graph API connectivity.
        
        Returns:
            Dictionary containing validation results and configuration status
        """
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'configuration': {}
        }
        
        try:
            # Test Graph API connectivity
            test_response = self.graph_mixin.call_graph_api("organization?$top=1&$select=displayName")
            validation_result['configuration']['graph_api_accessible'] = True
            validation_result['configuration']['organization_accessible'] = bool(test_response.get('value'))
            
        except Exception as e:
            validation_result['valid'] = False
            validation_result['errors'].append(f"Graph API not accessible: {str(e)}")
            validation_result['configuration']['graph_api_accessible'] = False
        
        # Validate role mappings
        try:
            role_validation = self._validate_role_mappings()
            validation_result['configuration'].update(role_validation)
            
        except Exception as e:
            validation_result['valid'] = False
            validation_result['errors'].append(f"Role configuration validation failed: {str(e)}")
        
        # Add configuration summary
        validation_result['configuration'].update({
            'total_role_mappings': len(self._role_mappings),
            'privilege_levels': [level.name for level in RoleLevel],
            'cache_timeout': self._cache_timeout
        })
        
        return validation_result
    
    def _validate_role_mappings(self) -> Dict[str, Any]:
        """
        Validate role mapping configuration for consistency.
        
        Returns:
            Dictionary with validation results
        """
        validation = {
            'role_mappings_valid': True,
            'role_count_by_level': {},
            'duplicate_permissions': [],
            'missing_default': False
        }
        
        # Check for default role
        if 'default' not in self._role_mappings:
            validation['missing_default'] = True
            validation['role_mappings_valid'] = False
        
        # Count roles by level and check for conflicts
        level_counts = {}
        all_permissions = set()
        
        for group_name, role_config in self._role_mappings.items():
            if group_name == 'default':
                continue
                
            level_name = role_config.level.name
            level_counts[level_name] = level_counts.get(level_name, 0) + 1
            
            # Check for permission overlaps (could be intentional, so just warn)
            for permission in role_config.permissions:
                if permission in all_permissions:
                    validation['duplicate_permissions'].append(permission)
                all_permissions.add(permission)
        
        validation['role_count_by_level'] = level_counts
        
        return validation
    
    @lru_cache(maxsize=100)
    def get_available_roles(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all available roles with caching (for performance).
        
        Returns:
            Dictionary of all available role configurations
        """
        return {
            group_name: role_config.to_dict() 
            for group_name, role_config in self._role_mappings.items()
        }


# Singleton instance for application-wide use
role_authenticator = RoleAuthenticator()
