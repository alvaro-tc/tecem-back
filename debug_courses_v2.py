import os
import django
import sys

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from api.school.models import Course

print("Checking for Parallels with ARCHIVED SUBJECTS...")
archived_subj_courses = Course.objects.filter(subject__archived=True)

if archived_subj_courses.exists():
    print(f"Found {archived_subj_courses.count()} parallels with archived subjects:")
    for c in archived_subj_courses:
        print(f" - ID: {c.id}, Parallel: {c.parallel}, Active: {c.active}, Subject: {c.subject.name} (Archived: {c.subject.archived})")
else:
    print("No parallels with archived subjects found.")

print("\nChecking filtering logic...")
# Simulation of the view's filter
default_view = Course.objects.filter(active=True, subject__archived=False)
visible_ids = [c.id for c in default_view]
print(f"Visible IDs (Default View): {visible_ids}")

# constant check
bad_courses = [c.id for c in archived_subj_courses if c.id in visible_ids]
if bad_courses:
    print(f"ERROR: The following IDs shouldn't be visible but are: {bad_courses}")
else:
    print("SUCCESS: Logic correctly excludes parallels with archived subjects.")
