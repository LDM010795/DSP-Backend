from rest_framework import generics, permissions
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
import os

# Angepasste Importe
from ..models import Module, ModuleCategory, Article, Content, SupplementaryContent, Chapter
from ..serializers import (
    ModuleListSerializer,
    ModuleDetailSerializer,
    ArticleSerializer,
    ContentSerializer,
    SupplementaryContentSerializer,
    ModuleCategorySerializer,
    ChapterSerializer,
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
    
    def update(self, request, *args, **kwargs):
        print(f"[DEBUG] ContentUpdateView.update() called for content {kwargs.get('pk')}")
        print(f"[DEBUG] Request data: {request.data}")
        
        # Für partielle Updates (z.B. nur order ändern) - nicht alle Felder überschreiben
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        return Response(serializer.data)

class ArticleUpdateView(generics.RetrieveUpdateDestroyAPIView):
    """Handle Article CRUD operations: GET (retrieve), PUT/PATCH (update), DELETE (destroy)."""
    
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def update(self, request, *args, **kwargs):
        print(f"[DEBUG] ArticleUpdateView.update() called for article {kwargs.get('pk')}")
        print(f"[DEBUG] Request data: {request.data}")
        print(f"[DEBUG] Request method: {request.method}")
        
        try:
            response = super().update(request, *args, **kwargs)
            print(f"[DEBUG] Update successful: {response.data}")
            return response
        except Exception as e:
            print(f"[DEBUG] Update failed with error: {e}")
            print(f"[DEBUG] Error type: {type(e)}")
            raise
    
    def destroy(self, request, *args, **kwargs):
        """
        Custom destroy method with proper logging.
        """
        instance = self.get_object()
        
        # Log the deletion attempt
        print(f"🗑️ [DEBUG] Deleting article: {instance.title} (ID: {instance.id})")
        
        # Note: ArticleImage models are linked to Module, not Article directly
        # So they will persist after article deletion, which is intentional
        # (images can be reused across multiple articles in the same module)
        
        # Perform the actual deletion
        response = super().destroy(request, *args, **kwargs)
        print(f"✅ [DEBUG] Article {instance.id} successfully deleted")
        return response 

# --- Administrative Create/Update Views ---


class ModuleCreateView(generics.ListCreateAPIView):
    """List all modules or create a new one (admin)."""

    queryset = Module.objects.all()
    serializer_class = ModuleDetailSerializer
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
    
    def get_queryset(self):
        return Module.objects.prefetch_related('chapters', 'chapters__contents', 'articles')


class ContentCreateView(generics.CreateAPIView):
    """Create new video/content for a module, auto-ordering inside module."""

    serializer_class = ContentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        print(f"[DEBUG] ContentCreateView.create() called")
        print(f"[DEBUG] Request data: {request.data}")
        
        # Automatisch Titel aus Dateinamen extrahieren, wenn kein Titel angegeben
        data = request.data.copy()
        if not data.get('title') and data.get('video_url'):
            video_url = data['video_url']
            filename = video_url.split('/')[-1]
            title = os.path.splitext(filename)[0]  # Ohne Extension
            data['title'] = title
            print(f"[DEBUG] Automatically extracted title from filename: {title}")
            request._full_data = data  # Aktualisiere request.data
        
        try:
            result = super().create(request, *args, **kwargs)
            print(f"[DEBUG] Content creation successful: {result.data}")
            return result
        except Exception as e:
            print(f"[DEBUG] Content creation failed with error: {e}")
            print(f"[DEBUG] Error type: {type(e)}")
            raise

    def perform_create(self, serializer):
        chapter = serializer.validated_data["chapter"]
        next_order = Content.objects.filter(chapter=chapter).count() + 1
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

# --- Chapter Views ---

class ChapterCreateView(generics.CreateAPIView):
    """Create new chapter for a module."""
    
    serializer_class = ChapterSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_create(self, serializer):
        # Automatically compute order per module
        module = serializer.validated_data['module']
        next_order = (
            Chapter.objects.filter(module=module).count() + 1
        )
        serializer.save(order=next_order)


class ChapterUpdateView(generics.UpdateAPIView):
    """Update existing chapter."""
    
    queryset = Chapter.objects.all()
    serializer_class = ChapterSerializer
    permission_classes = [permissions.IsAuthenticated]


class ChapterDetailView(generics.RetrieveAPIView):
    """Get chapter details."""
    
    queryset = Chapter.objects.all()
    serializer_class = ChapterSerializer
    permission_classes = [permissions.IsAuthenticated]


class ChapterListView(generics.ListAPIView):
    """List all chapters."""
    
    queryset = Chapter.objects.all()
    serializer_class = ChapterSerializer
    permission_classes = [permissions.IsAuthenticated]


class ChapterDeleteView(generics.DestroyAPIView):
    """Delete a chapter."""
    
    queryset = Chapter.objects.all()
    serializer_class = ChapterSerializer