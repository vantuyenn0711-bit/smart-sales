import uuid

from django.db import models


def customer_code():
    return f"KH-{uuid.uuid4().hex[:12].upper()}"


class Customer(models.Model):
    code = models.CharField("Mã khách hàng", max_length=32, unique=True, default=customer_code)
    name = models.CharField("Họ và tên", max_length=150, db_index=True)
    phone = models.CharField("Số điện thoại", max_length=25, db_index=True)
    email = models.EmailField("Email", blank=True)
    address = models.CharField("Địa chỉ", max_length=300, blank=True)
    note = models.TextField("Ghi chú", blank=True, max_length=2000)
    is_active = models.BooleanField("Đang hoạt động", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "pk"]

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = customer_code()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.name
