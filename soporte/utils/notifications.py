"""Utilidades para crear y distribuir notificaciones del sistema."""

from __future__ import annotations

from typing import Sequence

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from soporte.models import Notification

User = get_user_model()


def get_staff_notifiable_users() -> Sequence[User]:
    """Devuelve los usuarios de soporte (técnicos o administradores)."""

    return User.objects.filter(Q(is_staff=True) | Q(is_superuser=True)).distinct()


def _normalize_recipients(recipients):
    if recipients is None:
        return []
    if isinstance(recipients, (list, tuple, set)):
        return list(recipients)
    return [recipients]


def create_notification(notification_type: str, recipients, message: str, url: str, actor=None) -> None:
    """Crea notificaciones para uno o varios destinatarios."""

    users = [user for user in _normalize_recipients(recipients) if user]
    if not users:
        return

    Notification.objects.bulk_create(
        [
            Notification(
                user=user,
                actor=actor,
                type=notification_type,
                message=message,
                url=url,
                created_at=timezone.now(),
            )
            for user in users
        ]
    )


def notification_link(notification: Notification) -> str:
    """Devuelve la URL de la notificación con el parámetro para marcarla como leída."""

    if not notification.url:
        return ""

    split = urlsplit(notification.url)
    query = dict(parse_qsl(split.query))
    query["notif_id"] = str(notification.id)
    new_query = urlencode(query)
    return urlunsplit((split.scheme, split.netloc, split.path, new_query, split.fragment))

