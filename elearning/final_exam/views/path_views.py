from rest_framework import viewsets, permissions
# Angepasste Importe
from ..models import CertificationPath
from ..serializers import CertificationPathSerializer

class CertificationPathViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CertificationPath.objects.all().order_by('order')
    serializer_class = CertificationPathSerializer
    permission_classes = [permissions.IsAuthenticated] 