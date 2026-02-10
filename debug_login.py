
import os
import django
import sys

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth import authenticate
from api.user.models import User
from api.user.serializers import UserSerializer
from rest_framework.authtoken.models import Token

print("--- Debugging Login ---")

# 1. Check User Serializer
print("1. Testing UserSerializer with first user...")
try:
    user = User.objects.first()
    if user:
        print(f"   Found user: {user.email}")
        serializer = UserSerializer(user)

        print(f"   Serialized data keys: {serializer.data.keys()}")
        print("   [OK] UserSerializer works.")
    else:
        print("   [WARN] No users found in DB.")
except Exception as e:
    print(f"   [FAIL] UserSerializer failed: {e}")
    import traceback
    traceback.print_exc()

# 2. Check Database Schema for 'phone'
print("\n2. Checking 'phone' column in DB...")
from django.db import connection
with connection.cursor() as cursor:
    cursor.execute("PRAGMA table_info(api_user_user);")
    columns = [row[1] for row in cursor.fetchall()]
    if 'phone' in columns:
        print("   [OK] Column 'phone' exists.")
    else:
        print("   [FAIL] Column 'phone' DOES NOT exist.")

# 3. Simulate Login View logic (simplified)
print("\n3. Simulating Login Logic...")
# We won't actually call the view, but we can check if we can create a token
if user:
    try:
        token, created = Token.objects.get_or_create(user=user)
        print(f"   [OK] Token retrieved/created: {token.key}")
    except Exception as e:
        print(f"   [FAIL] Token creation failed: {e}")
        import traceback
        traceback.print_exc()
