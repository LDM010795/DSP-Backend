from django.core.management.base import BaseCommand
from elearning.modules.models import Task, TaskMultipleChoice


class Command(BaseCommand):
    help = 'Update existing tasks with correct task_type based on whether they have multiple choice questions'

    def handle(self, *args, **options):
        self.stdout.write('Updating task types...')
        
        # Get all tasks
        tasks = Task.objects.all()
        updated_count = 0
        
        for task in tasks:
            # Check if task has multiple choice questions
            has_multiple_choice = TaskMultipleChoice.objects.filter(task=task).exists()
            
            if has_multiple_choice:
                if task.task_type != Task.TaskType.MULTIPLE_CHOICE:
                    task.task_type = Task.TaskType.MULTIPLE_CHOICE
                    task.save()
                    updated_count += 1
                    self.stdout.write(f'Updated task "{task.title}" to multiple_choice')
            else:
                # Default to programming if no multiple choice questions
                if task.task_type != Task.TaskType.PROGRAMMING:
                    task.task_type = Task.TaskType.PROGRAMMING
                    task.save()
                    updated_count += 1
                    self.stdout.write(f'Updated task "{task.title}" to programming')
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully updated {updated_count} tasks')
        )
