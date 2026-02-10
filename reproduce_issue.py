
import os
import django
import sys

# Add the project root to sys.path
sys.path.append(os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from api.school.models import Program
from api.school.serializers import ProgramSerializer
from rest_framework.test import APIRequestFactory

print("Attempting to create Program...")
data = {'name': 'Test Program'}
serializer = ProgramSerializer(data=data)
if serializer.is_valid():
    try:
        instance = serializer.save()
        print(f"Program created successfully: {instance}")
    except Exception as e:
        import traceback
        traceback.print_exc()
else:
    print("Validation errors:", serializer.errors)
