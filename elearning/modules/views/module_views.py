from rest_framework import generics, permissions
from django.shortcuts import get_object_or_404

# Angepasste Importe
from ..models import Module, ModuleCategory, Article, Content, SupplementaryContent
from ..serializers import (
    ModuleListSerializer,
    ModuleDetailSerializer,
    ArticleSerializer,
    ContentSerializer,
    SupplementaryContentSerializer,
    ModuleCategorySerializer,
)

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
    serializer_class = ModuleDetailSerializer
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

class ArticleCreateView(generics.CreateAPIView):
    serializer_class = ArticleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        # Automatically compute order per module
        module = serializer.validated_data['module']
        next_order = (
            Article.objects.filter(module=module).count() + 1
        )
        serializer.save(order=next_order) 

class ContentUpdateView(generics.UpdateAPIView):
    queryset = Content.objects.all()
    serializer_class = ContentSerializer
    permission_classes = [permissions.IsAuthenticated]

class ArticleUpdateView(generics.UpdateAPIView):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    permission_classes = [permissions.IsAuthenticated] 

# --- Administrative Create/Update Views ---


class ModuleCreateView(generics.ListCreateAPIView):
    """List all modules or create a new one (admin)."""

    queryset = Module.objects.all()
    serializer_class = ModuleListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        category = serializer.validated_data.get("category")
        if not category:
            category, _ = ModuleCategory.objects.get_or_create(name="Sonstiges")
            serializer.save(category=category)
        else:
            serializer.save()


class ModuleUpdateView(generics.UpdateAPIView):
    """Update existing learning module (admin)."""

    queryset = Module.objects.all()
    serializer_class = ModuleListSerializer
    permission_classes = [permissions.IsAuthenticated]


# Admin Detail View
class ModuleDetailAdminView(generics.RetrieveAPIView):
    queryset = Module.objects.all()
    serializer_class = ModuleDetailSerializer
    permission_classes = [permissions.IsAuthenticated]


class ContentCreateView(generics.CreateAPIView):
    """Create new video/content for a module, auto-ordering inside module."""

    serializer_class = ContentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        module = serializer.validated_data["module"]
        next_order = Content.objects.filter(module=module).count() + 1
        serializer.save(order=next_order)


class SupplementaryContentCreateView(generics.CreateAPIView):
    """Create supplementary resource link for a content item with auto-order."""

    serializer_class = SupplementaryContentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        content = serializer.validated_data["content"]
        next_order = (
            SupplementaryContent.objects.filter(content=content).count() + 1
        )
        serializer.save(order=next_order) 


# --- Kategorie-Management ---


class CategoryListCreateView(generics.ListCreateAPIView):
    """Listet alle Kategorien auf oder legt eine neue an."""

    queryset = ModuleCategory.objects.all()
    serializer_class = ModuleCategorySerializer
    permission_classes = [permissions.IsAuthenticated]


class CategoryUpdateView(generics.UpdateAPIView):
    queryset = ModuleCategory.objects.all()
    serializer_class = ModuleCategorySerializer
    permission_classes = [permissions.IsAuthenticated] 