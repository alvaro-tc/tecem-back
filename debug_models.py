
import os
import django
import sys

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from api.user.models import User
print("User attributes:", dir(User))
try:
    print("User.objects:", User.objects)
except Exception as e:
    print("Error accessing User.objects:", e)
