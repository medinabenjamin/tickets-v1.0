from django.contrib import admin

from .models import SLARegla, SLACalculo, Ticket, Prioridad


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'titulo',
        'prioridad',
        'estado',
        'estado_sla',
        'fecha_compromiso_respuesta',
        'tecnico_asignado',
    )
    list_filter = ('estado', 'prioridad', 'estado_sla', 'tipo_ticket')
    search_fields = ('titulo', 'descripcion', 'solicitante__username')


@admin.register(SLARegla)
class SLAReglaAdmin(admin.ModelAdmin):
    list_display = ('prioridad', 'tipo_ticket', 'minutos_objetivo')
    list_filter = ('prioridad', 'tipo_ticket')
    search_fields = ('prioridad__nombre', 'tipo_ticket')


@admin.register(SLACalculo)
class SLACalculoAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'regla', 'minutos_objetivo', 'fecha_compromiso', 'estado', 'fecha_actualizacion')
    list_filter = ('estado',)
    search_fields = ('ticket__titulo', 'ticket__solicitante__username')


@admin.register(Prioridad)
class PrioridadAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'clave', 'minutos_resolucion', 'orden')
    search_fields = ('nombre', 'clave')
    ordering = ('orden', 'nombre')

