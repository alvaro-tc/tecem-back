from rest_framework import serializers
from . import models
from api.user.serializers import UserSerializer
from django.contrib.auth import get_user_model

User = get_user_model()

class AcademicPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.AcademicPeriod
        fields = '__all__'

class ProgramSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Program
        fields = '__all__'

class EvaluationCriterionSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.EvaluationCriterion
        fields = ['id', 'name', 'weight']
        read_only_fields = ['id']

class EvaluationTemplateSerializer(serializers.ModelSerializer):
    criteria = EvaluationCriterionSerializer(many=True, required=False)

    class Meta:
        model = models.EvaluationTemplate
        fields = ['id', 'name', 'description', 'criteria']

    def create(self, validated_data):
        criteria_data = validated_data.pop('criteria', [])
        template = models.EvaluationTemplate.objects.create(**validated_data)
        for criterion_data in criteria_data:
            models.EvaluationCriterion.objects.create(evaluation_template=template, **criterion_data)
        return template

    def update(self, instance, validated_data):
        criteria_data = validated_data.pop('criteria', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if criteria_data is not None:
             instance.criteria.all().delete()
             for criterion_data in criteria_data:
                 models.EvaluationCriterion.objects.create(evaluation_template=instance, **criterion_data)
        
        return instance

class SubjectSerializer(serializers.ModelSerializer):
    program_details = ProgramSerializer(source='program', read_only=True)
    period_details = AcademicPeriodSerializer(source='period', read_only=True)
    evaluation_template_details = EvaluationTemplateSerializer(source='evaluation_template', read_only=True)
    has_grades = serializers.SerializerMethodField()

    class Meta:
        model = models.Subject
        fields = '__all__'

    def get_has_grades(self, obj):
        return obj.courses.filter(enrollments__scores__isnull=False).exists()

class CourseSerializer(serializers.ModelSerializer):
    subject_details = SubjectSerializer(source='subject', read_only=True)
    teacher_name = serializers.CharField(source='teacher.email', read_only=True)
    
    class Meta:
        model = models.Course
        fields = '__all__'

class EnrollmentSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.email', read_only=True)
    student_details = UserSerializer(source='student', read_only=True)
    course_details = CourseSerializer(source='course', read_only=True)
    
    class Meta:
        model = models.Enrollment
        fields = '__all__'

class FamilyRelationshipSerializer(serializers.ModelSerializer):
    student_details = UserSerializer(source='student', read_only=True)
    parent_details = UserSerializer(source='parent', read_only=True)

    class Meta:
        model = models.FamilyRelationship
        fields = '__all__'

class MainEvaluationSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.MainEvaluation
        fields = '__all__'

class SubEvaluationSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.SubEvaluation
        fields = '__all__'

class ScoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Score
        fields = '__all__'

class CourseSubCriterionSerializer(serializers.ModelSerializer):
    course_details = CourseSerializer(source='course', read_only=True)
    class Meta:
        model = models.CourseSubCriterion
        fields = '__all__'

class CourseSpecialCriterionSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.CourseSpecialCriterion
        fields = '__all__'

class CriterionScoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.CriterionScore
        fields = '__all__'

class CourseTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.CourseTask
        fields = '__all__'

class TaskScoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.TaskScore
        fields = '__all__'

class ProjectSerializer(serializers.ModelSerializer):
    member_details = EnrollmentSerializer(source='members', many=True, read_only=True)
    leader_details = EnrollmentSerializer(source='student_in_charge', read_only=True)

    class Meta:
        model = models.Project
        fields = '__all__'

class RegistrationRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.RegistrationRequest
        fields = '__all__'
        extra_kwargs = {
            'members': {'required': False}
        }

    def validate(self, data):
        try:
            members = data.get('members', [])
            sub_criterion = data.get('sub_criterion')
            course = data.get('course')
            
            # If updating, get instance values if not provided
            if self.instance:
                if not sub_criterion: sub_criterion = self.instance.sub_criterion
                if not course: course = self.instance.course

            # 1. Validate Max Members
            # Ensure sub_criterion is not None before accessing attributes
            if sub_criterion and hasattr(sub_criterion, 'max_members') and sub_criterion.max_members is not None:
                 if len(members) > sub_criterion.max_members:
                      raise serializers.ValidationError(f"El proyecto excede el número máximo de integrantes ({sub_criterion.max_members}).")

            # 2. Validate Members belong to the same Course
            # Handle potential edge cases where course might be None or weird types
            course_id = None
            if course:
                course_id = course.id if hasattr(course, 'id') else course
            
            if course_id:
                for member in members:
                    # member is Enrollment object
                    member_course_id = member.course_id
                    if member_course_id != course_id:
                        raise serializers.ValidationError(f"El estudiante {member} no pertenece al curso seleccionada ({course_id}).")

            # 3. Validate Exclusivity
            # Check if any member is already in another project for this sub_criterion
            # Exclude current project if updating
            if sub_criterion:
                existing_projects = models.Project.objects.filter(sub_criterion=sub_criterion)
                if self.instance:
                    existing_projects = existing_projects.exclude(id=self.instance.id)
                    
                conflicting_members = existing_projects.filter(members__in=members).distinct()
                if conflicting_members.exists():
                    raise serializers.ValidationError("Uno o más estudiantes ya están asignados a otro proyecto para este criterio.")
        
        except serializers.ValidationError:
            raise
        except Exception as e:
            # Catch internal errors and report them as validation errors to avoid 500
            import traceback
            traceback.print_exc()
            raise serializers.ValidationError(f"Error interno validando proyecto: {str(e)}")

        return data
