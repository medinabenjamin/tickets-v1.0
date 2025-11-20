from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UsernameField
from django.contrib.auth.models import User
from django.utils.text import slugify

from .models import Adjunto, Comment, Prioridad, Ticket
from .roles import (
    ROLE_CHOICES,
    assign_role_to_user,
    get_user_role,
)


class TicketForm(forms.ModelForm):
    adjunto = forms.FileField(required=False, label="Adjuntar archivo")

    class Meta:
        model = Ticket
        fields = [
            'titulo',
            'categoria',
            'prioridad',
            'tipo_ticket',
            'area_funcional',
            'descripcion',
            'fecha_compromiso_respuesta',
            'estado_sla',
        ]
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 6}),
            'fecha_compromiso_respuesta': forms.DateTimeInput(attrs={'readonly': True}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['fecha_compromiso_respuesta'].disabled = True
        self.fields['estado_sla'].disabled = True
        prioridades_qs = Prioridad.objects.order_by("orden", "nombre")
        self.fields['prioridad'].queryset = prioridades_qs
        self.fields['prioridad'].empty_label = None
        if not self.instance.pk and not self.initial.get('prioridad'):
            default_prioridad = prioridades_qs.first()
            if default_prioridad:
                self.fields['prioridad'].initial = default_prioridad


class TechTicketForm(forms.ModelForm):
    """Formulario para que el técnico edite el estado y la prioridad del ticket."""

    class Meta:
        model = Ticket
        fields = [
            "estado",
            "prioridad",
            "tecnico_asignado",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['prioridad'].queryset = Prioridad.objects.order_by("orden", "nombre")
        self.fields['prioridad'].empty_label = None
        User = get_user_model()
        self.fields['tecnico_asignado'].queryset = (
            User.objects.filter(is_staff=True)
            .order_by('first_name', 'last_name', 'username')
        )


class PrioridadForm(forms.ModelForm):
    """Formulario para crear y actualizar prioridades de SLA."""

    class Meta:
        model = Prioridad
        fields = [
            "nombre",
            "clave",
            "minutos_resolucion",
            "orden",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            existing_class = field.widget.attrs.get('class', '')
            clases = f"{existing_class} form-control".strip()
            field.widget.attrs['class'] = clases

    def clean_clave(self):
        clave = slugify(self.cleaned_data['clave'])
        if not clave:
            raise forms.ValidationError("Ingresa un identificador válido.")
        return clave


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
    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        label="Rol del usuario",
        initial="solicitante",
        help_text="Define los permisos que el usuario heredará automáticamente.",
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'is_active']
        field_classes = {'username': UsernameField}
        labels = {
            'username': 'Nombre de usuario',
            'email': 'Correo electrónico',
            'first_name': 'Nombre',
            'last_name': 'Apellido',
            'is_active': 'Usuario activo',
        }
        help_texts = {
            'username': 'Requerido. Máximo 150 caracteres. Solo letras, números y los símbolos @/./+/-/_.',
            'is_active': 'Controla si el usuario puede iniciar sesión en la plataforma.',
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
            assign_role_to_user(user, self.cleaned_data['role'])
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
    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        label="Rol del usuario",
        help_text="Actualiza los permisos heredados asignando un rol diferente.",
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'is_active']
        field_classes = {'username': UsernameField}
        labels = {
            'username': 'Nombre de usuario',
            'email': 'Correo electrónico',
            'first_name': 'Nombre',
            'last_name': 'Apellido',
            'is_active': 'Usuario activo',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['role'].initial = get_user_role(self.instance)

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
            assign_role_to_user(user, self.cleaned_data['role'])
        return user
