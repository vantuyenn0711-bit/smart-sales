from datetime import timedelta

from django import forms
from django.contrib.auth import get_user_model
from django.utils import timezone

from catalog.models import Category


class AnalyticsFilterForm(forms.Form):
    category = forms.ModelChoiceField(label="Danh mục", queryset=Category.objects.none(), required=False)
    staff = forms.ModelChoiceField(label="Nhân viên", queryset=get_user_model().objects.none(), required=False)

    def __init__(self, data=None, **kwargs):
        today = timezone.localdate()
        params = {"from": (today - timedelta(days=29)).isoformat(), "to": today.isoformat()}
        if data is not None:
            params.update(data.dict() if hasattr(data, "dict") else data)
        super().__init__(params, **kwargs)
        self.fields["from"] = forms.DateField(label="Từ ngày", widget=forms.DateInput(attrs={"type": "date"}))
        self.fields["to"] = forms.DateField(label="Đến ngày", widget=forms.DateInput(attrs={"type": "date"}))
        self.fields["category"].queryset = Category.objects.order_by("name")
        self.fields["staff"].queryset = get_user_model().objects.filter(is_active=True).order_by("first_name", "username")
        self.order_fields(["from", "to", "category", "staff"])

    def clean(self):
        cleaned = super().clean()
        start, end = cleaned.get("from"), cleaned.get("to")
        if start and end:
            if start > end:
                self.add_error("to", "Ngày kết thúc phải từ ngày bắt đầu trở đi.")
            elif (end - start).days > 365:
                self.add_error("to", "Vui lòng chọn tối đa 366 ngày cho mỗi báo cáo.")
        return cleaned
