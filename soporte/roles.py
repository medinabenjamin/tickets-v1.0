"""Utilities to centralize user role management and related permissions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

from django.contrib.auth.models import Group, Permission, User
from django.db import transaction


@dataclass(frozen=True)
class RoleDefinition:
    key: str
    label: str
    description: str
    badge_class: str
    is_staff: bool
    is_superuser: bool
    group_name: Optional[str]
    permissions: Tuple[Tuple[str, str], ...]


ROLE_DEFINITIONS: Dict[str, RoleDefinition] = {
    "solicitante": RoleDefinition(
        key="solicitante",
        label="Solicitante",
        description="Puede crear tickets y consultar el estado de sus solicitudes.",
        badge_class="bg-primary",
        is_staff=False,
        is_superuser=False,
        group_name="Solicitantes",
        permissions=(),
    ),
    "agente": RoleDefinition(
        key="agente",
        label="Agente de soporte",
        description="Gestiona los tickets asignados y puede interactuar con los solicitantes.",
        badge_class="bg-secondary",
        is_staff=True,
        is_superuser=False,
        group_name="Agentes de soporte",
        permissions=(
            ("soporte", "view_ticket"),
            ("soporte", "add_ticket"),
            ("soporte", "change_ticket"),
            ("soporte", "delete_ticket"),
            ("soporte", "view_comment"),
            ("soporte", "add_comment"),
            ("soporte", "change_comment"),
            ("soporte", "delete_comment"),
            ("soporte", "view_adjunto"),
            ("soporte", "add_adjunto"),
            ("soporte", "change_adjunto"),
            ("soporte", "delete_adjunto"),
        ),
    ),
    "administrador": RoleDefinition(
        key="administrador",
        label="Administrador",
        description="Administra el sistema completo y posee todos los permisos.",
        badge_class="bg-dark",
        is_staff=True,
        is_superuser=True,
        group_name=None,
        permissions=(),
    ),
}

ROLE_CHOICES: Tuple[Tuple[str, str], ...] = tuple(
    (role.key, role.label) for role in ROLE_DEFINITIONS.values()
)


def _fetch_permissions(permissions: Iterable[Tuple[str, str]]) -> List[Permission]:
    """Return the list of Permission instances given (app_label, codename) tuples."""

    permission_objects: List[Permission] = []
    for app_label, codename in permissions:
        try:
            permission_objects.append(
                Permission.objects.get(
                    content_type__app_label=app_label,
                    codename=codename,
                )
            )
        except Permission.DoesNotExist:
            # Silently ignore missing permissions to keep the workflow resilient.
            continue
    return permission_objects


def _sync_group_permissions(group: Group, permissions: Iterable[Tuple[str, str]]) -> None:
    """Ensure the Django Group stores exactly the permissions for the role."""

    desired_permissions = _fetch_permissions(permissions)
    group.permissions.set(desired_permissions)


def ensure_role_group(role_key: str) -> Optional[Group]:
    """Create or update the backing group for the given role, if it uses one."""

    role = ROLE_DEFINITIONS[role_key]
    if not role.group_name:
        return None
    group, _ = Group.objects.get_or_create(name=role.group_name)
    _sync_group_permissions(group, role.permissions)
    return group


def assign_role_to_user(user: User, role_key: str) -> User:
    """Assign the given role to the user, updating staff flags and permissions."""

    if role_key not in ROLE_DEFINITIONS:
        raise ValueError(f"Rol desconocido: {role_key}")

    role = ROLE_DEFINITIONS[role_key]

    with transaction.atomic():
        user.groups.clear()
        user.user_permissions.clear()
        user.is_staff = role.is_staff
        user.is_superuser = role.is_superuser
        user.save(update_fields=["is_staff", "is_superuser"])

        group = ensure_role_group(role_key)
        if group is not None:
            user.groups.add(group)

    return user


def get_user_role(user: User) -> str:
    """Return the identifier of the role currently assigned to the user."""

    if user.is_superuser:
        return "administrador"

    for role in ROLE_DEFINITIONS.values():
        if not role.group_name:
            continue
        if user.groups.filter(name=role.group_name).exists():
            return role.key

    # Default fallback role.
    return "solicitante"


def get_role_label(role_key: str) -> str:
    return ROLE_DEFINITIONS[role_key].label


def get_role_badge_class(role_key: str) -> str:
    return ROLE_DEFINITIONS[role_key].badge_class


def get_role_description(role_key: str) -> str:
    return ROLE_DEFINITIONS[role_key].description
