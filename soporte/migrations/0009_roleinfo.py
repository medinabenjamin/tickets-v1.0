from django.db import migrations, models
import django.db.models.deletion


def crear_roleinfo(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    RoleInfo = apps.get_model('soporte', 'RoleInfo')
    for grupo in Group.objects.all():
        RoleInfo.objects.get_or_create(group=grupo)


def revertir_roleinfo(apps, schema_editor):
    RoleInfo = apps.get_model('soporte', 'RoleInfo')
    RoleInfo.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("soporte", "0008_alter_slacalculo_id_alter_slaregla_id"),
    ]

    operations = [
        migrations.CreateModel(
            name="RoleInfo",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "descripcion",
                    models.TextField(
                        blank=True, default="", verbose_name="Descripción del rol"
                    ),
                ),
                (
                    "group",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="info",
                        to="auth.group",
                        verbose_name="Rol",
                    ),
                ),
            ],
            options={
                "verbose_name": "Información de rol",
                "verbose_name_plural": "Información de roles",
            },
        ),
        migrations.RunPython(crear_roleinfo, revertir_roleinfo),
    ]
