from django.conf import settings
from django.db import models, transaction
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db.models import F


class AccountManager(BaseUserManager):
    def create_user(self, email, name, surname, patronymic=None, password=None, role="WORKER", **kwargs):
        if not email:
            raise ValueError("Email is required")
        if not name:
            raise ValueError("Name is required")
        if not surname:
            raise ValueError("Surname is required")

        email = self.normalize_email(email)
        # Сохраняем name, surname, patronymic
        user = self.model(
            email=email,
            name=name,
            surname=surname,
            patronymic=patronymic or "",  # Если None, пишем пустую строку
            role=role,
            **kwargs
        )
        if password:
            user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, name, surname, password=None, **kwargs):
        # Передаем параметры в create_user
        user = self.create_user(
            email=email,
            name=name,
            surname=surname,
            password=password,
            role=Account.Role.SUPERADMIN,
            **kwargs
        )
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user

    def create_admin(self, email, name, surname, password=None, **kwargs):
        user = self.create_user(
            email=email,
            name=name,
            surname=surname,
            password=password,
            role=Account.Role.ADMIN,
            **kwargs
        )
        user.is_staff = True
        user.save(using=self._db)
        return user

    def create_worker(self, email, name, surname, patronymic=None, password=None, work=None, position=None,
                      **kwargs):
        user = self.create_user(
            email=email,
            name=name,
            surname=surname,
            patronymic=patronymic,
            password=password,
            role=Account.Role.WORKER,
            **kwargs
        )

        if work is not None or position is not None:
            WorkerProfile.objects.update_or_create(user=user, defaults={
                "work": work or "",
                "position": position or ""
            })
        return user


class Account(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        SUPERADMIN = "SUPERADMIN", "Главный администратор"
        ADMIN = "ADMIN", "Администратор"
        WORKER = "WORKER", "Работник"

    email = models.EmailField(null=False, blank=False, unique=True)
    name = models.CharField(max_length=50, blank=False, null=False, verbose_name="Имя")
    surname = models.CharField(max_length=50, blank=False, null=False, verbose_name="Фамилия")
    patronymic = models.CharField(max_length=50, blank=True, default="", verbose_name="Отчество")

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.WORKER)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = AccountManager()

    USERNAME_FIELD = "email"
    # Поля, обязательные при создании суперюзера через консоль (кроме email и пароля)
    REQUIRED_FIELDS = ["name", "surname"]

    def __str__(self):
        # Красивое отображение ФИО
        full_name = f"{self.surname} {self.name} {self.patronymic}".strip()
        return f"{full_name} ({self.role})"

    def has_perm(self, perm, obj=None):
        if self.is_superuser or self.role == Account.Role.SUPERADMIN:
            return True
        return super().has_perm(perm, obj)

    def has_module_perms(self, app_label):
        if self.is_superuser or self.role == Account.Role.SUPERADMIN:
            return True
        return True

    @property
    def is_superadmin(self):
        return self.role == Account.Role.SUPERADMIN

    @property
    def is_admin_role(self):
        return self.role == Account.Role.ADMIN

    @property
    def is_worker(self):
        return self.role == Account.Role.WORKER

class WorkerProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="worker_profile")
    work = models.CharField(max_length=255, blank=True, null=False)
    position = models.CharField(max_length=255, blank=True, null=False)

    def __str__(self):
        return f"Profile for {self.user.email}"


# ОСНОВНЫЕ ТАБЛИЦЫ

class Patient(models.Model):
    name = models.CharField(max_length=255, verbose_name="Имя")
    surname = models.CharField(max_length=255, verbose_name="Фамилия")
    patronymic = models.CharField(max_length=255, blank=True, null=False, verbose_name="Отчество")
    birth_date = models.DateField(verbose_name="Дата рождения")
    gender = models.IntegerField(choices=[(0, 'Мужской'), (1, 'Женский')], verbose_name="Пол")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.surname} {self.name} {self.patronymic}".strip()


class MedicalCase(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="cases", verbose_name="Пациент")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name="Врач")
    diagnosis = models.TextField(blank=True, verbose_name="Диагноз/Описание")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата приема")

    def __str__(self):
        return f"Прием #{self.id} - {self.patient.surname} {self.patient.name} {self.patient.patronymic}".strip()


class DICOMUpload(models.Model):
    case = models.ForeignKey(MedicalCase, on_delete=models.CASCADE, related_name="dicom_uploads")
    file = models.FileField(upload_to='dicom_archives/%d/%m/%Y/', verbose_name="Архив DICOM")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Загрузка DICOM"
        verbose_name_plural = "Загрузки DICOM"


class ImplantLibrary(models.Model):
    name = models.CharField(max_length=100, verbose_name="Название варианта (заглушки)")

    # Изображения
    visualization_image = models.ImageField(upload_to='visualizations_images', verbose_name="3D Визуализация")
    density_graph = models.ImageField(upload_to='density_graphics', verbose_name="График плотности")

    # Технические параметры
    diameter = models.FloatField(verbose_name="Диаметр (мм)")
    length = models.FloatField(verbose_name="Длина (мм)")
    thread_shape = models.CharField(max_length=50, verbose_name="Форма резьбы")
    thread_pitch = models.FloatField(verbose_name="Шаг резьбы (мм)")
    thread_depth = models.CharField(max_length=50, verbose_name="Глубина резьбы (мм)")
    bone_type = models.CharField(max_length=50, verbose_name="Тип кости")
    hu_density = models.IntegerField(verbose_name="Плотность HU")
    chewing_load = models.FloatField(verbose_name="Жевательная нагрузка (кгс)")
    limit_stress = models.FloatField(verbose_name="Предельное напряжение (кг/мм2)")
    surface_area = models.FloatField(verbose_name="Площадь поверхности резьбы (мм2)")

    class Meta:
        verbose_name = "Вариант из библиотеки"
        verbose_name_plural = "Библиотека имплантов"

    def __str__(self):
        return f"{self.name} (D:{self.diameter} L:{self.length})"


class IndividualImplant(models.Model):
    case = models.OneToOneField(MedicalCase, on_delete=models.CASCADE, related_name="implant")
    implant_variant = models.ForeignKey(
        ImplantLibrary,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Выбранный вариант из библиотеки"
    )

    is_calculated = models.BooleanField(default=False, verbose_name="Расчет выполнен")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Результат расчета"
        verbose_name_plural = "Результаты расчетов"

    def __str__(self):
        return f"Расчет САПР для приема #{self.case_id}"
