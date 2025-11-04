"""
URL configuration for tickets project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from soporte.views import dashboard
from django.contrib.auth import views as auth_views
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path('', lambda r: redirect('dashboard') if r.user.is_authenticated else redirect('login')),
    path("", include("soporte.urls")),  # <- conecta la app soporte
    path("accounts/", include("django.contrib.auth.urls")),
    path('reportes/', include('reportes.urls')),
    path('faq/', include('faq.urls')),
    # tickets/urls.py

    # ...
    # This URL now points directly to the logout view
    path('accounts/logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    # You can also add the login view here
    path('accounts/login/', auth_views.LoginView.as_view(), name='login'),
    # ...
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    