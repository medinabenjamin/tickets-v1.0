# Generated manually for TicketHistory model
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('soporte', '0009_roleinfo'),
    ]

    operations = [
        migrations.CreateModel(
            name='TicketHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(choices=[('STATUS', 'Estado'), ('PRIORITY', 'Prioridad'), ('ASSIGNEE', 'Técnico'), ('TITLE', 'Título'), ('DESCRIPTION', 'Descripción'), ('CATEGORY', 'Categoría'), ('AREA', 'Área'), ('ATTACH_ADD', 'Adjunto agregado'), ('ATTACH_DEL', 'Adjunto eliminado'), ('COMMENT', 'Comentario')], max_length=20)),
                ('field', models.CharField(blank=True, default='', max_length=30)),
                ('old_value', models.TextField(blank=True, default='')),
                ('new_value', models.TextField(blank=True, default='')),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('actor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='acciones_tickets', to=settings.AUTH_USER_MODEL)),
                ('ticket', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='historial', to='soporte.ticket')),
            ],
            options={
                'verbose_name': 'Historial de ticket',
                'verbose_name_plural': 'Historial de tickets',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='tickethistory',
            index=models.Index(fields=['ticket', 'created_at'], name='tickethisto_ticket__4ae4a0_idx'),
        ),
        migrations.AddIndex(
            model_name='tickethistory',
            index=models.Index(fields=['ticket', 'action'], name='tickethisto_ticket__e19d2d_idx'),
        ),
    ]
