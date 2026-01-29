from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include, re_path
from django.views.static import serve
from django.conf import settings
from main import views
from main.views import *

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

    # Пациенты
    path('api/patients/', PatientListAPIView.as_view()),
    path('api/patients/create/', PatientCreateAPIView.as_view()),
    path('api/patients/update/<int:pk>/', PatientUpdateAPIView.as_view()),
    path('api/patients/<int:patient_id>/cases/', PatientHistoryAPIView.as_view()),

    # Приемы
    path('api/cases/', MedicalCaseListAPIView.as_view()),
    path('api/cases/create/', MedicalCaseCreateAPIView.as_view()),
    path('api/cases/update/<int:pk>/', MedicalCaseUpdateAPIView.as_view()),
    path('api/cases/<int:case_id>/upload-dicom/', DicomUploadAndProcessView.as_view(), name='dicom-upload-process'),
    path('api/patients/<int:patient_id>/cases/<int:case_id>/', MedicalCaseDetailAPIView.as_view()),


    # Шаблоны для генерации
    path('api/library/', LibraryListAPIView.as_view(), name='library-list'),
    path('api/library/create/', LibraryCreateAPIView.as_view(), name='library-create'),


    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)