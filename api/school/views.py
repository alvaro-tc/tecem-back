from rest_framework import viewsets, permissions, status, parsers
from rest_framework.decorators import action
from rest_framework.response import Response
from . import models
from . import serializers
from django.contrib.auth import get_user_model
from django.db.models import Exists, OuterRef
from django.utils import timezone

User = get_user_model()

class EvaluationTemplateViewSet(viewsets.ModelViewSet):
    queryset = models.EvaluationTemplate.objects.all()
    serializer_class = serializers.EvaluationTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]

class AcademicPeriodViewSet(viewsets.ModelViewSet):
    queryset = models.AcademicPeriod.objects.all()
    serializer_class = serializers.AcademicPeriodSerializer
    permission_classes = [permissions.IsAuthenticated]


class ProgramViewSet(viewsets.ModelViewSet):
    queryset = models.Program.objects.all()
    serializer_class = serializers.ProgramSerializer
    permission_classes = [permissions.IsAuthenticated]

class SubjectViewSet(viewsets.ModelViewSet):
    queryset = models.Subject.objects.all()
    serializer_class = serializers.SubjectSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        """
        Auto-archive subjects if their period has ended.
        """
        from datetime import date
        instance = serializer.save()
        
        # Check if period has ended and auto-archive if so
        if instance.period and instance.period.end_date < date.today():
            instance.archived = True
            instance.save()
            print(f"✅ Auto-archived subject: {instance.name} (period ended: {instance.period.end_date})")
        
        return instance


from decimal import Decimal

def recalculate_sub_criterion_scores(sub_criterion_id, enrollment_ids=None):
    """
    Recalculates the CriterionScore for a given sub-criterion.
    If enrollment_ids is None, recalculates for ALL enrollments in the course.
    Logic: (Sum(Score * Weight) / Sum(Weights)) * SubCrit.Percentage
    """
    try:
        sub_crit = models.CourseSubCriterion.objects.get(pk=sub_criterion_id)
        all_tasks = models.CourseTask.objects.filter(sub_criterion=sub_crit)
        total_weight = sum(t.weight for t in all_tasks)
        max_score = sub_crit.percentage  # Already Decimal

        target_enrollments = []
        if enrollment_ids:
            target_enrollments = models.Enrollment.objects.filter(id__in=enrollment_ids)
        else:
            # Get all active enrollments for the course
            target_enrollments = models.Enrollment.objects.filter(course=sub_crit.course)

        if total_weight > 0:
            for enroll in target_enrollments:
                # Calculate weighted average
                student_scores = models.TaskScore.objects.filter(enrollment=enroll, task__in=all_tasks)
                score_sum = Decimal('0.00')
                for s in student_scores:
                    score_sum += (s.score * s.task.weight)
                
                # Normalized average (0.0 to 1.0)
                # Ensure total_weight is Decimal
                normalized_avg = score_sum / Decimal(total_weight)
                
                # Final score scaled to Max Points (Direct Points)
                # normalized_avg is 0.0 to 1.0
                final_score = normalized_avg * sub_crit.percentage
                
                models.CriterionScore.objects.update_or_create(
                    enrollment=enroll,
                    sub_criterion=sub_crit,
                    defaults={'score': final_score}
                )
                
                # Update final grade for this student
                update_final_grade(enroll.id)
        else:
            # If total_weight is 0 (no tasks or all 0), maybe set score to 0?
            # For now, leaving as is or setting to 0 depending on logic.
            pass

    except Exception as e:
        print(f"Error recalculating averages: {e}")


class CourseViewSet(viewsets.ModelViewSet):
    queryset = models.Course.objects.all()
    serializer_class = serializers.CourseSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = (parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser)

    def perform_create(self, serializer):
        """
        Ensure courses are created as active by default.
        Archived status is inherited from the subject and should be controlled manually.
        """
        # Save with active=True explicitly to ensure course appears in list
        instance = serializer.save(active=True)
        print(f"✅ Created course: {instance.id}, active={instance.active}, subject_archived={instance.subject.archived if instance.subject else 'N/A'}")
        return instance

    def perform_update(self, serializer):
        print("=" * 80)
        print("CourseViewSet.perform_update called")
        print(f"Request data keys: {list(self.request.data.keys())}")
        print(f"Request FILES: {self.request.FILES}")
        instance = serializer.save()
        if instance.image:
            print(f"Image field value: {instance.image}")
            print(f"Image path: {instance.image.path}")
            print(f"Image url: {instance.image.url}")
        else:
            print("No image in instance after save")
        print("=" * 80)
        return instance


    def get_queryset(self):
        # Auto-Close Registrations if expired
        try:
            now = timezone.now()
            # Find open courses where end date has passed
            expired_courses = models.Course.objects.filter(
                is_registration_open=True, 
                registration_end__isnull=False, 
                registration_end__lt=now
            )
            if expired_courses.exists():
                # Close them and clear the end date as requested
                expired_courses.update(is_registration_open=False, registration_end=None)
        except Exception as e:
            print(f"Error auto-closing courses: {e}")

        user = self.request.user
        queryset = models.Course.objects.all()

        # Apply role-based filtering first
        if user.role == 'TEACHER':
            queryset = queryset.filter(teacher=user)
        elif user.role == 'STUDENT':
            queryset = queryset.filter(enrollments__student=user)
        elif user.role == 'PARENT':
            queryset = queryset.filter(enrollments__student__parent_relationships__parent=user).distinct()
        
        # Apply filters
        subject_id = self.request.query_params.get('subject')
        if subject_id:
            queryset = queryset.filter(subject_id=subject_id)

        period_id = self.request.query_params.get('period')
        if period_id:
            queryset = queryset.filter(period_id=period_id)

        show_archived = self.request.query_params.get('show_archived')
        
        if str(show_archived).lower() == 'true':
             pass
        else:
            # Default behavior: Show only active courses AND active subjects
            # We use exclude(subject__archived=True) to be explicit
            queryset = queryset.filter(active=True).exclude(subject__archived=True)

        return queryset

    @action(detail=True, methods=['get'])
    def preference(self, request, pk=None):
        """Get user preference for this course (last viewed tab)."""
        try:
            course = self.get_object()
            pref, created = models.CoursePreference.objects.get_or_create(user=request.user, course=course)
            return Response({'last_viewed_tab': pref.last_viewed_tab})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def set_preference(self, request, pk=None):
        """Set user preference for this course."""
        try:
            course = self.get_object()
            last_viewed_tab = request.data.get('last_viewed_tab')
            
            pref, created = models.CoursePreference.objects.get_or_create(user=request.user, course=course)
            pref.last_viewed_tab = last_viewed_tab
            pref.save()
            
            return Response({'status': 'success', 'last_viewed_tab': last_viewed_tab})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class EnrollmentViewSet(viewsets.ModelViewSet):
    queryset = models.Enrollment.objects.all()
    serializer_class = serializers.EnrollmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = models.Enrollment.objects.all()
        user = self.request.user
        
        if user.role == 'STUDENT':
            queryset = queryset.filter(student=user)
        elif user.role == 'PARENT':
            queryset = queryset.filter(student__parent_relationships__parent=user)
        
        # Allow filtering by course for admin/teachers
        course_id = self.request.query_params.get('course')
        if course_id:
            queryset = queryset.filter(course_id=course_id)
            
        return queryset.order_by('student__paternal_surname', 'student__maternal_surname', 'student__first_name')

    @action(detail=False, methods=['post'])
    def preview_bulk_upload(self, request):
        """
        Preview a CSV or Excel file upload. Returns found and not found students.
        Now uses robust parsing to extract full student details for creation.
        """
        file = request.FILES.get('file')
        if not file:
            return Response({"error": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST)

        students_found = [] # List of full student objects found in file
        
        try:
            filename = file.name.lower()
            if filename.endswith('.csv'):
                import csv
                import io
                decoded_file = file.read().decode('utf-8')
                io_string = io.StringIO(decoded_file)
                # Read header
                lines = io_string.readlines()
                if not lines: return Response({"error": "Empty file"}, status=status.HTTP_400_BAD_REQUEST)
                
                delimiter = ';' if ';' in lines[0] and lines[0].count(';') > lines[0].count(',') else ','
                headers = [h.strip().lower() for h in lines[0].split(delimiter)]
                rows = [l.split(delimiter) for l in lines[1:]]
            
            elif filename.endswith('.xlsx'):
                import openpyxl
                wb = openpyxl.load_workbook(file, data_only=True)
                sheet = wb.active
                # Scan first 50 rows for header
                header_row_idx = 0
                headers = []
                found_header = False
                import re
                
                target_headers = [
                    'ci', 'carnet', 'cedula', 'documento', 'c.i.', 'c.i', 'ci_number',
                    'paterno', 'apellido paterno', 'apellido_paterno', 'apellido 1',
                    'nombre', 'nombres', 'nombre completo', 'nombres y apellidos', 'estudiante', 'apellidos y nombres'
                ]
                
                rows_iter = list(sheet.iter_rows(values_only=True))
                for i, row in enumerate(rows_iter[:50]):
                   # Normalize headers
                   row_strs = [re.sub(r'\s+', ' ', str(c).strip().lower()) if c else '' for c in row]
                   if any(h in row_strs for h in target_headers):
                       headers = row_strs
                       header_row_idx = i
                       found_header = True
                       break
                
                if not found_header:
                    return Response({"error": "Could not find valid headers (CI, Paterno, Nombres)"}, status=status.HTTP_400_BAD_REQUEST)

                rows = rows_iter[header_row_idx+1:]
            
            else:
                 return Response({"error": "Unsupported file format"}, status=status.HTTP_400_BAD_REQUEST)

            # Map headers
            col_map = {}
            for idx, h in enumerate(headers):
                if h in ['ci', 'carnet', 'cedula', 'ci_number', 'documento', 'c.i.', 'c.i']: col_map['ci'] = idx
                elif h in ['paterno', 'apellido paterno', 'apellido_paterno', 'apellido 1']: col_map['paterno'] = idx
                elif h in ['materno', 'apellido materno', 'apellido_materno', 'apellido 2']: col_map['materno'] = idx
                elif h in ['nombre', 'nombres', 'nombre completo', 'nombres y apellidos', 'estudiante', 'apellidos y nombres']: col_map['full_name'] = idx
                elif h in ['email', 'correo', 'correo electronico']: col_map['email'] = idx
                elif h in ['celular', 'telefono', 'phone', 'cel']: col_map['phone'] = idx

            # Fallback
            for idx, h in enumerate(headers):
                 if h == 'nombres': col_map['nombres_only'] = idx

            if 'ci' not in col_map:
                 return Response({"error": f"Missing CI column. Found: {headers}"}, status=status.HTTP_400_BAD_REQUEST)

            seen_cis = set()
            import re

            for row in rows:
                if not row: continue
                # Handle list from CSV or tuple from Excel
                row_vals = [str(c).strip() if c is not None else '' for c in row]
                
                if len(row_vals) <= max(col_map.values()): continue # skip short rows

                raw_ci = row_vals[col_map['ci']]
                # Clean CI: keep only digits
                ci = re.sub(r'\D', '', raw_ci)

                if not ci: continue
                
                if ci in seen_cis: continue
                seen_cis.add(ci)
                
                email = row_vals[col_map['email']] if 'email' in col_map else ''
                phone = row_vals[col_map['phone']] if 'phone' in col_map else ''
                
                p_surname = row_vals[col_map['paterno']] if 'paterno' in col_map else ''
                m_surname = row_vals[col_map['materno']] if 'materno' in col_map else ''
                first_name = row_vals[col_map['nombres_only']] if 'nombres_only' in col_map else ''

                # Logic for Full Name parsing
                if 'full_name' in col_map and (not p_surname or not first_name):
                    full_name_str = row_vals[col_map['full_name']]
                    parts = full_name_str.split()
                    if len(parts) >= 3:
                         # "RIVERA CHAVEZ JUAN" -> Paterno: Rivera, Materno: Chavez, Nombre: Juan
                         p_surname = parts[0]
                         m_surname = parts[1]
                         first_name = " ".join(parts[2:])
                    elif len(parts) == 2:
                         # "RIVERA JUAN" -> Paterno: Rivera, Nombre: Juan
                         p_surname = parts[0]
                         first_name = parts[1]
                    elif len(parts) == 1:
                         p_surname = parts[0]
                    
                    if p_surname: p_surname = p_surname.title()
                    if m_surname: m_surname = m_surname.title()
                    if first_name: first_name = first_name.title()

                student_data = {
                    'ci_number': ci,
                    'paternal_surname': p_surname,
                    'maternal_surname': m_surname,
                    'first_name': first_name,
                    'email': email,
                    'phone': phone
                }
                
                students_found.append(student_data)

        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({"error": f"Error parsing file: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

        # Split into Existing vs New
        found_cis = [s['ci_number'] for s in students_found]
        existing_users_qs = User.objects.filter(ci_number__in=found_cis, role='STUDENT')
        
        # Create map of existing users
        existing_map = {u.ci_number: u for u in existing_users_qs}
        
        course_id = request.data.get('course_id')
        enrolled_student_ids = set()
        if course_id:
             enrolled_student_ids = set(models.Enrollment.objects.filter(course_id=course_id, student__in=existing_users_qs).values_list('student_id', flat=True))

        found_response = []
        to_create_response = []

        for s in students_found:
            ci = s['ci_number']
            if ci in existing_map:
                user = existing_map[ci]
                found_response.append({
                    'id': user.id,
                    'ci_number': user.ci_number,
                    'first_name': user.first_name,
                    'paternal_surname': user.paternal_surname,
                    'maternal_surname': user.maternal_surname,
                    'email': user.email,
                    'is_enrolled': user.id in enrolled_student_ids
                })
            else:
                # New student to create
                to_create_response.append(s)

        return Response({
            "found": found_response,
            "to_create": to_create_response
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def confirm_bulk_enrollment(self, request):
        """
        Enroll a list of student IDs into a course.
        Also creates new students if provided in 'students_to_create' list.
        """
        student_ids = request.data.get('student_ids', [])
        students_to_create = request.data.get('students_to_create', [])
        course_id = request.data.get('course_id')

        if not course_id:
            return Response({"error": "Course ID is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            course = models.Course.objects.get(id=course_id)
        except models.Course.DoesNotExist:
            return Response({"error": "Course not found"}, status=status.HTTP_404_NOT_FOUND)

        created_users_count = 0
        
        # 1. Create new students
        for s_data in students_to_create:
            ci = s_data.get('ci_number')
            if not ci: continue
            
            # Check if already exists (double check)
            if User.objects.filter(ci_number=ci).exists():
                user = User.objects.get(ci_number=ci)
                student_ids.append(user.id)
                continue
            
            try:
                # Use manager create_user
                email = s_data.get('email') or None
                # Check email conflict
                if email and User.objects.filter(email=email).exists():
                     email = None # Unset email if conflict, prioritize creation
                
                new_user = User.objects.create_user(
                    email=email,
                    password=ci, # Default password is CI
                    role='STUDENT',
                    ci_number=ci,
                    first_name=s_data.get('first_name', ''),
                    paternal_surname=s_data.get('paternal_surname', ''),
                    maternal_surname=s_data.get('maternal_surname', ''),
                    phone=s_data.get('phone', '')
                )
                student_ids.append(new_user.id)
                created_users_count += 1
            except Exception as e:
                print(f"Error creating user {ci}: {e}")

        # 2. Enroll all
        enrolled_count = 0
        student_ids = list(set(student_ids)) # Unique
        
        for student_id in student_ids:
            try:
                student = User.objects.get(id=student_id)
                _, created = models.Enrollment.objects.get_or_create(student=student, course=course)
                if created:
                    enrolled_count += 1
            except User.DoesNotExist:
                continue

        return Response({
            "status": "success", 
            "enrolled_count": enrolled_count,
            "created_users_count": created_users_count
        }, status=status.HTTP_200_OK)

class FamilyRelationshipViewSet(viewsets.ModelViewSet):
    queryset = models.FamilyRelationship.objects.all()
    serializer_class = serializers.FamilyRelationshipSerializer
    permission_classes = [permissions.IsAuthenticated]

class MainEvaluationViewSet(viewsets.ModelViewSet):
    queryset = models.MainEvaluation.objects.all()
    serializer_class = serializers.MainEvaluationSerializer
    permission_classes = [permissions.IsAuthenticated]

class SubEvaluationViewSet(viewsets.ModelViewSet):
    queryset = models.SubEvaluation.objects.all()
    serializer_class = serializers.SubEvaluationSerializer
    permission_classes = [permissions.IsAuthenticated]

class ScoreViewSet(viewsets.ModelViewSet):
    queryset = models.Score.objects.all()
    serializer_class = serializers.ScoreSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['post'])
    def bulk_update(self, request):
        """
        Expects a list of scores:
        [{ "enrollment": 1, "sub_evaluation": 2, "value": 100 }, ...]
        """
        data = request.data
        if not isinstance(data, list):
            return Response({"error": "Expected a list of scores"}, status=status.HTTP_400_BAD_REQUEST)
        
        updated_scores = []
        for item in data:
            enrollment_id = item.get('enrollment')
            sub_eval_id = item.get('sub_evaluation')
            value = item.get('value')
            
            score, created = models.Score.objects.update_or_create(
                enrollment_id=enrollment_id,
                sub_evaluation_id=sub_eval_id,
                defaults={'value': value}
            )
            updated_scores.append(score)
        
        return Response({"status": "Scores updated"}, status=status.HTTP_200_OK)

class ReportViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'])
    def dashboard_stats(self, request):
        from api.publications.models import Publication
        from django.db.models.functions import TruncMonth
        from django.db.models import Count, Avg, Sum
        from django.utils import timezone
        from datetime import timedelta

        user = request.user
        data = {'role': user.role}
        today = timezone.now().date()

        if user.role == 'ADMIN':
            # Card Counters
            data['card1'] = {'title': 'Total Estudiantes', 'count': User.objects.filter(role='STUDENT').count()}
            data['card2'] = {'title': 'Total Docentes', 'count': User.objects.filter(role='TEACHER').count()}
            data['card3'] = {'title': 'Cursos Activos', 'count': models.Course.objects.filter(active=True).count()}
            data['card4'] = {'title': 'Publicaciones', 'count': Publication.objects.count()}
            
            # Enrollment Growth (Last 12 months)
            last_year = today - timedelta(days=365)
            enrollments = models.Enrollment.objects.filter(date_enrolled__gte=last_year)
            
            monthly_counts = enrollments.annotate(
                month=TruncMonth('date_enrolled')
            ).values('month').annotate(
                count=Count('id')
            ).order_by('month')
            
            chart_data = []
            for entry in monthly_counts:
                chart_data.append({
                    'month': entry['month'].strftime('%b'),
                    'count': entry['count']
                })
            
            data['chart_data'] = chart_data
            data['chart_title'] = "Crecimiento de Inscripciones"

            # Popular Courses (Top 5)
            popular_courses = models.Course.objects.filter(active=True).annotate(
                student_count=Count('enrollments')
            ).order_by('-student_count')[:5]
            
            data['popular_data'] = [
                {
                    'name': course.subject.name,
                    'count': course.student_count,
                    'period': course.period.name,
                    'schedule': course.schedule
                } for course in popular_courses
            ]
            data['popular_title'] = "Cursos Populares"

        elif user.role == 'TEACHER':

            my_courses = models.Course.objects.filter(teacher=user, active=True)
            data['card1'] = {'title': 'Mis Cursos', 'count': my_courses.count()}
            data['card2'] = {'title': 'Mis Estudiantes', 'count': models.Enrollment.objects.filter(course__in=my_courses).values('student').distinct().count()}
            data['card3'] = {'title': 'Tareas Creadas', 'count': models.CourseTask.objects.filter(sub_criterion__course__in=my_courses).count()}
            data['card4'] = {'title': 'Proyectos', 'count': models.Project.objects.filter(course__in=my_courses).count()}

            # Enrollment Growth for Teacher's courses
            last_year = today - timedelta(days=365)
            enrollments = models.Enrollment.objects.filter(course__in=my_courses, date_enrolled__gte=last_year)
            
            monthly_counts = enrollments.annotate(
                month=TruncMonth('date_enrolled')
            ).values('month').annotate(
                count=Count('id')
            ).order_by('month')
            
            chart_data = []
            for entry in monthly_counts:
                chart_data.append({
                    'month': entry['month'].strftime('%b'),
                    'count': entry['count']
                })
            data['chart_data'] = chart_data
            data['chart_title'] = "Inscripciones en mis cursos"

            # Top Performing Students
            top_students = models.Enrollment.objects.filter(course__in=my_courses).exclude(final_grade__isnull=True).order_by('-final_grade')[:5]

            data['popular_data'] = [
                {
                    'name': f"{enrollment.student.first_name} {enrollment.student.paternal_surname}",
                    'count': enrollment.final_grade,
                    'period': enrollment.course.subject.name
                } for enrollment in top_students
            ]
            data['popular_title'] = "Mejores Estudiantes"

        elif user.role == 'STUDENT':

            my_enrollments = models.Enrollment.objects.filter(student=user)
            data['card1'] = {'title': 'Cursos Inscritos', 'count': my_enrollments.count()}
            data['card2'] = {'title': 'Tareas Completadas', 'count': models.TaskScore.objects.filter(enrollment__in=my_enrollments).count()}
            
            # Calculate Average Grade
            avg_grade = my_enrollments.aggregate(Avg('final_grade'))['final_grade__avg']
            data['card3'] = {'title': 'Promedio General', 'count': round(avg_grade, 2) if avg_grade else 0}
            
            data['card4'] = {'title': 'Proyectos', 'count': models.Project.objects.filter(members__student=user).count()}

            # Grades per Course Chart
            chart_data = []
            for enrollment in my_enrollments:
                if enrollment.final_grade is not None:
                     chart_data.append({
                        'month': enrollment.course.subject.code, # Using code as label for brevity
                        'count': enrollment.final_grade
                    })
            data['chart_data'] = chart_data
            data['chart_title'] = "Mis Calificaciones"

            # My Courses List (All enrolled courses with images)
            data['enrolled_courses'] = []
            
            # Filter by active courses to match Header logic
            # Also ensures we don't crash on weird data
            active_enrollments = my_enrollments.filter(course__active=True).select_related('course', 'course__subject', 'course__teacher', 'course__period')
            
            print(f"Dashboard Stats: Found {active_enrollments.count()} active enrollments for user {user.email}")

            for enrollment in active_enrollments:
                try:
                    course = enrollment.course
                    image_url = None
                    if course.image:
                        image_url = request.build_absolute_uri(course.image.url)
                    

                    # Calculate Criteria Grades (Hierarchical) - Aligned with Gradesheet
                    criteria_grades = []
                    
                    # Fetch all sub-criteria for the course, grouped by parent
                    sub_criteria = models.CourseSubCriterion.objects.filter(course=course).select_related('parent_criterion').annotate(
                        has_tasks=Exists(models.CourseTask.objects.filter(sub_criterion=OuterRef('pk'))),
                        has_projects=Exists(models.Project.objects.filter(sub_criterion=OuterRef('pk')))
                    ).order_by('parent_criterion__id', 'id')

                    # Group by Parent Criterion
                    grouped_criteria = {}
                    
                    # 1. Process Standard Sub-Criteria
                    for sub in sub_criteria:
                        parent = sub.parent_criterion
                        if not parent:
                            continue
                        
                        if parent.id not in grouped_criteria:
                            grouped_criteria[parent.id] = {
                                'name': parent.name,
                                'max_points': parent.weight, # Cap limit
                                'sum_max_points': 0, # Sum of children max points (for display if needed)
                                'score': 0,
                                'raw_score': 0, # Uncapped sum
                                'sub_criteria': [],
                                'is_special': False
                            }
                        
                        sub_tasks_list = []
                        if sub.has_tasks:
                             tasks = models.CourseTask.objects.filter(sub_criterion=sub)
                             task_scores = models.TaskScore.objects.filter(
                                 enrollment=enrollment,
                                 task__sub_criterion=sub
                             )
                             score_map_tasks = {ts.task_id: ts.score for ts in task_scores}
                             for task in tasks:
                                 score_val = score_map_tasks.get(task.id, 0)
                                 sub_tasks_list.append({
                                     'name': task.name,
                                     'weight': float(task.weight),
                                     'score': float(score_val)
                                 })
                        
                        # Get Score
                        sub_score = 0
                        
                        # Check if it's a Project Sub-Criterion
                        if sub.is_project:
                            # Find project where student is a member
                            project = models.Project.objects.filter(
                                sub_criterion=sub,
                                members=enrollment
                            ).first()
                            
                            if project:
                                sub_score = project.score
                            else:
                                sub_score = 0
                        else:
                            # Standard CriterionScore
                            score_obj = models.CriterionScore.objects.filter(
                                enrollment=enrollment,
                                sub_criterion=sub
                            ).first()
                            sub_score = score_obj.score if score_obj else 0
                        
                        sub_max = sub.percentage

                        grouped_criteria[parent.id]['sub_criteria'].append({
                            'name': sub.name,
                            'max_points': sub_max,
                            'score': sub_score,
                            'is_special': False,
                            'tasks': sub_tasks_list
                        })
                        grouped_criteria[parent.id]['sum_max_points'] += sub_max
                        grouped_criteria[parent.id]['raw_score'] += sub_score

                    # 2. Process Special Criteria (Extra Points) - Grouped under Parent
                    special_criteria = models.CourseSpecialCriterion.objects.filter(course=course).select_related('parent_criterion').annotate(
                        has_tasks=Exists(models.CourseTask.objects.filter(special_criterion=OuterRef('pk')))
                    ).order_by('id')

                    for spec in special_criteria:
                        final_score = 0
                        sub_tasks_list = []
                        
                        # Logic from gradesheet: Calculate from tasks if has_tasks
                        if spec.has_tasks:
                             tasks = models.CourseTask.objects.filter(special_criterion=spec)
                             task_scores = models.TaskScore.objects.filter(
                                 enrollment=enrollment,
                                 task__special_criterion=spec
                             )
                             score_map_tasks = {ts.task_id: ts.score for ts in task_scores}
                             
                             total_weight = 0
                             weighted_sum = 0
                             
                             for task in tasks:
                                 score_val = score_map_tasks.get(task.id, 0)
                                 sub_tasks_list.append({
                                     'name': task.name,
                                     'weight': float(task.weight),
                                     'score': float(score_val)
                                 })
                                 weighted_sum += score_val * task.weight
                                 total_weight += task.weight
                             
                             if total_weight > 0:
                                 # raw_avg is Decimal
                                 raw_avg = weighted_sum / total_weight
                                 # Ensure spec.percentage is Decimal
                                 final_score = raw_avg * spec.percentage
                             else:
                                 final_score = Decimal('0.00')
                        else:
                            # Direct Score from SpecialCriterionScore
                            score_obj = models.SpecialCriterionScore.objects.filter(
                                enrollment=enrollment,
                                special_criterion=spec
                            ).first()
                            final_score = score_obj.score if score_obj else Decimal('0.00')
                        
                        # Add to Parent Group if exists
                        parent = spec.parent_criterion
                        if parent and parent.id in grouped_criteria:
                             grouped_criteria[parent.id]['sub_criteria'].append({
                                'name': f"{spec.name} (Extra)",
                                'max_points': spec.percentage,
                                'score': final_score,
                                'is_special': True,
                                'tasks': sub_tasks_list
                            })
                             # Ensure raw_score is treated as Decimal (it starts as int 0? no, dependent on previous adds)
                             # Let's verify initialization
                             grouped_criteria[parent.id]['raw_score'] += final_score
                             # We rarely add special points to sum_max_points as they are "extra", but strictly speaking user didn't specify. 
                             # Usually extra points don't increase the denominator, only the numerator.
                        else:
                            # Fallback for orphaned special criteria (shouldn't happen with correct data)
                            criteria_grades.append({
                                'name': spec.name,
                                'max_points': spec.percentage,
                                'score': final_score,
                                'sub_criteria': [],
                                'is_special': True,
                                'tasks': sub_tasks_list
                            })

                    # 3. Finalize Groups and Apply Caps
                    for pid, group in grouped_criteria.items():
                        # Capping logic: Min(Raw Sum, Criterion Weight)
                        # Ensure we convert to float for comparison
                        limit = float(group['max_points'])
                        raw = float(group['raw_score'])
                        
                        final_group_score = min(raw, limit)
                        group['score'] = final_group_score
                        
                        criteria_grades.append(group)

                    data['enrolled_courses'].append({
                        'id': course.id,
                        'name': course.subject.name,
                        'code': course.subject.code,
                        'parallel': course.parallel,
                        'period': course.period.name,
                        'teacher': course.teacher.get_full_name() if course.teacher else "Sin Docente",
                        'image': image_url,
                        'grade': enrollment.final_grade,
                        'schedule': course.schedule,
                        'whatsapp_link': course.whatsapp_link,
                        'criteria_grades': criteria_grades
                    })
                except Exception as e:
                    print(f"Error processing enrollment {enrollment.id}: {e}")

            data['popular_data'] = [
                {
                    'name': enrollment.course.subject.name,
                    'count': enrollment.final_grade if enrollment.final_grade else "N/A",
                    'period': enrollment.course.teacher.get_full_name() if enrollment.course.teacher else "Sin Docente",
                    'schedule': enrollment.course.schedule
                } for enrollment in active_enrollments[:5]
            ]
            data['popular_title'] = "Mis Cursos"

        return Response(data)

class CourseSubCriterionViewSet(viewsets.ModelViewSet):
    queryset = models.CourseSubCriterion.objects.all()
    serializer_class = serializers.CourseSubCriterionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        course_id = self.request.query_params.get('course')
        if course_id:
            queryset = queryset.filter(course_id=course_id)
        return queryset

    def perform_create(self, serializer):
        course = serializer.validated_data['course']

        serializer.save()

    def perform_update(self, serializer):
        instance = serializer.instance

        
        # Check if is_project is being turned off
        new_is_project = serializer.validated_data.get('is_project')
        if new_is_project is False and instance.is_project:
            # Delete all related projects
            models.Project.objects.filter(sub_criterion=instance).delete()
            
        serializer.save()

    def perform_destroy(self, instance):

        instance.delete()

    @action(detail=False, methods=['post'])
    def bulk_update_settings(self, request):
        """
        Update visible/editable settings for a list of sub-criteria.
        Expects: { "updates": [ {"id": 1, "visible": true, "editable": false}, ... ] }
        """
        print("DEBUG: bulk_update_settings called")
        print(f"DEBUG: Data received: {request.data}")
        updates = request.data.get('updates', [])
        saved = 0
        for u in updates:
            crit_id = u.get('id')
            visible = u.get('visible')
            editable = u.get('editable')
            
            try:
                crit = models.CourseSubCriterion.objects.get(id=crit_id)
                if visible is not None: crit.visible_on_gradesheet = visible
                if editable is not None: crit.editable_on_gradesheet = editable
                crit.save()
                saved += 1
            except models.CourseSubCriterion.DoesNotExist:
                print(f"DEBUG: Criterion {crit_id} not found")
                continue
        
        print(f"DEBUG: Saved {saved} updates")
        return Response({"saved": saved})

class CourseSpecialCriterionViewSet(viewsets.ModelViewSet):
    queryset = models.CourseSpecialCriterion.objects.all()
    serializer_class = serializers.CourseSpecialCriterionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = models.CourseSpecialCriterion.objects.all()
        course_id = self.request.query_params.get('course', None)
        if course_id is not None:
            queryset = queryset.filter(course_id=course_id)
        return queryset

    def perform_create(self, serializer):
        course = serializer.validated_data['course']

        serializer.save()

    def perform_update(self, serializer):
        instance = self.get_object()

        serializer.save()

    def perform_destroy(self, instance):

        instance.delete()
    
    @action(detail=False, methods=['post'])
    def bulk_update_settings(self, request):
        """Update visibility and editability for multiple special criteria."""
        updates = request.data.get('updates', [])
        for update in updates:
            # Extract special- prefix from id if present
            spec_id = update.get('id', '')
            if isinstance(spec_id, str) and spec_id.startswith('special-'):
                spec_id = spec_id.replace('special-', '')
            
            try:
                spec = models.CourseSpecialCriterion.objects.get(id=spec_id)
                spec.visible_on_gradesheet = update.get('visible', spec.visible_on_gradesheet)
                spec.editable_on_gradesheet = update.get('editable', spec.editable_on_gradesheet)
                spec.save()
            except models.CourseSpecialCriterion.DoesNotExist:
                pass
        
        return Response({'status': 'success'})

class CriterionScoreViewSet(viewsets.ModelViewSet):
    queryset = models.CriterionScore.objects.all()
    serializer_class = serializers.CriterionScoreSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'])
    def gradesheet(self, request):
        course_id = request.query_params.get('course_id')
        if not course_id:
            return Response({"error": "Course ID required"}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Fetch Columns (SubCriteria) grouped by Parent
        # We need the parent criterion info
        sub_criteria = models.CourseSubCriterion.objects.filter(course_id=course_id).select_related('parent_criterion').annotate(
            has_tasks=Exists(models.CourseTask.objects.filter(sub_criterion=OuterRef('pk'))),
            has_projects=Exists(models.Project.objects.filter(sub_criterion=OuterRef('pk')))
        ).order_by('parent_criterion__id', 'id')
        
        # Fetch special criteria as well
        special_criteria = models.CourseSpecialCriterion.objects.filter(course_id=course_id).select_related('parent_criterion').annotate(
            has_tasks=Exists(models.CourseTask.objects.filter(special_criterion=OuterRef('pk')))
        ).order_by('parent_criterion__id', 'id')
        
        structure = []
        current_parent_id = None
        current_group = None

        # Process regular sub_criteria
        for sc in sub_criteria:
            parent = sc.parent_criterion
            if parent.id != current_parent_id:
                if current_group:
                    structure.append(current_group)
                current_parent_id = parent.id
                current_group = {
                    "id": parent.id,
                    "name": parent.name,
                    "weight": parent.weight,
                    "sub_criteria": [],
                    "special_criteria": []
                }
            
            current_group["sub_criteria"].append({
                "id": sc.id,
                "name": sc.name,
                "percentage": sc.percentage,
                "visible": sc.visible_on_gradesheet,
                "editable": sc.editable_on_gradesheet,
                "has_tasks": sc.has_tasks,
                "has_projects": sc.has_projects,
                "is_special": False
            })
        
        if current_group:
            structure.append(current_group)
        
        # Add special criteria to their respective groups
        for spec in special_criteria:
            if not spec.parent_criterion:
                continue
            parent_id = spec.parent_criterion.id
            # Find the group in structure
            group = next((g for g in structure if g['id'] == parent_id), None)
            if not group:
                # Create group if it doesn't exist yet
                group = {
                    "id": parent_id,
                    "name": spec.parent_criterion.name,
                    "weight": spec.parent_criterion.weight,
                    "sub_criteria": [],
                    "special_criteria": []
                }
                structure.append(group)
            
            group["special_criteria"].append({
                "id": f"special-{spec.id}",
                "actual_id": spec.id,
                "name": spec.name,
                "percentage": spec.percentage,
                "visible": spec.visible_on_gradesheet,
                "editable": spec.editable_on_gradesheet,
                "has_tasks": spec.has_tasks,
                "has_projects": False,
                "is_special": True
            })

        # 2. Rows (Students)
        enrollments = models.Enrollment.objects.filter(course_id=course_id).select_related('student').order_by('student__paternal_surname', 'student__maternal_surname', 'student__first_name')
        
        # 3. Scores Data
        scores = models.CriterionScore.objects.filter(enrollment__course_id=course_id)
        special_scores = models.SpecialCriterionScore.objects.filter(enrollment__course_id=course_id)
        
        score_map = {} # (enrollment_id, criterion_id_str) -> score
        for s in scores:
            score_map[(s.enrollment_id, str(s.sub_criterion_id))] = s.score
        for s in special_scores:
            score_map[(s.enrollment_id, f"special-{s.special_criterion_id}")] = s.score

        rows = []
        for enr in enrollments:
            student_grades = {}
            # Flatten subcriteria IDs for easy lookup
            for struct in structure:
                for sub in struct['sub_criteria']:
                    # Regular sub-criteria use ID as key
                    val = score_map.get((enr.id, str(sub['id'])))
                    if val is not None:
                         student_grades[sub['id']] = val
                
                # Special criteria
                for spec in struct['special_criteria']:
                    spec_key = spec['id'] # "special-{id}"
                    
                    # If it has tasks, calculate from tasks
                    if spec.get('has_tasks'):
                        # Calculate weighted average of tasks for this special criterion
                        tasks = models.CourseTask.objects.filter(special_criterion_id=spec['actual_id'])
                        task_scores = models.TaskScore.objects.filter(
                            enrollment_id=enr.id,
                            task__special_criterion_id=spec['actual_id']
                        )
                        
                        total_weight = 0
                        weighted_sum = 0
                        score_map_tasks = {ts.task_id: ts.score for ts in task_scores}
                        
                        for task in tasks:
                            score_val = score_map_tasks.get(task.id, 0)
                            weighted_sum += score_val * task.weight
                            total_weight += task.weight
                        
                        if total_weight > 0:
                            raw_avg = weighted_sum / total_weight
                            # percentage is Decimal, raw_avg can be Decimal or float (if 0.0)
                            # Safe to convert both to float for calculation/serialization
                            final_score = float(raw_avg) * float(spec['percentage'])
                            student_grades[spec_key] = final_score
                    else:
                        # If no tasks, check for manual score
                        val = score_map.get((enr.id, spec_key))
                        if val is not None:
                            student_grades[spec_key] = val
            
            rows.append({
                "enrollment_id": enr.id,
                "student_id": enr.student.id,
                "ci": enr.student.ci_number,
                "paterno": enr.student.paternal_surname,
                "materno": enr.student.maternal_surname,
                "nombre": enr.student.first_name,
                "grades": student_grades
            })
            
        return Response({
            "structure": structure,
            "rows": rows
        })

    @action(detail=False, methods=['post'])
    def bulk_save(self, request):
        # Expects: { "updates": [ {"enrollment_id": 1, "criterion_id": 2, "score": 50}, ... ] }
        updates = request.data.get('updates', [])
        saved = 0
        for u in updates:
            try:
                criteria_id_raw = u.get('criterion_id')
                enrollment_id = u.get('enrollment_id')
                score_val = u.get('score')
                
                # Check if it is a special criterion
                if str(criteria_id_raw).startswith('special-'):
                    actual_id = int(str(criteria_id_raw).replace('special-', ''))
                    # Verify if special criterion exists first to avoid IntegrityError
                    if not models.CourseSpecialCriterion.objects.filter(id=actual_id).exists():
                         print(f"Skipping special criterion {actual_id} - Not Found")
                         continue

                    models.SpecialCriterionScore.objects.update_or_create(
                        enrollment_id=enrollment_id,
                        special_criterion_id=actual_id,
                        defaults={'score': score_val}
                    )
                else:
                    # Regular sub-criterion
                    models.CriterionScore.objects.update_or_create(
                        enrollment_id=enrollment_id,
                        sub_criterion_id=criteria_id_raw,
                        defaults={'score': score_val}
                    )
                saved += 1
            except Exception as e:
                print(f"Error in bulk_save loop item {u}: {e}")
                # Continue saving others? Or return error?
                # Reporting error for this item makes debugging easier
                return Response({"error": f"Error saving item: {e}"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Recalculate final grades for affect enrollments
        affected_enrollment_ids = set(u.get('enrollment_id') for u in updates)
        for enr_id in affected_enrollment_ids:
            try:
                update_final_grade(enr_id)
            except Exception as e:
                print(f"Error calling update_final_grade for {enr_id}: {e}")
                # We don't want to fail the save if recalc fails, but we should log it.

        return Response({"saved": saved})

def update_final_grade(enrollment_id):
    """
    Calculates and updates the final_grade for an enrollment based on Direct Points.
    Logic:
    For each EvaluationCriterion:
      Total = Sum(SubCriterionScores) + Sum(SpecialCriterionScores)
      CappedTotal = Min(Total, Criterion.Weight)
    FinalGrade = Sum(CappedTotal for all Criteria)
    """
    from django.db.models import Sum
    try:
        enrollment = models.Enrollment.objects.get(pk=enrollment_id)
        course = enrollment.course
        
        final_grade = 0.0
        
        # Iterate over all parent criteria
        # We need to fetch them from the evaluation template if possible, or just used ones?
        # Better: get all criteria associated with the course via Subject -> EvaluationTemplate
        if course.subject and course.subject.evaluation_template:
            criteria = course.subject.evaluation_template.criteria.all()
            
            for criterion in criteria:
                # 1. Sum Regular SubCriteria Scores for this parent
                # Filter scores where sub_criterion__parent_criterion == criterion
                regular_sum = models.CriterionScore.objects.filter(
                    enrollment=enrollment,
                    sub_criterion__parent_criterion=criterion
                ).aggregate(t=Sum('score'))['t'] or 0
                
                # 2. Sum Special Criteria Scores for this parent
                special_sum = models.SpecialCriterionScore.objects.filter(
                    enrollment=enrollment,
                    special_criterion__parent_criterion=criterion
                ).aggregate(t=Sum('score'))['t'] or 0
                
                total_criterion_score = float(regular_sum) + float(special_sum)
                
                # 3. Cap at Criterion Weight
                max_weight = float(criterion.weight)
                capped_score = min(total_criterion_score, max_weight)
                
                final_grade += capped_score
                
        else:
            # Fallback for legacy courses or weird Data?
            # Just sum everything as before, but we can't cap without parent info easily.
            print(f"Warning: Course {course.id} has no evaluation template. Summing all scores directly.")
            total_regular = models.CriterionScore.objects.filter(enrollment=enrollment).aggregate(t=Sum('score'))['t'] or 0
            total_special = models.SpecialCriterionScore.objects.filter(enrollment=enrollment).aggregate(t=Sum('score'))['t'] or 0
            final_grade = float(total_regular) + float(total_special)

        enrollment.final_grade = final_grade
        enrollment.save()
        
    except Exception as e:
        print(f"Error updating final grade for {enrollment_id}: {e}")

class CourseTaskViewSet(viewsets.ModelViewSet):
    queryset = models.CourseTask.objects.all()
    serializer_class = serializers.CourseTaskSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        sub_criteria_id = self.request.query_params.get('sub_criteria_id')
        if sub_criteria_id:
            qs = qs.filter(sub_criterion_id=sub_criteria_id)
        return qs

    def perform_create(self, serializer):
        task = serializer.save()
        # Lock the parent criterion if it's a regular sub-criterion
        if task.sub_criterion:
            sub_crit = task.sub_criterion
            sub_crit.editable_on_gradesheet = False
            sub_crit.save()
            recalculate_sub_criterion_scores(sub_crit.id)
        # Note: Special criteria don't need locking or recalculation in the same way

    def perform_update(self, serializer):
        task = serializer.save()
        if task.sub_criterion:
            recalculate_sub_criterion_scores(task.sub_criterion.id)

    def perform_destroy(self, instance):
        if instance.sub_criterion:
            sub_id = instance.sub_criterion.id
            instance.delete()
            recalculate_sub_criterion_scores(sub_id)
        else:
            instance.delete()

class TaskScoreViewSet(viewsets.ModelViewSet):
    queryset = models.TaskScore.objects.all()
    serializer_class = serializers.TaskScoreSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = models.TaskScore.objects.all()
        enrollment_id = self.request.query_params.get('enrollment_id', None)
        task_id = self.request.query_params.get('task_id', None)
        if enrollment_id is not None:
            queryset = queryset.filter(enrollment_id=enrollment_id)
        if task_id is not None:
            queryset = queryset.filter(task_id=task_id)
        return queryset

    @action(detail=False, methods=['post'])
    def bulk_save(self, request):
        try:
            scores = request.data.get('updates', request.data.get('scores', []))
            saved_scores = []
            
            affected_enrollments = set()
            affected_subcriteria = set()

            for score_data in scores:
                enrollment_id = score_data.get('enrollment_id')
                task_id = score_data.get('task_id')
                score_value = score_data.get('score')

                score_obj, created = models.TaskScore.objects.update_or_create(
                    enrollment_id=enrollment_id,
                    task_id=task_id,
                    defaults={'score': score_value}
                )
                saved_scores.append(score_obj)
                
                affected_enrollments.add(enrollment_id)
                try:
                    task = models.CourseTask.objects.get(id=task_id)
                    if task.sub_criterion:
                        affected_subcriteria.add(('sub', task.sub_criterion.id))
                    elif task.special_criterion:
                        affected_subcriteria.add(('special', task.special_criterion.id))
                except models.CourseTask.DoesNotExist:
                    pass

            for enroll_id in affected_enrollments:
                for crit_type, crit_id in affected_subcriteria:
                    if crit_type == 'sub':
                        tasks = models.CourseTask.objects.filter(sub_criterion_id=crit_id)
                        scores = models.TaskScore.objects.filter(enrollment_id=enroll_id, task__sub_criterion_id=crit_id)
                        
                        total_weight = 0
                        weighted_sum = 0
                        score_map = {s.task_id: s.score for s in scores}
                        
                        for task in tasks:
                            s_val = score_map.get(task.id, 0)
                            weighted_sum += s_val * task.weight
                            total_weight += task.weight
                        
                        if total_weight > 0:
                            raw_avg = weighted_sum / total_weight
                            sub_crit = models.CourseSubCriterion.objects.get(id=crit_id)
                            final_score = float(raw_avg) * float(sub_crit.percentage)
                            
                            # Update CriterionScore
                            models.CriterionScore.objects.update_or_create(
                                enrollment_id=enroll_id,
                                sub_criterion_id=crit_id,
                                defaults={'score': final_score}
                            )
                    elif crit_type == 'special':
                        pass

                # Update Final Grade
                try:
                    update_final_grade(enroll_id)
                except Exception as e:
                    print(f"Error updating final grade for {enroll_id}: {e}")

            return Response({'status': 'success', 'saved': len(saved_scores)})
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({'error': str(e), 'traceback': traceback.format_exc()}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    @action(detail=False, methods=['get'])
    def task_sheet(self, request):
        try:
            course_id = request.query_params.get('course_id')
            sub_criterion_id = request.query_params.get('sub_criterion_id')
            
            if not course_id or not sub_criterion_id:
                return Response({'error': 'Missing course_id or sub_criterion_id'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Parse whether it's a special criterion or regular
            is_special = str(sub_criterion_id).startswith('special-')
            if is_special:
                actual_id = sub_criterion_id.replace('special-', '')
                tasks = models.CourseTask.objects.filter(special_criterion_id=actual_id).order_by('id')
            else:
                tasks = models.CourseTask.objects.filter(sub_criterion_id=sub_criterion_id).order_by('id')
            
            enrollments = models.Enrollment.objects.filter(course_id=course_id).select_related('student').order_by('student__paternal_surname', 'student__maternal_surname', 'student__first_name')
            
            rows = []
            for enrollment in enrollments:
                student = enrollment.student
                scores = models.TaskScore.objects.filter(enrollment=enrollment, task__in=tasks)
                score_map = {score.task_id: score.score for score in scores}
                
                rows.append({
                    'enrollment_id': enrollment.id,
                    'nombre': student.first_name,
                    'paterno': student.paternal_surname,
                    'materno': student.maternal_surname,
                    'ci': student.ci_number,
                    'scores': score_map
                })
                
            return Response({
                'tasks': serializers.CourseTaskSerializer(tasks, many=True).data,
                'rows': rows
            })
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ProjectViewSet(viewsets.ModelViewSet):
    queryset = models.Project.objects.all()
    serializer_class = serializers.ProjectSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = models.Project.objects.all()
        course = self.request.query_params.get('course', None)
        sub_criterion = self.request.query_params.get('sub_criterion', None)
        if course:
            queryset = queryset.filter(course_id=course)
        if sub_criterion:
            queryset = queryset.filter(sub_criterion_id=sub_criterion)
        return queryset.order_by('-id')

    def perform_create(self, serializer):
        project = serializer.save()
        self.sync_project_grades(project)

    def perform_update(self, serializer):
        project = serializer.save()
        self.sync_project_grades(project)

    def sync_project_grades(self, project):
        # Sync project score to members' CriterionScore
        if project.score is not None:
            sub_criterion = project.sub_criterion
            for member in project.members.all():
                # Store the Direct Score
                final_val = project.score 
                
                models.CriterionScore.objects.update_or_create(
                    enrollment=member,
                    sub_criterion=sub_criterion,
                    defaults={'score': final_val}
                )
                
                # Recalculate Final Grade
                try:
                    update_final_grade(member.id)
                except Exception as e:
                    print(f"Error updating final grade for {member.id} in project sync: {e}")

class StudentProjectRegistrationViewSet(viewsets.ViewSet):
    """
    View to handle student project registration.
    Public or simple auth access (since students register themselves).
    """
    permission_classes = [permissions.AllowAny] # Or Authenticated, but keeping it flexible

    @action(detail=False, methods=['get'])
    def available_projects(self, request):
        """
        List sub-criteria that are open for project registration.
        Optional filter: ?course_id=123
        """
        course_id = request.query_params.get('course_id')
        queryset = models.CourseSubCriterion.objects.filter(is_project_registration_open=True)
        
        if course_id:
            queryset = queryset.filter(course_id=course_id)
            
        # Add current status regarding dates
        now = timezone.now()
        print(f"DEBUG: Current Server Time (now): {now}")
        data = []
        for sc in queryset:
            # Check if active based on dates
            is_active_time = True
            print(f"DEBUG: Checking Criterion {sc.name} (ID: {sc.id})")
            print(f"DEBUG: Start: {sc.registration_start}, End: {sc.registration_end}")
            
            if sc.registration_start and now < sc.registration_start:
                print(f"DEBUG: INACTIVE - now < start")
                is_active_time = False
            if sc.registration_end and now > sc.registration_end:
                print(f"DEBUG: INACTIVE - now > end")
                is_active_time = False
            
            print(f"DEBUG: Result is_active_time: {is_active_time}")

            # Serialize course details with nested subject
            course_data = None
            if sc.course:
                print(f"DEBUG: Course found: {sc.course}")
                print(f"DEBUG: Course ID: {sc.course.id}, Parallel: {sc.course.parallel}")
                
                subject_data = None
                if sc.course.subject:
                    print(f"DEBUG: Subject found: {sc.course.subject}")
                    print(f"DEBUG: Subject ID: {sc.course.subject.id}")
                    print(f"DEBUG: Subject name: {sc.course.subject.name}")
                    print(f"DEBUG: Subject code: {sc.course.subject.code}")
                    
                    subject_data = {
                        'id': sc.course.subject.id,
                        'name': sc.course.subject.name,
                        'code': sc.course.subject.code
                    }
                else:
                    print(f"DEBUG: No subject found for course {sc.course.id}")
                
                course_data = {
                    'id': sc.course.id,
                    'parallel': sc.course.parallel,
                    'subject_details': subject_data
                }
            else:
                print(f"DEBUG: No course found for sub-criterion {sc.id}")

            data.append({
                'id': sc.id,
                'name': sc.name,
                'course_name': str(sc.course),
                'course_details': course_data,
                'max_members': sc.max_members,
                'description': f"Project for {sc.name}",
                'registration_start': sc.registration_start,
                'registration_end': sc.registration_end,
                'is_active_time': is_active_time
            })
            
            print(f"DEBUG: Added project data with course_details: {data[-1]}")
        return Response(data)

    @action(detail=False, methods=['get'])
    def validate_student(self, request):
        """
        Validate if a student (CI) is enrolled in the course for a project.
        Returns the student's full name if valid.
        """
        ci = request.query_params.get('ci')
        sub_criterion_id = request.query_params.get('sub_criterion_id')

        if not ci or not sub_criterion_id:
            return Response({'error': 'Missing CI or SubCriterion ID'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            sub_crit = models.CourseSubCriterion.objects.get(pk=sub_criterion_id)
            # Use ci_number instead of username
            user = User.objects.get(ci_number=ci)
            enrollment = models.Enrollment.objects.get(student=user, course=sub_crit.course)
            
            full_name = f"{user.first_name} {user.paternal_surname or ''} {user.maternal_surname or ''}".strip()
            return Response({'name': full_name, 'valid': True})
            
        except models.CourseSubCriterion.DoesNotExist:
            return Response({'error': 'Invalid SubCriterion'}, status=status.HTTP_404_NOT_FOUND)
        except User.DoesNotExist:
            return Response({'error': 'Student not found'}, status=status.HTTP_404_NOT_FOUND)
        except models.Enrollment.DoesNotExist:
            return Response({'error': 'Student not enrolled in this course'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': f'Server Error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def register(self, request):
        """
        Register a new project group.
        """
        try:
            leader_ci = request.data.get('leader_ci')
            members_ci = request.data.get('members_ci', [])
            name = request.data.get('name')
            description = request.data.get('description', '')
            sub_criterion_id = request.data.get('sub_criterion_id')

            if not leader_ci or not name or not sub_criterion_id:
                return Response({'error': 'Missing required fields'}, status=status.HTTP_400_BAD_REQUEST)

            try:
                sub_crit = models.CourseSubCriterion.objects.get(pk=sub_criterion_id)
            except models.CourseSubCriterion.DoesNotExist:
                return Response({'error': 'Invalid SubCriterion'}, status=status.HTTP_404_NOT_FOUND)

            if not sub_crit.is_project_registration_open:
                return Response({'error': 'Registration is closed for this project'}, status=status.HTTP_400_BAD_REQUEST)

            # Date Validation
            now = timezone.now()
            if sub_crit.registration_start and now < sub_crit.registration_start:
                 return Response({'error': 'Registration has not started yet'}, status=status.HTTP_400_BAD_REQUEST)
            if sub_crit.registration_end and now > sub_crit.registration_end:
                 return Response({'error': 'Registration deadline has passed'}, status=status.HTTP_400_BAD_REQUEST)

            # 1. Validate Leader
            try:
                leader_user = User.objects.get(ci_number=leader_ci)
                leader_enrollment = models.Enrollment.objects.get(student=leader_user, course=sub_crit.course)
            except User.DoesNotExist:
                 return Response({'error': f'Leader CI {leader_ci} not found'}, status=status.HTTP_400_BAD_REQUEST)
            except models.Enrollment.DoesNotExist:
                 return Response({'error': f'Leader CI {leader_ci} is not enrolled in this course'}, status=status.HTTP_400_BAD_REQUEST)

            # 2. Validate Members
            member_enrollments = []
            unique_cis = set(members_ci)
            
            # Total members = Leader + Members (excluding leader if in list)
            if leader_ci in unique_cis:
                unique_cis.remove(leader_ci) # Ensure leader is distinct

            total_count = 1 + len(unique_cis)

            if sub_crit.max_members and total_count > sub_crit.max_members:
                 return Response({'error': f'Group size ({total_count}) exceeds limit of {sub_crit.max_members}'}, status=status.HTTP_400_BAD_REQUEST)

            # Check Leader Exclusivity
            if models.Project.objects.filter(sub_criterion=sub_crit, members=leader_enrollment).exists():
                 return Response({'error': f'Leader {leader_ci} is already in a project'}, status=status.HTTP_400_BAD_REQUEST)

            for ci in unique_cis:
                try:
                    u = User.objects.get(ci_number=ci)
                    enr = models.Enrollment.objects.get(student=u, course=sub_crit.course)
                    
                    # Exclusivity Check
                    if models.Project.objects.filter(sub_criterion=sub_crit, members=enr).exists():
                         return Response({'error': f'Student {ci} is already in a project'}, status=status.HTTP_400_BAD_REQUEST)

                    member_enrollments.append(enr)
                except User.DoesNotExist:
                    return Response({'error': f'Student CI {ci} not found'}, status=status.HTTP_400_BAD_REQUEST)
                except models.Enrollment.DoesNotExist:
                    return Response({'error': f'Student CI {ci} not enrolled'}, status=status.HTTP_400_BAD_REQUEST)

            # 3. Create Project
            project = models.Project.objects.create(
                course=sub_crit.course,
                sub_criterion=sub_crit,
                name=name,
                description=description,
                student_in_charge=leader_enrollment
            )
            
            # Add members (Leader + Others)
            all_members = [leader_enrollment] + member_enrollments
            project.members.set(all_members)
            project.save()

            return Response({'message': 'Project registered successfully', 'project_id': project.id}, status=status.HTTP_201_CREATED)

        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({'error': f'Internal Server Error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class StudentCourseRegistrationViewSet(viewsets.ViewSet):
    permission_classes = [permissions.AllowAny]

    @action(detail=False, methods=['get'])
    def open_courses(self, request):
        now = timezone.now()
        courses = models.Course.objects.filter(is_registration_open=True, active=True)
        # Filter by dates if set
        valid_courses = []
        for course in courses:
            if course.registration_start and now < course.registration_start:
                continue
            if course.registration_end and now > course.registration_end:
                continue
            valid_courses.append(course)
        
        serializer = serializers.CourseSerializer(valid_courses, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def submit_request(self, request):
        serializer = serializers.RegistrationRequestSerializer(data=request.data)
        if serializer.is_valid():
            # Additional Validation
            ci = serializer.validated_data.get('ci')
            course = serializer.validated_data.get('course')
            email = serializer.validated_data.get('email')

            # Check if already enrolled
            if models.Enrollment.objects.filter(student__ci_number=ci, course=course).exists():
                return Response({'error': 'Ya estás inscrito en este curso.'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if pending request exists
            if models.RegistrationRequest.objects.filter(ci=ci, course=course, status='PENDING').exists():
                 return Response({'error': 'Ya tienes una solicitud pendiente para este curso.'}, status=status.HTTP_400_BAD_REQUEST)

             # Check email unique globally? Or just ensure no conflict if creating new user?
             # For now, simplistic check.
            
            serializer.save()
            return Response({'message': 'Solicitud enviada correctamente', 'id': serializer.instance.id}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class RegistrationRequestViewSet(viewsets.ModelViewSet):
    queryset = models.RegistrationRequest.objects.all()
    serializer_class = serializers.RegistrationRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        course_id = self.request.query_params.get('course_id')
        status_param = self.request.query_params.get('status')
        if course_id:
            queryset = queryset.filter(course_id=course_id)
        if status_param:
            queryset = queryset.filter(status=status_param)
        return queryset

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        reg_req = self.get_object()
        if reg_req.status != 'PENDING':
             return Response({'error': 'Solo se pueden aprobar solicitudes pendientes'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # 1. Find or Create User
            user = None
            try:
                user = User.objects.get(ci_number=reg_req.ci)
            except User.DoesNotExist:
                pass
            
            if not user:
                try:
                    # User asked for email to be the CI. Check if user exists with this "email"
                    user = User.objects.get(email=reg_req.ci)
                except User.DoesNotExist:
                    pass

            if not user:
                # Create User
                # "el correo es su numero de carnet y su contrasena es el mismo numero de carnet"
                user = User.objects.create_user(
                    email=reg_req.email, # Use the actual email provided by student
                    password=reg_req.ci, 
                    first_name=reg_req.first_name,
                    paternal_surname=reg_req.paternal_surname,
                    maternal_surname=reg_req.maternal_surname,
                    ci_number=reg_req.ci,
                    role='STUDENT'
                )
                print(f"Created User {user.email} (CI) with password {reg_req.ci}")

            # 2. Check Enrollment
            if models.Enrollment.objects.filter(student=user, course=reg_req.course).exists():
                 reg_req.status = 'APPROVED' # Already enrolled, just mark approved
                 reg_req.save()
                 return Response({'message': 'El estudiante ya estaba inscrito. Solicitud marcada como aprobada.'})

            # 3. Enroll
            models.Enrollment.objects.create(student=user, course=reg_req.course)
            
            reg_req.status = 'APPROVED'
            reg_req.save()
            
            return Response({'message': 'Estudiante inscrito correctamente'})

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        reg_req = self.get_object()
        if reg_req.status != 'PENDING':
             return Response({'error': 'Solo se pueden rechazar solicitudes pendientes'}, status=status.HTTP_400_BAD_REQUEST)
        
        reg_req.status = 'REJECTED'
        reg_req.save()
        return Response({'message': 'Solicitud rechazada'})
