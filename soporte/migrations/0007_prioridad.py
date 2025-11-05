from django.db import migrations, models
import django.db.models.deletion


DEFAULT_PRIORIDADES = (
    ("baja", "Baja", 1440, 1),
    ("media", "Media", 720, 2),
    ("alta", "Alta", 240, 3),
    ("critica", "Crítica", 60, 4),
)


def crear_prioridades(apps, schema_editor):
    Prioridad = apps.get_model("soporte", "Prioridad")
    Ticket = apps.get_model("soporte", "Ticket")
    SLARegla = apps.get_model("soporte", "SLARegla")

    prioridades_creadas = {}
    orden_base = 1
    for clave, nombre, minutos, orden in DEFAULT_PRIORIDADES:
        prioridad, created = Prioridad.objects.get_or_create(
            clave=clave,
            defaults={
                "nombre": nombre,
                "minutos_resolucion": minutos,
                "orden": orden,
            },
        )
        if not created:
            prioridad.nombre = nombre
            prioridad.minutos_resolucion = minutos
            prioridad.orden = orden
            prioridad.save(update_fields=["nombre", "minutos_resolucion", "orden"])
        prioridades_creadas[clave] = prioridad
        orden_base = max(orden_base, orden + 1)

    def obtener_prioridad_para_clave(clave):
        nonlocal orden_base
        if not clave:
            clave = "baja"
        prioridad = prioridades_creadas.get(clave)
        if prioridad is None:
            prioridad = Prioridad.objects.create(
                clave=clave,
                nombre=clave.replace("_", " ").title(),
                minutos_resolucion=1440,
                orden=orden_base,
            )
            prioridades_creadas[clave] = prioridad
            orden_base += 1
        return prioridad

    for ticket in Ticket.objects.all().only("id", "prioridad"):
        prioridad_obj = obtener_prioridad_para_clave(ticket.prioridad)
        Ticket.objects.filter(pk=ticket.pk).update(prioridad_sla=prioridad_obj)

    for regla in SLARegla.objects.all().only("id", "prioridad"):
        prioridad_obj = obtener_prioridad_para_clave(regla.prioridad)
        SLARegla.objects.filter(pk=regla.pk).update(prioridad_sla=prioridad_obj)


def revertir_prioridades(apps, schema_editor):
    # No se realiza ninguna acción en reversa para evitar pérdida de datos.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("soporte", "0006_slaregla_slacalculo_ticket_sla"),
    ]

    operations = [
        migrations.CreateModel(
            name="Prioridad",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "clave",
                    models.SlugField(
                        help_text=(
                            "Nombre corto sin espacios usado internamente para referirse a la prioridad. "
                            "Por ejemplo: 'baja', 'media', 'alta'."
                        ),
                        unique=True,
                        verbose_name="Identificador",
                    ),
                ),
                ("nombre", models.CharField(max_length=100, unique=True, verbose_name="Nombre")),
                (
                    "minutos_resolucion",
                    models.PositiveIntegerField(
                        help_text="Tiempo máximo estimado para resolver un ticket con esta prioridad.",
                        verbose_name="Tiempo objetivo (minutos)",
                    ),
                ),
                (
                    "orden",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="Se utiliza para ordenar las prioridades en los listados.",
                        verbose_name="Orden",
                    ),
                ),
            ],
            options={
                "ordering": ["orden", "nombre"],
                "verbose_name": "Prioridad de SLA",
                "verbose_name_plural": "Prioridades de SLA",
            },
        ),
        migrations.AddField(
            model_name="ticket",
            name="prioridad_sla",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="tickets",
                to="soporte.prioridad",
                verbose_name="Prioridad",
            ),
        ),
        migrations.AddField(
            model_name="slaregla",
            name="prioridad_sla",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="reglas",
                to="soporte.prioridad",
                verbose_name="Prioridad",
            ),
        ),
        migrations.RunPython(crear_prioridades, revertir_prioridades),
        migrations.AlterField(
            model_name="ticket",
            name="prioridad_sla",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="tickets",
                to="soporte.prioridad",
                verbose_name="Prioridad",
            ),
        ),
        migrations.AlterField(
            model_name="slaregla",
            name="prioridad_sla",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="reglas",
                to="soporte.prioridad",
                verbose_name="Prioridad",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="slaregla",
            unique_together=set(),
        ),
        migrations.RemoveField(
            model_name="ticket",
            name="prioridad",
        ),
        migrations.RemoveField(
            model_name="slaregla",
            name="prioridad",
        ),
        migrations.RenameField(
            model_name="ticket",
            old_name="prioridad_sla",
            new_name="prioridad",
        ),
        migrations.RenameField(
            model_name="slaregla",
            old_name="prioridad_sla",
            new_name="prioridad",
        ),
        migrations.AlterUniqueTogether(
            name="slaregla",
            unique_together={("prioridad", "tipo_ticket")},
        ),
    ]
