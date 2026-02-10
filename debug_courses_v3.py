import os
import django
import sys

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from api.school.models import Course

print(f"{'C_ID':<5} | {'Parallel':<10} | {'S_ID':<5} | {'S_Name':<20} | {'S_Arch':<10} | {'C_Active':<10}")
print("-" * 80)

for c in Course.objects.all():
    print(f"{c.id:<5} | {c.parallel:<10} | {c.subject.id:<5} | {c.subject.name:<20} | {str(c.subject.archived):<10} | {str(c.active):<10}")

print("\n--- Filtered View (active=True, subject__archived=False) ---")
filtered = Course.objects.filter(active=True, subject__archived=False)
print(f"Count: {filtered.count()}")
for c in filtered:
     print(f"Visible: {c.id} ({c.parallel}) - Subj: {c.subject.name}")

