from django import forms
from django.contrib.auth import get_user_model, password_validation
from django.contrib.auth.forms import UsernameField
from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.utils.safestring import mark_safe
from django.utils.text import slugify

from .models import Adjunto, Area, Comment, PerfilUsuario, Prioridad, RoleInfo, Ticket


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

        areas_qs = Area.objects.order_by("orden", "nombre")
        self.fields['area_funcional'].queryset = areas_qs
        self.fields['area_funcional'].empty_label = None
        if not self.instance.pk and not self.initial.get('area_funcional'):
            default_area = areas_qs.first()
            if default_area:
                self.fields['area_funcional'].initial = default_area

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
            if 'area_funcional' in self.fields and not self.fields['area_funcional'].initial:
                default_area = areas_qs.first()
                if default_area:
                    self.fields['area_funcional'].initial = default_area

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
            if 'area_funcional' in self.fields and not cleaned_data.get('area_funcional'):
                cleaned_data['area_funcional'] = (
                    self.fields['area_funcional'].initial
                    or self.fields['area_funcional'].queryset.first()
                )
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


class AreaForm(forms.ModelForm):
    """Formulario para crear y actualizar áreas funcionales."""

    class Meta:
        model = Area
        fields = [
            "nombre",
            "clave",
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


def _normalizar_rut(valor: str) -> str:
    """Devuelve el RUT en formato canónico sin puntos y con guion."""

    rut_limpio = valor.replace(".", "").replace("-", "").strip().upper()
    if len(rut_limpio) < 2:
        return rut_limpio
    cuerpo, dv = rut_limpio[:-1], rut_limpio[-1]
    return f"{cuerpo}-{dv}"


def rut_es_valido(valor: str) -> bool:
    """Valida el dígito verificador del RUT chileno."""

    rut_limpio = valor.replace(".", "").replace("-", "").strip().upper()
    if len(rut_limpio) < 2 or not rut_limpio[:-1].isdigit():
        return False

    cuerpo, dv_ingresado = rut_limpio[:-1], rut_limpio[-1]
    multiplicador = 2
    suma = 0
    for digito in reversed(cuerpo):
        suma += int(digito) * multiplicador
        multiplicador = 2 if multiplicador == 7 else multiplicador + 1

    resto = 11 - (suma % 11)
    if resto == 11:
        dv_calculado = "0"
    elif resto == 10:
        dv_calculado = "K"
    else:
        dv_calculado = str(resto)

    return dv_ingresado == dv_calculado


class UserCreateForm(forms.ModelForm):
    """Formulario para crear un nuevo usuario con validación de contraseña."""

    password = forms.CharField(
        widget=forms.PasswordInput,
        label="Contraseña",
        help_text=password_validation.password_validators_help_text_html(),
    )
    rut = forms.CharField(
        label="RUT",
        help_text="Ingresa el RUT sin puntos y con guion. Ejemplo: 12345678-5",
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
        if password:
            try:
                password_validation.validate_password(password)
            except ValidationError as e:
                self.add_error('password', e)
        return cleaned_data

    def clean_rut(self):
        rut = self.cleaned_data.get("rut", "")
        rut_normalizado = _normalizar_rut(rut)

        if not rut_normalizado or "-" not in rut_normalizado:
            raise forms.ValidationError("Ingresa un RUT válido con guion.")
        if not rut_es_valido(rut_normalizado):
            raise forms.ValidationError("El RUT ingresado no es válido.")

        if PerfilUsuario.objects.filter(rut=rut_normalizado).exists():
            raise forms.ValidationError("Ya existe un usuario con este RUT.")

        return rut_normalizado

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
            perfil_actualizado = False
            rut = self.cleaned_data.get("rut")
            if rut and perfil.rut != rut:
                perfil.rut = rut
                perfil_actualizado = True
            if perfil.es_critico != es_critico:
                perfil.es_critico = es_critico
                perfil_actualizado = True
            if perfil_actualizado:
                perfil.save(update_fields=['rut', 'es_critico'])
        return user


class UserUpdateForm(forms.ModelForm):
    """Formulario para editar un usuario y, opcionalmente, actualizar su contraseña."""

    password = forms.CharField(
        widget=forms.PasswordInput,
        label="Nueva contraseña",
        required=False,
        help_text=mark_safe(
            "Déjalo en blanco si no deseas cambiarla.<br>" +
            password_validation.password_validators_help_text_html()
        ),
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput,
        label="Confirmar contraseña",
        required=False,
    )
    rut = forms.CharField(
        label="RUT",
        help_text="Ingresa el RUT sin puntos y con guion. Ejemplo: 12345678-5",
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
                self.fields['rut'].initial = self.instance.perfil.rut or ''
            except PerfilUsuario.DoesNotExist:
                PerfilUsuario.objects.get_or_create(user=self.instance)
                self.fields['es_critico'].initial = False
                self.fields['rut'].initial = ''

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")
        if password or password_confirm:
            if password != password_confirm:
                self.add_error('password_confirm', "Las contraseñas no coinciden.")
            if password:
                try:
                    password_validation.validate_password(password, self.instance)
                except ValidationError as e:
                    self.add_error('password', e)
        return cleaned_data

    def clean_rut(self):
        rut = self.cleaned_data.get("rut", "")
        rut_normalizado = _normalizar_rut(rut)

        if not rut_normalizado or "-" not in rut_normalizado:
            raise forms.ValidationError("Ingresa un RUT válido con guion.")
        if not rut_es_valido(rut_normalizado):
            raise forms.ValidationError("El RUT ingresado no es válido.")

        perfil_qs = PerfilUsuario.objects.filter(rut=rut_normalizado)
        if self.instance and self.instance.pk:
            perfil_qs = perfil_qs.exclude(user=self.instance)
        if perfil_qs.exists():
            raise forms.ValidationError("Ya existe un usuario con este RUT.")

        return rut_normalizado

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('password')
        es_critico = self.cleaned_data.get('es_critico', False)
        rut = self.cleaned_data.get('rut')
        if password:
            user.set_password(password)
        if commit:
            user.save()
            groups = self.cleaned_data.get('groups')
            if groups is not None:
                user.groups.set(groups)
            perfil, _ = PerfilUsuario.objects.get_or_create(user=user)
            perfil_actualizado = False
            if perfil.es_critico != es_critico:
                perfil.es_critico = es_critico
                perfil_actualizado = True
            if rut and perfil.rut != rut:
                perfil.rut = rut
                perfil_actualizado = True
            if perfil_actualizado:
                perfil.save(update_fields=['rut', 'es_critico'])
            Ticket.objects.filter(solicitante=user).update(solicitante_critico=es_critico)
        return user
