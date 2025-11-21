from django import forms
from django.core.exceptions import FieldDoesNotExist
from django.db import models
from django.forms import inlineformset_factory
from .models import FAQ, FAQPaso


class FAQForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ['respuesta', 'categoria']:
            if field_name in self.fields:
                self.fields[field_name].required = False

    def clean(self):
        cleaned_data = super().clean()
        categoria_field = None

        if 'categoria' in self.fields:
            categoria_field = self._meta.model._meta.get_field('categoria')
            categoria = cleaned_data.get('categoria')

            if (categoria is None or categoria == '') and categoria_field:
                if getattr(categoria_field, 'remote_field', None):
                    categoria_model = categoria_field.remote_field.model
                    lookup_field = None
                    for candidate in ['nombre', 'name', 'titulo', 'title']:
                        try:
                            categoria_model._meta.get_field(candidate)
                            lookup_field = candidate
                            break
                        except FieldDoesNotExist:
                            continue

                    if lookup_field:
                        general, _ = categoria_model.objects.get_or_create(**{lookup_field: 'General'})
                        cleaned_data['categoria'] = general
                    else:
                        general = categoria_model.objects.first()
                        if general is None:
                            try:
                                general = categoria_model.objects.create()
                            except Exception:
                                general = None
                        cleaned_data['categoria'] = general
                else:
                    default_value = getattr(categoria_field, 'default', '')
                    cleaned_data['categoria'] = default_value if default_value is not models.NOT_PROVIDED else 'General'

        if 'respuesta' in cleaned_data:
            respuesta = cleaned_data.get('respuesta')
            if respuesta in (None, ''):
                cleaned_data['respuesta'] = ''

        return cleaned_data

    class Meta:
        model = FAQ
        fields = ['pregunta', 'respuesta', 'categoria']
        widgets = {
            'pregunta': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Título de la pregunta'}),
            'respuesta': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Describe la respuesta o el contexto'}),
            'categoria': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Categoría'}),
        }


class FAQPasoForm(forms.ModelForm):
    class Meta:
        model = FAQPaso
        fields = ['orden', 'titulo', 'descripcion', 'adjunto']
        widgets = {
            'orden': forms.HiddenInput(),
            'titulo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Título del paso'}),
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
