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


class FAQPaso(models.Model):
    faq = models.ForeignKey('FAQ', related_name='pasos', on_delete=models.CASCADE)
    orden = models.PositiveIntegerField(default=1)
    descripcion = models.TextField(blank=True)
    adjunto = models.FileField(upload_to='faq/', blank=True, null=True)

    class Meta:
        ordering = ['orden']

    def __str__(self):
        return f"Paso {self.orden} - {self.faq}"