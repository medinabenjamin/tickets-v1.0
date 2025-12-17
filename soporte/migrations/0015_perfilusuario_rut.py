from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('soporte', '0014_notification'),
    ]

    operations = [
        migrations.AddField(
            model_name='perfilusuario',
            name='rut',
            field=models.CharField(
                blank=True,
                help_text='Número de RUT en formato 12345678-9',
                max_length=12,
                null=True,
                unique=True,
                verbose_name='RUT',
            ),
        ),
    ]
