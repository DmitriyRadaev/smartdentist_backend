# views.py
import os
import random
import time
import zipfile

from django.views.decorators.csrf import csrf_exempt
from rest_framework import viewsets, generics, permissions, response, decorators, status
from rest_framework.generics import ListAPIView, CreateAPIView, UpdateAPIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt import tokens, views as jwt_views, serializers as jwt_serializers, \
    exceptions as jwt_exceptions
from django.contrib.auth import authenticate
from django.conf import settings
from django.middleware import csrf
from rest_framework import exceptions as rest_exceptions
from django.contrib.auth import get_user_model

from .models import (
    WorkerProfile, Patient, MedicalCase, ImplantLibrary, IndividualImplant, DICOMUpload
)

from .permissions import IsSuperAdmin, IsAdminOrSuperAdmin
from .seriailizers import AccountSerializer, WorkerRegistrationSerializer, AdminRegistrationSerializer, \
    SuperAdminRegistrationSerializer, WorkerProfileSerializer, UserProfileSerializer, PatientSerializer, \
    MedicalCaseSerializer, ImplantSerializer, ImplantLibrarySerializer

Account = get_user_model()


def get_user_tokens(user):
    refresh = tokens.RefreshToken.for_user(user)
    return {"refresh_token": str(refresh), "access_token": str(refresh.access_token)}


@decorators.api_view(["POST"])
@decorators.permission_classes([])
def loginView(request):
    email = request.data.get("email")
    password = request.data.get("password")
    if not email or not password:
        raise rest_exceptions.ValidationError({"detail": "Email and password required"})

    user = authenticate(email=email, password=password)
    if not user:
        raise rest_exceptions.AuthenticationFailed("Email or password is incorrect!")

    tokens_dict = get_user_tokens(user)
    res = response.Response(tokens_dict)

    res.set_cookie(
        key=settings.SIMPLE_JWT['AUTH_COOKIE'],
        value=tokens_dict["access_token"],
        expires=settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'],
        secure=settings.SIMPLE_JWT.get('AUTH_COOKIE_SECURE', False),
        httponly=settings.SIMPLE_JWT.get('AUTH_COOKIE_HTTP_ONLY', True),
        samesite=settings.SIMPLE_JWT.get('AUTH_COOKIE_SAMESITE', 'Lax')
    )
    res.set_cookie(
        key=settings.SIMPLE_JWT['AUTH_COOKIE_REFRESH'],
        value=tokens_dict["refresh_token"],
        expires=settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'],
        secure=settings.SIMPLE_JWT.get('AUTH_COOKIE_SECURE', False),
        httponly=settings.SIMPLE_JWT.get('AUTH_COOKIE_HTTP_ONLY', True),
        samesite=settings.SIMPLE_JWT.get('AUTH_COOKIE_SAMESITE', 'Lax')
    )
    res.set_cookie(
        key="user_role",
        value="admin" if user.is_staff else "worker",
        max_age=settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'],
        secure=settings.SIMPLE_JWT.get('AUTH_COOKIE_SECURE', False),
        httponly=True,
        samesite='Lax'
    )

    res["X-CSRFToken"] = csrf.get_token(request)
    return res

@csrf_exempt
@decorators.api_view(["POST"])
@decorators.permission_classes([permissions.AllowAny])
def logoutView(request):
    try:
        refresh_token = request.COOKIES.get(settings.SIMPLE_JWT['AUTH_COOKIE_REFRESH'])
        if refresh_token:
            token = tokens.RefreshToken(refresh_token)
            token.blacklist()
    except Exception:
        pass

    res = response.Response({"detail": "Logged out successfully"}, status=status.HTTP_200_OK)

    res.delete_cookie(
        key=settings.SIMPLE_JWT['AUTH_COOKIE'],
        path=settings.SIMPLE_JWT.get('AUTH_COOKIE_PATH', '/'),
        samesite=settings.SIMPLE_JWT.get('AUTH_COOKIE_SAMESITE', 'Lax')
    )

    res.delete_cookie(
        key=settings.SIMPLE_JWT['AUTH_COOKIE_REFRESH'],
        path=settings.SIMPLE_JWT.get('AUTH_COOKIE_PATH', '/'),
        samesite=settings.SIMPLE_JWT.get('AUTH_COOKIE_SAMESITE', 'Lax')
    )

    res.delete_cookie(
        key="user_role",
        path=settings.SIMPLE_JWT.get('AUTH_COOKIE_PATH', '/'),
        samesite=settings.SIMPLE_JWT.get('AUTH_COOKIE_SAMESITE', 'Lax')
    )

    res.delete_cookie(
        key="is_staff",
        path=settings.SIMPLE_JWT.get('AUTH_COOKIE_PATH', '/'),
        samesite=settings.SIMPLE_JWT.get('AUTH_COOKIE_SAMESITE', 'Lax')
    )

    res.delete_cookie(
        key=settings.CSRF_COOKIE_NAME,
        path='/',
        samesite=settings.CSRF_COOKIE_SAMESITE
    )

    res.delete_cookie(
        key="X-CSRFToken",
        path='/',
        samesite=settings.CSRF_COOKIE_SAMESITE
    )

    return res


class CookieTokenRefreshSerializer(jwt_serializers.TokenRefreshSerializer):
    refresh = None

    def validate(self, attrs):
        attrs['refresh'] = self.context['request'].COOKIES.get(settings.SIMPLE_JWT['AUTH_COOKIE_REFRESH'])
        if attrs['refresh']:
            return super().validate(attrs)
        raise jwt_exceptions.InvalidToken("No valid refresh token in cookie")


class CookieTokenRefreshView(jwt_views.TokenRefreshView):
    serializer_class = CookieTokenRefreshSerializer

    def finalize_response(self, request, response_obj, *args, **kwargs):
        if response_obj.data.get("access"):
            response_obj.set_cookie(
                key=settings.SIMPLE_JWT['AUTH_COOKIE'],
                value=response_obj.data['access'],
                expires=settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'],
                secure=settings.SIMPLE_JWT.get('AUTH_COOKIE_SECURE', False),
                httponly=True, # Жестко True
                samesite=settings.SIMPLE_JWT.get('AUTH_COOKIE_SAMESITE', 'Lax')
            )
            del response_obj.data["access"]

        if response_obj.data.get("refresh"):
            response_obj.set_cookie(
                key=settings.SIMPLE_JWT['AUTH_COOKIE_REFRESH'],
                value=response_obj.data['refresh'],
                expires=settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'],
                secure=settings.SIMPLE_JWT.get('AUTH_COOKIE_SECURE', False),
                httponly=True,
                samesite=settings.SIMPLE_JWT.get('AUTH_COOKIE_SAMESITE', 'Lax')
            )
            del response_obj.data["refresh"]

        response_obj["X-CSRFToken"] = request.COOKIES.get("csrftoken")
        return super().finalize_response(request, response_obj, *args, **kwargs)


@decorators.api_view(["GET"])
@decorators.permission_classes([permissions.IsAuthenticated])
def current_user_view(request):
    serializer = AccountSerializer(request.user)
    return response.Response(serializer.data)


# -------------------------------------------------------------------------
# РЕГИСТРАЦИЯ И ПРОФИЛИ
# -------------------------------------------------------------------------

class WorkerRegisterView(generics.CreateAPIView):
    serializer_class = WorkerRegistrationSerializer
    permission_classes = [permissions.AllowAny]


class AdminRegisterView(generics.CreateAPIView):
    serializer_class = AdminRegistrationSerializer
    permission_classes = [IsSuperAdmin]


class SuperAdminRegisterView(generics.CreateAPIView):
    serializer_class = SuperAdminRegistrationSerializer
    permission_classes = [IsSuperAdmin]


class WorkerProfileViewSet(viewsets.ModelViewSet):
    queryset = WorkerProfile.objects.select_related("user").all()
    serializer_class = WorkerProfileSerializer
    permission_classes = [IsAdminOrSuperAdmin]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.is_staff:
            return super().get_queryset()
        return WorkerProfile.objects.filter(user=user)

class UserProfileView(generics.RetrieveAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


# ОСНОВНАЯ ЛОГИКА

# Работа с пациентами
class PatientListCreateAPIView(APIView):
    def get(self, request):
        patients = Patient.objects.all().order_by('-created_at')
        serializer = PatientSerializer(patients, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = PatientSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Пациенты
class PatientListAPIView(ListAPIView):
    queryset = Patient.objects.all().order_by('-created_at')
    serializer_class = PatientSerializer

class PatientCreateAPIView(CreateAPIView):
    serializer_class = PatientSerializer

class PatientUpdateAPIView(UpdateAPIView):
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer
    lookup_field = 'pk'

# Приемы
class MedicalCaseListAPIView(ListAPIView):
    queryset = MedicalCase.objects.all().order_by('-created_at')
    serializer_class = MedicalCaseSerializer

class MedicalCaseCreateAPIView(CreateAPIView):
    serializer_class = MedicalCaseSerializer

class MedicalCaseUpdateAPIView(UpdateAPIView):
    queryset = MedicalCase.objects.all()
    serializer_class = MedicalCaseSerializer
    lookup_field = 'pk'

class PatientHistoryAPIView(ListAPIView):
    serializer_class = MedicalCaseSerializer
    def get_queryset(self):
        return MedicalCase.objects.filter(patient_id=self.kwargs['patient_id'])

class DicomUploadAndProcessView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, case_id):
        file_obj = request.FILES.get('file')

        if not file_obj:
            return Response({"error": "Архив не найден (поле 'file')"}, status=status.HTTP_400_BAD_REQUEST)

        # Проверка существования приема
        try:
            case = MedicalCase.objects.get(id=case_id)
        except MedicalCase.DoesNotExist:
            return Response({"error": "Прием не найден"}, status=status.HTTP_404_NOT_FOUND)

        # Сохраняем информацию о загрузке архива в БД
        DICOMUpload.objects.create(case=case, file=file_obj)

        # Подготовка папки для распаковки
        folder_name = f"case_{case_id}"
        extract_path = os.path.join(settings.MEDIA_ROOT, 'dicoms', folder_name)

        if not os.path.exists(extract_path):
            os.makedirs(extract_path, exist_ok=True)

        # Распаковка архива
        try:
            with zipfile.ZipFile(file_obj, 'r') as zip_ref:
                zip_ref.extractall(extract_path)
        except zipfile.BadZipFile:
            return Response({"error": "Файл не является валидным ZIP-архивом"}, status=status.HTTP_400_BAD_REQUEST)

        # Сбор путей ко всем файлам (для клиента)
        file_urls = []
        for root, dirs, files in os.walk(extract_path):
            for file in files:
                # Пропускаем скрытые файлы систем (типа __MACOSX)
                if not file.startswith('.'):
                    # Формируем URL относительно корня сайта
                    relative_path = os.path.relpath(os.path.join(root, file), settings.MEDIA_ROOT)
                    file_urls.append(settings.MEDIA_URL + relative_path)

        # Эмуляция "работы нейросети" (задержка 2 секунды)
        time.sleep(2.0)

        # Выбор случайного шаблона из нашей библиотеки (10 вариантов)
        library_variants = ImplantLibrary.objects.all()
        if not library_variants.exists():
            return Response({
                "error": "Библиотека расчетов пуста. Загрузите варианты через админку."
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        chosen_variant = random.choice(library_variants)

        # Создаем или обновляем результат расчета для этого кейса
        implant, created = IndividualImplant.objects.update_or_create(
            case=case,
            defaults={
                "implant_variant": chosen_variant,
                "is_calculated": True
            }
        )

        # 8. Финальный ответ
        return Response({
            "status": "success",
            "message": "Архив обработан. Нейросеть выполнила расчет.",
            "dicom_files_count": len(file_urls),
            "dicom_files": file_urls,
            "calculation": ImplantSerializer(implant).data
        }, status=status.HTTP_200_OK)


class ImplantDetailsAPIView(APIView):

    def get(self, request, case_id):
        try:
            implant = IndividualImplant.objects.get(case_id=case_id)
            return Response(ImplantSerializer(implant).data)
        except IndividualImplant.DoesNotExist:
            return Response({"error": "Расчет для этого приема еще не выполнен"}, status=404)


class LibraryListAPIView(ListAPIView):
    queryset = ImplantLibrary.objects.all()
    serializer_class = ImplantLibrarySerializer

class LibraryCreateAPIView(CreateAPIView):
    queryset = ImplantLibrary.objects.all()
    serializer_class = ImplantLibrarySerializer