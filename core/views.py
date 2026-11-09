from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import F, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.models import User
from catalog.models import Category, Product
from core.forms import (
    CategoryForm,
    CustomerForm,
    OrderForm,
    OrderItemFormSet,
    PaymentForm,
    ProductForm,
    StockAdjustmentForm,
    UserForm,
)
from core.models import AuditLog
from core.permissions import roles_required
from customers.models import Customer
from inventory.models import InventoryMovement, StockBalance
from inventory.services import adjust_stock
from orders.models import SalesOrder
from orders.services import create_order, transition_order
from payments.models import Payment
from payments.services import record_payment

MANAGERS = (User.Role.ADMIN, User.Role.MANAGER)
SELLERS = (*MANAGERS, User.Role.STAFF)


def _page(request, queryset, size=15):
    return Paginator(queryset, size).get_page(request.GET.get("page"))


def _search(request, queryset, fields):
    query = request.GET.get("q", "").strip()[:150]
    if query:
        condition = Q()
        for field in fields:
            condition |= Q(**{f"{field}__icontains": query})
        queryset = queryset.filter(condition)
    return queryset


def _sort(request, queryset, allowed, default):
    value = request.GET.get("sort", default)
    return queryset.order_by(value if value in allowed else default, "pk")


def _active(request, queryset):
    active = request.GET.get("active", "")
    return queryset.filter(is_active=active == "1") if active in {"0", "1"} else queryset


def _snapshot(instance):
    if not instance.pk:
        return {}
    tracked = {"sale_price", "cost_price", "is_active", "role"}
    fields = [field.name for field in instance._meta.fields if field.name in tracked]
    return type(instance).objects.filter(pk=instance.pk).values(*fields).first() or {}


def _audit(actor, action, instance, changed, previous=None):
    changes = {}
    for name in changed:
        if name == "password":
            changes["password_changed"] = True
        elif hasattr(instance, name):
            value = getattr(instance, name)
            value = value if isinstance(value, (bool, int)) or value is None else str(value)
            if previous and name in previous:
                old = previous[name]
                old = old if isinstance(old, (bool, int)) or old is None else str(old)
                changes[name] = {"old": old, "new": value}
            else:
                changes[name] = value
    AuditLog.objects.create(actor=actor, action=action, object_type=instance._meta.label_lower,
                            object_id=str(instance.pk), changes=changes)


def _save_form(request, form, *, title, subtitle, back, action, after_save=None):
    previous = _snapshot(form.instance)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                instance = form.save()
                if after_save:
                    after_save(instance)
                _audit(request.user, action, instance, form.changed_data, previous=previous)
            messages.success(request, "Đã lưu thay đổi thành công.")
            return redirect(back)
        except ValidationError as error:
            form.add_error(None, error)
        except IntegrityError:
            form.add_error(None, "Dữ liệu đã tồn tại hoặc vừa được thay đổi. Vui lòng kiểm tra và thử lại.")
    return render(request, "core/form.html", {"form": form, "page_title": title, "subtitle": subtitle, "back_url": back})


@login_required
def product_list(request):
    products = _active(request, _search(request, Product.objects.select_related("category", "stock"), ["sku", "name", "category__name"]))
    category = request.GET.get("category", "")
    if category.isdigit():
        products = products.filter(category_id=category)
    if request.GET.get("stock") == "low":
        products = products.filter(stock__quantity_on_hand__lte=F("low_stock_threshold"))
    products = _sort(request, products, {"name", "-name", "sale_price", "-sale_price", "sku", "-created_at"}, "-created_at")
    return render(request, "catalog/product_list.html", {"page_obj": _page(request, products), "categories": Category.objects.all(), "total_count": Product.objects.count(), "active_count": Product.objects.filter(is_active=True).count(), "low_count": Product.objects.filter(stock__quantity_on_hand__lte=F("low_stock_threshold")).count()})


@roles_required(*MANAGERS)
def product_create(request):
    form = ProductForm(request.POST or None, request.FILES or None)

    def initialize(product):
        StockBalance.objects.get_or_create(product=product)
        quantity = form.cleaned_data["initial_quantity"]
        if quantity:
            adjust_stock(actor=request.user, product_id=product.pk, quantity=quantity, reason="Nhập tồn ban đầu")

    return _save_form(request, form, title="Thêm sản phẩm", subtitle="Tạo sản phẩm, giá và tồn kho ban đầu.", back="core:product_list", action="product.created", after_save=initialize)


@roles_required(*MANAGERS)
def product_edit(request, pk):
    form = ProductForm(request.POST or None, request.FILES or None, instance=get_object_or_404(Product, pk=pk))
    return _save_form(request, form, title="Chỉnh sửa sản phẩm", subtitle="Giá mới không thay đổi các đơn đã tạo. Tắt Cho phép bán để lưu trữ sản phẩm.", back="core:product_list", action="product.updated")


@login_required
def category_list(request):
    categories = _active(request, _search(request, Category.objects.all(), ["code", "name"]))
    categories = _sort(request, categories, {"name", "-name", "code"}, "name")
    return render(request, "catalog/category_list.html", {"page_obj": _page(request, categories)})


@roles_required(*MANAGERS)
def category_create(request):
    return _save_form(request, CategoryForm(request.POST or None), title="Thêm danh mục", subtitle="Sắp xếp sản phẩm theo nhóm để dễ theo dõi.", back="core:category_list", action="category.created")


@roles_required(*MANAGERS)
def category_edit(request, pk):
    return _save_form(request, CategoryForm(request.POST or None, instance=get_object_or_404(Category, pk=pk)), title="Chỉnh sửa danh mục", subtitle="Danh mục ngừng hoạt động được giữ lại trong lịch sử.", back="core:category_list", action="category.updated")


@login_required
def customer_list(request):
    customers = _active(request, _search(request, Customer.objects.all(), ["code", "name", "phone", "email"]))
    customers = _sort(request, customers, {"name", "-name", "code", "-created_at"}, "-created_at")
    return render(request, "customers/customer_list.html", {"page_obj": _page(request, customers), "total_count": Customer.objects.count()})


@roles_required(*SELLERS)
def customer_create(request):
    return _save_form(request, CustomerForm(request.POST or None), title="Thêm khách hàng", subtitle="Lưu thông tin liên hệ và theo dõi lịch sử mua hàng.", back="core:customer_list", action="customer.created")


@roles_required(*SELLERS)
def customer_edit(request, pk):
    return _save_form(request, CustomerForm(request.POST or None, instance=get_object_or_404(Customer, pk=pk)), title="Chỉnh sửa khách hàng", subtitle="Tắt trạng thái hoạt động để lưu trữ hồ sơ.", back="core:customer_list", action="customer.updated")


@login_required
def customer_detail(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    orders = SalesOrder.objects.filter(customer=customer).select_related("created_by").prefetch_related("payments").order_by("-created_at")
    total_spent = orders.filter(status=SalesOrder.Status.COMPLETED).aggregate(total=Sum("total"))["total"] or 0
    return render(request, "customers/customer_detail.html", {"customer": customer, "page_obj": _page(request, orders), "total_spent": total_spent, "order_count": orders.count()})


@login_required
def order_list(request):
    orders = _search(request, SalesOrder.objects.select_related("customer", "created_by").prefetch_related("payments"), ["order_no", "customer__name", "customer__phone"])
    status = request.GET.get("status", "")
    if status in SalesOrder.Status.values:
        orders = orders.filter(status=status)
    if request.GET.get("customer", "").isdigit():
        orders = orders.filter(customer_id=request.GET["customer"])
    orders = _sort(request, orders, {"-created_at", "created_at", "total", "-total", "order_no"}, "-created_at")
    return render(request, "orders/order_list.html", {"page_obj": _page(request, orders), "statuses": SalesOrder.Status.choices, "total_count": SalesOrder.objects.count(), "processing_count": SalesOrder.objects.filter(status__in=["CONFIRMED", "PROCESSING"]).count()})


@roles_required(*SELLERS)
def order_create(request):
    form = OrderForm(request.POST or None, actor=request.user)
    formset = OrderItemFormSet(request.POST or None, prefix="items")
    if request.method == "POST" and form.is_valid() and formset.is_valid():
        try:
            order = create_order(actor=request.user, customer=form.cleaned_data["customer"], discount=form.cleaned_data["discount"], note=form.cleaned_data["note"], items=[{"product": row.cleaned_data["product"], "quantity": row.cleaned_data["quantity"]} for row in formset if row.cleaned_data and not row.cleaned_data.get("DELETE")])
            messages.success(request, "Đã tạo đơn nháp. Xác nhận đơn để trừ tồn kho.")
            return redirect("core:order_detail", pk=order.pk)
        except ValidationError as error:
            form.add_error(None, error)
    catalog = [{"id": p.pk, "name": p.name, "price": str(p.sale_price), "stock": getattr(getattr(p, "stock", None), "quantity_on_hand", 0)} for p in Product.objects.filter(is_active=True).select_related("stock")]
    return render(request, "orders/order_form.html", {"form": form, "formset": formset, "product_data": catalog})


def _order_context(order, payment_form=None, transition_error=None):
    return {"order": order, "payment_form": payment_form or PaymentForm(initial={"amount": order.balance_due}), "transition_error": transition_error}


def _order(pk):
    return get_object_or_404(SalesOrder.objects.select_related("customer", "created_by").prefetch_related("items__product", "payments__created_by", "history__actor"), pk=pk)


@login_required
def order_detail(request, pk):
    return render(request, "orders/order_detail.html", _order_context(_order(pk)))


@require_POST
@roles_required(*SELLERS)
def order_transition(request, pk):
    try:
        transition_order(actor=request.user, order_id=pk, target_status=request.POST.get("status", ""), reason=request.POST.get("reason", ""))
        messages.success(request, "Đã cập nhật trạng thái đơn hàng.")
        return redirect("core:order_detail", pk=pk)
    except ValidationError as error:
        return render(request, "orders/order_detail.html", _order_context(_order(pk), transition_error=" ".join(error.messages)), status=400)


@require_POST
@roles_required(*SELLERS)
def payment_create(request, pk):
    order = _order(pk)
    form = PaymentForm(request.POST)
    if form.is_valid():
        try:
            record_payment(actor=request.user, order_id=pk, **form.cleaned_data)
            messages.success(request, "Đã ghi nhận thanh toán. Số dư được cập nhật từ các giao dịch.")
            return redirect("core:order_detail", pk=pk)
        except ValidationError as error:
            form.add_error(None, error)
    return render(request, "orders/order_detail.html", _order_context(order, payment_form=form), status=400)


@login_required
def payment_list(request):
    payments = _search(request, Payment.objects.select_related("order", "order__customer", "created_by"), ["reference", "order__order_no", "order__customer__name"])
    if request.GET.get("method") in Payment.Method.values:
        payments = payments.filter(method=request.GET["method"])
    payments = _sort(request, payments, {"-paid_at", "paid_at", "amount", "-amount"}, "-paid_at")
    return render(request, "payments/payment_list.html", {"page_obj": _page(request, payments), "methods": Payment.Method.choices, "receipts": Payment.objects.aggregate(total=Sum("amount"))["total"] or 0})


@login_required
def inventory_list(request):
    products = _search(request, Product.objects.select_related("stock", "category"), ["sku", "name"])
    if request.GET.get("stock") == "low":
        products = products.filter(stock__quantity_on_hand__lte=F("low_stock_threshold"))
    products = _sort(request, products, {"name", "sku", "stock__quantity_on_hand", "-stock__quantity_on_hand"}, "name")
    movements = InventoryMovement.objects.select_related("product", "order", "actor").order_by("-created_at")[:15]
    return render(request, "inventory/inventory_list.html", {"page_obj": _page(request, products), "movements": movements, "adjustment_form": StockAdjustmentForm()})


@require_POST
@roles_required(*MANAGERS)
def stock_adjust(request, pk):
    product = get_object_or_404(Product, pk=pk)
    form = StockAdjustmentForm(request.POST)
    if form.is_valid():
        try:
            adjust_stock(actor=request.user, product_id=pk, **form.cleaned_data)
            messages.success(request, "Đã điều chỉnh tồn kho và ghi lịch sử.")
            return redirect("core:inventory_list")
        except ValidationError as error:
            form.add_error(None, error)
    return render(request, "inventory/stock_form.html", {"form": form, "product": product}, status=400)


@roles_required(*MANAGERS)
def audit_list(request):
    logs = _search(request, AuditLog.objects.select_related("actor"), ["action", "object_type", "object_id", "actor__username"])
    return render(request, "core/audit_list.html", {"page_obj": _page(request, logs.order_by("-created_at"))})


@roles_required(User.Role.ADMIN)
def user_list(request):
    users = _search(request, User.objects.all(), ["username", "first_name", "last_name", "email"])
    return render(request, "accounts/user_list.html", {"page_obj": _page(request, users.order_by("username"))})


@roles_required(User.Role.ADMIN)
def user_create(request):
    return _save_form(request, UserForm(request.POST or None), title="Thêm thành viên", subtitle="Cấp quyền phù hợp với công việc của từng thành viên.", back="core:user_list", action="user.created")


@roles_required(User.Role.ADMIN)
def user_edit(request, pk):
    user = get_object_or_404(User, pk=pk)
    previous = _snapshot(user)
    form = UserForm(request.POST or None, instance=user)
    if request.method == "POST" and form.is_valid():
        if user.pk == request.user.pk and (not form.cleaned_data["is_active"] or form.cleaned_data["role"] != User.Role.ADMIN):
            form.add_error(None, "Không thể tự vô hiệu hóa hoặc hạ quyền tài khoản đang đăng nhập.")
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                admins = list(User.objects.select_for_update().filter(is_active=True).filter(Q(role=User.Role.ADMIN) | Q(is_superuser=True)).order_by("pk"))
                if request.user.pk not in {admin.pk for admin in admins}:
                    raise PermissionDenied("Tài khoản quản trị không còn hoạt động.")
                remains_admin = form.cleaned_data["is_active"] and (form.cleaned_data["role"] == User.Role.ADMIN or user.is_superuser)
                if not remains_admin and user.pk in {admin.pk for admin in admins} and len(admins) <= 1:
                    form.add_error(None, "Phải giữ ít nhất một quản trị viên đang hoạt động.")
                else:
                    saved = form.save()
                    if saved.pk == request.user.pk and form.cleaned_data.get("password"):
                        update_session_auth_hash(request, saved)
                    _audit(request.user, "user.updated", saved, form.changed_data, previous=previous)
                    messages.success(request, "Đã cập nhật thành viên.")
                    return redirect("core:user_list")
        except IntegrityError:
            form.add_error(None, "Tên đăng nhập đã tồn tại. Vui lòng kiểm tra lại.")
    return render(request, "core/form.html", {"form": form, "page_title": "Chỉnh sửa thành viên", "subtitle": "Thay đổi vai trò, trạng thái hoặc đặt lại mật khẩu.", "back_url": "core:user_list"})
