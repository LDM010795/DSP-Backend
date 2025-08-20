from rest_framework import serializers
import os
# Angepasste Importe
from .models import Module, ModuleCategory, Content, SupplementaryContent, Task, UserTaskProgress, Article, Chapter, ArticleImage, TaskMultipleChoice

class SupplementaryContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupplementaryContent
        fields = ['id', 'label', 'url', 'order']

class ContentSerializer(serializers.ModelSerializer):
    supplementary_contents = SupplementaryContentSerializer(many=True, read_only=True)

    class Meta:
        model = Content
        fields = ['id', 'chapter', 'title', 'description', 'video_url', 'supplementary_title', 'order', 'supplementary_contents']
        extra_kwargs = {
            'title': {'required': False, 'allow_blank': True}
        }
    
    def validate(self, attrs):
        print(f"[DEBUG] ContentSerializer.validate() called with attrs: {attrs}")
        return super().validate(attrs)
    
    def create(self, validated_data):
        print(f"[DEBUG] ContentSerializer.create() called with validated_data: {validated_data}")
        try:
            result = super().create(validated_data)
            print(f"[DEBUG] Content creation successful: {result}")
            return result
        except Exception as e:
            print(f"[DEBUG] Content creation failed with error: {e}")
            print(f"[DEBUG] Error type: {type(e)}")
            raise

class TaskSerializer(serializers.ModelSerializer):
    """
    Task serializer with user-specific completion status.
    
    Includes a computed 'completed' field that indicates whether
    the current user has completed this task.
    """
    completed = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = ['id', 'chapter', 'title', 'description', 'difficulty', 'hint', 'order', 'task_type', 'completed']

    def to_representation(self, instance):
        """Add debug logging to see what data is being serialized."""
        data = super().to_representation(instance)
        print(f"🔍 [TaskSerializer] Serializing task {instance.id}: {data}")
        return data

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
    


class ArticleSerializer(serializers.ModelSerializer):
    module_id = serializers.PrimaryKeyRelatedField(
        queryset=Module.objects.all(),
        source='module',
        write_only=True,
        required=False,
        allow_null=True,
    )
    
    class Meta:
        model = Article
        fields = ['id', 'module', 'module_id', 'title', 'url', 'order', 'json_content']
        extra_kwargs = {
            'module': {'read_only': True}
        }
    
    def validate(self, attrs):
        print(f"[DEBUG] ArticleSerializer.validate() called with attrs: {attrs}")
        return super().validate(attrs)
    
    def update(self, instance, validated_data):
        print(f"[DEBUG] ArticleSerializer.update() called")
        print(f"[DEBUG] Instance: {instance}")
        print(f"[DEBUG] Validated data: {validated_data}")
        
        try:
            result = super().update(instance, validated_data)
            print(f"[DEBUG] Update successful: {result}")
            return result
        except Exception as e:
            print(f"[DEBUG] Update failed with error: {e}")
            print(f"[DEBUG] Error type: {type(e)}")
            raise

class ModuleCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ModuleCategory
        fields = ['id', 'name']


class ChapterSerializer(serializers.ModelSerializer):
    """Serializer for Chapter model."""
    
    module_id = serializers.PrimaryKeyRelatedField(
        queryset=Module.objects.all(),
        source='module',
        write_only=True,
        required=True,
    )
    contents = ContentSerializer(many=True, read_only=True)
    tasks = serializers.SerializerMethodField()
    articles = serializers.SerializerMethodField()
    
    class Meta:
        model = Chapter
        fields = ['id', 'module', 'module_id', 'title', 'description', 'order', 'is_active', 'contents', 'tasks', 'articles']
        extra_kwargs = {
            'module': {'read_only': True}
        }
    
    def get_tasks(self, obj):
        """
        Get tasks for this chapter with user-specific completion status.
        """
        request = self.context.get('request')
        tasks = Task.objects.filter(chapter=obj)
        
        if request:
            return TaskSerializer(tasks, many=True, context={'request': request}).data
        else:
            return TaskSerializer(tasks, many=True, context={}).data
    
    def get_articles(self, obj):
        """
        Get articles for this chapter.
        """
        articles = Article.objects.filter(chapter=obj)
        return ArticleSerializer(articles, many=True).data


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
    Detailed module serializer with nested chapters, content and user-specific task status.
    
    Uses SerializerMethodField for tasks to ensure proper request context
    propagation for completion status calculation.
    """
    chapters = ChapterSerializer(many=True, read_only=True)
    contents = serializers.SerializerMethodField()  # Get contents from chapters
    tasks = serializers.SerializerMethodField()  # For request context propagation
    articles = ArticleSerializer(many=True, read_only=True)
    category = ModuleCategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=ModuleCategory.objects.all(),
        source='category',
        write_only=True,
        required=False,
    )

    # Map von Bildname zu Cloud-URL für Bildauflösung im Frontend
    article_images = serializers.SerializerMethodField()

    class Meta:
        model = Module
        fields = ['id', 'title', 'category', 'category_id', 'is_public', 'chapters', 'contents', 'articles', 'tasks', 'article_images']

    def get_contents(self, obj):
        """
        Get contents from all chapters in this module.
        
        Args:
            obj: Module instance
            
        Returns:
            Serialized content data from all chapters
        """
        # Get contents from all chapters in this module
        contents = Content.objects.filter(chapter__module=obj)
        return ContentSerializer(contents, many=True).data

    def get_tasks(self, obj):
        """
        Get tasks with user-specific completion status.
        
        Args:
            obj: Module instance
            
        Returns:
            Serialized task data with completion status
        """
        request = self.context.get('request')
        # Get tasks from all chapters in this module
        tasks = Task.objects.filter(chapter__module=obj)
        
        # Propagate request context for user-specific data
        if request:
            return TaskSerializer(tasks, many=True, context={'request': request}).data
        else:
            # Fallback without user context
            return TaskSerializer(tasks, many=True, context={}).data

    def get_article_images(self, obj):
        # Liefert Mapping { image_name: cloud_url } für das Modul
        images = ArticleImage.objects.filter(module=obj).values('image_name', 'cloud_url')
        return {img['image_name']: img['cloud_url'] for img in images}

class ExecuteCodeSerializer(serializers.Serializer):
    code = serializers.CharField(trim_whitespace=False)
    task_id = serializers.IntegerField()


class TaskMultipleChoiceSerializer(serializers.ModelSerializer):
    """
    Serializer for TaskMultipleChoice model.
    
    Handles multiple choice questions with their options and correct answers.
    """
    
    class Meta:
        model = TaskMultipleChoice
        fields = [
            'id', 'task', 'question', 'option_1', 'option_2', 
            'option_3', 'option_4', 'correct_answer', 'order'
        ]
        extra_kwargs = {
            'task': {'required': True}  # Task is required for creation
        }
    
    def validate(self, attrs):
        """
        Validate the multiple choice question data.
        
        Ensures:
        - All options are provided
        - Correct answer index is valid
        - No duplicate options
        """
        # Check if all options are provided
        options = [
            attrs.get('option_1', ''),
            attrs.get('option_2', ''),
            attrs.get('option_3', ''),
            attrs.get('option_4', '')
        ]
        
        # Allow empty options for now (they can be filled later)
        # if any(not option.strip() for option in options):
        #     raise serializers.ValidationError("All options must be provided and non-empty")
        
        # Check for duplicate options (only if they're not empty)
        non_empty_options = [opt for opt in options if opt.strip()]
        if len(set(non_empty_options)) != len(non_empty_options):
            raise serializers.ValidationError("All options must be unique")
        
        # Validate correct_answer index
        correct_answer = attrs.get('correct_answer')
        if correct_answer is not None and (correct_answer < 0 or correct_answer > 3):
            raise serializers.ValidationError("correct_answer must be between 0 and 3")
        
        return attrs 