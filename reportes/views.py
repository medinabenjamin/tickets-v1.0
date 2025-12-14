# reportes/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Q
from django.db.models.functions import ExtractHour, TruncDate
from soporte.models import Ticket
from django.contrib.auth.models import User

@login_required
def dashboard_reportes(request):
    """
    NUEVA LÓGICA: Esta vista ahora es SOLO para Superusuarios.
    """
    # Si el usuario no es superusuario, se redirige al dashboard principal.
    if not request.user.is_superuser:
        return redirect('dashboard_principal')
        
    # --- Métricas Clave (KPIs) ---
    
    # 1. Tiempo Promedio de Resolución GLOBAL
    avg_resolution_time_global = Ticket.objects.filter(
        estado__in=['resuelto', 'cerrado'],
        tiempo_resolucion__isnull=False
    ).aggregate(avg_time=Avg('tiempo_resolucion'))['avg_time']

    if avg_resolution_time_global is not None:
        avg_resolution_time_global = str(avg_resolution_time_global).split(".")[0]

    # 2. Tiempo Promedio de Resolución POR TÉCNICO
    resolution_by_tech = User.objects.filter(
        is_staff=True,
        tickets_asignados__isnull=False,
    ).annotate(
        avg_time=Avg(
            'tickets_asignados__tiempo_resolucion',
            filter=Q(
                tickets_asignados__estado__in=['resuelto', 'cerrado'],
                tickets_asignados__tiempo_resolucion__isnull=False,
            ),
        ),
        total_resolved=Count(
            'tickets_asignados',
            filter=Q(
                tickets_asignados__estado__in=['resuelto', 'cerrado'],
                tickets_asignados__tiempo_resolucion__isnull=False,
            ),
        ),
        tickets_al_dia=Count(
            'tickets_asignados',
            filter=Q(
                tickets_asignados__estado_sla__in=[
                    Ticket.SLA_ESTADO_PENDIENTE,
                    Ticket.SLA_ESTADO_CUMPLIDO,
                ]
            ),
        ),
        vencidos_abiertos=Count(
            'tickets_asignados',
            filter=(
                Q(tickets_asignados__estado_sla=Ticket.SLA_ESTADO_VENCIDO)
                & ~Q(tickets_asignados__estado__in=['resuelto', 'cerrado'])
            ),
        ),
        cerrados_fuera_plazo=Count(
            'tickets_asignados',
            filter=Q(
                tickets_asignados__estado_sla=Ticket.SLA_ESTADO_VENCIDO,
                tickets_asignados__estado__in=['resuelto', 'cerrado'],
            ),
        ),
    ).order_by('avg_time')

    prioridades_por_tecnico_qs = (
        Ticket.objects.filter(tecnico_asignado__in=resolution_by_tech)
        .values('tecnico_asignado_id', 'prioridad__nombre')
        .annotate(total=Count('id'))
    )
    prioridades_por_tecnico = {}
    for entry in prioridades_por_tecnico_qs:
        prioridades_por_tecnico.setdefault(entry['tecnico_asignado_id'], []).append(
            {
                'nombre': entry['prioridad__nombre'],
                'total': entry['total'],
            }
        )

    resolution_by_tech = list(resolution_by_tech)
    for tech in resolution_by_tech:
        tech.prioridades = prioridades_por_tecnico.get(tech.id, [])

    # 3. Tickets por Categoría
    tickets_por_categoria = list(
        Ticket.objects.values('categoria').annotate(count=Count('categoria')).order_by('-count')
    )
    
    # 4. Distribución de Estados (Preparado para el gráfico)
    tickets_por_estado_query = Ticket.objects.values('estado').annotate(count=Count('estado')).order_by('estado')
    
    # Formatear datos para Chart.js
    estados_labels = [item['estado'].capitalize() for item in tickets_por_estado_query]
    estados_data = [item['count'] for item in tickets_por_estado_query]

    total_tickets = Ticket.objects.count()

    for item in tickets_por_categoria:
        if total_tickets:
            percentage = (item['count'] / total_tickets) * 100
        else:
            percentage = 0

        item['percentage'] = percentage
        item['percentage_display'] = f"{percentage:.2f}"

    # 5. Tickets cerrados por día
    tickets_cerrados_por_dia_qs = (
        Ticket.objects.filter(estado__in=['resuelto', 'cerrado'], fecha_cierre__isnull=False)
        .annotate(day=TruncDate('fecha_cierre'))
        .values('day')
        .annotate(total=Count('id'))
        .order_by('day')
    )
    tickets_cerrados_por_dia = {
        'labels': [item['day'].strftime('%Y-%m-%d') for item in tickets_cerrados_por_dia_qs],
        'data': [item['total'] for item in tickets_cerrados_por_dia_qs],
    }

    # 6. Heatmap de creación por hora del día
    tickets_por_hora_qs = (
        Ticket.objects.annotate(hour=ExtractHour('fecha_creacion'))
        .values('hour')
        .annotate(total=Count('id'))
        .order_by('hour')
    )

    tickets_por_hora_dict = {item['hour']: item['total'] for item in tickets_por_hora_qs}
    max_por_hora = max(tickets_por_hora_dict.values(), default=0)
    heatmap_por_hora = []

    for hour in range(24):
        total = tickets_por_hora_dict.get(hour, 0)
        intensidad = total / max_por_hora if max_por_hora else 0
        heatmap_por_hora.append(
            {
                'hora': hour,
                'total': total,
                'intensidad': intensidad,
            }
        )

    context = {
        'avg_resolution_time_global': avg_resolution_time_global,
        'resolution_by_tech': resolution_by_tech,
        'tickets_por_categoria': tickets_por_categoria,
        'total_tickets': total_tickets,
        'estados_chart_data': {
            'labels': estados_labels,
            'data': estados_data,
        },
        'tickets_cerrados_por_dia': tickets_cerrados_por_dia,
        'heatmap_por_hora': heatmap_por_hora,
    }
    return render(request, 'reportes/dashboard_reportes.html', context)