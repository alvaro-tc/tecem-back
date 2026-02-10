from django.db import models

class Publication(models.Model):
    """
    Model for managing publications (books, documents, etc.)
    """
    title = models.CharField(max_length=255, verbose_name="Título")
    author = models.CharField(max_length=255, verbose_name="Autor")
    stock = models.IntegerField(default=0, verbose_name="Existencias")
    pages = models.IntegerField(verbose_name="Páginas")
    dl = models.CharField(max_length=100, verbose_name="Depósito Legal", blank=True, null=True)
    summary = models.TextField(verbose_name="Resumen")
    image = models.ImageField(upload_to='publications/', verbose_name="Imagen", blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Publicación"
        verbose_name_plural = "Publicaciones"

    def __str__(self):
        return self.title
