# faq/views.py
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import FAQForm, FAQPasoFormSet
from .models import FAQ


def is_staff(user):
    return user.is_staff


@login_required
def lista_faqs(request):
    search_query = request.GET.get('q', '')

    if request.user.is_staff:
        faqs_queryset = FAQ.objects.all()
    else:
        faqs_queryset = FAQ.objects.filter(activo=True)

    if search_query:
        faqs_queryset = faqs_queryset.filter(
            Q(pregunta__icontains=search_query) | Q(respuesta__icontains=search_query)
        )

    faqs = faqs_queryset.order_by('id').prefetch_related('pasos')

    context = {
        'faqs': faqs,
        'search_query': search_query,
    }
    return render(request, 'faq/lista_faqs.html', context)


@login_required
@user_passes_test(is_staff)
def faq_crear(request):
    if request.method == 'POST':
        form = FAQForm(request.POST, request.FILES)
        formset = FAQPasoFormSet(request.POST, request.FILES)
        if form.is_valid() and formset.is_valid():
            faq = form.save(commit=False)
            faq.save()
            formset.instance = faq

            pasos = formset.save(commit=False)
            for p in formset.deleted_objects:
                p.delete()

            idx = 1
            for p in pasos:
                p.orden = idx
                p.faq = faq
                p.save()
                idx += 1

            messages.success(request, 'Pregunta frecuente creada.')
            return redirect('lista_faqs')
    else:
        form = FAQForm()
        formset = FAQPasoFormSet()
    return render(request, 'faq/faq_form.html', {'form': form, 'formset': formset, 'modo': 'crear'})


@login_required
@user_passes_test(is_staff)
def faq_editar(request, pk):
    faq = get_object_or_404(FAQ, pk=pk)
    if request.method == 'POST':
        form = FAQForm(request.POST, request.FILES, instance=faq)
        formset = FAQPasoFormSet(request.POST, request.FILES, instance=faq)
        if form.is_valid() and formset.is_valid():
            faq = form.save(commit=False)
            faq.save()
            formset.instance = faq

            pasos = formset.save(commit=False)
            for p in formset.deleted_objects:
                p.delete()

            idx = 1
            for p in pasos:
                p.orden = idx
                p.faq = faq
                p.save()
                idx += 1

            messages.success(request, 'Pregunta frecuente actualizada.')
            return redirect('lista_faqs')
    else:
        form = FAQForm(instance=faq)
        formset = FAQPasoFormSet(instance=faq)
    return render(request, 'faq/faq_form.html', {'form': form, 'formset': formset, 'modo': 'editar'})


@login_required
@user_passes_test(is_staff)
def faq_eliminar(request, pk):
    faq = get_object_or_404(FAQ, pk=pk)
    if request.method == 'POST':
        faq.delete()
        messages.success(request, 'Pregunta frecuente eliminada.')
        return redirect('lista_faqs')
    return render(request, 'faq/faq_confirm_delete.html', {'faq': faq})