from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from catalog.models import Product
from core.permissions import MANAGE_ROLES, SELL_ROLES, require_role
from core.services import MAX_QUANTITY, audit, money, validate_quantity
from customers.models import Customer
from inventory.models import InventoryMovement, StockBalance
from orders.models import OrderStatusHistory, SalesOrder, SalesOrderItem


@transaction.atomic
def create_order(*, actor, customer=None, items, discount=Decimal(0), note=""):
    require_role(actor, *SELL_ROLES)
    discount = money(discount)
    if discount:
        require_role(actor, *MANAGE_ROLES)
    if not isinstance(items, (list, tuple)) or not 1 <= len(items) <= 100:
        raise ValidationError("Đơn hàng cần từ 1 đến 100 dòng sản phẩm.")
    note = str(note or "").strip()
    if len(note) > 2000:
        raise ValidationError("Ghi chú không được vượt quá 2.000 ký tự.")
    requested = {}
    for item in items:
        try:
            product_id = item["product"].pk
            quantity = item["quantity"]
        except (KeyError, TypeError, AttributeError):
            raise ValidationError("Dòng sản phẩm không hợp lệ.") from None
        validate_quantity(quantity)
        if not product_id or product_id in requested:
            raise ValidationError("Sản phẩm không hợp lệ hoặc bị trùng trong đơn.")
        requested[product_id] = quantity
    products = list(
        Product.objects.select_for_update(of=("self",))
        .select_related("category")
        .filter(pk__in=requested)
        .order_by("pk")
    )
    if len(products) != len(requested):
        raise ValidationError("Có sản phẩm không tồn tại.")
    lines = []
    subtotal = Decimal(0)
    for product in products:
        if not product.is_active or not product.category.is_active:
            raise ValidationError(f"Sản phẩm {product.sku} đã ngừng kinh doanh.")
        price, cost = money(product.sale_price), money(product.cost_price)
        line_total = money(price * requested[product.pk])
        subtotal = money(subtotal + line_total)
        lines.append(
            SalesOrderItem(
                product=product,
                quantity=requested[product.pk],
                unit_price_snapshot=price,
                cost_snapshot=cost,
                line_total=line_total,
            )
        )
    if discount > subtotal:
        raise ValidationError("Chiết khấu không được lớn hơn tổng tiền hàng.")
    if customer is not None:
        try:
            customer = Customer.objects.get(pk=customer.pk, is_active=True)
        except (Customer.DoesNotExist, AttributeError):
            raise ValidationError("Khách hàng không tồn tại hoặc đã ngừng hoạt động.") from None
    order = SalesOrder.objects.create(
        customer=customer,
        subtotal=subtotal,
        discount=discount,
        total=subtotal - discount,
        created_by=actor,
        note=note,
    )
    for line in lines:
        line.order = order
    SalesOrderItem.objects.bulk_create(lines)
    OrderStatusHistory.objects.create(
        order=order,
        from_status="",
        to_status=SalesOrder.Status.DRAFT,
        actor=actor,
        reason="Tạo đơn nháp",
    )
    audit(actor=actor, action="Tạo đơn hàng", obj=order, changes={"total": str(order.total)})
    return order


@transaction.atomic
def transition_order(*, actor, order_id, target_status, reason=""):
    require_role(actor, *SELL_ROLES)
    if target_status == SalesOrder.Status.CANCELLED:
        require_role(actor, *MANAGE_ROLES)
    reason = str(reason or "").strip()
    if len(reason) > 500:
        raise ValidationError("Lý do không được vượt quá 500 ký tự.")
    try:
        order = SalesOrder.objects.select_for_update().get(pk=order_id)
    except SalesOrder.DoesNotExist:
        raise ValidationError("Đơn hàng không tồn tại.") from None
    allowed = {
        SalesOrder.Status.DRAFT: {SalesOrder.Status.CONFIRMED, SalesOrder.Status.CANCELLED},
        SalesOrder.Status.CONFIRMED: {SalesOrder.Status.PROCESSING, SalesOrder.Status.CANCELLED},
        SalesOrder.Status.PROCESSING: {SalesOrder.Status.COMPLETED, SalesOrder.Status.CANCELLED},
    }
    if target_status not in allowed.get(order.status, set()):
        raise ValidationError("Không thể chuyển sang trạng thái này từ trạng thái hiện tại.")
    if target_status == SalesOrder.Status.CANCELLED:
        if not reason:
            raise ValidationError("Vui lòng nhập lý do hủy đơn.")
        if order.amount_paid:
            raise ValidationError("Đơn đã thu tiền cần quy trình hoàn tiền; MVP chưa hỗ trợ hủy đơn này.")
    old_status = order.status
    if target_status == SalesOrder.Status.CONFIRMED or (
        target_status == SalesOrder.Status.CANCELLED and old_status != SalesOrder.Status.DRAFT
    ):
        lines = list(order.items.select_related("product__category").order_by("product_id"))
        if not lines:
            raise ValidationError("Đơn hàng không có sản phẩm.")
        # Every path that takes multiple balance locks uses the same product order.
        balances = {
            balance.product_id: balance
            for balance in StockBalance.objects.select_for_update()
            .filter(product_id__in=[line.product_id for line in lines])
            .order_by("product_id")
        }
        for line in lines:
            if line.product_id not in balances:
                raise ValidationError("Sản phẩm chưa có thông tin tồn kho.")
            balance = balances[line.product_id]
            delta = -line.quantity if target_status == SalesOrder.Status.CONFIRMED else line.quantity
            if target_status == SalesOrder.Status.CONFIRMED and (
                not line.product.is_active or not line.product.category.is_active
            ):
                raise ValidationError(f"Sản phẩm {line.product.sku} đã ngừng kinh doanh.")
            if not 0 <= balance.quantity_on_hand + delta <= MAX_QUANTITY:
                raise ValidationError(f"Không đủ tồn kho hoặc vượt giới hạn cho sản phẩm {line.product.sku}.")
            balance.quantity_on_hand += delta
            balance.save(update_fields=["quantity_on_hand"])
            InventoryMovement.objects.create(
                product_id=line.product_id,
                order=order,
                signed_qty=delta,
                kind=InventoryMovement.Kind.SALE if delta < 0 else InventoryMovement.Kind.CANCELLATION,
                reason=reason or f"Xác nhận {order.order_no}",
                actor=actor,
            )
    order.status = target_status
    if target_status == SalesOrder.Status.COMPLETED:
        order.completed_at = timezone.now()
    order.save(update_fields=["status", "completed_at", "updated_at"])
    OrderStatusHistory.objects.create(
        order=order,
        from_status=old_status,
        to_status=target_status,
        actor=actor,
        reason=reason,
    )
    audit(
        actor=actor,
        action="Cập nhật trạng thái đơn",
        obj=order,
        changes={"from": old_status, "to": target_status, "reason": reason},
    )
    return order
