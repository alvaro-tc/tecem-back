import os
import django
import sys

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from api.school.models import Course

print(f"{'Course ID':<10} | {'Paralelo':<20} | {'Course Active':<15} | {'Subject':<30} | {'Subject Archived':<20}")
print("-" * 110)

courses = Course.objects.all()
for c in courses:
    print(f"{c.id:<10} | {c.parallel:<20} | {str(c.active):<15} | {c.subject.name:<30} | {str(c.subject.archived):<20}")

print("\n")
print(f"Total Courses: {courses.count()}")
print(f"Active Courses (Active=True): {courses.filter(active=True).count()}")
print(f"Courses with Active Subjects (Subj.Achived=False): {courses.filter(subject__archived=False).count()}")
print(f"Visible by Default (Active=True AND Subj.Archived=False): {courses.filter(active=True, subject__archived=False).count()}")
