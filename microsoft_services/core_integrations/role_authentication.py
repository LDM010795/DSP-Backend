"""
DSP Role Authentication System

Zentrale Logik für die Zuordnung von Microsoft-Gruppenmitgliedschaften zu Django-Rollen.

Rollen-Hierarchie:
- Admin Gruppe → is_superuser = True, is_staff = True
- Lehrer Gruppe → is_staff = True, is_superuser = False  
- Keine Gruppe/Andere → normaler authenticated user
"""

import logging
from typing import Dict, Any, Tuple
from .mixins import GraphAPIBaseMixin

logger = logging.getLogger(__name__)

class RoleAuthenticator:
    """
    Verwaltet die Zuordnung von Microsoft-Gruppenmitgliedschaften zu Django-Rollen
    """
    
    # Microsoft-Gruppennamen → Django-Rollen Mapping
    ROLE_MAPPINGS = {
        'Admin': {
            'is_staff': True,
            'is_superuser': True,
            'role_name': 'Administrator'
        },
        'Lehrer': {
            'is_staff': True,
            'is_superuser': False,
            'role_name': 'Teacher'
        },
        # Default für alle anderen/keine Gruppe
        'default': {
            'is_staff': False,
            'is_superuser': False,
            'role_name': 'Student'
        }
    }
    
    def __init__(self):
        self.graph_mixin = GraphAPIBaseMixin()
    
    def get_user_role_from_microsoft(self, user_email: str) -> Dict[str, Any]:
        """
        Ermittelt die Rolle eines Users basierend auf Microsoft-Gruppenmitgliedschaften
        
        Args:
            user_email: E-Mail des Users
            
        Returns:
            Dict mit Rollen-Informationen: {
                'is_staff': bool,
                'is_superuser': bool,
                'role_name': str,
                'groups': list,
                'success': bool,
                'error': str or None
            }
        """
        try:
            # 1. User-ID aus Microsoft holen
            user_id = self._get_user_id_by_email(user_email)
            if not user_id:
                return self._create_default_role(f"User {user_email} not found in Microsoft")
            
            # 2. Gruppenmitgliedschaften des Users abrufen
            user_groups = self._get_user_groups(user_id)
            if user_groups is None:
                return self._create_default_role(f"Could not retrieve groups for {user_email}")
            
            # 3. Rolle basierend auf Gruppenmitgliedschaften bestimmen
            role_info = self._determine_role_from_groups(user_groups)
            role_info['groups'] = user_groups
            role_info['success'] = True
            role_info['error'] = None
            
            logger.info(f"Role determined for {user_email}: {role_info['role_name']} (Groups: {user_groups})")
            return role_info
            
        except Exception as e:
            logger.error(f"Error determining role for {user_email}: {str(e)}")
            return self._create_default_role(f"Error determining role: {str(e)}")
    
    def _get_user_id_by_email(self, email: str) -> str | None:
        """
        Holt die Microsoft User-ID basierend auf der E-Mail
        """
        try:
            user_filter = f"mail eq '{email}' or userPrincipalName eq '{email}'"
            search_query = f"users?$filter={user_filter}&$select=id"
            
            response = self.graph_mixin.call_graph_api(search_query)
            users = response.get('value', [])
            
            if users:
                return users[0].get('id')
            return None
            
        except Exception as e:
            logger.error(f"Error getting user ID for {email}: {str(e)}")
            return None
    
    def _get_user_groups(self, user_id: str) -> list | None:
        """
        Holt alle Gruppenmitgliedschaften eines Users
        """
        try:
            # Gruppenmitgliedschaften des Users abrufen
            groups_query = f"users/{user_id}/memberOf?$select=displayName,id"
            response = self.graph_mixin.call_graph_api(groups_query)
            
            groups = response.get('value', [])
            group_names = [group.get('displayName') for group in groups if group.get('displayName')]
            
            return group_names
            
        except Exception as e:
            logger.error(f"Error getting groups for user {user_id}: {str(e)}")
            return None
    
    def _determine_role_from_groups(self, user_groups: list) -> Dict[str, Any]:
        """
        Bestimmt die Django-Rolle basierend auf Gruppenmitgliedschaften
        
        Priorität: Admin > Lehrer > Default
        """
        # Admin hat höchste Priorität
        if 'Admin' in user_groups:
            return self.ROLE_MAPPINGS['Admin'].copy()
        
        # Lehrer hat zweithöchste Priorität
        if 'Lehrer' in user_groups:
            return self.ROLE_MAPPINGS['Lehrer'].copy()
        
        # Default für alle anderen
        return self.ROLE_MAPPINGS['default'].copy()
    
    def _create_default_role(self, error_msg: str = None) -> Dict[str, Any]:
        """
        Erstellt Default-Rolle bei Fehlern oder fehlenden Gruppen
        """
        role_info = self.ROLE_MAPPINGS['default'].copy()
        role_info.update({
            'groups': [],
            'success': False,
            'error': error_msg
        })
        return role_info
    
    @classmethod
    def get_available_roles(cls) -> Dict[str, Dict[str, Any]]:
        """
        Gibt alle verfügbaren Rollen zurück (für Dokumentation/Admin-UI)
        """
        return cls.ROLE_MAPPINGS.copy()
    
    def validate_role_configuration(self) -> Dict[str, Any]:
        """
        Validiert die Rollen-Konfiguration (für Health-Checks)
        """
        try:
            # Test Graph API Verbindung
            response = self.graph_mixin.call_graph_api("groups?$top=1&$select=displayName")
            
            return {
                'valid': True,
                'roles_configured': len(self.ROLE_MAPPINGS) - 1,  # -1 für 'default'
                'graph_api_accessible': True,
                'available_roles': list(self.ROLE_MAPPINGS.keys())
            }
            
        except Exception as e:
            return {
                'valid': False,
                'error': str(e),
                'graph_api_accessible': False
            }
