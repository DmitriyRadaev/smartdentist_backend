"""
URL configuration for smartdentist_backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
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
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include, re_path
from django.views.static import serve
from django.conf import settings
from main import views
from main.views import UserProfileView

urlpatterns = [
    path('admin/', admin.site.urls),
    # Авторизация
    path("api/login/", views.loginView, name="login"),
    path("api/logout/", views.logoutView, name="logout"),
    path("api/refresh_token/", views.CookieTokenRefreshView.as_view(), name="token_refresh"),

    # Регистрация
    path("api/register/worker/", views.WorkerRegisterView.as_view(), name="worker_register"),
    path("api/register/admin/", views.AdminRegisterView.as_view(), name="admin_register"),
    # Профиль
    path('api/account/profile/', UserProfileView.as_view(), name='current-user-profile'), # GET: Получить данные текущего пользователя

    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)