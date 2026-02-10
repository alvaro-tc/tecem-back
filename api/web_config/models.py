from django.db import models

class SocialMediaLink(models.Model):
    facebook = models.URLField(max_length=255, blank=True, null=True)
    youtube = models.URLField(max_length=255, blank=True, null=True)
    tiktok = models.URLField(max_length=255, blank=True, null=True)
    instagram = models.URLField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # Ensure only one instance exists
        if not self.pk and SocialMediaLink.objects.exists():
            return SocialMediaLink.objects.first()
        return super(SocialMediaLink, self).save(*args, **kwargs)

    def __str__(self):
        return "Social Media Configuration"

    class Meta:
        verbose_name = "Social Media Link"
        verbose_name_plural = "Social Media Links"
