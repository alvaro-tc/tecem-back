from rest_framework import serializers
from .models import SocialMediaLink

class SocialMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = SocialMediaLink
        fields = ['id', 'facebook', 'youtube', 'tiktok', 'instagram', 'updated_at']
        read_only_fields = ['id', 'updated_at']
