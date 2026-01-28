from rest_framework import serializers, generics
from django.contrib.auth import get_user_model
from .models import (
    WorkerProfile, Patient, MedicalCase, IndividualImplant, ImplantLibrary
)

# -------------------------------------------------------------------------
# АУТЕНТИФИКАЦИЯ И ПОЛЬЗОВАТЕЛИ
# -------------------------------------------------------------------------
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
    # Достаем данные из связанной библиотеки
    visualization_image = serializers.ImageField(source='implant_variant.visualization_image', read_only=True)
    density_graph = serializers.ImageField(source='implant_variant.density_graph', read_only=True)
    diameter = serializers.FloatField(source='implant_variant.diameter', read_only=True)
    length = serializers.FloatField(source='implant_variant.length', read_only=True)
    thread_shape = serializers.CharField(source='implant_variant.thread_shape', read_only=True)
    thread_pitch = serializers.FloatField(source='implant_variant.thread_pitch', read_only=True)
    thread_depth = serializers.CharField(source='implant_variant.thread_depth', read_only=True)
    bone_type = serializers.CharField(source='implant_variant.bone_type', read_only=True)
    hu_density = serializers.IntegerField(source='implant_variant.hu_density', read_only=True)
    chewing_load = serializers.FloatField(source='implant_variant.chewing_load', read_only=True)
    limit_stress = serializers.FloatField(source='implant_variant.limit_stress', read_only=True)
    surface_area = serializers.FloatField(source='implant_variant.surface_area', read_only=True)

    class Meta:
        model = IndividualImplant
        fields = '__all__'

class ImplantLibrarySerializer(serializers.ModelSerializer):
    class Meta:
        model = ImplantLibrary
        fields = '__all__'