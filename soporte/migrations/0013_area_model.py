from django.db import migrations, models
import django.db.models.deletion


def seed_areas(apps, schema_editor):
    Area = apps.get_model('soporte', 'Area')
    Ticket = apps.get_model('soporte', 'Ticket')

    areas_data = [
        ('finanzas', 'Finanzas'),
        ('rrhh', 'Recursos Humanos (RRHH)'),
        ('ventas', 'Ventas'),
        ('marketing', 'Marketing'),
        ('produccion', 'Producción/Operaciones'),
        ('ti', 'Tecnología de la Información (TI)'),
        ('general', 'General/Administración'),
    ]

    area_map = {}
    for order, (clave, nombre) in enumerate(areas_data, start=1):
        area, _ = Area.objects.get_or_create(
            clave=clave,
            defaults={
                'nombre': nombre,
                'orden': order,
            },
        )
        area_map[clave] = area

    default_area = area_map.get('general') or Area.objects.first()

    for ticket in Ticket.objects.all():
        legacy_clave = getattr(ticket, 'area_funcional', None)
        area = area_map.get(legacy_clave) or default_area
        if area:
            ticket.area_funcional_temp = area
            ticket.save(update_fields=['area_funcional_temp'])


class Migration(migrations.Migration):

    dependencies = [
        ('soporte', '0012_perfilusuario_ticket_solicitante_critico'),
    ]

    operations = [
        migrations.CreateModel(
            name='Area',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('clave', models.SlugField(help_text="Nombre corto sin espacios usado internamente para referirse al área. Por ejemplo: 'finanzas', 'rrhh', 'marketing'.", max_length=50, unique=True, verbose_name='Identificador')),
                ('nombre', models.CharField(max_length=100, unique=True, verbose_name='Nombre')),
                ('orden', models.PositiveIntegerField(default=0, help_text='Se utiliza para ordenar las áreas en los listados y selectores.', verbose_name='Orden')),
            ],
            options={
                'verbose_name': 'Área funcional',
                'verbose_name_plural': 'Áreas funcionales',
                'ordering': ['orden', 'nombre'],
            },
        ),
        migrations.AddField(
            model_name='ticket',
            name='area_funcional_temp',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='+', to='soporte.area'),
        ),
        migrations.RunPython(seed_areas, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='ticket',
            name='area_funcional',
        ),
        migrations.RenameField(
            model_name='ticket',
            old_name='area_funcional_temp',
            new_name='area_funcional',
        ),
        migrations.AlterField(
            model_name='ticket',
            name='area_funcional',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='tickets', to='soporte.area', verbose_name='Área Solicitante'),
        ),
    ]
