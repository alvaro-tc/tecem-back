from rest_framework import viewsets, permissions
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from .models import Publication
from .serializers import PublicationSerializer

class PublicationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Publication model
    Temporarily allowing all operations for any user until authentication is properly configured
    """
    queryset = Publication.objects.all()
    serializer_class = PublicationSerializer
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    permission_classes = [permissions.AllowAny]  # Temporary: allow all users
