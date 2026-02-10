from rest_framework import serializers
from .models import Publication

class PublicationSerializer(serializers.ModelSerializer):
    """
    Serializer for Publication model
    """
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Publication
        fields = ['id', 'title', 'author', 'stock', 'pages', 'dl', 'summary', 'image', 'image_url', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at', 'image_url']

    def get_image_url(self, obj):
        """Return the full image URL"""
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None
