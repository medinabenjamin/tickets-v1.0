from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from .forms import CommentForm, TicketForm
from .models import Area, Prioridad


class AttachmentValidationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="usuario", password="segura123!")
        self.prioridad = Prioridad.objects.create(
            nombre="Alta",
            clave="alta",
            minutos_resolucion=60,
            orden=1,
        )
        self.area = Area.objects.create(
            nombre="TI",
            clave="ti",
            orden=1,
        )

    def test_ticket_form_rejects_non_image_attachment(self):
        form_data = {
            "titulo": "Problema de red",
            "descripcion": "No hay conexión a Internet.",
        }
        archivo = SimpleUploadedFile(
            "malicioso.exe",
            b"contenido ejecutable",
            content_type="application/octet-stream",
        )
        form = TicketForm(data=form_data, files={"adjunto": archivo}, user=self.user)

        self.assertFalse(form.is_valid())
        self.assertIn("adjunto", form.errors)

    def test_ticket_form_accepts_allowed_image(self):
        form_data = {
            "titulo": "Problema de red",
            "descripcion": "No hay conexión a Internet.",
        }
        archivo = SimpleUploadedFile(
            "captura.png",
            b"contenido de imagen",
            content_type="image/png",
        )
        form = TicketForm(data=form_data, files={"adjunto": archivo}, user=self.user)

        self.assertTrue(form.is_valid())

    def test_comment_form_rejects_non_image_attachment(self):
        archivo = SimpleUploadedFile(
            "script.exe",
            b"contenido ejecutable",
            content_type="application/octet-stream",
        )
        form = CommentForm(data={"text": "Comentario con adjunto"}, files={"adjunto": archivo})

        self.assertFalse(form.is_valid())
        self.assertIn("adjunto", form.errors)

    def test_comment_form_accepts_allowed_image(self):
        archivo = SimpleUploadedFile(
            "comentario.jpeg",
            b"contenido de imagen",
            content_type="image/jpeg",
        )
        form = CommentForm(data={"text": "Comentario con imagen"}, files={"adjunto": archivo})

        self.assertTrue(form.is_valid())
