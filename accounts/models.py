from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import UserManager as DjangoUserManager
from django.db import models


class UserManager(DjangoUserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("role", "ADMIN")
        return super().create_superuser(username, email, password, **extra_fields)


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Quản trị viên"
        MANAGER = "MANAGER", "Quản lý"
        STAFF = "STAFF", "Nhân viên bán hàng"
        VIEWER = "VIEWER", "Người xem"

    role = models.CharField(max_length=10, choices=Role.choices, default=Role.VIEWER)
    objects = UserManager()

    def __str__(self):
        return self.get_full_name() or self.username

    class Meta(AbstractUser.Meta):
        constraints = [
            models.CheckConstraint(
                condition=models.Q(role__in=["ADMIN", "MANAGER", "STAFF", "VIEWER"]),
                name="user_valid_role",
            )
        ]
