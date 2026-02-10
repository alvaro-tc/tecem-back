
import os
import django
import sys
from django.test import RequestFactory

# Add the project root to sys.path
sys.path.append(os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from api.school.views import ProgramViewSet
from rest_framework.test import force_authenticate
from django.contrib.auth import get_user_model

User = get_user_model()

print(f"Python version: {sys.version}")
print(f"Django version: {django.get_version()}")

try:
    # Create a user for authentication
    user = User.objects.filter(role='ADMIN').first()
    if not user:
        print("No admin user found, creating dummy...")
        user = User.objects.create(email='test@example.com', password='password', role='ADMIN')

    factory = RequestFactory()
    data = {'name': 'Test Program V2'}
    request = factory.post('/api/programs', data, content_type='application/json')
    force_authenticate(request, user=user)
    
    view = ProgramViewSet.as_view({'post': 'create'})
    response = view(request)
    
    print(f"Response status: {response.status_code}")
    print(f"Response data: {response.data}")

except Exception as e:
    import traceback
    traceback.print_exc()
