import uuid

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from core.permissions import SELL_ROLES, require_role
from core.services import audit, money
from orders.models import SalesOrder
from payments.models import Payment


@transaction.atomic
def record_payment(*, actor, order_id, amount, method, reference="", idempotency_key):
    require_role(actor, *SELL_ROLES)
    amount = money(amount, positive=True)
    if method not in Payment.Method.values:
        raise ValidationError("Phương thức thanh toán không hợp lệ.")
    reference = str(reference or "").strip().upper() or None
    if reference and len(reference) > 100:
        raise ValidationError("Mã tham chiếu không được vượt quá 100 ký tự.")
    try:
        token = uuid.UUID(str(idempotency_key))
    except (ValueError, TypeError, AttributeError):
        raise ValidationError("Mã chống gửi trùng không hợp lệ. Vui lòng tải lại trang.") from None
    try:
        order = SalesOrder.objects.select_for_update().get(pk=order_id)
    except SalesOrder.DoesNotExist:
        raise ValidationError("Đơn hàng không tồn tại.") from None
    existing = Payment.objects.filter(idempotency_key=token).first()
    if existing:
        if (
            existing.order_id == order.pk
            and existing.amount == amount
            and existing.method == method
            and existing.reference == reference
            and existing.created_by_id == actor.pk
        ):
            return existing
        raise ValidationError("Mã chống gửi trùng đã được dùng cho giao dịch khác.")
    if order.status not in {
        SalesOrder.Status.CONFIRMED,
        SalesOrder.Status.PROCESSING,
        SalesOrder.Status.COMPLETED,
    }:
        raise ValidationError("Chỉ được thu tiền cho đơn đã xác nhận và chưa hủy.")
    if reference and Payment.objects.filter(reference=reference).exists():
        raise ValidationError("Mã tham chiếu thanh toán đã tồn tại.")
    if amount > order.balance_due:
        raise ValidationError("Số tiền vượt quá số dư còn phải thanh toán.")
    try:
        # Savepoint allows a cross-order reference/token race to become a clean validation error.
        with transaction.atomic():
            payment = Payment.objects.create(
                order=order,
                method=method,
                amount=amount,
                reference=reference,
                idempotency_key=token,
                created_by=actor,
            )
    except IntegrityError:
        raise ValidationError("Giao dịch hoặc mã tham chiếu này đã được ghi nhận.") from None
    audit(
        actor=actor,
        action="Ghi nhận thanh toán",
        obj=payment,
        changes={"order": order.order_no, "amount": str(amount), "method": method, "reference": reference},
    )
    return payment
