"""
Downloadable Resource Views
===========================

This module defines the API views for accessing downloadable learning
resources (e.g., PDFs, code files, Jupyter notebooks, slides) associated
with modules in the DSP E-Learning Platform.

Purpose:
--------
- Provide authenticated and public access to downloadable resources.
- Allow filtering by resource type (e.g., ?type=pdf, ?type=code).
- Integrate seamlessly with the Wasabi-based cloud storage system
  via presigned download URLs generated in the serializer.

Filtering Example:
------------------
- GET /api/modules/<module_id>/resources/ → returns all public resources.
- GET /api/modules/<module_id>/resources/?type=pdf → returns only PDFs.

Security:
---------
- Uses `IsAuthenticatedOrReadOnly` permission:
  - Unauthenticated users can view public resources.
  - Authenticated users may get extended access in the future.

Author: DSP Development Team
Date: 11-07-2025
"""


from rest_framework import generics, permissions
from ..models_downloads import DownloadableResource
from ..serializers_downloads import DownloadableResourceSerializer

class ModuleResourcesListView(generics.ListAPIView):
    """
    Returns all downloadable resources for a given module.
    Optional filter by type: ?type=pdf / ?type=code / ?type=slides
    """
    serializer_class = DownloadableResourceSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        module_id = self.kwargs.get("module_id")
        resource_type = self.request.query_params.get("type")
        queryset = DownloadableResource.objects.filter(module_id=module_id, is_public=True)
        if resource_type:
            queryset = queryset.filter(resource_type=resource_type)
        return queryset