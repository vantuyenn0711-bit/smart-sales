from django.core.exceptions import ValidationError
from django.db import transaction

from core.permissions import MANAGE_ROLES, require_role
from core.services import MAX_QUANTITY, audit, validate_quantity
from inventory.models import InventoryMovement, StockBalance


@transaction.atomic
def adjust_stock(*, actor, product_id, quantity, reason):
    require_role(actor, *MANAGE_ROLES)
    validate_quantity(quantity, signed=True)
    reason = str(reason or "").strip()
    if not reason or len(reason) > 500:
        raise ValidationError("Cần nhập lý do điều chỉnh (tối đa 500 ký tự).")
    try:
        balance = StockBalance.objects.select_for_update().get(product_id=product_id)
    except StockBalance.DoesNotExist:
        raise ValidationError("Sản phẩm không tồn tại.") from None
    new_quantity = balance.quantity_on_hand + quantity
    if new_quantity < 0 or new_quantity > MAX_QUANTITY:
        raise ValidationError("Điều chỉnh vượt tồn khả dụng hoặc giới hạn số lượng.")
    old_quantity = balance.quantity_on_hand
    balance.quantity_on_hand = new_quantity
    balance.save(update_fields=["quantity_on_hand"])
    InventoryMovement.objects.create(
        product_id=product_id,
        signed_qty=quantity,
        kind=InventoryMovement.Kind.ADJUSTMENT,
        reason=reason,
        actor=actor,
    )
    audit(
        actor=actor,
        action="Điều chỉnh tồn kho",
        obj=balance.product,
        changes={"before": old_quantity, "after": new_quantity, "reason": reason},
    )
    return balance
