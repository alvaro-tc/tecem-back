from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from .models import SocialMediaLink
from .serializers import SocialMediaSerializer

class SocialMediaViewSet(viewsets.ModelViewSet):
    """
    ViewSet to manage Social Media Links configuration.
    It ensures we are always working with the single instance of configuration.
    """
    queryset = SocialMediaLink.objects.all()
    serializer_class = SocialMediaSerializer
    permission_classes = [permissions.AllowAny] # Allow read access to anyone, write to admin/staff (refined later)

    def get_object(self):
        # Always return the first instance, create if doesn't exist
        obj, created = SocialMediaLink.objects.get_or_create(pk=1)
        return obj

    def list(self, request, *args, **kwargs):
        # Return the single object instead of a list
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        # Prevent creation of new instances, just update the existing one
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)
