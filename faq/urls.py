# faq/urls.py

from django.urls import path

from . import views

urlpatterns = [
    # ¡El nombre 'lista_faqs' es crucial, ya que lo usamos en base.html!
    path('', views.lista_faqs, name='lista_faqs'),
    path('nueva/', views.faq_crear, name='faq_crear'),
    path('<int:pk>/editar/', views.faq_editar, name='faq_editar'),
    path('<int:pk>/eliminar/', views.faq_eliminar, name='faq_eliminar'),
]