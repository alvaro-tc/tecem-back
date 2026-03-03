from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('school', '0028_auto_20260302_0928'),
    ]

    operations = [
        migrations.AddField(
            model_name='course',
            name='is_visible',
            field=models.BooleanField(
                default=False,
                help_text='Si está activo, el curso aparece en la página principal y en la página de cursos públicos'
            ),
        ),
    ]
