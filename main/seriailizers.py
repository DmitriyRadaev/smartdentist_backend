import os

from django.conf import settings
from rest_framework import serializers, generics
from django.contrib.auth import get_user_model
from .models import (
    WorkerProfile, Patient, MedicalCase, IndividualImplant, ImplantLibrary
)

# АУТЕНТИФИКАЦИЯ И ПОЛЬЗОВАТЕЛИ
Account = get_user_model()


class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ("id", "email", "name", "surname", "patronymic", "is_active", "is_staff", "is_superuser", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")


class WorkerRegistrationSerializer(serializers.ModelSerializer):
    work = serializers.CharField(write_only=True, required=True)
    position = serializers.CharField(write_only=True, required=True)
    password = serializers.CharField(write_only=True, min_length=6)
    password2 = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = Account
        # Явно перечисляем новые поля
        fields = ("email", "name", "surname", "patronymic", "password", "password2", "work", "position")

    def validate(self, attrs):
        if attrs.get("password") != attrs.get("password2"):
            raise serializers.ValidationError({"password": "Пароли не совпадают"})
        return attrs

    def create(self, validated_data):
        validated_data.pop("password2")
        place = validated_data.pop("work")
        pos = validated_data.pop("position")
        password = validated_data.pop("password")

        # Передаем данные напрямую в create_worker
        user = Account.objects.create_worker(
            email=validated_data["email"],
            name=validated_data["name"],
            surname=validated_data["surname"],
            patronymic=validated_data.get("patronymic", ""),
            password=password,
            work=place,
            position=pos
        )
        return user


class AdminRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    password2 = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = Account
        fields = ("email", "name", "surname", "patronymic", "password", "password2")

    def validate(self, attrs):
        if attrs.get("password") != attrs.get("password2"):
            raise serializers.ValidationError({"password": "Пароли не совпадают"})
        return attrs

    def create(self, validated_data):
        validated_data.pop("password2")
        # Передаем данные в create_admin
        user = Account.objects.create_admin(
            email=validated_data["email"],
            name=validated_data["name"],
            surname=validated_data["surname"],
            patronymic=validated_data.get("patronymic", ""),
            password=validated_data["password"]
        )
        return user


class SuperAdminRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    password2 = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = Account
        fields = ("email", "name", "surname", "patronymic", "password", "password2")

    def validate(self, attrs):
        if attrs.get("password") != attrs.get("password2"):
            raise serializers.ValidationError({"password": "Пароли не совпадают"})
        return attrs

    def create(self, validated_data):
        validated_data.pop("password2")
        user = Account.objects.create_superuser(
            email=validated_data["email"],
            name=validated_data["name"],
            surname=validated_data["surname"],
            patronymic=validated_data.get("patronymic", ""),
            password=validated_data["password"]
        )
        return user


class WorkerProfileSerializer(serializers.ModelSerializer):
    user = AccountSerializer(read_only=True)

    class Meta:
        model = WorkerProfile
        fields = ("id", "user", "work", "position")


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ("name", "surname", "patronymic")


class PatientSerializer(serializers.ModelSerializer):
    fio = serializers.SerializerMethodField(read_only=True)
    birth_date = serializers.DateField(
        format="%d.%m.%Y",
        input_formats=['%d.%m.%Y', 'iso-8601']
    )

    class Meta:
        model = Patient
        fields = ['id', 'fio', 'name', 'surname', 'patronymic', 'birth_date', 'gender']
        extra_kwargs = {
            'name': {'write_only': True},
            'surname': {'write_only': True},
            'patronymic': {'write_only': True},
        }

    def get_fio(self, obj):
        return f"{obj.surname} {obj.name} {obj.patronymic}".strip()


class MedicalCaseSerializer(serializers.ModelSerializer):
    patient_fio = serializers.CharField(source='patient.__str__', read_only=True)

    # Указываем формат вывода для даты и времени приема
    created_at = serializers.DateTimeField(
        format="%d.%m.%Y",
        read_only=True
    )

    class Meta:
        model = MedicalCase
        fields = ['id', 'patient', 'patient_fio', 'user', 'diagnosis', 'created_at']



class ImplantSerializer(serializers.ModelSerializer):
    visualization_image = serializers.SerializerMethodField()
    density_graph = serializers.SerializerMethodField()
    diameter = serializers.ReadOnlyField(source='implant_variant.diameter', default=None)
    length = serializers.ReadOnlyField(source='implant_variant.length', default=None)
    thread_shape = serializers.ReadOnlyField(source='implant_variant.thread_shape', default=None)
    thread_pitch = serializers.ReadOnlyField(source='implant_variant.thread_pitch', default=None)
    thread_depth = serializers.ReadOnlyField(source='implant_variant.thread_depth', default=None)
    bone_type = serializers.ReadOnlyField(source='implant_variant.bone_type', default=None)
    hu_density = serializers.ReadOnlyField(source='implant_variant.hu_density', default=None)
    chewing_load = serializers.ReadOnlyField(source='implant_variant.chewing_load', default=None)
    limit_stress = serializers.ReadOnlyField(source='implant_variant.limit_stress', default=None)
    surface_area = serializers.ReadOnlyField(source='implant_variant.surface_area', default=None)

    class Meta:
        model = IndividualImplant
        fields = '__all__'

    def get_visualization_image(self, obj):
        if obj.implant_variant and obj.implant_variant.visualization_image:
            return self.context['request'].build_absolute_uri(obj.implant_variant.visualization_image.url)
        return None

    def get_density_graph(self, obj):
        if obj.implant_variant and obj.implant_variant.density_graph:
            return self.context['request'].build_absolute_uri(obj.implant_variant.density_graph.url)
        return None


class ImplantLibrarySerializer(serializers.ModelSerializer):
    class Meta:
        model = ImplantLibrary
        fields = '__all__'

class CaseDetailSerializer(serializers.ModelSerializer):
    implant_data = serializers.SerializerMethodField()
    dicom_files = serializers.SerializerMethodField()
    patient_fio = serializers.CharField(source='patient.__str__', read_only=True)
    created_at = serializers.DateTimeField(format="%d.%m.%Y %H:%M", read_only=True)

    class Meta:
        model = MedicalCase
        fields = ['id', 'patient_fio', 'user', 'diagnosis', 'created_at', 'implant_data', 'dicom_files']

    def get_implant_data(self, obj):
        # Безопасно проверяем наличие OneToOne связи
        try:
            implant = getattr(obj, 'implant', None)
            if implant:
                return ImplantSerializer(implant, context=self.context).data
        except Exception:
            pass
        return None

    def get_dicom_files(self, obj):
        # Проверка наличия request в контексте, чтобы не было 500 ошибки
        request = self.context.get('request')
        if not request:
            return []

        folder_path = os.path.join(settings.MEDIA_ROOT, 'dicoms', f'case_{obj.id}')
        file_urls = []
        if os.path.exists(folder_path):
            for root, dirs, files in os.walk(folder_path):
                for f in sorted(files):
                    if not f.startswith('.'):
                        rel_path = os.path.relpath(os.path.join(root, f), settings.MEDIA_ROOT)
                        # Используем request для построения ссылки
                        path = os.path.join(settings.MEDIA_URL, rel_path).replace('\\', '/')
                        file_urls.append(request.build_absolute_uri(path))
        return file_urls