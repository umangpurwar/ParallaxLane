"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
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
from accounts.views import CustomLoginView
from django.conf import settings
from django.conf.urls.static import static
from accounts.views import health_check
from rest_framework_simplejwt.views import TokenRefreshView


urlpatterns = [
    path("admin/", admin.site.urls),

    path("api/accounts/", include("accounts.urls")),
    
    path("api/exams/", include("exams.urls")),

    path("api/monitoring/", include("monitoring.urls")),

    path("api/admin/", include("admin_panel.urls")),

    path("api/master-admin/", include("admin_panel.master_admin_urls")),

    path("api/login/", CustomLoginView.as_view()),

    path('api/organisations/', include('organisations.urls')),

    path('api/health/', health_check, name='health_check'),

    path("api/token/refresh/", TokenRefreshView.as_view()),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
