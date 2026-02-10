import os
import sys
import django

sys.path.append(os.getcwd())
import environ
env = environ.Env()
env.read_env(os.path.join(os.getcwd(), '.env'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from api.user.models import User
from api.user.serializers import ManageUserSerializer

# Try to create a user via Serializer to mimic the ViewSet
data = {
    'email': 'test_student_debug@example.com',
    'password': 'password123',
    'first_name': 'Test',
    'paternal_surname': 'Student',
    'role': 'STUDENT',
    'ci_number': '99887766'
}

print("Attempting to create user with data:", data)

try:
    serializer = ManageUserSerializer(data=data)
    if serializer.is_valid():
        user = serializer.save()
        print(f"User created successfully: {user.email} (ID: {user.id})")
    else:
        print("Serializer errors:", serializer.errors)
except Exception as e:
    import traceback
    print("Caught Exception during user creation:")
    traceback.print_exc()
