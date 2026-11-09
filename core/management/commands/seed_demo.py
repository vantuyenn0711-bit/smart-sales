import os
import uuid
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from catalog.models import Category, Product
from core.models import AuditLog
from customers.models import Customer
from inventory.services import adjust_stock
from orders.models import SalesOrder
from orders.services import create_order, transition_order
from payments.models import Payment
from payments.services import record_payment


class Command(BaseCommand):
    help = "Create clearly labelled synthetic demo data; never resets existing data or passwords."

    def add_arguments(self, parser):
        parser.add_argument("--password-env", default="DEMO_PASSWORD", help="Environment variable containing the initial demo password.")

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEMO_MODE:
            raise CommandError("Set DEMO_MODE=true explicitly before loading synthetic demo data.")
        if AuditLog.objects.filter(action="Demo initialized", object_type="seed_demo").exists():
            self.stdout.write("Demo data already exists. No data or passwords changed.")
            return
        password = os.environ.get(options["password_env"], "")
        if not password:
            raise CommandError("Provide an initial password through --password-env. Passwords are never printed.")
        User = get_user_model()
        usernames = ["demo_admin", "demo_manager", "demo_sales", "demo_viewer"]
        if User.objects.filter(username__in=usernames).exists() or Product.objects.filter(sku__startswith="DEMO-").exists():
            raise CommandError("Demo identifiers already exist without a completed seed marker. Nothing was overwritten.")
        users = []
        for username, role, first, last in [
            ("demo_admin", "ADMIN", "Tuyền", "Nguyễn Văn"),
            ("demo_manager", "MANAGER", "Linh", "Trần Khánh"),
            ("demo_sales", "STAFF", "Minh", "Lê Hoàng"),
            ("demo_viewer", "VIEWER", "An", "Phạm Ngọc"),
        ]:
            user = User(username=username, role=role, first_name=first, last_name=last, email=f"{username}@example.invalid")
            try:
                validate_password(password, user=user)
            except ValidationError as exc:
                raise CommandError("Initial demo password does not meet Django password validation.") from exc
            user.set_password(password)
            user.save()
            users.append(user)
        admin, manager, sales, _viewer = users
        categories = [Category.objects.create(code=code, name=name) for code, name in [
            ("DEMO-AUDIO", "Âm thanh"), ("DEMO-ACCESS", "Phụ kiện"), ("DEMO-OFFICE", "Thiết bị văn phòng"),
        ]]
        products = []
        for index, (name, category, sale, cost, stock) in enumerate([
            ("Tai nghe Bluetooth Air Pro", 0, 1290000, 780000, 150),
            ("Bàn phím cơ không dây K75", 2, 1850000, 1120000, 140),
            ("Chuột không dây Silent M3", 2, 450000, 235000, 180),
            ("Loa Bluetooth Mini S2", 0, 890000, 520000, 110),
            ("Sạc nhanh USB-C 65W", 1, 590000, 310000, 160),
            ("Cáp USB-C bọc dù 1.5m", 1, 190000, 85000, 210),
            ("Giá đỡ laptop nhôm", 2, 390000, 195000, 7),
            ("Hub chuyển đổi USB-C 6 in 1", 1, 750000, 410000, 4),
        ], 1):
            product = Product.objects.create(sku=f"DEMO-SP{index:03}", name=name, category=categories[category], sale_price=sale, cost_price=cost)
            adjust_stock(actor=admin, product_id=product.pk, quantity=stock, reason="Tồn đầu kỳ · dữ liệu demo")
            products.append(product)
        customers = [Customer.objects.create(code=f"DEMO-KH{index:03}", name=name, phone=f"090000{index:04}", email=f"customer{index}@example.invalid", address=address, note="Khách hàng giả lập để trình diễn, không phải dữ liệu cá nhân thật.") for index, (name, address) in enumerate([
            ("Nguyễn Hoàng Anh", "Bắc Ninh · địa chỉ demo"), ("Trần Minh Trang", "Hà Nội · địa chỉ demo"),
            ("Lê Quốc Bảo", "Đà Nẵng · địa chỉ demo"), ("Phạm Thu Hà", "TP. Hồ Chí Minh · địa chỉ demo"),
            ("Vũ Đức Huy", "Bắc Giang · địa chỉ demo"), ("Đỗ Ngọc Mai", "Hải Phòng · địa chỉ demo"),
        ], 1)]
        now = timezone.now()
        for index in range(42):
            actor = sales if index % 3 else manager
            product = products[index % 6]
            items = [{"product": product, "quantity": 1 + index % 3}]
            if index % 4 == 0:
                items.append({"product": products[(index + 1) % 6], "quantity": 1})
            order = create_order(actor=actor, customer=customers[index % len(customers)], items=items, discount=Decimal(20000) if actor == manager else Decimal(0), note="Đơn hàng demo · dữ liệu giả lập")
            timestamp = now - timedelta(days=(index * 3) % 29, hours=index % 5)
            if index >= 38:
                status = ["DRAFT", "CONFIRMED", "PROCESSING", "CANCELLED"][index - 38]
            else:
                status = "COMPLETED"
            if status == "CANCELLED":
                transition_order(actor=manager, order_id=order.pk, target_status="CANCELLED", reason="Hủy đơn demo theo yêu cầu khách")
            elif status != "DRAFT":
                transition_order(actor=actor, order_id=order.pk, target_status="CONFIRMED")
                if status in {"PROCESSING", "COMPLETED"}:
                    transition_order(actor=actor, order_id=order.pk, target_status="PROCESSING")
                if status == "COMPLETED":
                    transition_order(actor=actor, order_id=order.pk, target_status="COMPLETED")
                if index % 7 != 0:
                    amount = order.total if index % 5 else order.total // 2
                    payment = record_payment(actor=actor, order_id=order.pk, amount=amount, method="CASH" if index % 2 else "TRANSFER", reference=f"DEMO-TT{index:04}", idempotency_key=uuid.uuid4())
                    # Fixture dates only: business creation still goes through normal services.
                    Payment.objects.filter(pk=payment.pk).update(paid_at=timestamp + timedelta(minutes=15))
            dates = {"created_at": timestamp, "updated_at": timestamp + timedelta(minutes=10)}
            if status == "COMPLETED":
                dates["completed_at"] = timestamp + timedelta(minutes=10)
            SalesOrder.objects.filter(pk=order.pk).update(**dates)
        AuditLog.objects.create(actor=admin, action="Demo initialized", object_type="seed_demo", object_id="v1", changes={"synthetic": True, "orders": 42})
        self.stdout.write(self.style.SUCCESS("Created synthetic demo: 4 roles, 3 categories, 8 products, 6 customers, 42 orders. Usernames: demo_admin, demo_manager, demo_sales, demo_viewer. Password came from the specified environment variable."))
