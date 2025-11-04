from django.db import models

# Create your models here.
# faq/models.py

from django.db import models
from django.contrib.auth.models import User

class FAQ(models.Model):
    pregunta = models.CharField(max_length=255, verbose_name="Pregunta Frecuente")
    respuesta = models.TextField(verbose_name="Respuesta")
    # Para categorizar, aunque no es obligatorio, es útil
    categoria = models.CharField(max_length=50, default='General', verbose_name="Categoría") 
    activo = models.BooleanField(default=True, verbose_name="Activo")
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Pregunta Frecuente"
        verbose_name_plural = "Preguntas Frecuentes"
    
    def __str__(self):
        return self.pregunta