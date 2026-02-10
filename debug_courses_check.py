
import os
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from api.school.models import Course
from api.school.serializers import CourseSerializer
import json

try:
    courses = Course.objects.all()
    print(f"Found {courses.count()} courses in DB.")
    
    serializer = CourseSerializer(courses, many=True)
    data = serializer.data
    
    if len(data) > 0:
        print("First course data keys:", data[0].keys())
        print("First course subject_details:", data[0].get('subject_details'))
    else:
        print("No serialized data.")

except Exception as e:
    print(f"Error: {e}")
