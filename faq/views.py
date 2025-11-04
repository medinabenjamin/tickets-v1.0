# faq/views.py
from django.shortcuts import render
from .models import FAQ
from django.contrib.auth.decorators import login_required
from django.db.models import Q # Necesario para búsquedas complejas

@login_required
def lista_faqs(request):
    # Obtiene el término de búsqueda desde la URL (?q=...)
    search_query = request.GET.get('q', '')
    
    # Inicia la consulta con las preguntas activas
    faqs = FAQ.objects.filter(activo=True)
    
    # Si hay un término de búsqueda, filtra los resultados
    if search_query:
        # Busca en el campo 'pregunta' O en el campo 'respuesta'
        faqs = faqs.filter(
            Q(pregunta__icontains=search_query) | 
            Q(respuesta__icontains=search_query)
        )
    
    faqs = faqs.order_by('categoria', 'pregunta')

    context = {
        'faqs': faqs,
        'search_query': search_query, # Pasa el término de búsqueda a la plantilla
    }
    return render(request, 'faq/lista_faqs.html', context)