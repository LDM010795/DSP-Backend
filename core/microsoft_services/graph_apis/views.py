"""
Microsoft Graph API Test Views - DSP (Digital Solutions Platform)

Dieses Modul enthält Test- und Diagnose-Views für Microsoft Graph API Application Permissions.
Ermöglicht das Testen von Token-Akquise und grundlegenden Graph-Endpunkten.

Author: DSP Development Team
Created: 10.07.2025
Version: 1.0.0
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from ..core_integrations.mixins import GraphAPIBaseMixin
from ..core_integrations.token_manager import azure_token_manager
import logging

logger = logging.getLogger(__name__)

# --- Test-Endpoint für Microsoft Graph Application Permissions ---


class UserReadTestView(APIView):
    """
    Test View für Microsoft Graph Application Permissions

    Endpoints:
    GET /api/microsoft/graph/test/ - Testet Graph API Zugriff
    """

    def get(self, request):
        """
        Testet ob Microsoft Graph API Zugriff funktioniert

        Returns:
            Response mit Test-Ergebnis
        """
        try:
            logger.info("Testing Microsoft Graph API access")

            # 1. Token holen
            try:
                token = azure_token_manager.get_access_token()
                token_success = True
                token_message = "Token successfully obtained"
            except Exception as e:
                token_success = False
                token_message = f"Token failed: {str(e)}"
                logger.error(f"Token error: {str(e)}")

            if not token_success:
                return Response(
                    {
                        "success": False,
                        "message": "Azure Token Test failed",
                        "token_test": {"success": False, "error": token_message},
                        "next_steps": [
                            "Check AZURE_TENANT_ID environment variable",
                            "Check AZURE_CLIENT_ID environment variable",
                            "Check AZURE_CLIENT_SECRET environment variable",
                        ],
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # 2. Graph API Test mit /organization endpoint (funktioniert mit App Permissions)
            try:
                mixin = GraphAPIBaseMixin()
                org_info = mixin.call_graph_api("organization")

                graph_success = True
                graph_message = "Microsoft Graph API access working"

                # Organization Info extrahieren
                orgs = org_info.get("value", [])
                if orgs:
                    org = orgs[0]
                    org_name = org.get("displayName", "Unknown Organization")
                    org_domain = org.get("verifiedDomains", [{}])[0].get(
                        "name", "Unknown Domain"
                    )
                else:
                    org_name = "No organization data"
                    org_domain = "No domain data"

            except Exception as e:
                graph_success = False
                graph_message = f"Graph API failed: {str(e)}"
                org_name = None
                org_domain = None
                logger.error(f"Graph API error: {str(e)}")

            # 3. Ergebnis
            overall_success = token_success and graph_success

            response_data = {
                "success": overall_success,
                "message": "Microsoft Graph API test completed",
                "tests": {
                    "token_test": {"success": token_success, "message": token_message},
                    "graph_api_test": {
                        "success": graph_success,
                        "message": graph_message,
                    },
                },
            }

            # Wenn erfolgreich, Organization-Info hinzufügen
            if overall_success:
                response_data["organization_info"] = {
                    "name": org_name,
                    "domain": org_domain,
                }
                response_data["available_endpoints"] = [
                    "GET /api/microsoft/graph/organization",
                    "GET /api/microsoft/graph/users (with User.Read.All permission)",
                    "Add more permissions in Azure Portal for more endpoints",
                ]
            else:
                response_data["troubleshooting"] = [
                    "Go to Azure Portal → App registrations → Your App",
                    "Navigate to API permissions",
                    "Add permission → Microsoft Graph → Application permissions",
                    "Select Directory.Read.All (for organization endpoint)",
                    'Click "Grant admin consent for [your organization]"',
                    "Redeploy your application",
                ]

            return Response(
                response_data,
                status=status.HTTP_200_OK
                if overall_success
                else status.HTTP_403_FORBIDDEN,
            )

        except Exception as e:
            logger.error(f"Graph API test failed: {str(e)}")
            return Response(
                {
                    "success": False,
                    "message": f"Test failed with unexpected error: {str(e)}",
                    "error_type": type(e).__name__,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
