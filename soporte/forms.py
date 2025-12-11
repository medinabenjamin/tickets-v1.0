from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UsernameField
from django.contrib.auth.models import Group, User
from django.utils.text import slugify

from .models import Adjunto, Comment, PerfilUsuario, Prioridad, RoleInfo, Ticket


class TicketForm(forms.ModelForm):
    adjunto = forms.FileField(required=False, label="Adjuntar archivo")

    class Meta:
        model = Ticket
        fields = [
            'titulo',
            'categoria',
            'prioridad',
            'area_funcional',
            'descripcion',
            'fecha_compromiso_respuesta',
            'estado_sla',
        ]
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 6}),
            'fecha_compromiso_respuesta': forms.DateTimeInput(attrs={'readonly': True}),
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
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

        if self.user and not self.user.is_staff:
            hidden_fields = [
                'categoria',
                'prioridad',
                'fecha_compromiso_respuesta',
                'estado_sla',
            ]
            for field_name in hidden_fields:
                if field_name in self.fields:
                    self.fields[field_name].widget = forms.HiddenInput()
                    self.fields[field_name].required = False

            if 'categoria' in self.fields and not self.fields['categoria'].initial:
                self.fields['categoria'].initial = Ticket._meta.get_field('categoria').default
            if 'prioridad' in self.fields and not self.fields['prioridad'].initial:
                default_prioridad = prioridades_qs.first()
                if default_prioridad:
                    self.fields['prioridad'].initial = default_prioridad

    def clean(self):
        cleaned_data = super().clean()
        if self.user and not self.user.is_staff:
            if 'categoria' in self.fields and not cleaned_data.get('categoria'):
                cleaned_data['categoria'] = (
                    self.fields['categoria'].initial
                    or Ticket._meta.get_field('categoria').default
                )
            if 'prioridad' in self.fields:
                prioridades_qs = self.fields['prioridad'].queryset
                prioridad_default = (
                    cleaned_data.get('prioridad')
                    or self.fields['prioridad'].initial
                    or prioridades_qs.first()
                )
                cleaned_data['prioridad'] = prioridad_default
        return cleaned_data


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


class RoleForm(forms.ModelForm):
    descripcion = forms.CharField(
        label="Descripción del rol",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
    )

    class Meta:
        model = Group
        fields = ["name"]
        labels = {"name": "Nombre del rol"}
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        info = getattr(self.instance, "info", None)
        if info:
            self.fields["descripcion"].initial = info.descripcion

    def save(self, commit=True):
        group = super().save(commit=commit)
        descripcion = self.cleaned_data.get("descripcion", "")
        if commit:
            info, _ = RoleInfo.objects.get_or_create(group=group)
            info.descripcion = descripcion
            info.save()
        return group


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
    es_critico = forms.BooleanField(
        required=False,
        label="Usuario crítico",
        help_text="Si está activo, los tickets creados por este usuario se destacarán en la lista.",
    )
    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all().order_by("name"),
        required=False,
        label="Roles",
        help_text="Selecciona uno o más roles para el usuario.",
        widget=forms.SelectMultiple(attrs={"class": "form-select", "size": 6}),
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'is_active', 'es_critico', 'groups']
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
        es_critico = self.cleaned_data.get('es_critico', False)
        if commit:
            user.save()
            groups = self.cleaned_data.get('groups')
            if groups is not None:
                user.groups.set(groups)
            perfil, _ = PerfilUsuario.objects.get_or_create(user=user)
            if perfil.es_critico != es_critico:
                perfil.es_critico = es_critico
                perfil.save(update_fields=['es_critico'])
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
    es_critico = forms.BooleanField(
        required=False,
        label="Usuario crítico",
        help_text="Los tickets del usuario aparecerán destacados si esta opción está marcada.",
    )
    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all().order_by("name"),
        required=False,
        label="Roles",
        help_text="Asigna uno o más roles al usuario.",
        widget=forms.SelectMultiple(attrs={"class": "form-select", "size": 6}),
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'is_active', 'es_critico', 'groups']
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
            self.fields['groups'].initial = self.instance.groups.all()
            try:
                self.fields['es_critico'].initial = self.instance.perfil.es_critico
            except PerfilUsuario.DoesNotExist:
                PerfilUsuario.objects.get_or_create(user=self.instance)
                self.fields['es_critico'].initial = False

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
        es_critico = self.cleaned_data.get('es_critico', False)
        if password:
            user.set_password(password)
        if commit:
            user.save()
            groups = self.cleaned_data.get('groups')
            if groups is not None:
                user.groups.set(groups)
            perfil, _ = PerfilUsuario.objects.get_or_create(user=user)
            if perfil.es_critico != es_critico:
                perfil.es_critico = es_critico
                perfil.save(update_fields=['es_critico'])
            Ticket.objects.filter(solicitante=user).update(solicitante_critico=es_critico)
        return user
