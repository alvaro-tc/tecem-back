import os
import django
import sys
import traceback

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

try:
    django.setup()
    from api.school import views
    print("Import successful")
except Exception:
    traceback.print_exc()
