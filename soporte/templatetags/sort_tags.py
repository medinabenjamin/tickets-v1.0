from django import template

register = template.Library()


@register.simple_tag
def next_direction(current_sort, current_dir, column):
    """Return the next sorting direction for a given column."""
    if current_sort == column:
        return 'desc' if current_dir == 'asc' else 'asc'
    return 'asc'
