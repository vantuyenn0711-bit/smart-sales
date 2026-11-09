from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter
def money(value):
    try:
        return f"{Decimal(value):,.0f}".replace(",", ".") + " ₫"
    except (InvalidOperation, TypeError, ValueError):
        return "0 ₫"


@register.filter
def initials(value):
    return "".join(word[0] for word in str(value).split()[:2]).upper() or "SS"


@register.filter
def payment_label(value):
    return {"paid": "Đã thanh toán", "partial": "Thanh toán một phần", "unpaid": "Chưa thanh toán", "PAID": "Đã thanh toán", "PARTIAL": "Thanh toán một phần", "UNPAID": "Chưa thanh toán"}.get(str(value), value)


@register.filter
def subtract(left, right):
    try:
        return left - right
    except TypeError:
        return 0
