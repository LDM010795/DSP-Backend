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
    """
    Task serializer with user-specific completion status.
    
    Includes a computed 'completed' field that indicates whether
    the current user has completed this task.
    """
    completed = serializers.SerializerMethodField()
    task_config = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = ['id', 'title', 'description', 'difficulty', 'hint', 'order', 'completed', 'task_type', 'task_config']

    def get_completed(self, obj):
        """
        Check if the current user has completed this task.
        
        Args:
            obj: Task instance
            
        Returns:
            bool: True if user completed the task, False otherwise
        """
        user = self.context.get('request').user
        if user and user.is_authenticated:
            # Check for existing completion record
            return UserTaskProgress.objects.filter(user=user, task=obj, completed=True).exists()
        return False  # Unauthenticated users haven't completed anything
    
    def get_task_config(self, obj):
        """Get task configuration based on task type."""
        if obj.task_type == obj.TaskType.MULTIPLE_CHOICE:
            return obj.get_multiple_choice_config()
        elif obj.task_type == obj.TaskType.PROGRAMMING:
            return {
                'test_file_path': obj.test_file_path,
                'has_automated_tests': obj.has_automated_tests()
            }
        return None

class ArticleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Article
        fields = ['id', 'module', 'title', 'url', 'order', 'json_content']

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
    """
    Detailed module serializer with nested content and user-specific task status.
    
    Uses SerializerMethodField for tasks to ensure proper request context
    propagation for completion status calculation.
    """
    contents = ContentSerializer(many=True, read_only=True)
    tasks = serializers.SerializerMethodField()  # For request context propagation
    articles = ArticleSerializer(many=True, read_only=True)
    category = ModuleCategorySerializer(read_only=True)

    class Meta:
        model = Module
        fields = ['id', 'title', 'category', 'is_public', 'contents', 'articles', 'tasks']

    def get_tasks(self, obj):
        """
        Get tasks with user-specific completion status.
        
        Args:
            obj: Module instance
            
        Returns:
            Serialized task data with completion status
        """
        request = self.context.get('request')
        tasks = obj.tasks.all()
        
        # Propagate request context for user-specific data
        if request:
            return TaskSerializer(tasks, many=True, context={'request': request}).data
        else:
            # Fallback without user context
            return TaskSerializer(tasks, many=True, context={}).data

class ExecuteCodeSerializer(serializers.Serializer):
    code = serializers.CharField(trim_whitespace=False)
    task_id = serializers.IntegerField() 