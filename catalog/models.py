import uuid

from django.core.validators import MinValueValidator
from django.db import models, transaction


def product_image_path(instance, filename):
    suffix = filename.rsplit(".", 1)[-1].lower()
    return f"products/{uuid.uuid4().hex}.{suffix}"


class Category(models.Model):
    code = models.CharField("Mã danh mục", max_length=32, unique=True)
    name = models.CharField("Tên danh mục", max_length=120)
    is_active = models.BooleanField("Đang hoạt động", default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Product(models.Model):
    sku = models.CharField("SKU", max_length=50, unique=True)
    name = models.CharField("Tên sản phẩm", max_length=180, db_index=True)
    category = models.ForeignKey(
        Category, verbose_name="Danh mục", on_delete=models.PROTECT, related_name="products"
    )
    sale_price = models.DecimalField(
        "Giá bán (₫)", max_digits=16, decimal_places=0, validators=[MinValueValidator(0)]
    )
    cost_price = models.DecimalField(
        "Giá vốn (₫)", max_digits=16, decimal_places=0, validators=[MinValueValidator(0)]
    )
    image = models.ImageField("Hình ảnh", upload_to=product_image_path, blank=True)
    is_active = models.BooleanField("Đang kinh doanh", default=True)
    low_stock_threshold = models.PositiveIntegerField("Ngưỡng tồn thấp", default=10)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "pk"]
        constraints = [
            models.CheckConstraint(condition=models.Q(sale_price__gte=0), name="product_sale_nonnegative"),
            models.CheckConstraint(condition=models.Q(cost_price__gte=0), name="product_cost_nonnegative"),
        ]

    @transaction.atomic
    def save(self, *args, **kwargs):
        result = super().save(*args, **kwargs)
        from inventory.models import StockBalance

        StockBalance.objects.get_or_create(product_id=self.pk)
        return result

    def __str__(self):
        return f"{self.sku} · {self.name}"
