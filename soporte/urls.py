# soporte/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # Vistas de Navegación Principal
    path("dashboard-principal/", views.dashboard, name="dashboard_principal"),
    path("tickets/", views.home, name="home_tickets"),
    path("crear/", views.crear_ticket, name="crear_ticket"),
    path('salir/', views.salir, name="salir"),
    path('notificaciones/unread/', views.notificaciones_unread, name='notificaciones_unread'),
    path('notificaciones/', views.lista_notificaciones, name='lista_notificaciones'),

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
    path('roles/', views.roles_list, name='roles_list'),
    path('roles/nuevo/', views.rol_crear, name='rol_crear'),
    path('roles/<int:pk>/editar/', views.rol_editar, name='rol_editar'),
    path('roles/<int:pk>/eliminar/', views.rol_eliminar, name='rol_eliminar'),

    # Gestión SLA - Prioridades
    path('sla/prioridades/', views.lista_prioridades_sla, name='sla_prioridades'),
    path('sla/prioridades/nueva/', views.crear_prioridad_sla, name='sla_prioridad_crear'),
    path('sla/prioridades/<int:prioridad_id>/editar/', views.editar_prioridad_sla, name='sla_prioridad_editar'),
    path('sla/prioridades/<int:prioridad_id>/eliminar/', views.eliminar_prioridad_sla, name='sla_prioridad_eliminar'),

    # Gestión de Áreas
    path('areas/', views.lista_areas, name='areas'),
    path('areas/nueva/', views.crear_area, name='area_crear'),
    path('areas/<int:area_id>/editar/', views.editar_area, name='area_editar'),
    path('areas/<int:area_id>/eliminar/', views.eliminar_area, name='area_eliminar'),
]