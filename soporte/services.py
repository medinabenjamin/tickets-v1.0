from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import TicketHistory

User = get_user_model()


def log_history(ticket, actor, action, field="", old=None, new=None, metadata=None):
    TicketHistory.objects.create(
        ticket=ticket,
        actor=actor,
        action=action,
        field=field or "",
        old_value="" if old is None else str(old),
        new_value="" if new is None else str(new),
        metadata=metadata or {},
    )


def recalc_sla_for_priority(ticket):
    """
    Recalcula deadline/compromisos según la prioridad del ticket.
    Devuelve (deadline_old, deadline_new).
    """
    old_deadline = ticket.fecha_compromiso_respuesta
    prioridad = getattr(ticket, "prioridad", None)
    minutes = prioridad.minutos_resolucion if prioridad else 0
    new_deadline = None
    if minutes:
        new_deadline = timezone.now() + timedelta(minutes=minutes)
    ticket.fecha_compromiso_respuesta = new_deadline
    if hasattr(ticket, "_determinar_estado_sla"):
        ticket.estado_sla = ticket._determinar_estado_sla(new_deadline)
    return (old_deadline, new_deadline)


def _display_from_choices(choices, value):
    if value is None:
        return None
    mapping = dict(choices or [])
    return mapping.get(value, value)


def update_ticket(ticket, actor, changes: dict, comment: str = None):
    """
    Cambia campos del ticket en bloque y registra 1..n entradas en TicketHistory.
    changes: diccionario con posibles claves: 'status','priority','assignee','title','description','category','area'
    """
    # STATUS
    if 'status' in changes:
        old, new = ticket.estado, changes['status']
        if old != new:
            log_history(
                ticket,
                actor,
                TicketHistory.Action.STATUS,
                'estado',
                _display_from_choices(ticket.ESTADO_CHOICES, old),
                _display_from_choices(ticket.ESTADO_CHOICES, new),
            )
            ticket.estado = new

    # PRIORITY (recalcula SLA)
    if 'priority' in changes:
        old, new = getattr(ticket, 'prioridad', None), changes['priority']
        if old != new:
            ticket.prioridad = new
            deadline_old, deadline_new = recalc_sla_for_priority(ticket) if new else (ticket.fecha_compromiso_respuesta, ticket.fecha_compromiso_respuesta)
            log_history(
                ticket,
                actor,
                TicketHistory.Action.PRIORITY,
                'prioridad',
                getattr(old, 'nombre', old),
                getattr(new, 'nombre', new),
                metadata={
                    'deadline_old': str(deadline_old) if deadline_old else None,
                    'deadline_new': str(deadline_new) if deadline_new else None,
                },
            )

    # ASSIGNEE
    if 'assignee' in changes:
        old, new = getattr(ticket, 'tecnico_asignado', None), changes['assignee']
        if old != new:
            log_history(
                ticket,
                actor,
                TicketHistory.Action.ASSIGNEE,
                'tecnico_asignado',
                getattr(old, 'username', old),
                getattr(new, 'username', new),
            )
            ticket.tecnico_asignado = new

    # TITLE
    if 'title' in changes:
        old, new = ticket.titulo, changes['title']
        if old != new:
            log_history(ticket, actor, TicketHistory.Action.TITLE, 'titulo', old, new)
            ticket.titulo = new

    # DESCRIPTION (log solo resumen)
    if 'description' in changes:
        old, new = ticket.descripcion, changes['description']
        if old != new:
            def short(s):
                return "" if s is None else (s[:140] + ('…' if len(s) > 140 else ''))
            log_history(ticket, actor, TicketHistory.Action.DESCRIPTION, 'descripcion', short(old), short(new))
            ticket.descripcion = new

    # CATEGORY / AREA
    if 'category' in changes:
        old, new = getattr(ticket, 'categoria', None), changes['category']
        if old != new:
            log_history(
                ticket,
                actor,
                TicketHistory.Action.CATEGORY,
                'categoria',
                _display_from_choices(ticket.CATEGORIA_CHOICES, old),
                _display_from_choices(ticket.CATEGORIA_CHOICES, new),
            )
            ticket.categoria = new
    if 'area' in changes:
        old, new = getattr(ticket, 'area_funcional', None), changes['area']
        if old != new:
            log_history(
                ticket,
                actor,
                TicketHistory.Action.AREA,
                'area_funcional',
                _display_from_choices(ticket.AREA_CHOICES, old),
                _display_from_choices(ticket.AREA_CHOICES, new),
            )
            ticket.area_funcional = new

    # COMMENT
    if comment:
        log_history(ticket, actor, TicketHistory.Action.COMMENT, 'comentario', new=comment)

    ticket.save(update_fields=None)


def log_attachment(ticket, actor, file_obj, added=True):
    """
    Registrar adjuntos agregados/eliminados.
    file_obj: usar su nombre/size para metadata.
    """
    action = TicketHistory.Action.ATTACH_ADD if added else TicketHistory.Action.ATTACH_DEL
    meta = {
        'filename': getattr(file_obj, 'name', None),
        'size': getattr(file_obj, 'size', None),
        'content_type': getattr(file_obj, 'content_type', None),
    }
    log_history(ticket, actor, action, 'attachment', new=meta['filename'], metadata=meta)
