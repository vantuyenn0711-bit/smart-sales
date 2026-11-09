from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.db.models import Count, DecimalField, ExpressionWrapper, F, Sum
from django.db.models.functions import TruncDate

from catalog.models import Product
from core.models import AuditLog
from orders.models import SalesOrder, SalesOrderItem
from payments.models import Payment

ZERO = Decimal("0")


def order_scope(filters):
    orders = SalesOrder.objects.all()
    if filters.get("category"):
        matching_ids = SalesOrderItem.objects.filter(product__category=filters["category"]).values("order_id")
        orders = orders.filter(pk__in=matching_ids)
    if filters.get("staff"):
        orders = orders.filter(created_by=filters["staff"])
    return orders


def in_range(queryset, field, start, end):
    return queryset.filter(**{f"{field}__date__gte": start, f"{field}__date__lte": end})


def metrics_for(scope, start, end):
    completed = in_range(scope.filter(status=SalesOrder.Status.COMPLETED), "completed_at", start, end)
    created = in_range(scope, "created_at", start, end)
    payments = in_range(Payment.objects.filter(order_id__in=scope.values("pk")), "paid_at", start, end)
    revenue = completed.aggregate(value=Sum("total"))["value"] or ZERO
    count = completed.count()
    cost_expression = ExpressionWrapper(F("quantity") * F("cost_snapshot"), output_field=DecimalField(max_digits=20, decimal_places=0))
    cost = SalesOrderItem.objects.filter(order_id__in=completed.values("pk")).aggregate(value=Sum(cost_expression))["value"] or ZERO
    return {
        "revenue": revenue, "receipts": payments.aggregate(value=Sum("amount"))["value"] or ZERO,
        "order_count": created.count(), "completed_count": count,
        "average_order": (revenue / count).quantize(Decimal("1"), rounding=ROUND_HALF_UP) if count else ZERO, "profit": revenue - cost,
        "cancelled_count": created.filter(status=SalesOrder.Status.CANCELLED).count(),
    }, completed, payments


def report_context(filters):
    start, end = filters["from"], filters["to"]
    scope = order_scope(filters)
    metrics, completed, payments = metrics_for(scope, start, end)
    days = (end - start).days + 1
    previous, _, _ = metrics_for(scope, start - timedelta(days=days), start - timedelta(days=1))
    revenue_days = dict(completed.annotate(day=TruncDate("completed_at")).values("day").annotate(value=Sum("total")).values_list("day", "value"))
    payment_days = dict(payments.annotate(day=TruncDate("paid_at")).values("day").annotate(value=Sum("amount")).values_list("day", "value"))
    dates = [start + timedelta(days=index) for index in range(days)]
    chart = {"labels": [day.strftime("%d/%m") for day in dates], "revenue": [float(revenue_days.get(day, ZERO)) for day in dates], "receipts": [float(payment_days.get(day, ZERO)) for day in dates]}
    counts = dict(in_range(scope, "created_at", start, end).values("status").annotate(count=Count("pk")).values_list("status", "count"))
    top = SalesOrderItem.objects.filter(order_id__in=completed.values("pk")).values("product__name", "product__sku").annotate(quantity=Sum("quantity"), revenue=Sum("line_total")).order_by("-quantity", "product__name")[:5]
    stock = Product.objects.filter(is_active=True, stock__quantity_on_hand__lte=F("low_stock_threshold")).select_related("stock", "category").order_by("stock__quantity_on_hand", "name")
    if filters.get("category"):
        stock = stock.filter(category=filters["category"])
    return {
        "start": start, "end": end, "filters": filters, "metrics": metrics,
        "previous_metrics": previous, "chart_data": chart,
        "status_counts": [{"status": status, "label": label, "count": counts.get(status, 0)} for status, label in SalesOrder.Status.choices],
        "top_products": list(top), "low_stock": stock[:5], "low_stock_count": stock.count(),
        "recent_orders": in_range(scope, "created_at", start, end).select_related("customer", "created_by").prefetch_related("payments").order_by("-created_at")[:6],
        "recent_activity": AuditLog.objects.select_related("actor").order_by("-created_at")[:5],
        "completed_orders": completed.select_related("customer", "created_by").order_by("-completed_at"),
        "receipt_records": payments.select_related("order", "created_by").order_by("-paid_at"),
    }
