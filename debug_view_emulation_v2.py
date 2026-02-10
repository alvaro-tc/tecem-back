import os
import django
import sys
from django.db import connection

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from api.school.models import Course

print("--- Data Check ---")
c1 = Course.objects.get(pk=1)
print(f"C1 Subj Arch (Python): {c1.subject.archived} (Type: {type(c1.subject.archived)})")

print("\n--- Filter Test (Current) ---")
q1 = Course.objects.filter(active=True, subject__archived=False)
print(f"Count: {q1.count()}")
print(f"Contains C1: {q1.filter(pk=1).exists()}")
# print(q1.query)

print("\n--- Exclude Test (Proposed) ---")
q2 = Course.objects.filter(active=True).exclude(subject__archived=True)
print(f"Count: {q2.count()}")
print(f"Contains C1: {q2.filter(pk=1).exists()}")

