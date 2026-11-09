import io
import uuid
from decimal import Decimal
from types import SimpleNamespace

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.test import Client
from django.urls import reverse
from PIL import Image

from accounts.models import User
from catalog.models import Category, Product
from core.models import AuditLog
from customers.models import Customer
from inventory.models import InventoryMovement
from inventory.services import adjust_stock
from orders.models import SalesOrder
from payments.models import Payment

pytestmark = pytest.mark.django_db


@pytest.fixture
def web_data():
    users = {role.lower(): User.objects.create(username=f"web_{role.lower()}", role=role) for role in User.Role.values}
    category = Category.objects.create(code="WEB", name="Phụ kiện kiểm thử")
    product = Product.objects.create(sku="WEB-50", name="Bàn phím kiểm thử", category=category, sale_price=50000, cost_price=20000)
    adjust_stock(actor=users["manager"], product_id=product.pk, quantity=50, reason="Nhập tồn kiểm thử")
    customer = Customer.objects.create(name="Khách thử nghiệm", phone="0912345678")
    return SimpleNamespace(**users, category=category, product=product, customer=customer)


def order_payload(data, quantity=3):
    return {
        "customer": data.customer.pk, "discount": "0", "note": "Đơn kiểm thử giao diện",
        "items-TOTAL_FORMS": "1", "items-INITIAL_FORMS": "0", "items-MIN_NUM_FORMS": "0", "items-MAX_NUM_FORMS": "50",
        "items-0-product": data.product.pk, "items-0-quantity": str(quantity),
    }


def make_order(client, data, quantity=3):
    response = client.post(reverse("core:order_create"), order_payload(data, quantity))
    assert response.status_code == 302
    return SalesOrder.objects.latest("pk")


@pytest.mark.parametrize("name", ["dashboard", "product_list", "category_list", "customer_list", "order_list", "payment_list", "inventory_list"])
def test_operational_pages_require_login(client, name):
    response = client.get(reverse(f"core:{name}"))
    assert response.status_code == 302
    assert response.url.startswith("/login/?next=")


@pytest.mark.parametrize("name", ["dashboard", "product_list", "category_list", "customer_list", "order_list", "payment_list", "inventory_list", "audit_list", "user_list", "product_create", "category_create", "customer_create", "order_create", "user_create"])
def test_admin_pages_render_real_records(client, web_data, name):
    client.force_login(web_data.admin)
    response = client.get(reverse(f"core:{name}"))
    assert response.status_code == 200
    assert "Smart Sales" in response.content.decode()


def test_viewer_cannot_write_or_access_admin_even_direct_url(client, web_data):
    client.force_login(web_data.viewer)
    for name in ("product_create", "category_create", "customer_create", "order_create", "user_create", "audit_list", "user_list"):
        assert client.get(reverse(f"core:{name}")).status_code == 403
    for name, pk in (("product_edit", web_data.product.pk), ("customer_edit", web_data.customer.pk), ("user_edit", web_data.staff.pk)):
        assert client.post(reverse(f"core:{name}", args=[pk]), {"sale_price": 1}).status_code == 403
    assert client.post(reverse("core:stock_adjust", args=[web_data.product.pk]), {"quantity": 50, "reason": "forged"}).status_code == 403
    web_data.product.refresh_from_db()
    assert web_data.product.sale_price == Decimal(50000)
    assert web_data.product.stock.quantity_on_hand == 50


def test_staff_cannot_manage_catalog_inventory_or_users(client, web_data):
    client.force_login(web_data.staff)
    for name in ("product_create", "category_create", "user_list", "audit_list"):
        assert client.get(reverse(f"core:{name}")).status_code == 403
    content = client.get(reverse("core:product_list")).content.decode()
    assert "Giá vốn" not in content
    assert reverse("core:product_create") not in content


def test_product_crud_archive_and_initial_stock_are_audited(client, web_data):
    client.force_login(web_data.manager)
    payload = {"sku": "NEW-50", "name": "Chuột mới", "category": web_data.category.pk, "sale_price": 80000, "cost_price": 40000, "low_stock_threshold": 5, "initial_quantity": 50, "is_active": "on"}
    assert client.post(reverse("core:product_create"), payload).status_code == 302
    product = Product.objects.get(sku="NEW-50")
    assert product.stock.quantity_on_hand == 50
    assert InventoryMovement.objects.filter(product=product, signed_qty=50).count() == 1
    payload.pop("initial_quantity")
    payload.pop("is_active")
    payload["sale_price"] = 90000
    assert client.post(reverse("core:product_edit", args=[product.pk]), payload).status_code == 302
    product.refresh_from_db()
    assert not product.is_active
    assert product.sale_price == 90000
    audit = AuditLog.objects.get(object_id=str(product.pk), action="product.updated")
    assert audit.changes["sale_price"] == {"old": "80000", "new": "90000"}
    assert audit.changes["is_active"] == {"old": True, "new": False}


def test_negative_price_duplicate_sku_and_race_do_not_500(client, web_data, monkeypatch):
    client.force_login(web_data.manager)
    payload = {"sku": web_data.product.sku, "name": "Bản trùng", "category": web_data.category.pk, "sale_price": -1, "cost_price": 0, "low_stock_threshold": 5, "initial_quantity": 0, "is_active": "on"}
    response = client.post(reverse("core:product_create"), payload)
    assert response.status_code == 200
    assert response.context["form"].errors
    assert Product.objects.count() == 1
    payload.update(sku="CONCURRENT-NEW", sale_price=100)
    monkeypatch.setattr(Product, "save", lambda *args, **kwargs: (_ for _ in ()).throw(IntegrityError("duplicate")))
    response = client.post(reverse("core:product_create"), payload)
    assert response.status_code == 200
    assert "Dữ liệu đã tồn tại" in response.content.decode()


def test_uploaded_image_validation_and_persistence(client, web_data, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    client.force_login(web_data.manager)
    payload = {"sku": "IMG", "name": "Sản phẩm có ảnh", "category": web_data.category.pk, "sale_price": 100, "cost_price": 0, "low_stock_threshold": 5, "initial_quantity": 0, "is_active": "on"}
    payload["image"] = SimpleUploadedFile("bad.svg", b"<svg>no</svg>", content_type="image/svg+xml")
    response = client.post(reverse("core:product_create"), payload)
    assert response.context["form"].errors.get("image")
    image = io.BytesIO()
    Image.new("RGB", (50, 50), "blue").save(image, format="PNG")
    payload["image"] = SimpleUploadedFile("valid.png", image.getvalue(), content_type="image/png")
    assert client.post(reverse("core:product_create"), payload).status_code == 302
    product = Product.objects.get(sku="IMG")
    assert product.image.storage.exists(product.image.name)
    assert "valid.png" not in product.image.name


def test_oversize_dimensions_rejected_even_small_file(client, web_data, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    client.force_login(web_data.manager)
    image = io.BytesIO()
    Image.new("RGB", (5000, 1), "white").save(image, format="PNG")
    payload = {"sku": "HUGE", "name": "Ảnh quá rộng", "category": web_data.category.pk, "sale_price": 100, "cost_price": 0, "low_stock_threshold": 5, "initial_quantity": 0, "is_active": "on", "image": SimpleUploadedFile("huge.png", image.getvalue(), content_type="image/png")}
    response = client.post(reverse("core:product_create"), payload)
    assert response.status_code == 200
    assert "Kích thước ảnh tối đa" in response.content.decode()
    assert not Product.objects.filter(sku="HUGE").exists()


def test_customer_crud_validation_and_profile(client, web_data):
    client.force_login(web_data.staff)
    payload = {"code": "", "name": "Khách hàng mới", "phone": "0987654321", "email": "khach@example.test", "address": "Địa chỉ mẫu", "note": "Khách demo", "is_active": "on"}
    assert client.post(reverse("core:customer_create"), payload).status_code == 302
    customer = Customer.objects.get(name="Khách hàng mới")
    assert customer.code
    assert client.get(reverse("core:customer_detail", args=[customer.pk])).status_code == 200
    payload["email"] = "not-an-email"
    assert client.post(reverse("core:customer_edit", args=[customer.pk]), payload).context["form"].errors.get("email")


def test_real_ui_order_payment_complete_flow_and_rejected_errors(client, web_data):
    data = web_data
    client.force_login(data.staff)
    payload = order_payload(data)
    payload.update(discount="9000", total="1", subtotal="1")
    assert client.post(reverse("core:order_create"), payload).status_code == 302
    order = SalesOrder.objects.latest("pk")
    assert order.total == 150000
    assert order.discount == 0
    transition = reverse("core:order_transition", args=[order.pk])
    assert client.post(transition, {"status": "CONFIRMED"}).status_code == 302
    assert data.product.stock.quantity_on_hand == 47
    assert client.post(transition, {"status": "CONFIRMED"}).status_code == 400
    assert InventoryMovement.objects.filter(product=data.product, kind="SALE").count() == 1
    data.product.sale_price = 90000
    data.product.save()
    assert client.get(reverse("core:order_detail", args=[order.pk])).status_code == 200
    order.refresh_from_db()
    assert order.total == 150000
    payment_url = reverse("core:payment_create", args=[order.pk])
    first = {"amount": "50000", "method": "CASH", "reference": "WEB-FIRST", "idempotency_key": str(uuid.uuid4())}
    assert client.post(payment_url, first).status_code == 302
    assert client.post(payment_url, first).status_code == 302
    assert Payment.objects.filter(order=order).count() == 1
    overpay = {"amount": "100001", "method": "CASH", "reference": "WEB-OVER", "idempotency_key": str(uuid.uuid4())}
    response = client.post(payment_url, overpay)
    assert response.status_code == 400
    assert "vượt quá" in response.content.decode()
    assert client.post(payment_url, {"amount": "100000", "method": "TRANSFER", "reference": "WEB-FINAL", "idempotency_key": str(uuid.uuid4())}).status_code == 302
    assert order.amount_paid == 150000
    assert client.post(transition, {"status": "PROCESSING"}).status_code == 302
    assert client.post(transition, {"status": "COMPLETED"}).status_code == 302
    order.refresh_from_db()
    assert order.status == "COMPLETED"
    assert order.balance_due == 0


def test_insufficient_stock_and_duplicate_rows_surface_clear_errors(client, web_data):
    client.force_login(web_data.staff)
    order = make_order(client, web_data, 60)
    response = client.post(reverse("core:order_transition", args=[order.pk]), {"status": "CONFIRMED"})
    assert response.status_code == 400
    assert "không đủ" in response.content.decode().lower()
    assert web_data.product.stock.quantity_on_hand == 50
    payload = order_payload(web_data)
    payload.update({"items-TOTAL_FORMS": "2", "items-1-product": web_data.product.pk, "items-1-quantity": "1"})
    response = client.post(reverse("core:order_create"), payload)
    assert response.status_code == 200
    assert "Một sản phẩm chỉ được xuất hiện một lần" in response.content.decode()
    assert SalesOrder.objects.count() == 1


def test_cancel_authorization_and_restore_once(client, web_data):
    client.force_login(web_data.staff)
    order = make_order(client, web_data)
    transition = reverse("core:order_transition", args=[order.pk])
    client.post(transition, {"status": "CONFIRMED"})
    assert client.post(transition, {"status": "CANCELLED", "reason": "Khách yêu cầu"}).status_code == 403
    client.force_login(web_data.manager)
    assert client.post(transition, {"status": "CANCELLED", "reason": "Khách yêu cầu"}).status_code == 302
    assert client.post(transition, {"status": "CANCELLED", "reason": "Khách yêu cầu"}).status_code == 400
    assert web_data.product.stock.quantity_on_hand == 50
    assert InventoryMovement.objects.filter(order=order, kind="CANCELLATION").count() == 1


def test_zero_stock_adjust_and_overdraw_error_preserve_stock(client, web_data):
    client.force_login(web_data.manager)
    url = reverse("core:stock_adjust", args=[web_data.product.pk])
    for quantity in (0, -51):
        response = client.post(url, {"quantity": quantity, "reason": "Kiểm thử dữ liệu"})
        assert response.status_code == 400
        assert response.context["form"].errors
    assert web_data.product.stock.quantity_on_hand == 50


def test_catalog_search_filter_sort_pagination_persist_filters(client, web_data):
    client.force_login(web_data.viewer)
    for index in range(17):
        Product.objects.create(sku=f"PAGE-{index}", name=f"Chuột phân trang {index:02}", category=web_data.category, sale_price=100 + index, cost_price=0)
    response = client.get(reverse("core:product_list"), {"q": "Chuột", "sort": "-sale_price", "active": "1"})
    assert response.status_code == 200
    assert response.context["page_obj"].paginator.count == 17
    assert list(response.context["page_obj"])[0].sale_price == 116
    assert "q=Chu%E1%BB%99t" in response.content.decode()
    assert "page=2" in response.content.decode()
    assert "Bàn phím kiểm thử" not in response.content.decode()


def test_team_permissions_secure_password_and_self_protection(client, web_data):
    client.force_login(web_data.admin)
    payload = {"username": "new_staff", "first_name": "Mới", "last_name": "Nhân viên", "email": "staff@example.test", "role": "STAFF", "is_active": "on", "password": "LocalTest-Passcode-582!", "is_superuser": "on"}
    assert client.post(reverse("core:user_create"), payload).status_code == 302
    user = User.objects.get(username="new_staff")
    assert user.check_password(payload["password"])
    assert not user.is_superuser
    assert payload["password"] not in str(list(AuditLog.objects.values_list("changes", flat=True)))
    own = {"username": web_data.admin.username, "first_name": "", "last_name": "", "email": "", "role": "VIEWER", "is_active": "on", "password": ""}
    response = client.post(reverse("core:user_edit", args=[web_data.admin.pk]), own)
    assert response.status_code == 200
    assert "Không thể tự" in response.content.decode()
    web_data.admin.refresh_from_db()
    assert web_data.admin.role == "ADMIN"
    own["role"] = "ADMIN"
    own.pop("is_active")
    assert client.post(reverse("core:user_edit", args=[web_data.admin.pk]), own).context["form"].errors
    web_data.admin.refresh_from_db()
    assert web_data.admin.is_active


def test_login_csrf_and_safe_redirect(client, web_data):
    web_data.staff.set_password("LocalLogin-Password-582!")
    web_data.staff.save()
    secure_client = Client(enforce_csrf_checks=True)
    assert secure_client.post(reverse("login"), {"username": web_data.staff.username, "password": "LocalLogin-Password-582!"}).status_code == 403
    secure_client.get(reverse("login"))
    response = secure_client.post(reverse("login"), {"username": web_data.staff.username, "password": "LocalLogin-Password-582!", "next": "https://untrusted.invalid/path", "csrfmiddlewaretoken": secure_client.cookies["csrftoken"].value})
    assert response.status_code == 302
    assert response.url == "/"
    assert secure_client.get(reverse("logout")).status_code == 405
    secure_client.force_login(web_data.manager)
    assert secure_client.post(reverse("core:stock_adjust", args=[web_data.product.pk]), {"quantity": 3, "reason": "No CSRF"}).status_code == 403


def test_user_text_is_escaped_in_customer_profile(client, web_data):
    web_data.customer.name = '<script>alert("bad")</script>'
    web_data.customer.save()
    client.force_login(web_data.staff)
    response = client.get(reverse("core:customer_detail", args=[web_data.customer.pk]))
    assert b"<script>alert" not in response.content
    assert b"&lt;script&gt;" in response.content


@pytest.mark.parametrize("state", ["DRAFT", "CANCELLED", "PAID"])
def test_stale_payment_form_shows_error_when_payment_panel_unavailable(client, web_data, state):
    client.force_login(web_data.manager)
    order = make_order(client, web_data)
    if state == "CANCELLED":
        client.post(reverse("core:order_transition", args=[order.pk]), {"status": "CANCELLED", "reason": "Hủy kiểm thử"})
    if state == "PAID":
        client.post(reverse("core:order_transition", args=[order.pk]), {"status": "CONFIRMED"})
        response = client.post(reverse("core:payment_create", args=[order.pk]), {"amount": order.total, "method": "CASH", "reference": "STALE-FULL", "idempotency_key": uuid.uuid4()})
        assert response.status_code == 302
    before = Payment.objects.count()
    response = client.post(reverse("core:payment_create", args=[order.pk]), {"amount": 1, "method": "CASH", "reference": "STALE-EXTRA", "idempotency_key": uuid.uuid4()})
    assert response.status_code == 400
    assert "Chưa thể ghi nhận thanh toán." in response.content.decode()
    assert Payment.objects.count() == before
