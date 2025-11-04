from django import forms
from django.contrib.auth.forms import UsernameField
from django.contrib.auth.models import Group, Permission, User

from .models import Adjunto, Comment, Ticket


class TicketForm(forms.ModelForm):
    adjunto = forms.FileField(required=False, label="Adjuntar archivo")

    class Meta:
        model = Ticket
        fields = ['titulo', 'categoria', 'prioridad', 'tipo_ticket', 'area_funcional', 'descripcion']
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 6}),
        }


class TechTicketForm(forms.ModelForm):
    """Formulario para que el técnico edite el estado y la prioridad del ticket."""

    class Meta:
        model = Ticket
        fields = ["estado", "prioridad"]


class CommentForm(forms.ModelForm):
    """Formulario para agregar comentarios a un ticket."""

    class Meta:
        model = Comment
        fields = ['text', 'adjunto']
        widgets = {
            'text': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Escribe tu respuesta o actualización aquí...'}),
            'adjunto': forms.FileInput(attrs={'class': 'form-control form-control-sm'}),
        }
        labels = {
            'text': 'Comentario:',
            'adjunto': 'Adjuntar archivo (Opcional):'
        }


class UserCreateForm(forms.ModelForm):
    """Formulario para crear un nuevo usuario con validación de contraseña."""

    password = forms.CharField(
        widget=forms.PasswordInput,
        label="Contraseña",
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput,
        label="Confirmar contraseña",
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active', 'is_superuser']
        field_classes = {'username': UsernameField}
        labels = {
            'username': 'Nombre de usuario',
            'email': 'Correo electrónico',
            'first_name': 'Nombre',
            'last_name': 'Apellido',
            'is_staff': 'Miembro del personal',
            'is_active': 'Usuario activo',
            'is_superuser': 'Superusuario',
        }
        help_texts = {
            'username': 'Requerido. Máximo 150 caracteres. Solo letras, números y los símbolos @/./+/-/_.',
            'is_staff': 'Permite que el usuario acceda a las herramientas internas del sistema.',
            'is_active': 'Controla si el usuario puede iniciar sesión en la plataforma.',
            'is_superuser': 'Otorga todos los permisos disponibles sin restricciones.',
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")
        if password and password_confirm and password != password_confirm:
            self.add_error('password_confirm', "Las contraseñas no coinciden.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user


class UserUpdateForm(forms.ModelForm):
    """Formulario para editar un usuario y, opcionalmente, actualizar su contraseña."""

    password = forms.CharField(
        widget=forms.PasswordInput,
        label="Nueva contraseña",
        required=False,
        help_text="Déjalo en blanco si no deseas cambiarla.",
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput,
        label="Confirmar contraseña",
        required=False,
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active', 'is_superuser']
        field_classes = {'username': UsernameField}
        labels = {
            'username': 'Nombre de usuario',
            'email': 'Correo electrónico',
            'first_name': 'Nombre',
            'last_name': 'Apellido',
            'is_staff': 'Miembro del personal',
            'is_active': 'Usuario activo',
            'is_superuser': 'Superusuario',
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")
        if password or password_confirm:
            if password != password_confirm:
                self.add_error('password_confirm', "Las contraseñas no coinciden.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('password')
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return user


class UserPermissionForm(forms.ModelForm):
    """Formulario para asignar grupos y permisos específicos a un usuario."""

    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all().order_by('name'),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Grupos",
        help_text="Selecciona uno o más grupos para asignar permisos de manera conjunta.",
    )
    user_permissions = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.select_related('content_type').order_by('content_type__app_label', 'codename'),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Permisos individuales",
        help_text="Marca los permisos específicos que el usuario debe tener directamente.",
    )

    class Meta:
        model = User
        fields = ['groups', 'user_permissions']
