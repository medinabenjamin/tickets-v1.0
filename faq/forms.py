from django import forms
from django.forms import inlineformset_factory
from .models import FAQ, FAQPaso


class FAQForm(forms.ModelForm):
    class Meta:
        model = FAQ
        fields = ['pregunta', 'respuesta', 'categoria', 'activo']
        widgets = {
            'pregunta': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Título de la pregunta'}),
            'respuesta': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Describe la respuesta o el contexto'}),
            'categoria': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Categoría'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class FAQPasoForm(forms.ModelForm):
    class Meta:
        model = FAQPaso
        fields = ['orden', 'descripcion', 'adjunto']
        widgets = {
            'orden': forms.HiddenInput(),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Describe el paso...'}),
            'adjunto': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['orden'].required = False


FAQPasoFormSet = inlineformset_factory(
    FAQ,
    FAQPaso,
    form=FAQPasoForm,
    extra=1,
    can_delete=True,
    validate_min=False,
)
