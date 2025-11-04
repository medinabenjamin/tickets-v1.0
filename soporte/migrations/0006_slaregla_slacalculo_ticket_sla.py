from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('soporte', '0005_comment_adjunto_alter_comment_author'),
    ]

    operations = [
        migrations.AddField(
            model_name='ticket',
            name='estado_sla',
            field=models.CharField(
                choices=[
                    ('pendiente', 'Pendiente'),
                    ('vencido', 'Vencido'),
                    ('cumplido', 'Cumplido'),
                    ('sin_regla', 'Sin regla'),
                ],
                default='sin_regla',
                max_length=20,
                verbose_name='Estado del SLA',
            ),
        ),
        migrations.AddField(
            model_name='ticket',
            name='fecha_compromiso_respuesta',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Compromiso de respuesta'),
        ),
        migrations.CreateModel(
            name='SLARegla',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('prioridad', models.CharField(choices=[('baja', 'Baja'), ('media', 'Media'), ('alta', 'Alta'), ('critica', 'Crítica')], max_length=20)),
                ('tipo_ticket', models.CharField(choices=[('incidencia', 'Incidencia'), ('solicitud', 'Solicitud')], max_length=20)),
                ('minutos_objetivo', models.PositiveIntegerField()),
            ],
            options={
                'verbose_name': 'Regla de SLA',
                'verbose_name_plural': 'Reglas de SLA',
                'unique_together': {('prioridad', 'tipo_ticket')},
            },
        ),
        migrations.CreateModel(
            name='SLACalculo',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('minutos_objetivo', models.PositiveIntegerField(blank=True, null=True)),
                ('fecha_compromiso', models.DateTimeField(blank=True, null=True)),
                ('estado', models.CharField(choices=[('pendiente', 'Pendiente'), ('vencido', 'Vencido'), ('cumplido', 'Cumplido'), ('sin_regla', 'Sin regla')], default='sin_regla', max_length=20)),
                ('fecha_actualizacion', models.DateTimeField(auto_now=True)),
                ('regla', models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name='calculos', to='soporte.slaregla')),
                ('ticket', models.OneToOneField(on_delete=models.CASCADE, related_name='sla_calculo', to='soporte.ticket')),
            ],
            options={
                'verbose_name': 'Cálculo de SLA',
                'verbose_name_plural': 'Cálculos de SLA',
            },
        ),
    ]
