"""
E-Learning User Fetch Own Info

This view allows users to check their own information

Views:


Features:


Author: Christian Litke
Version: 1.0.0
"""

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from elearning.users.models import Profile
from elearning.users.serializers import UserSerializer


class CurrentUserView(APIView):
    def get(self, request):
        try:
            serializer = UserSerializer(request.user)
            return Response(serializer.data)
        except Profile.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
