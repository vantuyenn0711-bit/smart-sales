from io import BytesIO

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_GET
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

from analytics.forms import AnalyticsFilterForm
from analytics.services import report_context


def filtered_context(request):
    form = AnalyticsFilterForm(request.GET)
    if not form.is_valid():
        return {"filter_form": form}, 400
    context = report_context(form.cleaned_data)
    context["filter_form"] = form
    return context, 200


@login_required
@require_GET
def dashboard(request):
    context, status = filtered_context(request)
    context["page_section"] = "dashboard"
    return render(request, "analytics/dashboard.html", context, status=status)


@login_required
@require_GET
def reports(request):
    context, status = filtered_context(request)
    if status == 200:
        context["page_obj"] = Paginator(context["completed_orders"], 15).get_page(request.GET.get("page"))
    return render(request, "analytics/reports.html", context, status=status)


def excel_value(value):
    if value is None:
        return ""
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    if hasattr(value, "tzinfo") and value.tzinfo:
        return timezone.localtime(value).replace(tzinfo=None)
    return value


@login_required
@require_GET
def export(request):
    context, status = filtered_context(request)
    if status != 200:
        return render(request, "analytics/reports.html", context, status=status)
    book = Workbook()
    summary = book.active
    summary.title = "Tổng quan"
    summary.append(["SMART SALES · BÁO CÁO NỘI BỘ", "VND"])
    summary.append(["Từ ngày", context["start"].isoformat()])
    summary.append(["Đến ngày", context["end"].isoformat()])
    summary.append(["Doanh thu đơn hoàn thành", context["metrics"]["revenue"]])
    summary.append(["Tiền đã thu theo ngày thu", context["metrics"]["receipts"]])
    if request.user.is_superuser or request.user.role in {"ADMIN", "MANAGER"}:
        summary.append(["Lợi nhuận gộp ước tính", context["metrics"]["profit"]])
    summary.append(["Phạm vi", "Chưa bao gồm trả hàng / hoàn tiền (P2). Danh mục lọc toàn đơn có chứa sản phẩm."])
    orders = book.create_sheet("Đơn hoàn thành")
    orders.append(["Mã đơn", "Khách hàng", "Hoàn thành lúc", "Trạng thái", "Tạm tính", "Chiết khấu", "Doanh thu", "Người tạo"])
    for order in context["completed_orders"].iterator(chunk_size=500):
        orders.append([excel_value(value) for value in [order.order_no, order.customer.name if order.customer else "Khách lẻ", order.completed_at, order.get_status_display(), order.subtotal, order.discount, order.total, order.created_by.get_full_name() or order.created_by.username]])
    receipts = book.create_sheet("Tiền đã thu")
    receipts.append(["Mã đơn", "Ngày thu", "Phương thức", "Số tiền", "Tham chiếu", "Người nhập"])
    for payment in context["receipt_records"].iterator(chunk_size=500):
        receipts.append([excel_value(value) for value in [payment.order.order_no, payment.paid_at, payment.get_method_display(), payment.amount, payment.reference, payment.created_by.get_full_name() or payment.created_by.username]])
    for sheet in book:
        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = sheet.dimensions
        for cell in sheet[1]:
            cell.fill = PatternFill("solid", fgColor="172B4D")
            cell.font = Font(color="FFFFFF", bold=True)
        for column in sheet.columns:
            letter = column[0].column_letter
            sheet.column_dimensions[letter].width = min(60, max(18, max(len(str(cell.value or "")) for cell in column) + 3))
        for row in sheet.iter_rows(min_row=2):
            for cell in row:
                if isinstance(cell.value, (int, float)):
                    cell.number_format = '#,##0'
    stream = BytesIO()
    book.save(stream)
    response = HttpResponse(stream.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = f'attachment; filename="smart-sales-{context["start"]}-{context["end"]}.xlsx"'
    response["Cache-Control"] = "private, no-store"
    return response
