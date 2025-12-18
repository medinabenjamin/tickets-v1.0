import re

from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.utils.translation import gettext as _

ALLOWED_IMAGE_EXTENSIONS = ["jpg", "jpeg", "png"]
IMAGE_ACCEPT_ATTR = ",".join(f".{ext}" for ext in ALLOWED_IMAGE_EXTENSIONS)
image_file_validator = FileExtensionValidator(
    allowed_extensions=ALLOWED_IMAGE_EXTENSIONS,
    message=_("Solo se permiten archivos JPG, JPEG o PNG."),
)


class StrongPasswordValidator:
    """Custom validator to enforce strong passwords with multiple character sets."""

    def __init__(self, min_length=12):
        self.min_length = min_length

    def validate(self, password, user=None):
        errors = []
        if len(password) < self.min_length:
            errors.append(
                _(f"La contraseña debe tener al menos {self.min_length} caracteres.")
            )
        if not re.search(r"[A-Z]", password):
            errors.append(_("La contraseña debe incluir al menos una letra mayúscula."))
        if not re.search(r"[a-z]", password):
            errors.append(_("La contraseña debe incluir al menos una letra minúscula."))
        if not re.search(r"\d", password):
            errors.append(_("La contraseña debe incluir al menos un número."))
        if not re.search(r"[^\w\s]", password):
            errors.append(_("La contraseña debe incluir al menos un símbolo."))
        if errors:
            raise ValidationError(errors)

    def get_help_text(self):
        return _(
            "Tu contraseña debe tener al menos {min_length} caracteres y contener "
            "mayúsculas, minúsculas, números y símbolos."
        ).format(min_length=self.min_length)
