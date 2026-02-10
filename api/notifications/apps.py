from django.apps import AppConfig

class NotificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api.notifications'
    label = 'api_notifications'

    def ready(self):
        import api.notifications.signals
