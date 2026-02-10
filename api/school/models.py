

from django.db import models
from django.conf import settings

class AcademicPeriod(models.Model):
    name = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField()
    active = models.BooleanField(default=True)
    parent_period = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='sub_periods')

    def __str__(self):
        return self.name

class Program(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class Subject(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50)
    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name='subjects')
    period = models.ForeignKey('AcademicPeriod', on_delete=models.CASCADE, related_name='subjects', null=True)
    description = models.TextField(blank=True, null=True)
    archived = models.BooleanField(default=False)
    evaluation_template = models.ForeignKey('EvaluationTemplate', on_delete=models.SET_NULL, null=True, blank=True, related_name='subjects')
    subcriteria_locked = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.code} - {self.name}"

class Course(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='courses')
    period = models.ForeignKey(AcademicPeriod, on_delete=models.CASCADE, related_name='courses')
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='teaching_courses')
    active = models.BooleanField(default=True)
    parallel = models.CharField(max_length=50, blank=True, null=True)
    schedule = models.TextField(blank=True, null=True)
    whatsapp_link = models.URLField(blank=True, null=True)
    
    # Registration Settings
    is_registration_open = models.BooleanField(default=False)
    registration_start = models.DateTimeField(null=True, blank=True)
    registration_end = models.DateTimeField(null=True, blank=True)
    image = models.FileField(upload_to='course_images/', blank=True, null=True)

    def __str__(self):
        return f"{self.subject.code} ({self.period.name}) - {self.parallel}"

class Enrollment(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='enrollments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    date_enrolled = models.DateField(auto_now_add=True)
    final_grade = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    class Meta:
        unique_together = ('student', 'course')

    def __str__(self):
        return f"{self.student} in {self.course}"

class FamilyRelationship(models.Model):
    RELATIONSHIPS = [
        ('FATHER', 'Father'),
        ('MOTHER', 'Mother'),
        ('GUARDIAN', 'Guardian'),
        ('OTHER', 'Other'),
    ]
    parent = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='children_relationships')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='parent_relationships')
    relationship_type = models.CharField(max_length=20, choices=RELATIONSHIPS)

    def __str__(self):
        return f"{self.parent} -> {self.student} ({self.relationship_type})"

class MainEvaluation(models.Model):
    name = models.CharField(max_length=255) # e.g., "1st Quarter"
    period = models.ForeignKey(AcademicPeriod, on_delete=models.CASCADE, related_name='main_evaluations')
    weight = models.DecimalField(max_digits=5, decimal_places=2) # e.g. 0.30 for 30%
    lock_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.period})"

class SubEvaluation(models.Model):
    main_evaluation = models.ForeignKey(MainEvaluation, on_delete=models.CASCADE, related_name='sub_evaluations')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='sub_evaluations')
    name = models.CharField(max_length=255) # e.g. "Homework 1"
    weight = models.DecimalField(max_digits=5, decimal_places=2, default=1.0) # Weight relative to MainEvaluation
    max_score = models.DecimalField(max_digits=5, decimal_places=2, default=100.0)
    date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} - {self.course}"

class Score(models.Model):
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name='scores')
    sub_evaluation = models.ForeignKey(SubEvaluation, on_delete=models.CASCADE, related_name='scores')
    value = models.DecimalField(max_digits=5, decimal_places=2)
    feedback = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('enrollment', 'sub_evaluation')

    def __str__(self):
        return f"{self.value} for {self.enrollment}"

class EvaluationTemplate(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class EvaluationCriterion(models.Model):
    evaluation_template = models.ForeignKey(EvaluationTemplate, on_delete=models.CASCADE, related_name='criteria', null=True)
    name = models.CharField(max_length=255)
    weight = models.DecimalField(max_digits=5, decimal_places=2) # e.g. 30.00 for 30%

    def __str__(self):
        return f"{self.name} ({self.weight}%) - {self.evaluation_template}"

class CourseSubCriterion(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='sub_criteria')
    parent_criterion = models.ForeignKey(EvaluationCriterion, on_delete=models.CASCADE, related_name='course_sub_criteria')
    name = models.CharField(max_length=255)
    percentage = models.DecimalField(max_digits=5, decimal_places=2) # e.g. 50.00 for 50% of the parent criterion
    visible_on_gradesheet = models.BooleanField(default=True)
    editable_on_gradesheet = models.BooleanField(default=True)
    is_project = models.BooleanField(default=False, help_text="If true, this criterion requires group projects instead of individual tasks")
    is_project_registration_open = models.BooleanField(default=False)
    registration_start = models.DateTimeField(null=True, blank=True)
    registration_end = models.DateTimeField(null=True, blank=True)
    max_members = models.IntegerField(null=True, blank=True, help_text="Maximum number of members per project group")

    def __str__(self):
        return f"{self.name} ({self.percentage}%) - {self.course}"

class CourseSpecialCriterion(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='special_criteria')
    parent_criterion = models.ForeignKey(EvaluationCriterion, on_delete=models.CASCADE, related_name='course_special_criteria', null=True) # null=True to avoid migration errors on existing data
    name = models.CharField(max_length=255)
    percentage = models.DecimalField(max_digits=5, decimal_places=2) # e.g. 5.00 for 5 bonus points
    visible_on_gradesheet = models.BooleanField(default=True)
    editable_on_gradesheet = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.percentage} pts) - {self.course}"

class CriterionScore(models.Model):
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name='criterion_scores')
    sub_criterion = models.ForeignKey(CourseSubCriterion, on_delete=models.CASCADE, related_name='scores')
    score = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    
    class Meta:
        unique_together = ('enrollment', 'sub_criterion')

    def __str__(self):
        return f"{self.score} - {self.enrollment} - {self.sub_criterion}"

class SpecialCriterionScore(models.Model):
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name='special_criterion_scores')
    special_criterion = models.ForeignKey(CourseSpecialCriterion, on_delete=models.CASCADE, related_name='scores')
    score = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)

    class Meta:
        unique_together = ('enrollment', 'special_criterion')

    def __str__(self):
        return f"{self.score} - {self.enrollment} - {self.special_criterion}"

class CourseTask(models.Model):
    sub_criterion = models.ForeignKey(CourseSubCriterion, on_delete=models.CASCADE, related_name='tasks', null=True, blank=True)
    special_criterion = models.ForeignKey(CourseSpecialCriterion, on_delete=models.CASCADE, related_name='tasks', null=True, blank=True)
    name = models.CharField(max_length=255)
    weight = models.IntegerField(default=1, help_text="Weight of the task (e.g., 2 means it counts as 2 tasks)")
    is_locked = models.BooleanField(default=False)
    is_public = models.BooleanField(default=True)
    
    def clean(self):
        from django.core.exceptions import ValidationError
        # Ensure exactly one of sub_criterion or special_criterion is set
        if not self.sub_criterion and not self.special_criterion:
            raise ValidationError("Either sub_criterion or special_criterion must be set")
        if self.sub_criterion and self.special_criterion:
            raise ValidationError("Cannot set both sub_criterion and special_criterion")
    
    def __str__(self):
        criterion = self.sub_criterion or self.special_criterion
        return f"{self.name} ({self.weight}x) - {criterion}"

class TaskScore(models.Model):
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name='task_scores')
    task = models.ForeignKey(CourseTask, on_delete=models.CASCADE, related_name='scores')
    score = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    
    class Meta:
        unique_together = ('enrollment', 'task')
    
    def __str__(self):
        return f"{self.score} - {self.enrollment} - {self.task}"

class Project(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='projects')
    sub_criterion = models.ForeignKey(CourseSubCriterion, on_delete=models.CASCADE, related_name='projects')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    student_in_charge = models.ForeignKey(Enrollment, on_delete=models.SET_NULL, null=True, blank=True, related_name='led_projects')
    members = models.ManyToManyField(Enrollment, related_name='projects')
    score = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    
    def __str__(self):
        return self.name

class RegistrationRequest(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]
    
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='registration_requests')
    ci = models.CharField(max_length=20)
    first_name = models.CharField(max_length=100)
    paternal_surname = models.CharField(max_length=100)
    maternal_surname = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField()
    cellphone = models.CharField(max_length=20, blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('course', 'ci') # Prevent duplicate requests for same course

    def __str__(self):
        return f"{self.first_name} {self.paternal_surname} - {self.course} ({self.status})"
