from django.urls import path

from analytics.views import dashboard
from core import views

app_name = "core"
urlpatterns = [
    path("", dashboard, name="dashboard"),
    path("products/", views.product_list, name="product_list"),
    path("products/new/", views.product_create, name="product_create"),
    path("products/<int:pk>/edit/", views.product_edit, name="product_edit"),
    path("categories/", views.category_list, name="category_list"),
    path("categories/new/", views.category_create, name="category_create"),
    path("categories/<int:pk>/edit/", views.category_edit, name="category_edit"),
    path("customers/", views.customer_list, name="customer_list"),
    path("customers/new/", views.customer_create, name="customer_create"),
    path("customers/<int:pk>/", views.customer_detail, name="customer_detail"),
    path("customers/<int:pk>/edit/", views.customer_edit, name="customer_edit"),
    path("orders/", views.order_list, name="order_list"),
    path("orders/new/", views.order_create, name="order_create"),
    path("orders/<int:pk>/", views.order_detail, name="order_detail"),
    path("orders/<int:pk>/transition/", views.order_transition, name="order_transition"),
    path("orders/<int:pk>/payments/", views.payment_create, name="payment_create"),
    path("payments/", views.payment_list, name="payment_list"),
    path("inventory/", views.inventory_list, name="inventory_list"),
    path("inventory/<int:pk>/adjust/", views.stock_adjust, name="stock_adjust"),
    path("audit/", views.audit_list, name="audit_list"),
    path("team/", views.user_list, name="user_list"),
    path("team/new/", views.user_create, name="user_create"),
    path("team/<int:pk>/edit/", views.user_edit, name="user_edit"),
]
