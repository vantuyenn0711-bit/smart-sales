import uuid
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier
from types import SimpleNamespace

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, close_old_connections, connection, transaction

from accounts.models import User
from catalog.models import Category, Product
from core.models import AuditLog
from core.services import money
from customers.models import Customer
from inventory.models import InventoryMovement, StockBalance
from inventory.services import adjust_stock
from orders.models import OrderStatusHistory, SalesOrder, SalesOrderItem
from orders.services import create_order, transition_order
from payments.models import Payment
from payments.services import record_payment


@pytest.fixture
def domain_data():
    admin = User.objects.create(username="domain_admin", role=User.Role.ADMIN)
    manager = User.objects.create(username="domain_manager", role=User.Role.MANAGER)
    staff = User.objects.create(username="domain_staff", role=User.Role.STAFF)
    viewer = User.objects.create(username="domain_viewer", role=User.Role.VIEWER)
    category = Category.objects.create(code="TECH", name="Công nghệ")
    product = Product.objects.create(
        sku="DEMO-50",
        name="Sản phẩm kiểm thử",
        category=category,
        sale_price=50000,
        cost_price=20000,
    )
    customer = Customer.objects.create(name="Khách hàng kiểm thử", phone="0900000000")
    adjust_stock(actor=manager, product_id=product.pk, quantity=50, reason="Nhập kho kiểm thử")
    return SimpleNamespace(
        admin=admin,
        manager=manager,
        staff=staff,
        viewer=viewer,
        category=category,
        product=product,
        customer=customer,
    )


def draft(data, quantity=3, **kwargs):
    return create_order(
        actor=data.staff,
        customer=data.customer,
        items=[{"product": data.product, "quantity": quantity}],
        **kwargs,
    )


def confirmed(data, quantity=3):
    order = draft(data, quantity)
    return transition_order(actor=data.staff, order_id=order.pk, target_status="CONFIRMED")


def pay(data, order, amount, **kwargs):
    return record_payment(
        actor=data.staff,
        order_id=order.pk,
        amount=amount,
        method="CASH",
        idempotency_key=kwargs.pop("idempotency_key", uuid.uuid4()),
        **kwargs,
    )


pytestmark = pytest.mark.django_db


def test_confirm_50_to_47_once_with_history(domain_data):
    data = domain_data
    order = draft(data)
    assert StockBalance.objects.get(product=data.product).quantity_on_hand == 50
    assert order.total == Decimal(150000)
    transition_order(actor=data.staff, order_id=order.pk, target_status="CONFIRMED")
    with pytest.raises(ValidationError):
        transition_order(actor=data.staff, order_id=order.pk, target_status="CONFIRMED")
    assert StockBalance.objects.get(product=data.product).quantity_on_hand == 47
    movement = InventoryMovement.objects.get(order=order, kind="SALE")
    assert movement.signed_qty == -3
    assert OrderStatusHistory.objects.filter(order=order, to_status="CONFIRMED").count() == 1


def test_insufficient_stock_leaves_order_draft_and_ledger_unchanged(domain_data):
    data = domain_data
    confirmed(data)
    order = draft(data, 60)
    before = InventoryMovement.objects.count()
    with pytest.raises(ValidationError, match="Không đủ tồn"):
        transition_order(actor=data.staff, order_id=order.pk, target_status="CONFIRMED")
    order.refresh_from_db()
    assert order.status == "DRAFT"
    assert StockBalance.objects.get(product=data.product).quantity_on_hand == 47
    assert InventoryMovement.objects.count() == before
    assert order.history.count() == 1


def test_multiline_insufficient_stock_rolls_back_all_balances(domain_data):
    data = domain_data
    empty = Product.objects.create(
        sku="EMPTY",
        name="Hết hàng",
        category=data.category,
        sale_price=10000,
        cost_price=5000,
    )
    order = create_order(
        actor=data.staff,
        items=[
            {"product": data.product, "quantity": 3},
            {"product": empty, "quantity": 1},
        ],
    )
    before_audit = AuditLog.objects.count()
    with pytest.raises(ValidationError):
        transition_order(actor=data.staff, order_id=order.pk, target_status="CONFIRMED")
    assert StockBalance.objects.get(product=data.product).quantity_on_hand == 50
    assert not InventoryMovement.objects.filter(order=order).exists()
    assert AuditLog.objects.count() == before_audit


def test_current_database_price_used_and_snapshot_survives_changes(domain_data):
    data = domain_data
    # The object handed to the service is deliberately stale.
    Product.objects.filter(pk=data.product.pk).update(sale_price=60000, cost_price=25000)
    order = draft(data)
    assert order.total == Decimal(180000)
    line = order.items.get()
    assert line.unit_price_snapshot == Decimal(60000)
    assert line.cost_snapshot == Decimal(25000)
    transition_order(actor=data.staff, order_id=order.pk, target_status="CONFIRMED")
    Product.objects.filter(pk=data.product.pk).update(sale_price=90000, cost_price=50000)
    order.refresh_from_db()
    line.refresh_from_db()
    assert order.total == Decimal(180000)
    assert line.line_total == Decimal(180000)
    assert line.cost_snapshot == Decimal(25000)
    line.unit_price_snapshot = 1
    with pytest.raises(ValidationError):
        line.save()


@pytest.mark.parametrize("quantity", [0, -1, 1.5, "3", True, 1_000_000_001])
def test_invalid_quantities_never_create_order(domain_data, quantity):
    with pytest.raises(ValidationError):
        draft(domain_data, quantity)
    assert SalesOrder.objects.count() == 0


def test_duplicates_empty_items_and_discount_over_total_rejected(domain_data):
    data = domain_data
    with pytest.raises(ValidationError):
        create_order(actor=data.staff, items=[])
    with pytest.raises(ValidationError):
        create_order(
            actor=data.staff,
            items=[
                {"product": data.product, "quantity": 1},
                {"product": data.product, "quantity": 2},
            ],
        )
    with pytest.raises(ValidationError):
        create_order(actor=data.manager, items=[{"product": data.product, "quantity": 1}], discount=50001)
    assert not SalesOrder.objects.exists()


def test_staff_cannot_grant_discount_manager_can(domain_data):
    data = domain_data
    with pytest.raises(PermissionDenied):
        draft(data, discount=1000)
    order = create_order(
        actor=data.manager,
        items=[{"product": data.product, "quantity": 3}],
        discount=1000,
    )
    assert order.subtotal == Decimal(150000)
    assert order.total == Decimal(149000)


@pytest.mark.parametrize("field", ["is_active", "category"])
def test_inactive_catalog_cannot_be_ordered(domain_data, field):
    data = domain_data
    if field == "category":
        data.category.is_active = False
        data.category.save(update_fields=["is_active"])
    else:
        data.product.is_active = False
        data.product.save(update_fields=["is_active"])
    with pytest.raises(ValidationError):
        draft(data)
    assert not SalesOrder.objects.exists()


def test_archived_customer_rejected_even_with_stale_instance(domain_data):
    data = domain_data
    Customer.objects.filter(pk=data.customer.pk).update(is_active=False)
    with pytest.raises(ValidationError):
        draft(data)


@pytest.mark.parametrize("starting_status", ["DRAFT", "CONFIRMED", "PROCESSING"])
def test_unpaid_cancellation_returns_stock_exactly_once(domain_data, starting_status):
    data = domain_data
    order = draft(data)
    if starting_status != "DRAFT":
        transition_order(actor=data.staff, order_id=order.pk, target_status="CONFIRMED")
    if starting_status == "PROCESSING":
        transition_order(actor=data.staff, order_id=order.pk, target_status="PROCESSING")
    transition_order(actor=data.manager, order_id=order.pk, target_status="CANCELLED", reason="Khách đổi ý")
    with pytest.raises(ValidationError):
        transition_order(actor=data.manager, order_id=order.pk, target_status="CANCELLED", reason="Gửi lặp")
    assert StockBalance.objects.get(product=data.product).quantity_on_hand == 50
    assert InventoryMovement.objects.filter(order=order, kind="CANCELLATION").count() == (
        0 if starting_status == "DRAFT" else 1
    )
    assert order.history.filter(to_status="CANCELLED").count() == 1


def test_paid_order_cannot_cancel_and_completed_cannot_go_back(domain_data):
    data = domain_data
    order = confirmed(data)
    pay(data, order, 10000)
    with pytest.raises(ValidationError, match="hoàn tiền"):
        transition_order(actor=data.manager, order_id=order.pk, target_status="CANCELLED", reason="Hủy")
    transition_order(actor=data.staff, order_id=order.pk, target_status="PROCESSING")
    transition_order(actor=data.staff, order_id=order.pk, target_status="COMPLETED")
    order.refresh_from_db()
    assert order.completed_at is not None
    for target in ["CONFIRMED", "PROCESSING", "CANCELLED"]:
        with pytest.raises(ValidationError):
            transition_order(actor=data.manager, order_id=order.pk, target_status=target, reason="Hủy")
    assert StockBalance.objects.get(product=data.product).quantity_on_hand == 47


def test_cancel_needs_reason_and_management_role(domain_data):
    data = domain_data
    order = confirmed(data)
    with pytest.raises(PermissionDenied):
        transition_order(actor=data.staff, order_id=order.pk, target_status="CANCELLED", reason="Hủy")
    with pytest.raises(ValidationError):
        transition_order(actor=data.manager, order_id=order.pk, target_status="CANCELLED")


def test_partial_full_payment_and_replay_do_not_duplicate(domain_data):
    data = domain_data
    order = confirmed(data)
    token = uuid.uuid4()
    first = pay(data, order, 50000, reference=" cash-001 ", idempotency_key=token)
    assert first.reference == "CASH-001"
    repeated = pay(data, order, 50000, reference="CASH-001", idempotency_key=token)
    assert repeated.pk == first.pk
    order.refresh_from_db()
    assert order.amount_paid == Decimal(50000)
    assert order.balance_due == Decimal(100000)
    assert order.payment_status == "partial"
    pay(data, order, 100000, reference="CASH-002")
    order.refresh_from_db()
    assert order.payment_status == "paid"
    assert order.balance_due == 0
    assert order.payments.count() == 2


def test_payment_duplicate_reference_overpay_and_changed_token_payload(domain_data):
    data = domain_data
    order = confirmed(data)
    token = uuid.uuid4()
    pay(data, order, 50000, reference="REF-1", idempotency_key=token)
    for kwargs in [
        {"amount": 50000, "reference": "ref-1"},
        {"amount": 100001},
        {"amount": 40000, "idempotency_key": token, "reference": "REF-1"},
    ]:
        with pytest.raises(ValidationError):
            pay(data, order, **kwargs)
    assert order.payments.count() == 1
    assert order.amount_paid == Decimal(50000)


@pytest.mark.parametrize("amount", [-1, 0, "NaN", "Infinity", "1e1000", "garbage"])
def test_invalid_payment_amount_rejected(domain_data, amount):
    order = confirmed(domain_data)
    with pytest.raises(ValidationError):
        pay(domain_data, order, amount)
    assert not Payment.objects.exists()


def test_draft_cancelled_payments_and_invalid_method_token_rejected(domain_data):
    data = domain_data
    order = draft(data)
    with pytest.raises(ValidationError):
        pay(data, order, 1)
    transition_order(actor=data.manager, order_id=order.pk, target_status="CANCELLED", reason="Hủy")
    with pytest.raises(ValidationError):
        pay(data, order, 1)
    valid_order = confirmed(data)
    with pytest.raises(ValidationError):
        record_payment(
            actor=data.staff, order_id=valid_order.pk, amount=1, method="CARD", idempotency_key=uuid.uuid4()
        )
    with pytest.raises(ValidationError):
        pay(data, valid_order, 1, idempotency_key="invalid")


def test_viewer_and_inactive_staff_cannot_mutate_domain(domain_data):
    data = domain_data
    order = confirmed(data)
    for actor in [data.viewer, data.staff]:
        if actor == data.staff:
            actor.is_active = False
        with pytest.raises(PermissionDenied):
            create_order(actor=actor, items=[{"product": data.product, "quantity": 1}])
        with pytest.raises(PermissionDenied):
            transition_order(actor=actor, order_id=order.pk, target_status="PROCESSING")
        with pytest.raises(PermissionDenied):
            record_payment(
                actor=actor, order_id=order.pk, amount=1, method="CASH", idempotency_key=uuid.uuid4()
            )
        with pytest.raises(PermissionDenied):
            adjust_stock(actor=actor, product_id=data.product.pk, quantity=1, reason="Thử")


def test_negative_stock_adjustment_and_missing_reason_rejected(domain_data):
    data = domain_data
    before = InventoryMovement.objects.count()
    with pytest.raises(ValidationError):
        adjust_stock(actor=data.manager, product_id=data.product.pk, quantity=-51, reason="Xuất")
    with pytest.raises(ValidationError):
        adjust_stock(actor=data.manager, product_id=data.product.pk, quantity=1, reason="")
    assert StockBalance.objects.get(product=data.product).quantity_on_hand == 50
    assert InventoryMovement.objects.count() == before


def test_database_rejects_negative_stock_price_duplicate_sku_and_invalid_totals(domain_data):
    data = domain_data
    operations = [
        lambda: StockBalance.objects.filter(product=data.product).update(quantity_on_hand=-1),
        lambda: Product.objects.filter(pk=data.product.pk).update(sale_price=-1),
        lambda: Product.objects.create(
            sku=data.product.sku, name="Trùng", category=data.category, sale_price=1, cost_price=0
        ),
    ]
    order = draft(data)
    operations.append(lambda: SalesOrder.objects.filter(pk=order.pk).update(total=1))
    operations.append(lambda: SalesOrderItem.objects.filter(order=order).update(quantity=0))
    for operation in operations:
        with pytest.raises(IntegrityError), transaction.atomic():
            operation()


def test_ledger_payment_and_history_records_are_append_only(domain_data):
    data = domain_data
    order = confirmed(data)
    payment = pay(data, order, 1000)
    for obj in [payment, order.history.first(), order.movements.first(), AuditLog.objects.first()]:
        with pytest.raises(ValidationError):
            obj.save()
        with pytest.raises(ValidationError):
            obj.delete()


def test_vnd_rounds_half_up():
    assert money("1000.49") == Decimal(1000)
    assert money("1000.50") == Decimal(1001)


def race(functions):
    barrier = Barrier(len(functions))

    def call(fn):
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            result = fn()
            return ("ok", result.pk)
        except ValidationError:
            return ("rejected", None)
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=len(functions)) as pool:
        return list(pool.map(call, functions))


def require_postgres():
    if connection.vendor != "postgresql":
        pytest.skip("Row-lock concurrency acceptance requires real PostgreSQL")


@pytest.mark.django_db(transaction=True)
def test_concurrent_orders_cannot_oversell(domain_data):
    require_postgres()
    data = domain_data
    first, second = draft(data, 30), draft(data, 30)
    results = race(
        [
            lambda: transition_order(actor=data.staff, order_id=first.pk, target_status="CONFIRMED"),
            lambda: transition_order(actor=data.staff, order_id=second.pk, target_status="CONFIRMED"),
        ]
    )
    assert sorted(status for status, _ in results) == ["ok", "rejected"]
    assert StockBalance.objects.get(product=data.product).quantity_on_hand == 20
    assert InventoryMovement.objects.filter(kind="SALE").count() == 1
    assert SalesOrder.objects.filter(status="CONFIRMED").count() == 1


@pytest.mark.django_db(transaction=True)
def test_concurrent_confirmation_same_order_deducts_once(domain_data):
    require_postgres()
    data = domain_data
    order = draft(data)
    results = race(
        [
            lambda: transition_order(actor=data.staff, order_id=order.pk, target_status="CONFIRMED"),
            lambda: transition_order(actor=data.staff, order_id=order.pk, target_status="CONFIRMED"),
        ]
    )
    assert sorted(status for status, _ in results) == ["ok", "rejected"]
    assert StockBalance.objects.get(product=data.product).quantity_on_hand == 47
    assert InventoryMovement.objects.filter(order=order, kind="SALE").count() == 1


@pytest.mark.django_db(transaction=True)
def test_concurrent_payments_cannot_overpay(domain_data):
    require_postgres()
    data = domain_data
    order = confirmed(data)
    results = race(
        [
            lambda: pay(data, order, 100000, reference="CONCURRENT-A"),
            lambda: pay(data, order, 100000, reference="CONCURRENT-B"),
        ]
    )
    assert sorted(status for status, _ in results) == ["ok", "rejected"]
    assert order.amount_paid == Decimal(100000)
    assert order.payments.count() == 1


@pytest.mark.django_db(transaction=True)
def test_concurrent_identical_payment_replay_credits_once(domain_data):
    require_postgres()
    data = domain_data
    order = confirmed(data)
    token = uuid.uuid4()
    results = race(
        [
            lambda: pay(data, order, 75000, idempotency_key=token),
            lambda: pay(data, order, 75000, idempotency_key=token),
        ]
    )
    assert [status for status, _ in results] == ["ok", "ok"]
    assert len({pk for _, pk in results}) == 1
    assert order.amount_paid == Decimal(75000)
    assert order.payments.count() == 1


@pytest.mark.django_db(transaction=True)
def test_concurrent_reference_on_distinct_orders_is_unique(domain_data):
    require_postgres()
    data = domain_data
    first, second = confirmed(data), confirmed(data)
    results = race(
        [
            lambda: pay(data, first, 1000, reference="SHARED-REFERENCE"),
            lambda: pay(data, second, 1000, reference="SHARED-REFERENCE"),
        ]
    )
    assert sorted(status for status, _ in results) == ["ok", "rejected"]
    assert Payment.objects.filter(reference="SHARED-REFERENCE").count() == 1


@pytest.mark.django_db(transaction=True)
def test_concurrent_cancel_and_payment_never_leave_paid_cancelled_order(domain_data):
    require_postgres()
    data = domain_data
    order = confirmed(data)
    results = race(
        [
            lambda: pay(data, order, 1000),
            lambda: transition_order(
                actor=data.manager, order_id=order.pk, target_status="CANCELLED", reason="Hủy đồng thời"
            ),
        ]
    )
    assert sorted(status for status, _ in results) == ["ok", "rejected"]
    order.refresh_from_db()
    stock = StockBalance.objects.get(product=data.product).quantity_on_hand
    if order.status == "CANCELLED":
        assert order.amount_paid == 0
        assert stock == 50
    else:
        assert order.status == "CONFIRMED"
        assert order.amount_paid == Decimal(1000)
        assert stock == 47


@pytest.mark.django_db(transaction=True)
def test_concurrent_stock_adjustment_and_confirmation_do_not_lose_updates(domain_data):
    require_postgres()
    data = domain_data
    order = draft(data)
    results = race(
        [
            lambda: adjust_stock(
                actor=data.manager, product_id=data.product.pk, quantity=1, reason="Nhập thêm"
            ),
            lambda: transition_order(actor=data.staff, order_id=order.pk, target_status="CONFIRMED"),
        ]
    )
    assert [status for status, _ in results] == ["ok", "ok"]
    assert StockBalance.objects.get(product=data.product).quantity_on_hand == 48


def test_superuser_command_defaults_to_admin_role():
    admin = User.objects.create_superuser(username="super_admin", password="Local-test-password-1")
    assert admin.role == User.Role.ADMIN
    assert admin.is_superuser
