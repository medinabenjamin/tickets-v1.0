# soporte/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import logout, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages # <--- IMPORTACIÓN AÑADIDA
from django.db.models import Avg, Count, Max, ProtectedError, Q
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.models import Group, Permission, User
from django.core.paginator import Paginator
from django.http import HttpResponse, HttpResponseForbidden
import csv
from .models import Ticket, Comment, Adjunto, Prioridad
from .forms import (
    TicketForm,
    CommentForm,
    TechTicketForm,
    UserCreateForm,
    UserUpdateForm,
    PrioridadForm,
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

def es_personal_sla(user):
    return user.is_staff


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
        return redirect('dashboard_principal')
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
        tickets_list = tickets_list.filter(prioridad__clave=prioridad_filter)
    tecnico_filter = request.GET.get('tecnico')
    if request.user.is_staff and tecnico_filter:
        tickets_list = tickets_list.filter(tecnico_asignado__username=tecnico_filter)
    search_query = request.GET.get('search') or request.GET.get('q')
    if search_query:
        tickets_list = tickets_list.filter(Q(titulo__icontains=search_query) | Q(descripcion__icontains=search_query))
    tickets = tickets_list.select_related('prioridad', 'solicitante', 'tecnico_asignado')

    sort = request.GET.get('sort')
    direction = request.GET.get('dir', 'asc')
    sort_map = {
        'prioridad': 'prioridad__orden',
        'estado': 'estado',
        'solicitante': 'solicitante__username',
        'tecnico': 'tecnico_asignado__username',
        'fecha_creacion': 'fecha_creacion',
    }

    if sort in sort_map:
        order_field = sort_map[sort]
        if direction == 'desc':
            order_field = '-' + order_field
        tickets = tickets.order_by(order_field, '-fecha_creacion')
    else:
        tickets = tickets.order_by('-fecha_creacion')

    base_querydict = request.GET.copy()
    for param in ['sort', 'dir']:
        if param in base_querydict:
            base_querydict.pop(param)
    base_query = base_querydict.urlencode()
    context = {
        "tickets": tickets,
        "estados": Ticket.ESTADO_CHOICES,
        "prioridades": Prioridad.objects.order_by("orden", "nombre"),
        "tecnicos": User.objects.filter(is_staff=True),
        "selected_estado": estado_filter,
        "selected_prioridad": prioridad_filter,
        "selected_tecnico": tecnico_filter,
        "search_query": search_query,
        "sort": sort,
        "dir": direction,
        "direction": direction,
        "base_query": base_query,
    }
    return render(request, "soporte/home.html", context)

@login_required
def detalle_ticket(request, ticket_id):
    ticket = _obtener_ticket_autorizado(request, ticket_id)
    if ticket is None:
        return redirect('home_tickets')
    comments = _comentarios_ticket(ticket)
    form_acciones = TechTicketForm(instance=ticket)
    comment_form = CommentForm()
    if request.method == "POST":
        if 'tech_form_submit' in request.POST:
            if not request.user.is_staff:
                return HttpResponseForbidden()
            form_acciones = TechTicketForm(request.POST, instance=ticket)
            if form_acciones.is_valid():
                prioridad_cambiada = 'prioridad' in form_acciones.changed_data
                form_acciones.save()
                if prioridad_cambiada:
                    ticket.refresh_from_db(fields=['fecha_compromiso_respuesta', 'estado_sla'])
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
        'comment_form': comment_form,
        'form_acciones': form_acciones,
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
        form = TicketForm(request.POST, request.FILES, user=request.user)
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
        form = TicketForm(user=request.user)
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

    tickets_resueltos = Ticket.objects.filter(
        estado__in=['resuelto', 'cerrado'],
        tiempo_resolucion__isnull=False,
    )
    promedio_resolucion_timedelta = tickets_resueltos.aggregate(
        promedio=Avg('tiempo_resolucion')
    ).get('promedio')
    promedio_resolucion = None
    if promedio_resolucion_timedelta:
        total_seconds = int(promedio_resolucion_timedelta.total_seconds())
        horas, remainder = divmod(total_seconds, 3600)
        minutos, _ = divmod(remainder, 60)
        promedio_resolucion = f"{horas} horas {minutos} minutos"

    tickets_por_tecnico = (
        Ticket.objects.exclude(tecnico_asignado__isnull=True)
        .values('tecnico_asignado__username')
        .annotate(total=Count('id'))
        .order_by('-total')
    )

    sla_resumen = (
        Ticket.objects.values('estado_sla')
        .annotate(total=Count('id'))
        .order_by('estado_sla')
    )
    tickets_recientes = (
        Ticket.objects.select_related('prioridad', 'solicitante')
        .all()
        .order_by('-fecha_creacion')[:5]
    )
    tickets_por_estado = list(Ticket.objects.values('estado').annotate(total=Count('estado')))
    tickets_por_prioridad_qs = (
        Ticket.objects.values('prioridad__nombre', 'prioridad__clave')
        .annotate(total=Count('prioridad'))
        .order_by('prioridad__orden', 'prioridad__nombre')
    )
    tickets_por_prioridad = [
        {
            'nombre': entry['prioridad__nombre'],
            'clave': entry['prioridad__clave'],
            'total': entry['total'],
        }
        for entry in tickets_por_prioridad_qs
    ]
    context = {
        'total_tickets': total_tickets, 'tickets_abiertos': tickets_abiertos,
        'tickets_en_progreso': tickets_en_progreso, 'tickets_cerrados': tickets_cerrados,
        'tickets_recientes': tickets_recientes, 'tickets_por_estado': tickets_por_estado,
        'tickets_por_prioridad': tickets_por_prioridad, 'promedio_resolucion': promedio_resolucion,
        'tickets_por_tecnico': tickets_por_tecnico, 'sla_resumen': sla_resumen,
    }
    return render(request, 'soporte/dashboard.html', context)


# --- GESTIÓN DE SLA ---


@login_required
@user_passes_test(es_personal_sla)
def lista_prioridades_sla(request):
    prioridades = Prioridad.objects.order_by("orden", "nombre")
    return render(
        request,
        'soporte/sla_prioridad_list.html',
        {
            'prioridades': prioridades,
        },
    )


@login_required
@user_passes_test(es_personal_sla)
def crear_prioridad_sla(request):
    if request.method == 'POST':
        form = PrioridadForm(request.POST)
        if form.is_valid():
            prioridad = form.save()
            messages.success(
                request,
                f"Prioridad '{prioridad.nombre}' creada correctamente.",
            )
            return redirect('sla_prioridades')
    else:
        next_order = (
            Prioridad.objects.aggregate(max_orden=Max('orden')).get('max_orden') or 0
        )
        form = PrioridadForm(initial={'orden': next_order + 1})
    return render(
        request,
        'soporte/sla_prioridad_form.html',
        {
            'form': form,
            'titulo': 'Crear prioridad',
        },
    )


@login_required
@user_passes_test(es_personal_sla)
def editar_prioridad_sla(request, prioridad_id):
    prioridad = get_object_or_404(Prioridad, id=prioridad_id)
    if request.method == 'POST':
        form = PrioridadForm(request.POST, instance=prioridad)
        if form.is_valid():
            prioridad_actualizada = form.save()
            messages.success(
                request,
                f"Prioridad '{prioridad_actualizada.nombre}' actualizada correctamente.",
            )
            return redirect('sla_prioridades')
    else:
        form = PrioridadForm(instance=prioridad)
    return render(
        request,
        'soporte/sla_prioridad_form.html',
        {
            'form': form,
            'prioridad': prioridad,
            'titulo': 'Editar prioridad',
        },
    )


@login_required
@user_passes_test(es_personal_sla)
def eliminar_prioridad_sla(request, prioridad_id):
    prioridad = get_object_or_404(Prioridad, id=prioridad_id)
    if request.method == 'POST':
        nombre = prioridad.nombre
        try:
            prioridad.delete()
        except ProtectedError:
            messages.error(
                request,
                "No es posible eliminar la prioridad porque existen tickets asociados.",
            )
        else:
            messages.success(request, f"Prioridad '{nombre}' eliminada correctamente.")
        return redirect('sla_prioridades')
    return render(
        request,
        'soporte/sla_prioridad_confirm_delete.html',
        {
            'prioridad': prioridad,
        },
    )

# --- VISTAS DE MANTENEDOR (¡ACTUALIZADAS!) ---

@login_required
@user_passes_test(lambda u: u.is_staff)
def mantenedor_usuarios(request):
    """Listado de usuarios con filtros, ordenamiento y paginación."""

    query = request.GET.get('q', '').strip()
    role_filter = request.GET.get('role') or ''
    is_active_param = request.GET.get('is_active')
    order = request.GET.get('order', '-date_joined')

    allowed_orders = {
        'username', '-username', 'email', '-email',
        'date_joined', '-date_joined', 'last_login', '-last_login',
    }
    if order not in allowed_orders:
        order = '-date_joined'

    usuarios_qs = (
        User.objects.select_related()
        .prefetch_related('groups')
        .order_by(order)
    )

    if query:
        usuarios_qs = usuarios_qs.filter(
            Q(username__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(email__icontains=query)
        )

    if role_filter:
        usuarios_qs = usuarios_qs.filter(groups__name=role_filter)

    if is_active_param in ('0', '1'):
        usuarios_qs = usuarios_qs.filter(is_active=bool(int(is_active_param)))

    paginator = Paginator(usuarios_qs, 15)
    try:
        page_number = int(request.GET.get('page', 1))
    except (TypeError, ValueError):
        page_number = 1
    page_obj = paginator.get_page(page_number)

    start_index = (page_obj.number - 1) * paginator.per_page + 1 if paginator.count else 0
    end_index = start_index + len(page_obj.object_list) - 1 if paginator.count else 0

    base_querydict = request.GET.copy()
    if 'page' in base_querydict:
        base_querydict.pop('page')
    base_query = base_querydict.urlencode()

    order_toggles = {}
    for field in ['username', 'email', 'date_joined', 'last_login']:
        if order == field:
            order_toggles[field] = f'-{field}'
        elif order == f'-{field}':
            order_toggles[field] = field
        else:
            order_toggles[field] = field

    context = {
        'page_obj': page_obj,
        'total': paginator.count,
        'query': query,
        'role_filter': role_filter,
        'is_active_filter': is_active_param,
        'order': order,
        'order_toggles': order_toggles,
        'roles_disponibles': Group.objects.order_by('name').values_list('name', flat=True),
        'start_index': start_index,
        'end_index': end_index,
        'base_query': base_query,
    }
    return render(request, 'soporte/usuarios_list.html', context)


@login_required
@user_passes_test(lambda u: u.is_staff)
def crear_usuario(request):
    """Renderiza el formulario de creación de usuarios y procesa el guardado."""

    if request.method == 'POST':
        form = UserCreateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Usuario creado correctamente.")
            return redirect('mantenedor_usuarios')
    else:
        form = UserCreateForm()

    context = {
        'form': form,
        'is_edit': False,
    }
    return render(request, 'soporte/usuario_form.html', context)


@login_required
@user_passes_test(lambda u: u.is_staff)
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
        'is_edit': True,
    }
    return render(request, 'soporte/usuario_form.html', context)


@login_required
@user_passes_test(lambda u: u.is_staff)
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


@login_required
@user_passes_test(lambda u: u.is_staff)
def roles_list(request):
    query = request.GET.get('q', '').strip()
    roles_qs = Group.objects.annotate(total_usuarios=Count('user')).order_by('name')
    if query:
        roles_qs = roles_qs.filter(name__icontains=query)

    paginator = Paginator(roles_qs, 15)
    try:
        page_number = int(request.GET.get('page', 1))
    except (TypeError, ValueError):
        page_number = 1
    page_obj = paginator.get_page(page_number)

    base_querydict = request.GET.copy()
    if 'page' in base_querydict:
        base_querydict.pop('page')
    base_query = base_querydict.urlencode()

    start_index = page_obj.start_index() if paginator.count else 0
    end_index = page_obj.end_index() if paginator.count else 0

    context = {
        'page_obj': page_obj,
        'query': query,
        'base_query': base_query,
        'start_index': start_index,
        'end_index': end_index,
    }
    return render(request, 'soporte/roles_list.html', context)


@login_required
@user_passes_test(lambda u: u.is_staff)
def rol_crear(request):
    permisos = Permission.objects.select_related('content_type').order_by('content_type__app_label', 'name')
    permisos_agrupados = {}
    for perm in permisos:
        permisos_agrupados.setdefault(perm.content_type.app_label, []).append(perm)

    if request.method == 'POST':
        nombre = request.POST.get('name', '').strip()
        if not nombre:
            messages.error(request, 'El nombre del rol es obligatorio.')
        else:
            grupo = Group.objects.create(name=nombre)
            seleccionados = request.POST.getlist('permissions')
            grupo.permissions.set(seleccionados)
            messages.success(request, 'Rol creado correctamente.')
            return redirect('roles_list')

    context = {
        'permisos_agrupados': permisos_agrupados,
        'titulo': 'Crear rol',
        'permisos_actuales': set(),
    }
    return render(request, 'soporte/rol_form.html', context)


@login_required
@user_passes_test(lambda u: u.is_staff)
def rol_editar(request, pk):
    grupo = get_object_or_404(Group, pk=pk)
    permisos = Permission.objects.select_related('content_type').order_by('content_type__app_label', 'name')
    permisos_agrupados = {}
    for perm in permisos:
        permisos_agrupados.setdefault(perm.content_type.app_label, []).append(perm)

    permisos_actuales = set(grupo.permissions.values_list('id', flat=True))

    if request.method == 'POST':
        nombre = request.POST.get('name', '').strip()
        if not nombre:
            messages.error(request, 'El nombre del rol es obligatorio.')
        else:
            grupo.name = nombre
            grupo.save()
            seleccionados = request.POST.getlist('permissions')
            grupo.permissions.set(seleccionados)
            messages.success(request, 'Rol actualizado correctamente.')
            return redirect('roles_list')

    context = {
        'grupo': grupo,
        'permisos_agrupados': permisos_agrupados,
        'permisos_actuales': permisos_actuales,
        'titulo': 'Editar rol',
    }
    return render(request, 'soporte/rol_form.html', context)


@login_required
@user_passes_test(lambda u: u.is_staff)
def rol_eliminar(request, pk):
    grupo = get_object_or_404(Group, pk=pk)
    usuarios_asociados = grupo.user_set.count()

    if request.method == 'POST':
        nombre = grupo.name
        grupo.delete()
        messages.success(request, f"Rol '{nombre}' eliminado correctamente.")
        return redirect('roles_list')

    context = {
        'grupo': grupo,
        'usuarios_asociados': usuarios_asociados,
    }
    return render(request, 'soporte/rol_confirm_delete.html', context)


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
            ticket.get_estado_display(), ticket.prioridad.nombre,
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