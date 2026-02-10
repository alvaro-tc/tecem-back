import os
import sys
sys.path.append(os.getcwd())
import environ
env = environ.Env()
env.read_env(os.path.join(os.getcwd(), '.env'))
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()
email = 'admin@example.com'
password = 'admin'
if not User.objects.filter(email=email).exists():
    try:
        User.objects.create_superuser(email=email, password=password)
        print(f"Superuser '{email}' created with password '{password}'.")
    except Exception as e:
        print(f"Error creating superuser: {e}")
else:
    print(f"Superuser '{email}' already exists.")
