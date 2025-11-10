"""
Downloadable Resource Serializer
===============================

This module defines the serializer for the DownloadableResource model,
enabling structured API representation and dynamic presigned download
URL generation via Wasabi Cloud Storage.

Purpose:
--------
- Serialize DownloadableResource objects for API responses.
- Automatically generate secure, time-limited presigned URLs
  to allow users to download files from Wasabi without exposing
  direct storage credentials.
- Maintain compatibility with DRF's standard serialization layer.

Key Components:
---------------
1. **DownloadableResourceSerializer**
   - Extends Django REST Framework's ModelSerializer.
   - Serializes metadata fields (title, type, module, cloud path, etc.).
   - Adds a computed field `download_url` using `get_download_url()`.

2. **get_download_url(obj)**
   - Uses the WasabiService class to create a presigned URL
     based on the resource’s `cloud_key`.
   - Ensures secure, temporary access to the file (default: 2 hours validity).
   - Returns `None` if generation fails, ensuring API robustness.

Integration:
------------
This serializer is used by:
- `ModuleResourcesListView` (and optionally article-based views)
  to expose downloadable resources through the REST API.

Author: DSP Development Team
Date: 11-07-2025
"""

from rest_framework import serializers
from .models_downloads import DownloadableResource
from elearning.modules.services.wasabi_service import WasabiService


class DownloadableResourceSerializer(serializers.ModelSerializer):
    """
    Serializer for DownloadableResource model.
    Adds a dynamic field 'download_url' that generates a presigned Wasabi URL.
    """

    download_url = serializers.SerializerMethodField()

    class Meta:
        model = DownloadableResource
        fields = [
            "id",
            "title",
            "description",
            "resource_type",
            "module",
            "article",
            "cloud_key",
            "cloud_url",
            "download_url",
            "size_bytes",
            "is_public",
            "created_at",
        ]

    def get_download_url(self, obj):
        """
        Generates a temporary presigned URL using WasabiService
        """
        try:
            service = WasabiService()
            return service.generate_presigned_url(obj.cloud_key)
        except Exception:
            return None
