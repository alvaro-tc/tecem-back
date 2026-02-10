from rest_framework import serializers
from .models import SocialMediaLink, LandingPageConfig

class SocialMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = SocialMediaLink
        fields = ['id', 'facebook', 'youtube', 'tiktok', 'instagram', 'updated_at']
        read_only_fields = ['id', 'updated_at']

class LandingPageConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = LandingPageConfig
        fields = ['id', 'landing_image', 'updated_at']
        read_only_fields = ['id', 'updated_at']
