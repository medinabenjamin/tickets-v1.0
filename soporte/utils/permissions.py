from django.apps import apps


SPANISH_ACTIONS = {
    "add": "Crear",
    "change": "Editar",
    "delete": "Eliminar",
    "view": "Ver",
}


def get_app_verbose_name(app_label):
    app_config = apps.get_app_config(app_label)
    return app_config.verbose_name or app_label


def get_model_verbose_name(permission):
    model_class = permission.content_type.model_class()
    return model_class._meta.verbose_name if model_class else permission.content_type.model


def spanish_action_from_codename(codename_prefix):
    return SPANISH_ACTIONS.get(codename_prefix, codename_prefix.capitalize())


def spanish_permission_label(permission):
    codename_parts = permission.codename.split("_", 1)
    action = spanish_action_from_codename(codename_parts[0])
    model_verbose = get_model_verbose_name(permission)
    label = f"{action} {model_verbose}".strip()
    return label[0].upper() + label[1:]
