from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from django.core.exceptions import ValidationError

from core.models import AuditLog

MAX_MONEY = Decimal("9999999999999999")
MAX_QUANTITY = 1_000_000_000


def money(value, *, positive=False):
    try:
        result = Decimal(str(value))
        if not result.is_finite() or result < 0 or result > MAX_MONEY:
            raise ValueError
        result = result.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        if positive and result <= 0:
            raise ValueError
    except (InvalidOperation, ValueError, TypeError):
        raise ValidationError("Số tiền không hợp lệ hoặc vượt giới hạn cho phép.") from None
    return result


def validate_quantity(value, *, signed=False):
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value == 0
        or abs(value) > MAX_QUANTITY
        or (not signed and value < 0)
    ):
        raise ValidationError("Số lượng phải là số nguyên hợp lệ và khác 0.")
    return value


def audit(*, actor, action, obj, changes=None):
    return AuditLog.objects.create(
        actor=actor,
        action=action,
        object_type=obj._meta.label,
        object_id=str(obj.pk),
        changes=changes or {},
    )
