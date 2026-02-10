
import os
import django
import sys

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.db import connection
from api.school.models import Course, EvaluationTemplate
from api.school.serializers import CourseSerializer, EvaluationTemplateSerializer

def check_column_exists(table_name, column_name):
    with connection.cursor() as cursor:
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = [row[1] for row in cursor.fetchall()]
        if column_name in columns:
            print(f"[OK] Column '{column_name}' exists in table '{table_name}'.")
            return True
        else:
            print(f"[ERROR] Column '{column_name}' MISSING in table '{table_name}'.")
            return False

print("--- Database Schema Check ---")
check_column_exists('api_user_user', 'phone')
check_column_exists('api_school_course', 'parallel')

print("\n--- Testing Course Serializer ---")
try:
    courses = Course.objects.all()[:5]
    print(f"Found {len(courses)} courses.")
    serializer = CourseSerializer(courses, many=True)
    data = serializer.data
    print("[OK] CourseSerializer works.")
except Exception as e:
    print(f"[FAIL] CourseSerializer failed: {e}")
    import traceback
    traceback.print_exc()

print("\n--- Testing EvaluationTemplate Serializer ---")
try:
    templates = EvaluationTemplate.objects.all()[:5]
    print(f"Found {len(templates)} templates.")
    serializer = EvaluationTemplateSerializer(templates, many=True)
    data = serializer.data
    print("[OK] EvaluationTemplateSerializer works.")
except Exception as e:
    print(f"[FAIL] EvaluationTemplateSerializer failed: {e}")
    import traceback
    traceback.print_exc()
