from api.user.serializers import UserSerializer, ManageUserSerializer, ProfileUpdateSerializer
from api.user.models import User
from rest_framework import viewsets, status, filters
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework import mixins


from rest_framework.decorators import action

class ManageUserViewSet(viewsets.ModelViewSet):
    serializer_class = ManageUserSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = [filters.SearchFilter]
    search_fields = ['email', 'first_name', 'paternal_surname', 'maternal_surname', 'ci_number']

    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({'error': str(e), 'traceback': traceback.format_exc()}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get_queryset(self):
        role = self.request.query_params.get('role')
        queryset = User.objects.all().order_by('paternal_surname', 'maternal_surname', 'first_name')
        if role:
            queryset = queryset.filter(role=role)
        return queryset

    @action(detail=False, methods=['get', 'patch'], url_path='profile')
    def profile(self, request):
        """
        GET: Return current user's profile
        PATCH: Update current user's profile
        """
        user = request.user
        
        if request.method == 'GET':
            serializer = UserSerializer(user)
            return Response(serializer.data)
        
        elif request.method == 'PATCH':
            serializer = ProfileUpdateSerializer(data=request.data, context={'request': request})
            serializer.is_valid(raise_exception=True)
            
            # Update user fields
            update_fields = ['email', 'phone', 'first_name', 'paternal_surname', 'maternal_surname', 'ci_number']
            for field in update_fields:
                if field in serializer.validated_data:
                    setattr(user, field, serializer.validated_data[field])

            if 'active_course' in serializer.validated_data:
                # Validate course exists
                course_id = serializer.validated_data['active_course']
                if course_id:
                   from api.school.models import Course 
                   try:
                       c = Course.objects.get(pk=course_id)
                       user.active_course = c
                   except Course.DoesNotExist:
                       pass # Ignore invalid course
                else:
                    user.active_course = None
            
            # Handle password change
            if 'new_password' in serializer.validated_data:
                user.set_password(serializer.validated_data['new_password'])
            
            user.save()
            
            # Return updated user data
            response_serializer = UserSerializer(user)
            return Response({
                'success': True,
                'message': 'Perfil actualizado exitosamente',
                'user': response_serializer.data
            })

    @action(detail=False, methods=['post'], url_path='update-credentials')
    def update_credentials(self, request):
        """
        POST: Update email and password for forced update
        """
        user = request.user
        from api.user.serializers import UserCredentialsUpdateSerializer
        serializer = UserCredentialsUpdateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        serializer.update(user, serializer.validated_data)
        
        response_serializer = UserSerializer(user)
        return Response({
            'success': True,
            'message': 'Credenciales actualizadas exitosamente',
            'user': response_serializer.data
        })

    @action(detail=False, methods=['post'])
    def preview_bulk_create(self, request):
        file = request.FILES.get('file')
        if not file:
            return Response({"error": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST)

        students_to_create = []
        errors = []
        
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
                    'role': 'STUDENT',
                    'username': ci, 
                    'email': email
                }
                
                students_to_create.append(student_data)

        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({"error": f"Error parsing file: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

        # Separate into existing and new
        existing_cis = User.objects.filter(ci_number__in=[s['ci_number'] for s in students_to_create]).values_list('ci_number', flat=True)
        existing_cis_set = set(existing_cis)
        
        new_students = []
        existing_students = []

        for s in students_to_create:
            if s['ci_number'] in existing_cis_set:
                s['is_update'] = True # Flag as update
                existing_students.append(s)
            else:
                s['is_update'] = False
                new_students.append(s)

        return Response({
            "to_create": new_students,
            "existing": existing_students
        })

    @action(detail=False, methods=['post'])
    def confirm_bulk_create(self, request):
        students = request.data.get('students', [])
        created_count = 0
        updated_count = 0
        
        for s in students:
            ci = s.get('ci_number')
            email = s.get('email', '').strip()
            
            # 1. Update existing
            if s.get('is_update'):
                try:
                    user = User.objects.get(ci_number=ci)
                    # Update fields if provided
                    if s.get('first_name'): user.first_name = s['first_name']
                    if s.get('paternal_surname'): user.paternal_surname = s['paternal_surname']
                    if s.get('maternal_surname'): user.maternal_surname = s['maternal_surname']
                    if email: user.email = email # Update email if provided
                    user.save()
                    updated_count += 1
                except User.DoesNotExist:
                    pass # Should not happen usually
                continue

            # 2. Create new
            if not email:
                email = None

            # Prepare data for creation
            user_data = {
                'email': email,
                'password': ci,
                'role': 'STUDENT',
                'ci_number': ci,
                'first_name': s.get('first_name', ''),
                'paternal_surname': s.get('paternal_surname', ''),
                'maternal_surname': s.get('maternal_surname', '')
            }
            
            # Check if email exists (conflict with another user?)
            if email and User.objects.filter(email=email).exists():
                 # If duplicate email, skip or error? 
                 # For now, let's just print error and continue, preventing crash
                 print(f"Skipping {ci}: Email {email} exists")
                 continue

            try:
                User.objects.create_user(**user_data)
                created_count += 1
            except Exception as e:
                print(f"Error creating user {ci}: {e}")
                continue
        
        return Response({"created": created_count, "updated": updated_count}, status=status.HTTP_201_CREATED)


class UserViewSet(
    viewsets.GenericViewSet, mixins.CreateModelMixin, mixins.UpdateModelMixin
):
    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated,)

    error_message = {"success": False, "msg": "Error updating user"}

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", True)
        instance = User.objects.get(id=request.data.get("userID"))
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, "_prefetched_objects_cache", None):
            instance._prefetched_objects_cache = {}

        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        user_id = request.data.get("userID")

        if not user_id:
            raise ValidationError(self.error_message)

        if self.request.user.pk != int(user_id) and not self.request.user.is_superuser:
            raise ValidationError(self.error_message)

        self.update(request)

        return Response({"success": True}, status.HTTP_200_OK)
