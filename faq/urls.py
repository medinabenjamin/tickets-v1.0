# faq/urls.py

from django.urls import path
from .views import lista_faqs

urlpatterns = [
    # ¡El nombre 'lista_faqs' es crucial, ya que lo usamos en base.html!
    path('', lista_faqs, name='lista_faqs'), 
]