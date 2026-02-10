import os
import django
import sys

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from api.school.models import Subject

print(f"{'ID':<5} | {'Name':<30} | {'Archived (DB)':<15}")
print("-" * 60)

subjects = Subject.objects.all()
for s in subjects:
    print(f"{s.id:<5} | {s.name:<30} | {s.archived:<15}")
