from django import forms

from catalog.models import Product
from inventory.models import InventoryMovement


class MovementFilterForm(forms.Form):
    q = forms.CharField(label="Tìm kiếm", required=False, max_length=150, widget=forms.TextInput(attrs={"placeholder": "SKU, sản phẩm, đơn hàng, lý do…"}))
    product = forms.ModelChoiceField(label="Sản phẩm", required=False, queryset=Product.objects.none(), empty_label="Tất cả sản phẩm")
    kind = forms.ChoiceField(label="Loại biến động", required=False, choices=[("", "Tất cả biến động"), *InventoryMovement.Kind.choices])
    from_date = forms.DateField(label="Từ ngày", required=False, widget=forms.DateInput(attrs={"type": "date"}))
    to_date = forms.DateField(label="Đến ngày", required=False, widget=forms.DateInput(attrs={"type": "date"}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["product"].queryset = Product.objects.order_by("name")
        for field in self.fields.values():
            field.widget.attrs["class"] = "input"

    def clean(self):
        cleaned = super().clean()
        start, end = cleaned.get("from_date"), cleaned.get("to_date")
        if start and end and start > end:
            self.add_error("to_date", "Ngày kết thúc phải từ ngày bắt đầu trở đi.")
        return cleaned
