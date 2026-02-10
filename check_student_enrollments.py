import os
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.apps import apps
from django.contrib.auth import get_user_model

def check_enrollments():
    User = get_user_model()
    try:
        Enrollment = apps.get_model('school', 'Enrollment')
    except LookupError:
        print("Could not find app 'school', trying 'api.school' or listing apps...")
        for app in apps.get_app_configs():
            print(f"App: {app.name} Label: {app.label}")
        return

    # Find students with ANY enrollments first
    students_with_enrollments = User.objects.filter(role='STUDENT', enrollments__isnull=False).distinct()
    print(f"Found {students_with_enrollments.count()} students with enrollments.")

    if students_with_enrollments.count() == 0:
        print("No students found with enrollments. Checking all students...")
        all_students = User.objects.filter(role='STUDENT')
        print(f"Total students: {all_students.count()}")
        return

    for student in students_with_enrollments[:5]:
        print(f"\nChecking student: {student}")
        enrollments = Enrollment.objects.filter(student=student)
        print(f"  Total Enrollments: {enrollments.count()}")
        
        active_enrollments = enrollments.filter(course__active=True)
        print(f"  Active Course Enrollments: {active_enrollments.count()}")

        for enrollment in active_enrollments:
            course = enrollment.course
            print(f"    - Course: {course.subject.name} ({course.code}) | Active: {course.active} | Image: {course.image}")
            if not course.image:
                print("      WARNING: Course has no image!")

if __name__ == '__main__':
    check_enrollments()
