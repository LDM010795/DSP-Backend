from django.contrib.auth.models import User
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser, IsAuthenticated
# Angepasste Importe
from ..serializers import UserSerializer, SetInitialPasswordSerializer

class UserCrudViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by('id')
    serializer_class = UserSerializer
    permission_classes = [IsAdminUser]

class SetInitialPasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        if not user.profile.force_password_change:
            return Response({'detail': 'Passwort wurde bereits gesetzt.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = SetInitialPasswordSerializer(data=request.data)
        if serializer.is_valid():
            user.set_password(serializer.validated_data['password'])
            user.profile.force_password_change = False
            user.save()
            user.profile.save()
            return Response({'detail': 'Passwort erfolgreich gesetzt.'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST) 