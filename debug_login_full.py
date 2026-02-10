
import os
import django
import sys
import jwt
from datetime import datetime, timedelta

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.conf import settings
from api.user.models import User
from api.authentication.models import ActiveSession

print("--- Debugging Login Full Logic ---")

def _generate_jwt_token(user):
    print("Generating token...")
    token = jwt.encode(
        {"id": user.pk, "exp": datetime.utcnow() + timedelta(days=7)},
        settings.SECRET_KEY,
        algorithm="HS256"
    )
    print(f"Token type: {type(token)}")
    if isinstance(token, bytes):
        token = token.decode('utf-8')
    return token

try:
    user = User.objects.first()
    if not user:
        print("No user found! Creating one...")
        user = User.objects.create_user(email="test@test.com", password="password123")
    
    print(f"User: {user.email}")
    
    # Simulate DB lookup
    try:
        session = ActiveSession.objects.get(user=user)
        print("Existing session found.")
        # Decode check
        jwt.decode(session.token, settings.SECRET_KEY, algorithms=["HS256"])
        print("Token valid.")
    except Exception as e:
        print(f"Session lookup/decode failed (expected if new/expired): {e}")
        # Create new
        print("Creating new session...")
        token = _generate_jwt_token(user)
        ActiveSession.objects.create(user=user, token=token)
        print("New session created.")

    print("[SUCCESS] Login logic simulation passed.")

except Exception as e:
    print(f"\n[FAIL] Exception: {e}")
    import traceback
    traceback.print_exc()
