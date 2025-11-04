# soporte/forms.py

from django import forms
from django.contrib.auth.models import User
from .models import Ticket, Comment, Adjunto # Importa todos los modelos necesarios

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

# --- Formulario de Comentarios ACTUALIZADO ---
class CommentForm(forms.ModelForm):
    """Formulario para agregar comentarios a un ticket."""
    class Meta:
        model = Comment
        # Añadimos el nuevo campo de adjunto
        fields = ['text', 'adjunto']
        widgets = {
            'text': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Escribe tu respuesta o actualización aquí...'}),
            'adjunto': forms.FileInput(attrs={'class': 'form-control form-control-sm'}),
        }
        labels = {
            'text': 'Comentario:',
            'adjunto': 'Adjuntar archivo (Opcional):'
        }

class UserRoleForm(forms.ModelForm):
    """Formulario para que el Superusuario edite roles y estado de un usuario."""
    class Meta:
        model = User
        fields = ['is_staff', 'is_active', 'email']

# --- ¡FORMULARIO AÑADIDO PARA CREAR USUARIOS! ---
class NewUserForm(forms.ModelForm):
    """Formulario para que el Superusuario cree un nuevo usuario."""
    password = forms.CharField(
        widget=forms.PasswordInput, 
        label="Contraseña"
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput, 
        label="Confirmar Contraseña"
    )

    class Meta:
        model = User
        # Campos que el admin puede definir al crear
        fields = ['username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active']
    
    def clean_password_confirm(self):
        # Validación para asegurar que las contraseñas coincidan
        pw = self.cleaned_data.get("password")
        pw_conf = self.cleaned_data.get("password_confirm")
        if pw and pw_conf and pw != pw_conf:
            raise forms.ValidationError("Las contraseñas no coinciden.")
        return pw_conf