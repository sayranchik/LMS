from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = "student", "Студент"
        TEACHER = "teacher", "Викладач"
        ADMIN = "admin", "Адміністратор"

    role = models.CharField("Роль", max_length=10, choices=Role.choices, default=Role.STUDENT)
    bio = models.TextField("Про себе", blank=True)

    @property
    def is_lms_admin(self):
        return self.is_superuser or self.role == self.Role.ADMIN

    @property
    def is_teacher(self):
        return self.role == self.Role.TEACHER

    @property
    def is_student(self):
        return self.role == self.Role.STUDENT and not self.is_superuser

    @property
    def can_manage_assignments(self):
        return self.is_lms_admin or self.is_teacher

    def __str__(self):
        return self.get_full_name() or self.username
