from rest_framework import serializers
# Angepasste Importe
from .models import Module, Content, SupplementaryContent, Task, UserTaskProgress

class SupplementaryContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupplementaryContent
        fields = ['id', 'label', 'url', 'order']

class ContentSerializer(serializers.ModelSerializer):
    supplementary_contents = SupplementaryContentSerializer(many=True, read_only=True)

    class Meta:
        model = Content
        fields = ['id', 'title', 'description', 'video_url', 'supplementary_title', 'order', 'supplementary_contents']

class TaskSerializer(serializers.ModelSerializer):
    # Feld, das angibt, ob der aktuelle Benutzer die Aufgabe gelöst hat
    is_completed = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = ['id', 'title', 'description', 'difficulty', 'hint', 'order', 'is_completed']

    def get_is_completed(self, obj):
        # Hole den User aus dem Request-Kontext
        user = self.context.get('request').user
        if user and user.is_authenticated:
            # Prüfe, ob ein UserTaskProgress-Eintrag existiert und 'completed' ist
            return UserTaskProgress.objects.filter(user=user, task=obj, completed=True).exists()
        return False # Für nicht authentifizierte User

class ModuleListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Module
        fields = ['id', 'title', 'category', 'is_public']

class ModuleDetailSerializer(serializers.ModelSerializer):
    contents = ContentSerializer(many=True, read_only=True)
    tasks = serializers.SerializerMethodField() # Verwende SerializerMethodField, um Kontext zu übergeben

    class Meta:
        model = Module
        fields = ['id', 'title', 'category', 'is_public', 'contents', 'tasks']

    def get_tasks(self, obj):
        # Hole den Request aus dem Kontext und übergebe ihn an den TaskSerializer
        request = self.context.get('request')
        tasks = obj.tasks.all()
        return TaskSerializer(tasks, many=True, context={'request': request}).data

class ExecuteCodeSerializer(serializers.Serializer):
    code = serializers.CharField(trim_whitespace=False)
    task_id = serializers.IntegerField() 