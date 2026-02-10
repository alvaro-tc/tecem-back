
import os
import django
import sys

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from api.notifications.models import Notification
from api.user.models import User

print("--- Debugging Notifications ---")

try:
    user = User.objects.first()
    if not user:
        print("No user found")
        sys.exit()

    print(f"User: {user.email}")
    
    # Simulate get_queryset
    qs = Notification.objects.filter(recipient=user)
    print(f"Count: {qs.count()}")
    
    # Simulate update
    print("Attempting update...")
    qs.update(is_read=True)
    print("Update success!")

except Exception as e:
    print(f"[FAIL] Exception: {e}")
    import traceback
    traceback.print_exc()
