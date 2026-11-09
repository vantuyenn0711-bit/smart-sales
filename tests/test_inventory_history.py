import pytest
from django.urls import reverse

from accounts.models import User
from catalog.models import Category, Product
from inventory.services import adjust_stock

pytestmark = pytest.mark.django_db


def test_full_history_keeps_old_records_searchable_and_paginated(client):
    manager = User.objects.create_user(username="history_manager", role="MANAGER")
    viewer = User.objects.create_user(username="history_viewer", role="VIEWER")
    category = Category.objects.create(code="HISTORY", name="Danh mục kiểm thử")
    product = Product.objects.create(sku="HISTORY-1", name="Sản phẩm", category=category, sale_price=1000, cost_price=500)
    for index in range(25):
        adjust_stock(actor=manager, product_id=product.pk, quantity=1, reason=f"Kiểm kê {index:02}")
    client.force_login(viewer)
    route = reverse("inventory:movement_list")
    first = client.get(route)
    assert first.status_code == 200
    assert first.context["page_obj"].paginator.count == 25
    assert len(first.context["page_obj"]) == 20
    second = client.get(route, {"page": 2})
    assert "Kiểm kê 00" in second.content.decode()
    searched = client.get(route, {"q": "Kiểm kê 00"})
    assert searched.context["page_obj"].paginator.count == 1
    assert client.get(route, {"from_date": "invalid"}).status_code == 400
    assert client.get(route, {"from_date": "2026-11-09", "to_date": "2026-11-01"}).status_code == 400
    assert client.post(route, {}).status_code == 405
    client.logout()
    assert client.get(route).status_code == 302
