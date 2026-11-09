import uuid
from datetime import timedelta
from decimal import Decimal
from io import BytesIO

import pytest
from django.urls import reverse
from django.utils import timezone
from openpyxl import load_workbook

from accounts.models import User
from analytics.services import report_context
from catalog.models import Category, Product
from customers.models import Customer
from inventory.services import adjust_stock
from orders.models import SalesOrder
from orders.services import create_order, transition_order
from payments.models import Payment
from payments.services import record_payment

pytestmark = pytest.mark.django_db


@pytest.fixture
def analytics_data():
    actor = User.objects.create_user(username="report_manager", password="Report-test-password-638!", role="MANAGER")
    cat = Category.objects.create(code="REPORT", name="Thiết bị")
    products = [Product.objects.create(sku=f"REPORT-{i}", name=f"Sản phẩm {i}", category=cat, sale_price=100000, cost_price=40000) for i in range(2)]
    for product in products:
        adjust_stock(actor=actor, product_id=product.pk, quantity=50, reason="Nhập kiểm thử")
    customer = Customer.objects.create(code="REPORT-C", name="=1+1", phone="0900000000")
    order = create_order(actor=actor, customer=customer, items=[{"product": product, "quantity": 2} for product in products], discount=20000)
    for status in ("CONFIRMED", "PROCESSING", "COMPLETED"):
        transition_order(actor=actor, order_id=order.pk, target_status=status)
    payment = record_payment(actor=actor, order_id=order.pk, amount=100000, method="CASH", reference="=SUM(A1:A2)", idempotency_key=uuid.uuid4())
    return actor, cat, products, order, payment


def test_revenue_receipts_cost_and_whole_order_category_filter(analytics_data):
    actor, cat, products, order, payment = analytics_data
    today = timezone.localdate()
    context = report_context({"from": today, "to": today, "category": cat, "staff": actor})
    assert context["metrics"]["revenue"] == Decimal(380000)
    assert context["metrics"]["receipts"] == Decimal(100000)
    assert context["metrics"]["profit"] == Decimal(220000)
    assert context["metrics"]["order_count"] == 1
    assert context["metrics"]["completed_count"] == 1
    assert sum(context["chart_data"]["revenue"]) == 380000
    assert sum(item["quantity"] for item in context["top_products"]) == 4


def test_revenue_uses_completion_day_receipts_use_payment_day(analytics_data):
    actor, _, _, order, payment = analytics_data
    old = timezone.now() - timedelta(days=10)
    SalesOrder.objects.filter(pk=order.pk).update(created_at=old)
    Payment.objects.filter(pk=payment.pk).update(paid_at=old)
    today = timezone.localdate()
    context = report_context({"from": today, "to": today})
    assert context["metrics"]["revenue"] == 380000
    assert context["metrics"]["order_count"] == 0
    assert context["metrics"]["receipts"] == 0
    assert context["metrics"]["completed_count"] == 1


def test_average_order_rounds_half_up_to_whole_vnd(analytics_data):
    actor, category, _, _, _ = analytics_data
    product = Product.objects.create(sku="ROUND-1", name="Làm tròn", category=category, sale_price=1, cost_price=0)
    adjust_stock(actor=actor, product_id=product.pk, quantity=1, reason="Kiểm thử làm tròn")
    order = create_order(actor=actor, items=[{"product": product, "quantity": 1}])
    for status in ("CONFIRMED", "PROCESSING", "COMPLETED"):
        transition_order(actor=actor, order_id=order.pk, target_status=status)
    today = timezone.localdate()
    context = report_context({"from": today, "to": today})
    assert context["metrics"]["revenue"] == 380001
    assert context["metrics"]["average_order"] == 190001


def test_draft_and_cancelled_are_not_revenue(analytics_data):
    actor, _, products, _, _ = analytics_data
    cancelled = create_order(actor=actor, items=[{"product": products[0], "quantity": 1}])
    transition_order(actor=actor, order_id=cancelled.pk, target_status="CANCELLED", reason="Kiểm thử")
    create_order(actor=actor, items=[{"product": products[0], "quantity": 1}])
    today = timezone.localdate()
    context = report_context({"from": today, "to": today})
    assert context["metrics"]["revenue"] == 380000
    assert context["metrics"]["order_count"] == 3
    assert context["metrics"]["cancelled_count"] == 1


@pytest.mark.parametrize("query", [
    {"from": "bad-date"}, {"from": "2026-11-09", "to": "2026-11-01"},
    {"from": "2020-01-01", "to": "2026-11-09"}, {"category": "not-an-id"}, {"staff": "999999999"},
])
def test_invalid_report_filter_is_clear_400(client, analytics_data, query):
    client.force_login(analytics_data[0])
    for route in ("core:dashboard", "analytics:reports", "analytics:export"):
        response = client.get(reverse(route), query)
        assert response.status_code == 400
        assert response.context["filter_form"].errors


def test_report_xlsx_reconciles_and_neutralizes_formulas(client, analytics_data):
    actor, _, _, order, payment = analytics_data
    client.force_login(actor)
    response = client.get(reverse("analytics:export"))
    assert response.status_code == 200
    workbook = load_workbook(BytesIO(response.content))
    assert workbook["Tổng quan"]["B4"].value == 380000
    assert workbook["Tổng quan"]["B5"].value == 100000
    assert workbook["Đơn hoàn thành"]["B2"].value == "'=1+1"
    assert workbook["Tiền đã thu"]["E2"].value == "'=SUM(A1:A2)"
    assert workbook["Đơn hoàn thành"]["G2"].value == order.total


def test_viewer_export_hides_margin(client, analytics_data):
    viewer = User.objects.create_user(username="report_viewer", role="VIEWER")
    client.force_login(viewer)
    workbook = load_workbook(BytesIO(client.get(reverse("analytics:export")).content))
    assert "Lợi nhuận" not in " ".join(str(cell.value) for row in workbook["Tổng quan"] for cell in row)


def test_empty_database_dashboard_renders_zero_values(client):
    viewer = User.objects.create_user(username="empty_viewer", role="VIEWER")
    client.force_login(viewer)
    response = client.get(reverse("core:dashboard"))
    assert response.status_code == 200
    assert response.context["metrics"]["revenue"] == 0
    assert not response.context["top_products"]
    assert "Chưa có đơn hàng" in response.content.decode()


@pytest.mark.parametrize("route", ["core:dashboard", "analytics:reports", "analytics:export"])
def test_anonymous_cannot_access_reports(client, route):
    response = client.get(reverse(route))
    assert response.status_code == 302
    assert response.url.startswith(reverse("login"))
