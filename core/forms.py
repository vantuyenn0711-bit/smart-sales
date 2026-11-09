import uuid

from django import forms
from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.forms import formset_factory

from accounts.models import User
from catalog.models import Category, Product
from customers.models import Customer
from payments.models import Payment


class StyledFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if not isinstance(field.widget, (forms.CheckboxInput, forms.HiddenInput)):
                field.widget.attrs.setdefault("class", "input")
            if field.help_text:
                field.widget.attrs.setdefault("aria-describedby", f"id_{name}_help")


class CategoryForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Category
        fields = ["code", "name", "is_active"]
        labels = {"code": "Mã danh mục", "name": "Tên danh mục", "is_active": "Đang sử dụng"}


class ProductForm(StyledFormMixin, forms.ModelForm):
    initial_quantity = forms.IntegerField(
        label="Tồn kho ban đầu", min_value=0, max_value=1_000_000, initial=0,
        help_text="Chỉ áp dụng khi tạo sản phẩm. Các lần nhập/xuất sau được ghi ở Tồn kho.",
    )

    class Meta:
        model = Product
        fields = ["sku", "name", "category", "sale_price", "cost_price", "image", "low_stock_threshold", "is_active"]
        labels = {
            "sku": "Mã sản phẩm (SKU)", "name": "Tên sản phẩm", "category": "Danh mục",
            "sale_price": "Giá bán (đ)", "cost_price": "Giá vốn (đ)", "image": "Ảnh sản phẩm",
            "low_stock_threshold": "Ngưỡng cảnh báo tồn", "is_active": "Cho phép bán",
        }
        widgets = {"image": forms.ClearableFileInput(attrs={"accept": "image/png,image/jpeg,image/webp"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.filter(is_active=True)
        if self.instance.pk:
            self.fields.pop("initial_quantity")
            self.fields["category"].queryset = Category.objects.filter(
                Q(is_active=True) | Q(pk=self.instance.category_id)
            )
        for name in ("sale_price", "cost_price"):
            self.fields[name].min_value = 0
            self.fields[name].widget.attrs.update(min=0, step=1)
        self.fields["image"].help_text = "PNG, JPEG hoặc WebP; tối đa 2 MB."

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if not image or not hasattr(image, "content_type"):
            return image
        if image.size > 2 * 1024 * 1024:
            raise ValidationError("Ảnh phải nhỏ hơn hoặc bằng 2 MB.")
        if image.content_type not in {"image/png", "image/jpeg", "image/webp"}:
            raise ValidationError("Chỉ chấp nhận ảnh PNG, JPEG hoặc WebP.")
        if getattr(image, "image", None) and image.image.format not in {"PNG", "JPEG", "WEBP"}:
            raise ValidationError("Nội dung ảnh không hợp lệ.")
        if getattr(image, "image", None):
            width, height = image.image.size
            if width > 4096 or height > 4096 or width * height > 16_000_000:
                raise ValidationError("Kích thước ảnh tối đa 4096 × 4096 và 16 triệu điểm ảnh.")
        return image


class CustomerForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Customer
        fields = ["code", "name", "phone", "email", "address", "note", "is_active"]
        labels = {
            "code": "Mã khách hàng", "name": "Tên khách hàng", "phone": "Số điện thoại",
            "email": "Email", "address": "Địa chỉ", "note": "Ghi chú", "is_active": "Đang hoạt động",
        }
        widgets = {"address": forms.Textarea(attrs={"rows": 2}), "note": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["code"].required = False
        self.fields["code"].help_text = "Để trống để hệ thống tự tạo mã."


class OrderForm(StyledFormMixin, forms.Form):
    customer = forms.ModelChoiceField(label="Khách hàng", queryset=Customer.objects.none(), required=False, empty_label="Khách lẻ")
    discount = forms.DecimalField(label="Chiết khấu toàn đơn (đ)", min_value=0, max_digits=16, decimal_places=0, initial=0)
    note = forms.CharField(label="Ghi chú đơn hàng", required=False, widget=forms.Textarea(attrs={"rows": 3}), max_length=2000)

    def __init__(self, *args, actor=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["customer"].queryset = Customer.objects.filter(is_active=True).order_by("name")
        if actor and not (actor.is_superuser or actor.role in {User.Role.ADMIN, User.Role.MANAGER}):
            self.fields["discount"].disabled = True
            self.fields["discount"].help_text = "Quản lý hoặc quản trị viên mới được áp dụng chiết khấu."


class OrderItemForm(StyledFormMixin, forms.Form):
    product = forms.ModelChoiceField(label="Sản phẩm", queryset=Product.objects.none(), empty_label="Chọn sản phẩm")
    quantity = forms.IntegerField(label="Số lượng", min_value=1, max_value=1_000_000, initial=1)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["product"].queryset = Product.objects.filter(is_active=True, category__is_active=True).order_by("name")


class BaseOrderItemFormSet(forms.BaseFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return
        seen = set()
        count = 0
        for form in self.forms:
            if not form.cleaned_data or form.cleaned_data.get("DELETE"):
                continue
            product = form.cleaned_data.get("product")
            if product:
                if product.pk in seen:
                    raise ValidationError("Một sản phẩm chỉ được xuất hiện một lần. Hãy gộp số lượng.")
                seen.add(product.pk)
                count += 1
        if not count:
            raise ValidationError("Thêm ít nhất một sản phẩm vào đơn hàng.")


OrderItemFormSet = formset_factory(OrderItemForm, formset=BaseOrderItemFormSet, extra=1, can_delete=True, max_num=50, validate_max=True)


class PaymentForm(StyledFormMixin, forms.Form):
    amount = forms.DecimalField(label="Số tiền thu (đ)", min_value=1, max_digits=16, decimal_places=0)
    method = forms.ChoiceField(label="Phương thức", choices=Payment.Method.choices)
    reference = forms.CharField(label="Mã tham chiếu", max_length=100, required=False, help_text="Mã giao dịch duy nhất, nếu có. Chuyển khoản cần được đối chiếu thủ công.")
    idempotency_key = forms.UUIDField(widget=forms.HiddenInput, initial=uuid.uuid4)


class StockAdjustmentForm(StyledFormMixin, forms.Form):
    quantity = forms.IntegerField(label="Số lượng thay đổi", min_value=-1_000_000, max_value=1_000_000, help_text="Số dương để nhập thêm, số âm để xuất điều chỉnh.")
    reason = forms.CharField(label="Lý do điều chỉnh", min_length=3, max_length=500)

    def clean_quantity(self):
        quantity = self.cleaned_data["quantity"]
        if quantity == 0:
            raise ValidationError("Số lượng thay đổi phải khác 0.")
        return quantity


class UserForm(StyledFormMixin, forms.ModelForm):
    password = forms.CharField(label="Mật khẩu mới", required=False, widget=forms.PasswordInput, help_text="Tối thiểu 10 ký tự. Để trống khi không đổi mật khẩu.")

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "role", "is_active"]
        labels = {"username": "Tên đăng nhập", "first_name": "Tên", "last_name": "Họ", "email": "Email", "role": "Vai trò", "is_active": "Cho phép đăng nhập"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password"].required = not self.instance.pk

    def clean_password(self):
        password = self.cleaned_data.get("password")
        if password:
            if len(password) < 10:
                raise ValidationError("Mật khẩu cần ít nhất 10 ký tự.")
            password_validation.validate_password(password, self.instance)
        return password

    def save(self, commit=True):
        user = super().save(commit=False)
        if self.cleaned_data.get("password"):
            user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user
