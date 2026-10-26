from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models

class Department(models.Model):
    name=models.CharField(max_length=150, unique=True, verbose_name="Название отдела")

    class Meta:
        verbose_name = "Отдел"
        verbose_name_plural = "Отделы"
        ordering = ["name"]

    def __str__(self):
        return self.name

class CustomUserManager(UserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields["department_id"] = extra_fields.pop("department")
        return super().create_superuser(
            username, email, password, **extra_fields
        )

class User(AbstractUser):
    department=models.ForeignKey(Department, on_delete=models.PROTECT, related_name="users")

    objects = CustomUserManager()

    REQUIRED_FIELDS = ["department"]
