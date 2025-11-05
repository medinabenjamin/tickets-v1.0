# reportes/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count
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

    # 2. Tiempo Promedio de Resolución POR TÉCNICO
    resolution_by_tech = User.objects.filter(
        is_staff=True,
        tickets_asignados__estado__in=['resuelto', 'cerrado'],
        tickets_asignados__tiempo_resolucion__isnull=False
    ).annotate(
        avg_time=Avg('tickets_asignados__tiempo_resolucion'),
        total_resolved=Count('tickets_asignados')
    ).order_by('avg_time')

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
            item['percentage'] = (item['count'] / total_tickets) * 100
        else:
            item['percentage'] = 0

    context = {
        'avg_resolution_time_global': avg_resolution_time_global,
        'resolution_by_tech': resolution_by_tech,
        'tickets_por_categoria': tickets_por_categoria,
        'total_tickets': total_tickets,
        'estados_chart_data': {
            'labels': estados_labels,
            'data': estados_data,
        },
    }
    return render(request, 'reportes/dashboard_reportes.html', context)