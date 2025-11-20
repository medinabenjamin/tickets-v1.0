# soporte/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # Vistas de Navegación Principal
    path("dashboard-principal/", views.dashboard, name="dashboard_principal"),
    path("tickets/", views.home, name="home_tickets"),
    path("crear/", views.crear_ticket, name="crear_ticket"),
    path('salir/', views.salir, name="salir"),

    # Gestión de Tickets
    path("ticket/<int:ticket_id>/", views.detalle_ticket, name="detalle_ticket"),
    path("ticket/<int:ticket_id>/editar/", views.editar_ticket, name="editar_ticket"),
    
    # NUEVAS RUTAS para impresión y PDF
    path('ticket/<int:ticket_id>/vista_previa/', views.vista_previa_imprimir, name='vista_previa_imprimir'),
    path('ticket/<int:ticket_id>/exportar_pdf/', views.exportar_ticket_pdf, name='exportar_ticket_pdf'),
    
    # Reportes
    path('reportes/exportar/csv/', views.exportar_tickets_csv, name='exportar_tickets_csv'),
    
    # Mantenedor de Usuarios y Roles
    path('usuarios/', views.mantenedor_usuarios, name='mantenedor_usuarios'),
    path('usuarios/crear/', views.crear_usuario, name='crear_usuario'),
    path('mantenedor/usuarios/<int:user_id>/editar/', views.editar_usuario, name='editar_usuario'),
    path('mantenedor/usuarios/<int:user_id>/eliminar/', views.eliminar_usuario, name='eliminar_usuario'),

    # Gestión SLA - Prioridades
    path('sla/prioridades/', views.lista_prioridades_sla, name='sla_prioridades'),
    path('sla/prioridades/nueva/', views.crear_prioridad_sla, name='sla_prioridad_crear'),
    path('sla/prioridades/<int:prioridad_id>/editar/', views.editar_prioridad_sla, name='sla_prioridad_editar'),
    path('sla/prioridades/<int:prioridad_id>/eliminar/', views.eliminar_prioridad_sla, name='sla_prioridad_eliminar'),
]