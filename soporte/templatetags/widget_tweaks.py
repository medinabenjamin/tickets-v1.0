"""Minimal replacements for the django-widget-tweaks helpers used in the project.

This module provides a drop-in alternative for the small subset of the
``django-widget-tweaks`` API that is referenced from the templates.  The
project only relies on the ``render_field`` template tag to add CSS classes
and other HTML attributes when rendering form fields.  Shipping this
lightweight implementation keeps the templates working without introducing a
runtime dependency that was missing from the environment.
"""

from __future__ import annotations

from django import template
from django.utils.html import mark_safe

register = template.Library()


def _merge_attrs(original: dict[str, str], updates: dict[str, str]) -> dict[str, str]:
    """Return a new attribute dictionary combining ``original`` and ``updates``.

    When both dictionaries contain a ``class`` entry we append the new value so
    existing CSS hooks are not lost.  All other attributes are overwritten by
    the explicit value supplied from the template tag call.
    """

    merged = original.copy()
    for attr, value in updates.items():
        if attr == "class" and attr in merged:
            merged[attr] = f"{merged[attr]} {value}".strip()
        else:
            merged[attr] = value
    return merged


@register.simple_tag
def render_field(bound_field, **attrs):
    """Render ``bound_field`` while applying extra HTML attributes.

    The helper mirrors the behaviour provided by ``django-widget-tweaks`` for
    the ``render_field`` tag which is widely used throughout the templates.
    ``bound_field`` is rendered with any attributes passed in the template and
    the resulting HTML is marked as safe because it originates from Django's
    own form widgets.
    """

    widget_attrs = getattr(bound_field.field.widget, "attrs", {})
    final_attrs = _merge_attrs(widget_attrs, attrs)
    return mark_safe(bound_field.as_widget(attrs=final_attrs))
