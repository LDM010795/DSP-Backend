from rest_framework import permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
import subprocess
import tempfile
import os

# Angepasste Importe
from ..models import Task
from ..serializers import ExecuteCodeSerializer

class ExecutePythonCodeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = ExecuteCodeSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        code = serializer.validated_data['code']
        task_id = serializer.validated_data['task_id']

        task = get_object_or_404(Task, pk=task_id)
        if not task.test_file_path:
            return Response(
                {"error": "Für diese Aufgabe ist kein Testfall hinterlegt."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Pfad zur Testdatei erstellen, relativ zum 'elearning'-App-Verzeichnis
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__))) # -> .../elearning/
        test_file_full_path = os.path.join(base_dir, task.test_file_path)

        if not os.path.exists(test_file_full_path):
             return Response(
                {"error": f"Testfall-Datei nicht gefunden unter: {task.test_file_path}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_code_file:
            temp_code_file.write(code)
            temp_code_file_path = temp_code_file.name

        try:
            env = os.environ.copy()
            env['PYTHONPATH'] = os.path.dirname(temp_code_file_path) + os.pathsep + env.get('PYTHONPATH', '')
            
            result = subprocess.run(
                ['python', '-m', 'unittest', test_file_full_path],
                capture_output=True,
                text=True,
                timeout=10,
                env=env
            )

            success = result.returncode == 0
            
            return Response({
                "success": success,
                "output": result.stdout + result.stderr
            })

        except subprocess.TimeoutExpired:
            return Response({
                "success": False,
                "error": "Timeout: Die Ausführung des Codes hat zu lange gedauert."
            }, status=status.HTTP_408_REQUEST_TIMEOUT)
        finally:
            os.remove(temp_code_file_path) 