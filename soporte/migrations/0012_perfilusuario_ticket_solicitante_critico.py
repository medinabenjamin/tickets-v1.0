from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def crear_perfiles(apps, schema_editor):
    User = apps.get_model(settings.AUTH_USER_MODEL.split('.')[0], settings.AUTH_USER_MODEL.split('.')[1])
    PerfilUsuario = apps.get_model('soporte', 'PerfilUsuario')
    for usuario in User.objects.all():
        PerfilUsuario.objects.get_or_create(user=usuario)


class Migration(migrations.Migration):

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("soporte", "0011_rename_tickethisto_ticket__4ae4a0_idx_soporte_tic_ticket__6c9bb4_idx_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="PerfilUsuario",
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
                    "es_critico",
                    models.BooleanField(
                        default=False,
                        help_text="Si está marcado, los tickets de este usuario tendrán prioridad visible.",
                        verbose_name="Usuario crítico",
                    ),
                ),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="perfil",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Usuario",
                    ),
                ),
            ],
            options={
                "verbose_name": "Perfil de usuario",
                "verbose_name_plural": "Perfiles de usuario",
            },
        ),
        migrations.AddField(
            model_name="ticket",
            name="solicitante_critico",
            field=models.BooleanField(
                default=False,
                db_index=True,
                help_text="Indica si el solicitante es marcado como crítico al momento de registrar el ticket.",
                verbose_name="Solicitante crítico",
            ),
        ),
        migrations.RunPython(crear_perfiles, migrations.RunPython.noop),
    ]
