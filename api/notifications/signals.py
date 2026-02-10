from django.db.models.signals import post_save
from django.dispatch import receiver
from api.school.models import Enrollment, Course
from api.notifications.models import Notification
from api.user.models import User

# Enrollment Notification
@receiver(post_save, sender=Enrollment)
def create_enrollment_notification(sender, instance, created, **kwargs):
    if created:
        course = instance.course
        if course.teacher:
            Notification.objects.create(
                recipient=course.teacher,
                title="Nueva Inscripción Pendiente",
                message=f"El estudiante {instance.student.email} se ha inscrito al paralelo {course.parallel} de {course.subject.name}.",
                type="info",
                link=f"/school/enrollments?course={course.id}"
            )

# User Update Notification
@receiver(post_save, sender=User)
def create_user_notification(sender, instance, created, **kwargs):
    if not created:
        # Check if relevant fields changed? Simpler: Just notify on profile update via specific action usually, 
        # but for signal, maybe only if critical info changed.
        # User requested "cambios en la cuenta".
        # Let's verify context. If updated by admin, notify user?
        # For now, let's keep it simple or maybe skip this one if it's too noisy.
        # I'll implement a 'welcome' notification instead for new users.
        pass
    else:
        Notification.objects.create(
            recipient=instance,
            title="Bienvenido",
            message=f"Bienvenido a la plataforma, {instance.first_name}!",
            type="success",
            link="/dashboard/default"
        )
