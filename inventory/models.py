from django.conf import settings
from django.db import models

from core.models import ImmutableRecord


class StockBalance(models.Model):
    product = models.OneToOneField("catalog.Product", on_delete=models.PROTECT, related_name="stock")
    quantity_on_hand = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(quantity_on_hand__gte=0), name="stock_nonnegative"),
        ]

    def __str__(self):
        return f"{self.product.sku}: {self.quantity_on_hand}"


class InventoryMovement(ImmutableRecord):
    class Kind(models.TextChoices):
        OPENING = "OPENING", "Tồn đầu kỳ"
        ADJUSTMENT = "ADJUSTMENT", "Điều chỉnh"
        SALE = "SALE", "Xuất bán"
        CANCELLATION = "CANCELLATION", "Hoàn tồn hủy đơn"

    product = models.ForeignKey("catalog.Product", on_delete=models.PROTECT, related_name="movements")
    order = models.ForeignKey(
        "orders.SalesOrder", on_delete=models.PROTECT, null=True, blank=True, related_name="movements"
    )
    signed_qty = models.IntegerField()
    kind = models.CharField(max_length=16, choices=Kind.choices)
    reason = models.CharField(max_length=500)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        constraints = [
            models.CheckConstraint(condition=~models.Q(signed_qty=0), name="movement_nonzero"),
            models.CheckConstraint(
                condition=(
                    models.Q(kind="SALE", signed_qty__lt=0, order__isnull=False)
                    | models.Q(kind="CANCELLATION", signed_qty__gt=0, order__isnull=False)
                    | models.Q(kind__in=["OPENING", "ADJUSTMENT"], order__isnull=True)
                ),
                name="movement_kind_consistent",
            ),
            models.UniqueConstraint(
                fields=["order", "product", "kind"],
                condition=models.Q(order__isnull=False),
                name="movement_once_per_order_kind",
            ),
        ]
