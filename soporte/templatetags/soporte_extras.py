from datetime import timedelta

from django import template
from django.utils import timezone

register = template.Library()


@register.filter
def countdown(value):
    """Devuelve un string legible con el tiempo restante hasta ``value``."""
    if not value:
        return ""
    now = timezone.now()
    if isinstance(value, (int, float)):
        target = now + timedelta(seconds=value)
    else:
        target = value
    delta = target - now
    total_seconds = int(delta.total_seconds())
    sign = "-" if total_seconds < 0 else ""
    total_seconds = abs(total_seconds)
    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours or days:
        parts.append(f"{hours}h")
    parts.append(f"{minutes}m")
    return sign + " ".join(parts)
