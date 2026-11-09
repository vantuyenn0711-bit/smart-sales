import uuid
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Sum
from django.utils import timezone

from core.models import ImmutableRecord


def order_number():
    return f"DH-{timezone.localdate():%y%m%d}-{uuid.uuid4().hex[:12].upper()}"


class SalesOrder(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Bản nháp"
        CONFIRMED = "CONFIRMED", "Đã xác nhận"
        PROCESSING = "PROCESSING", "Đang xử lý"
        COMPLETED = "COMPLETED", "Hoàn thành"
        CANCELLED = "CANCELLED", "Đã hủy"

    order_no = models.CharField(max_length=40, unique=True, default=order_number)
    customer = models.ForeignKey(
        "customers.Customer", on_delete=models.PROTECT, null=True, blank=True, related_name="orders"
    )
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT, db_index=True)
    subtotal = models.DecimalField(max_digits=16, decimal_places=0, validators=[MinValueValidator(0)])
    discount = models.DecimalField(
        max_digits=16, decimal_places=0, default=0, validators=[MinValueValidator(0)]
    )
    total = models.DecimalField(max_digits=16, decimal_places=0, validators=[MinValueValidator(0)])
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="sales_orders"
    )
    note = models.TextField(blank=True, max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        constraints = [
            models.CheckConstraint(condition=models.Q(subtotal__gte=0), name="order_subtotal_nonnegative"),
            models.CheckConstraint(condition=models.Q(discount__gte=0), name="order_discount_nonnegative"),
            models.CheckConstraint(
                condition=models.Q(discount__lte=F("subtotal")), name="order_discount_within_subtotal"
            ),
            models.CheckConstraint(
                condition=models.Q(total=F("subtotal") - F("discount")), name="order_total_consistent"
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=["DRAFT", "CONFIRMED", "PROCESSING", "COMPLETED", "CANCELLED"]),
                name="order_valid_status",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(status="COMPLETED", completed_at__isnull=False)
                    | (~models.Q(status="COMPLETED") & models.Q(completed_at__isnull=True))
                ),
                name="order_completed_date_consistent",
            ),
        ]

    @property
    def amount_paid(self):
        if hasattr(self, "paid_amount"):
            return self.paid_amount or Decimal(0)
        if "payments" in getattr(self, "_prefetched_objects_cache", {}):
            return sum((payment.amount for payment in self.payments.all()), Decimal(0))
        return self.payments.aggregate(total=Sum("amount"))["total"] or Decimal(0)

    @property
    def balance_due(self):
        return self.total - self.amount_paid

    @property
    def payment_status(self):
        paid = self.amount_paid
        if paid >= self.total:
            return "paid"
        return "partial" if paid else "unpaid"

    def __str__(self):
        return self.order_no


class SalesOrderItem(ImmutableRecord):
    order = models.ForeignKey(SalesOrder, on_delete=models.PROTECT, related_name="items")
    product = models.ForeignKey("catalog.Product", on_delete=models.PROTECT, related_name="order_items")
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_price_snapshot = models.DecimalField(max_digits=16, decimal_places=0)
    cost_snapshot = models.DecimalField(max_digits=16, decimal_places=0)
    line_total = models.DecimalField(max_digits=16, decimal_places=0)

    class Meta:
        ordering = ["pk"]
        constraints = [
            models.UniqueConstraint(fields=["order", "product"], name="unique_product_per_order"),
            models.CheckConstraint(condition=models.Q(quantity__gt=0), name="order_item_positive_quantity"),
            models.CheckConstraint(
                condition=models.Q(unit_price_snapshot__gte=0), name="order_item_price_nonnegative"
            ),
            models.CheckConstraint(
                condition=models.Q(cost_snapshot__gte=0), name="order_item_cost_nonnegative"
            ),
            models.CheckConstraint(
                condition=models.Q(line_total=F("quantity") * F("unit_price_snapshot")),
                name="order_line_total_consistent",
            ),
        ]


class OrderStatusHistory(ImmutableRecord):
    order = models.ForeignKey(SalesOrder, on_delete=models.PROTECT, related_name="history")
    from_status = models.CharField(max_length=12, blank=True)
    to_status = models.CharField(max_length=12, choices=SalesOrder.Status.choices)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    reason = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "pk"]
