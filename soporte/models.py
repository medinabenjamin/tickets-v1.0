"""Modelos de la aplicación de soporte."""
import os
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class PerfilUsuario(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="perfil",
        verbose_name="Usuario",
    )
    es_critico = models.BooleanField(
        default=False,
        verbose_name="Usuario crítico",
        help_text="Si está marcado, los tickets de este usuario tendrán prioridad visible.",
    )

    class Meta:
        verbose_name = "Perfil de usuario"
        verbose_name_plural = "Perfiles de usuario"

    def __str__(self):
        return f"Perfil de {self.user.username}"


class Prioridad(models.Model):
    """Nivel de prioridad disponible para los tickets."""

    clave = models.SlugField(
        max_length=50,
        unique=True,
        verbose_name="Identificador",
        help_text=(
            "Nombre corto sin espacios usado internamente para referirse a la prioridad. "
            "Por ejemplo: 'baja', 'media', 'alta'."
        ),
    )
    nombre = models.CharField(max_length=100, unique=True, verbose_name="Nombre")
    minutos_resolucion = models.PositiveIntegerField(
        verbose_name="Tiempo objetivo (minutos)",
        help_text="Tiempo máximo estimado para resolver un ticket con esta prioridad.",
    )
    orden = models.PositiveIntegerField(
        default=0,
        verbose_name="Orden",
        help_text="Se utiliza para ordenar las prioridades en los listados.",
    )

    class Meta:
        ordering = ["orden", "nombre"]
        verbose_name = "Prioridad de SLA"
        verbose_name_plural = "Prioridades de SLA"

    def __str__(self):
        return self.nombre


class Ticket(models.Model):
    """Ticket de soporte con información de SLA."""

    AREA_CHOICES = [
        ('finanzas', 'Finanzas'),
        ('rrhh', 'Recursos Humanos (RRHH)'),
        ('ventas', 'Ventas'),
        ('marketing', 'Marketing'),
        ('produccion', 'Producción/Operaciones'),
        ('ti', 'Tecnología de la Información (TI)'),
        ('general', 'General/Administración'),
    ]

    CATEGORIA_CHOICES = [
        ('soporte', 'Soporte Técnico'),
        ('consulta', 'Consulta'),
        ('incidencia', 'Incidencia'),
        ('solicitud', 'Solicitud'),
    ]

    TIPO_CHOICES = [
        ('incidencia', 'Incidencia'),
        ('solicitud', 'Solicitud'),
    ]

    ESTADO_CHOICES = [
        ('abierto', 'Abierto'),
        ('progreso', 'En Progreso'),
        ('resuelto', 'Resuelto'),
        ('cerrado', 'Cerrado'),
    ]

    SLA_ESTADO_PENDIENTE = 'pendiente'
    SLA_ESTADO_VENCIDO = 'vencido'
    SLA_ESTADO_CUMPLIDO = 'cumplido'
    SLA_ESTADO_SIN_REGLA = 'sin_regla'

    SLA_ESTADO_CHOICES = [
        (SLA_ESTADO_PENDIENTE, 'Pendiente'),
        (SLA_ESTADO_VENCIDO, 'Vencido'),
        (SLA_ESTADO_CUMPLIDO, 'Cumplido'),
        (SLA_ESTADO_SIN_REGLA, 'Sin regla'),
    ]

    titulo = models.CharField(max_length=200)
    descripcion = models.TextField()
    solicitante = models.ForeignKey(User, on_delete=models.CASCADE, related_name="tickets")
    solicitante_critico = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name="Solicitante crítico",
        help_text="Indica si el solicitante es marcado como crítico al momento de registrar el ticket.",
    )
    tecnico_asignado = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tickets_asignados",
    )

    categoria = models.CharField(max_length=50, choices=CATEGORIA_CHOICES, default='soporte')
    prioridad = models.ForeignKey(
        Prioridad,
        on_delete=models.PROTECT,
        related_name="tickets",
        verbose_name="Prioridad",
    )
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='abierto')
    tipo_ticket = models.CharField(
        max_length=20,
        choices=TIPO_CHOICES,
        default='incidencia',
        verbose_name="Tipo de Ticket",
    )
    area_funcional = models.CharField(
        max_length=20,
        choices=AREA_CHOICES,
        default='general',
        verbose_name="Área Solicitante",
    )

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    fecha_cierre = models.DateTimeField(null=True, blank=True)
    tiempo_resolucion = models.DurationField(
        null=True,
        blank=True,
        verbose_name="Tiempo de Resolución",
    )
    fecha_compromiso_respuesta = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Compromiso de respuesta",
    )
    estado_sla = models.CharField(
        max_length=20,
        choices=SLA_ESTADO_CHOICES,
        default=SLA_ESTADO_SIN_REGLA,
        verbose_name="Estado del SLA",
    )

    def save(self, *args, **kwargs):
        if self.solicitante_id:
            self.solicitante_critico = self._obtener_estado_critico_solicitante()
        if self.estado in ['resuelto', 'cerrado'] and not self.fecha_cierre:
            self.fecha_cierre = timezone.now()
            if self.fecha_creacion:
                self.tiempo_resolucion = self.fecha_cierre - self.fecha_creacion
        elif self.estado not in ['resuelto', 'cerrado'] and self.fecha_cierre:
            self.fecha_cierre = None
            self.tiempo_resolucion = None

        super().save(*args, **kwargs)

        regla, minutos_objetivo, fecha_compromiso, estado_sla = self._calcular_datos_sla()
        needs_update = False
        if self.fecha_compromiso_respuesta != fecha_compromiso:
            self.fecha_compromiso_respuesta = fecha_compromiso
            needs_update = True
        if self.estado_sla != estado_sla:
            self.estado_sla = estado_sla
            needs_update = True

        if needs_update:
            super().save(update_fields=['fecha_compromiso_respuesta', 'estado_sla'])

        SLACalculo.objects.update_or_create(
            ticket=self,
            defaults={
                'regla': regla,
                'minutos_objetivo': minutos_objetivo,
                'fecha_compromiso': fecha_compromiso,
                'estado': estado_sla,
            },
        )

    def __str__(self):
        return f"[{self.prioridad}] {self.titulo}"

    def _calcular_datos_sla(self):
        regla = self._obtener_regla_sla()
        if regla:
            minutos_objetivo = regla.minutos_objetivo
        elif self.prioridad:
            minutos_objetivo = self.prioridad.minutos_resolucion
        else:
            minutos_objetivo = None

        if not minutos_objetivo:
            return None, None, None, self.SLA_ESTADO_SIN_REGLA
        base_datetime = self.fecha_creacion or timezone.now()
        fecha_compromiso = base_datetime + timedelta(minutes=minutos_objetivo)
        estado_sla = self._determinar_estado_sla(fecha_compromiso)
        return regla, minutos_objetivo, fecha_compromiso, estado_sla

    def _obtener_estado_critico_solicitante(self):
        try:
            return self.solicitante.perfil.es_critico
        except (AttributeError, PerfilUsuario.DoesNotExist):
            perfil, _ = PerfilUsuario.objects.get_or_create(user=self.solicitante)
            return perfil.es_critico

    def _obtener_regla_sla(self):
        if not self.prioridad or not self.tipo_ticket:
            return None
        try:
            return SLARegla.objects.get(prioridad=self.prioridad, tipo_ticket=self.tipo_ticket)
        except SLARegla.DoesNotExist:
            return None

    def _determinar_estado_sla(self, fecha_compromiso):
        if not fecha_compromiso:
            return self.SLA_ESTADO_SIN_REGLA
        if self.estado in ['resuelto', 'cerrado']:
            cierre = self.fecha_cierre or timezone.now()
            if cierre <= fecha_compromiso:
                return self.SLA_ESTADO_CUMPLIDO
            return self.SLA_ESTADO_VENCIDO
        if timezone.now() > fecha_compromiso:
            return self.SLA_ESTADO_VENCIDO
        return self.SLA_ESTADO_PENDIENTE


class SLARegla(models.Model):
    """Regla que define el tiempo objetivo de respuesta para un SLA."""

    prioridad = models.ForeignKey(
        Prioridad,
        on_delete=models.CASCADE,
        related_name="reglas",
        verbose_name="Prioridad",
    )
    tipo_ticket = models.CharField(max_length=20, choices=Ticket.TIPO_CHOICES)
    minutos_objetivo = models.PositiveIntegerField()

    class Meta:
        unique_together = ('prioridad', 'tipo_ticket')
        verbose_name = "Regla de SLA"
        verbose_name_plural = "Reglas de SLA"

    def __str__(self):
        return f"{self.prioridad.nombre} - {self.get_tipo_ticket_display()} ({self.minutos_objetivo} min)"


class SLACalculo(models.Model):
    """Resultado del cálculo del SLA para un ticket."""

    ticket = models.OneToOneField('Ticket', on_delete=models.CASCADE, related_name='sla_calculo')
    regla = models.ForeignKey(
        SLARegla,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='calculos',
    )
    minutos_objetivo = models.PositiveIntegerField(null=True, blank=True)
    fecha_compromiso = models.DateTimeField(null=True, blank=True)
    estado = models.CharField(
        max_length=20,
        choices=Ticket.SLA_ESTADO_CHOICES,
        default=Ticket.SLA_ESTADO_SIN_REGLA,
    )
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Cálculo de SLA"
        verbose_name_plural = "Cálculos de SLA"

    def __str__(self):
        return f"SLA Ticket #{self.ticket_id}: {self.get_estado_display()}"


class Comment(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="comments")
    text = models.TextField()
    adjunto = models.FileField(upload_to='adjuntos_comentarios/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comentario de {self.author.username} en {self.ticket.titulo}"

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
        return any(self.archivo.name.lower().endswith(ext) for ext in image_extensions)


class TicketHistory(models.Model):
    class Action(models.TextChoices):
        STATUS = "STATUS", _("Estado")
        PRIORITY = "PRIORITY", _("Prioridad")
        ASSIGNEE = "ASSIGNEE", _("Técnico")
        TITLE = "TITLE", _("Título")
        DESCRIPTION = "DESCRIPTION", _("Descripción")
        CATEGORY = "CATEGORY", _("Categoría")
        AREA = "AREA", _("Área")
        ATTACH_ADD = "ATTACH_ADD", _("Adjunto agregado")
        ATTACH_DEL = "ATTACH_DEL", _("Adjunto eliminado")
        COMMENT = "COMMENT", _("Comentario")

    ticket = models.ForeignKey('soporte.Ticket', on_delete=models.CASCADE, related_name='historial')
    actor = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='acciones_tickets',
    )
    action = models.CharField(max_length=20, choices=Action.choices)
    field = models.CharField(max_length=30, blank=True, default="")
    old_value = models.TextField(blank=True, default="")
    new_value = models.TextField(blank=True, default="")
    metadata = models.JSONField(blank=True, default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['ticket', 'created_at']),
            models.Index(fields=['ticket', 'action']),
        ]
        verbose_name = "Historial de ticket"
        verbose_name_plural = "Historial de tickets"


@receiver(post_save, sender=User)
def crear_perfil_usuario(sender, instance, created, **kwargs):
    if created:
        PerfilUsuario.objects.create(user=instance)
    else:
        PerfilUsuario.objects.get_or_create(user=instance)


class RoleInfo(models.Model):
    group = models.OneToOneField(
        Group,
        on_delete=models.CASCADE,
        related_name='info',
        verbose_name='Rol',
    )
    descripcion = models.TextField(blank=True, default='', verbose_name='Descripción del rol')

    class Meta:
        verbose_name = 'Información de rol'
        verbose_name_plural = 'Información de roles'

    def __str__(self):
        return f"Información de {self.group.name}"


@receiver(post_save, sender=Group)
def crear_roleinfo_si_no_existe(sender, instance, created, **kwargs):
    if created:
        RoleInfo.objects.create(group=instance)
    else:
        RoleInfo.objects.get_or_create(group=instance)
