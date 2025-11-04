# soporte/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import os # Necesario para obtener el nombre del archivo

class Ticket(models.Model):
    # Opciones de elección para el ÁREA FUNCIONAL
    AREA_CHOICES = [
        ('finanzas', 'Finanzas'),
        ('rrhh', 'Recursos Humanos (RRHH)'),
        ('ventas', 'Ventas'),
        ('marketing', 'Marketing'),
        ('produccion', 'Producción/Operaciones'),
        ('ti', 'Tecnología de la Información (TI)'),
        ('general', 'General/Administración'),
    ]

    # Opciones de elección para la categoría del ticket
    CATEGORIA_CHOICES = [
        ('soporte', 'Soporte Técnico'),
        ('consulta', 'Consulta'),
        ('incidencia', 'Incidencia'),
        ('solicitud', 'Solicitud'),
    ]
    
    # Opciones de elección para el tipo de ticket
    TIPO_CHOICES = [
        ('incidencia', 'Incidencia'),
        ('solicitud', 'Solicitud'),
    ]
    
    # Opciones de elección para la prioridad del ticket
    PRIORIDAD_CHOICES = [
        ('baja', 'Baja'),
        ('media', 'Media'),
        ('alta', 'Alta'),
        ('critica', 'Crítica'),
    ]

    # Opciones de elección para el estado del ticket
    ESTADO_CHOICES = [
        ('abierto', 'Abierto'),
        ('progreso', 'En Progreso'),
        ('resuelto', 'Resuelto'),
        ('cerrado', 'Cerrado'),
    ]

    titulo = models.CharField(max_length=200)
    descripcion = models.TextField()
    solicitante = models.ForeignKey(User, on_delete=models.CASCADE, related_name="tickets")
    tecnico_asignado = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="tickets_asignados")
    
    categoria = models.CharField(max_length=50, choices=CATEGORIA_CHOICES, default='soporte') 
    prioridad = models.CharField(max_length=20, choices=PRIORIDAD_CHOICES, default='baja')
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='abierto')
    tipo_ticket = models.CharField(max_length=20, choices=TIPO_CHOICES, default='incidencia', verbose_name="Tipo de Ticket")
    area_funcional = models.CharField(max_length=20, choices=AREA_CHOICES, default='general', verbose_name="Área Solicitante")

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    fecha_cierre = models.DateTimeField(null=True, blank=True)
    tiempo_resolucion = models.DurationField(null=True, blank=True, verbose_name="Tiempo de Resolución")

    def save(self, *args, **kwargs):
        if self.estado in ['resuelto', 'cerrado'] and not self.fecha_cierre:
            self.fecha_cierre = timezone.now()
            if self.fecha_creacion:
                self.tiempo_resolucion = self.fecha_cierre - self.fecha_creacion
        elif self.estado not in ['resuelto', 'cerrado'] and self.fecha_cierre:
            self.fecha_cierre = None
            self.tiempo_resolucion = None
        super().save(*args, **kwargs)

    def __str__(self):
        return f"[{self.prioridad}] {self.titulo}"

class Comment(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="comments") # Corregido related_name
    text = models.TextField()
    
    # --- ¡CAMPOS AÑADIDOS! ---
    adjunto = models.FileField(upload_to='adjuntos_comentarios/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comentario de {self.author.username} en {self.ticket.titulo}"

    # --- ¡MÉTODO AÑADIDO! ---
    def is_image(self):
        """Verifica si el adjunto es una imagen para mostrar vista previa."""
        if not self.adjunto:
            return False
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
        return any(self.adjunto.name.lower().endswith(ext) for ext in image_extensions)
    
class Adjunto(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='adjuntos')
    archivo = models.FileField(upload_to='adjuntos_tickets/')
    subido_por = models.ForeignKey(User, on_delete=models.CASCADE)
    fecha_subida = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return os.path.basename(self.archivo.name)

    def is_image(self):
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
        return any