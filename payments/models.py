import uuid

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from core.models import ImmutableRecord


class Payment(ImmutableRecord):
    class Method(models.TextChoices):
        CASH = "CASH", "Tiền mặt"
        TRANSFER = "TRANSFER", "Chuyển khoản"

    order = models.ForeignKey("orders.SalesOrder", on_delete=models.PROTECT, related_name="payments")
    method = models.CharField(max_length=10, choices=Method.choices)
    amount = models.DecimalField(max_digits=16, decimal_places=0, validators=[MinValueValidator(1)])
    reference = models.CharField(max_length=100, unique=True, null=True, blank=True)
    idempotency_key = models.UUIDField(unique=True, default=uuid.uuid4)
    paid_at = models.DateTimeField(default=timezone.now, db_index=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    class Meta:
        ordering = ["-paid_at", "-pk"]
        constraints = [
            models.CheckConstraint(condition=models.Q(amount__gt=0), name="payment_positive_amount"),
            models.CheckConstraint(
                condition=models.Q(method__in=["CASH", "TRANSFER"]), name="payment_valid_method"
            ),
        ]
