from rest_framework import serializers
# Angepasste Importe
from .models import Module, ModuleCategory, Content, SupplementaryContent, Task, UserTaskProgress, Article

class SupplementaryContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupplementaryContent
        fields = ['id', 'label', 'url', 'order']

class ContentSerializer(serializers.ModelSerializer):
    supplementary_contents = SupplementaryContentSerializer(many=True, read_only=True)

    class Meta:
        model = Content
        fields = ['id', 'module', 'title', 'description', 'video_url', 'supplementary_title', 'order', 'supplementary_contents']

class TaskSerializer(serializers.ModelSerializer):
    # Feld, das angibt, ob der aktuelle Benutzer die Aufgabe gelöst hat
    completed = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = ['id', 'title', 'description', 'difficulty', 'hint', 'order', 'completed']

    def get_completed(self, obj):
        # Hole den User aus dem Request-Kontext
        user = self.context.get('request').user
        if user and user.is_authenticated:
            # Prüfe, ob ein UserTaskProgress-Eintrag existiert und 'completed' ist
            return UserTaskProgress.objects.filter(user=user, task=obj, completed=True).exists()
        return False # Für nicht authentifizierte User

class ArticleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Article
        fields = ['id', 'module', 'title', 'url', 'order']

class ModuleCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ModuleCategory
        fields = ['id', 'name']


class ModuleListSerializer(serializers.ModelSerializer):
    category = ModuleCategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=ModuleCategory.objects.all(),
        source='category',
        write_only=True,
        required=False,
    )

    class Meta:
        model = Module
        fields = ['id', 'title', 'category', 'category_id', 'is_public']

class ModuleDetailSerializer(serializers.ModelSerializer):
    contents = ContentSerializer(many=True, read_only=True)
    tasks = serializers.SerializerMethodField() # Verwende SerializerMethodField, um Kontext zu übergeben
    articles = ArticleSerializer(many=True, read_only=True)
    category = ModuleCategorySerializer(read_only=True)

    class Meta:
        model = Module
        fields = ['id', 'title', 'category', 'is_public', 'contents', 'articles', 'tasks']

    def get_tasks(self, obj):
        # Hole den Request aus dem Kontext und übergebe ihn an den TaskSerializer
        request = self.context.get('request')
        tasks = obj.tasks.all()
        return TaskSerializer(tasks, many=True, context={'request': request}).data

class ExecuteCodeSerializer(serializers.Serializer):
    code = serializers.CharField(trim_whitespace=False)
    task_id = serializers.IntegerField() 