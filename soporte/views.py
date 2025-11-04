# soporte/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import logout, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages # <--- IMPORTACIÓN AÑADIDA
from django.db.models import Count, Q, Avg
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.models import User
from django.http import HttpResponse
import csv
from .models import Ticket, Comment, Adjunto
from .forms import (
    TicketForm,
    CommentForm,
    TechTicketForm,
    UserCreateForm,
    UserUpdateForm,
)
from .roles import (
    ROLE_DEFINITIONS,
    get_role_badge_class,
    get_role_label,
    get_user_role,
)
import logging

# Importaciones para PDF
from django.template.loader import get_template

# Configura el logger para la aplicación
logger = logging.getLogger(__name__)

# --- FUNCIONES AUXILIARES ---
def enviar_notificacion_correo(subject, message, recipient_list):
    try:
        send_mail(subject, message, settings.EMAIL_HOST_USER, recipient_list, fail_silently=False)
        logger.info(f"Correo enviado exitosamente a: {recipient_list}")
    except Exception as e:
        logger.error(f"Error al enviar el correo: {e}")

def es_superusuario(user):
    return user.is_superuser


def _obtener_ticket_autorizado(request, ticket_id):
    """Devuelve el ticket si el usuario tiene permisos para verlo."""
    ticket = get_object_or_404(Ticket, id=ticket_id)
    if not request.user.is_staff and ticket.solicitante != request.user:
        return None
    return ticket


def _comentarios_ticket(ticket, orden='-created_at'):
    """Retorna los comentarios de un ticket en el orden especificado."""
    return Comment.objects.filter(ticket=ticket).order_by(orden)
    
# --- VISTAS PRINCIPALES ---
@login_required
def inicio(request):
    """Redirige al usuario según su rol."""
    if not request.user.is_authenticated:
        return redirect('login') 
    if request.user.is_staff:
        return redirect('dashboard')
    else:
        return redirect('crear_ticket')

@login_required
def home(request):
    tickets_list = Ticket.objects.all()
    if not request.user.is_staff:
        tickets_list = tickets_list.filter(solicitante=request.user)
    estado_filter = request.GET.get('estado')
    if estado_filter:
        tickets_list = tickets_list.filter(estado=estado_filter)
    prioridad_filter = request.GET.get('prioridad')
    if prioridad_filter:
        tickets_list = tickets_list.filter(prioridad=prioridad_filter)
    tecnico_filter = request.GET.get('tecnico')
    if request.user.is_staff and tecnico_filter:
        tickets_list = tickets_list.filter(tecnico_asignado__username=tecnico_filter)
    search_query = request.GET.get('q')
    if search_query:
        tickets_list = tickets_list.filter(Q(titulo__icontains=search_query) | Q(descripcion__icontains=search_query))
    tickets = tickets_list.order_by('-fecha_creacion')
    context = {
        "tickets": tickets, "estados": Ticket.ESTADO_CHOICES, "prioridades": Ticket.PRIORIDAD_CHOICES,
        "tecnicos": User.objects.filter(is_staff=True), "selected_estado": estado_filter,
        "selected_prioridad": prioridad_filter, "selected_tecnico": tecnico_filter, "search_query": search_query,
    }
    return render(request, "soporte/home.html", context)

@login_required
def detalle_ticket(request, ticket_id):
    ticket = _obtener_ticket_autorizado(request, ticket_id)
    if ticket is None:
        return redirect('home_tickets')
    comments = _comentarios_ticket(ticket)
    tech_form = TechTicketForm(instance=ticket)
    comment_form = CommentForm()
    if request.method == "POST":
        if 'tech_form_submit' in request.POST and request.user.is_staff:
            tech_form = TechTicketForm(request.POST, instance=ticket)
            if tech_form.is_valid():
                tech_form.save()
                return redirect('detalle_ticket', ticket_id=ticket.id)
        elif 'cerrar_ticket_submit' in request.POST and request.user.is_staff:
            ticket.estado = 'cerrado'
            ticket.save()
            return redirect('detalle_ticket', ticket_id=ticket.id)
        elif 'comment_form_submit' in request.POST:
            comment_form = CommentForm(request.POST, request.FILES)
            if comment_form.is_valid():
                new_comment = comment_form.save(commit=False)
                new_comment.ticket = ticket
                new_comment.author = request.user
                new_comment.save()
                if ticket.solicitante != request.user:
                    pass # Lógica de notificación
                return redirect('detalle_ticket', ticket_id=ticket.id)
    context = {
        'ticket': ticket, 'comments': comments,
        'comment_form': comment_form, 'tech_form': tech_form,
    }
    return render(request, "soporte/detalle_ticket.html", context)

@login_required
def vista_previa_imprimir(request, ticket_id):
    ticket = _obtener_ticket_autorizado(request, ticket_id)
    if ticket is None:
        return redirect('home_tickets')
    comments = _comentarios_ticket(ticket, orden='created_at')
    context = {'ticket': ticket, 'comments': comments}
    return render(request, "soporte/imprimir_ticket.html", context)

@login_required
def exportar_ticket_pdf(request, ticket_id):
    from weasyprint import HTML

    ticket = _obtener_ticket_autorizado(request, ticket_id)
    if ticket is None:
        return redirect('home_tickets')
    comments = _comentarios_ticket(ticket, orden='created_at')
    template = get_template("soporte/imprimir_ticket.html")
    context = {'ticket': ticket, 'comments': comments}
    html_string = template.render(context)
    pdf_file = HTML(string=html_string).write_pdf()
    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="ticket_{ticket.id}.pdf"'
    return response

@login_required
def crear_ticket(request):
    if request.method == "POST":
        form = TicketForm(request.POST, request.FILES) 
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.solicitante = request.user
            ticket.estado = 'abierto'
            tecnico_disponible = User.objects.filter(is_staff=True).order_by('?').first()
            if tecnico_disponible:
                ticket.tecnico_asignado = tecnico_disponible
            ticket.save()
            archivo_adjunto = form.cleaned_data.get('adjunto')
            if archivo_adjunto:
                Adjunto.objects.create(ticket=ticket, archivo=archivo_adjunto, subido_por=request.user)
            return redirect('home_tickets')
    else:
        form = TicketForm()
    return render(request, "soporte/crear_ticket.html", {'form': form})

@login_required
def editar_ticket(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id, solicitante=request.user)
    if request.method == "POST":
        form = TicketForm(request.POST, instance=ticket)
        if form.is_valid():
            form.save()
            return redirect('detalle_ticket', ticket_id=ticket.id)
    else:
        form = TicketForm(instance=ticket)
    return render(request, "soporte/editar_ticket.html", {"form": form})

@login_required
def dashboard(request):
    if not request.user.is_staff:
        return redirect('crear_ticket')
    total_tickets = Ticket.objects.count()
    tickets_abiertos = Ticket.objects.filter(estado='abierto').count()
    tickets_en_progreso = Ticket.objects.filter(estado='progreso').count()
    tickets_cerrados = Ticket.objects.filter(estado__in=['resuelto', 'cerrado']).count()
    tickets_recientes = Ticket.objects.all().order_by('-fecha_creacion')[:5]
    tickets_por_estado = list(Ticket.objects.values('estado').annotate(total=Count('estado')))
    tickets_por_prioridad = list(Ticket.objects.values('prioridad').annotate(total=Count('prioridad')))
    context = {
        'total_tickets': total_tickets, 'tickets_abiertos': tickets_abiertos,
        'tickets_en_progreso': tickets_en_progreso, 'tickets_cerrados': tickets_cerrados,
        'tickets_recientes': tickets_recientes, 'tickets_por_estado': tickets_por_estado,
        'tickets_por_prioridad': tickets_por_prioridad,
    }
    return render(request, 'soporte/dashboard.html', context)

# --- VISTAS DE MANTENEDOR (¡ACTUALIZADAS!) ---

@login_required
@user_passes_test(es_superusuario)
def mantenedor_usuarios(request):
    """Muestra el listado de usuarios y permite crear nuevos registros."""

    if request.method == 'POST':
        form = UserCreateForm(request.POST)
        if form.is_valid():
            usuario = form.save()
            messages.success(request, f"Usuario {usuario.username} creado exitosamente.")
            return redirect('mantenedor_usuarios')
    else:
        form = UserCreateForm()

    usuarios_qs = User.objects.all().order_by('username').prefetch_related('groups')
    usuarios = list(usuarios_qs)
    for usuario in usuarios:
        role_key = get_user_role(usuario)
        usuario.role_key = role_key
        usuario.role_label = get_role_label(role_key)
        usuario.role_badge = get_role_badge_class(role_key)
    context = {
        'usuarios': usuarios,
        'form': form,
        'role_definitions': ROLE_DEFINITIONS,
    }
    return render(request, 'soporte/mantenedor_usuarios.html', context)


@login_required
@user_passes_test(es_superusuario)
def editar_usuario(request, user_id):
    usuario = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, instance=usuario)
        if form.is_valid():
            usuario_actualizado = form.save()
            if usuario_actualizado == request.user:
                update_session_auth_hash(request, usuario_actualizado)
            messages.success(request, f"Usuario {usuario_actualizado.username} actualizado correctamente.")
            return redirect('mantenedor_usuarios')
    else:
        form = UserUpdateForm(instance=usuario)

    context = {
        'form': form,
        'usuario': usuario,
    }
    return render(request, 'soporte/editar_usuario.html', context)


@login_required
@user_passes_test(es_superusuario)
def eliminar_usuario(request, user_id):
    usuario = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        if usuario == request.user:
            messages.error(request, 'No puedes eliminar tu propia cuenta mientras estás autenticado.')
            return redirect('mantenedor_usuarios')
        username = usuario.username
        usuario.delete()
        messages.success(request, f'Usuario {username} eliminado correctamente.')
        return redirect('mantenedor_usuarios')

    context = {'usuario': usuario}
    return render(request, 'soporte/confirmar_eliminar_usuario.html', context)


# --- VISTAS DE EXPORTACIÓN ---
@login_required
def exportar_tickets_csv(request):
    if not request.user.is_staff:
        return redirect('home_tickets') 
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="reporte_tickets.csv"'
    response.write(u'\ufeff'.encode('utf8'))
    writer = csv.writer(response)
    writer.writerow(['ID', 'Título', 'Descripción', 'Solicitante', 'Técnico', 'Estado', 'Prioridad', 'Categoría', 'Tipo', 'Área', 'Creación', 'Resolución'])
    for ticket in Ticket.objects.all().order_by('-fecha_creacion'):
        writer.writerow([
            ticket.id, ticket.titulo, ticket.descripcion, ticket.solicitante.username,
            ticket.tecnico_asignado.username if ticket.tecnico_asignado else '-',
            ticket.get_estado_display(), ticket.get_prioridad_display(),
            ticket.get_categoria_display(), ticket.get_tipo_ticket_display(),
            ticket.get_area_funcional_display(),
            ticket.fecha_creacion.strftime('%Y-%m-%d %H:%M'),
            str(ticket.tiempo_resolucion).split('.')[0] if ticket.tiempo_resolucion else '-'
        ])
    return response

# --- VISTAS DE PERFIL DE USUARIO ---
@login_required
def ver_perfil(request):
    return render(request, 'soporte/perfil.html')

@login_required
def cambiar_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, '¡Tu contraseña ha sido actualizada exitosamente!')
            return redirect('ver_perfil')
        else:
            messages.error(request, 'Por favor corrige los errores.')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'soporte/cambiar_password.html', {'form': form})

# --- AUTENTICACIÓN ---
def salir(request):
    logout(request)
    return redirect('login')