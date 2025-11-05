from django.urls import path
from .views import dashboard_reportes

urlpatterns = [
    # Usamos la función directamente, sin el prefijo 'views.'
    path('dashboard-reportes/', dashboard_reportes, name='dashboard_de_reportes'),
]
