from rest_framework import generics, permissions
from django.shortcuts import get_object_or_404

# Angepasste Importe
from ..models import Module
from ..serializers import ModuleListSerializer, ModuleDetailSerializer

# --- Public Views (ohne User-Kontext) ---

class ModuleListViewPublic(generics.ListAPIView):
    queryset = Module.objects.filter(is_public=True)
    serializer_class = ModuleListSerializer
    permission_classes = [permissions.AllowAny]

class ModuleDetailViewPublic(generics.RetrieveAPIView):
    queryset = Module.objects.filter(is_public=True)
    serializer_class = ModuleDetailSerializer
    permission_classes = [permissions.AllowAny]

# --- User-Specific Views (mit User-Kontext) ---

class UserModuleListView(generics.ListAPIView):
    serializer_class = ModuleListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Module.get_accessible_modules_for_user(self.request.user)

class UserModuleDetailView(generics.RetrieveAPIView):
    serializer_class = ModuleDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Module.objects.all()

    def get_object(self):
        obj = super().get_object()
        if not obj.check_user_accessibility(self.request.user):
            self.permission_denied(self.request)
        return obj 