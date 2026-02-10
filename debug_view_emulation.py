import os
import django
import sys

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from api.school.models import Course, Subject

print("--- Data Check ---")
# Courses 1 and 2
c1 = Course.objects.get(pk=1)
print(f"C1: {c1} | Active: {c1.active} | Subj: {c1.subject.name} | Subj Arch: {c1.subject.archived}")

# Emulate View Logic
print("\n--- View Logic Emulation ---")
queryset = Course.objects.all()
initial = queryset.count()
print(f"Initial: {initial}")

# Apply Active Filter
filtered = queryset.filter(active=True, subject__archived=False)
filtered_count = filtered.count()
print(f"Filtered (active=True, subj_arch=False): {filtered_count}")

print("IDs in Filtered:")
for c in filtered:
    print(f" - {c.id}: {c} (Subj Arch: {c.subject.archived})")

# Check if C1 is in Filtered
if c1 in filtered:
    print("ERROR: C1 is present in filtered list!")
else:
    print("SUCCESS: C1 is excluded.")
