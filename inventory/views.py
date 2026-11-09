from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render
from django.views.decorators.http import require_GET

from inventory.forms import MovementFilterForm
from inventory.models import InventoryMovement


@login_required
@require_GET
def movement_list(request):
    form = MovementFilterForm(request.GET)
    records = InventoryMovement.objects.select_related("product", "order", "actor").order_by("-created_at", "-pk")
    valid = form.is_valid()
    if valid:
        filters = form.cleaned_data
        if filters.get("q"):
            term = filters["q"]
            records = records.filter(Q(product__sku__icontains=term) | Q(product__name__icontains=term) | Q(order__order_no__icontains=term) | Q(reason__icontains=term))
        if filters.get("product"):
            records = records.filter(product=filters["product"])
        if filters.get("kind"):
            records = records.filter(kind=filters["kind"])
        if filters.get("from_date"):
            records = records.filter(created_at__date__gte=filters["from_date"])
        if filters.get("to_date"):
            records = records.filter(created_at__date__lte=filters["to_date"])
    else:
        records = records.none()
    return render(request, "inventory/movement_list.html", {"form": form, "page_obj": Paginator(records, 20).get_page(request.GET.get("page"))}, status=200 if valid else 400)
