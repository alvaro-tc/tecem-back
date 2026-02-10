from django.contrib import admin
from .models import Publication

@admin.register(Publication)
class PublicationAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'stock', 'pages', 'dl', 'created_at']
    list_filter = ['created_at', 'author']
    search_fields = ['title', 'author', 'dl']
    readonly_fields = ['created_at', 'updated_at']
