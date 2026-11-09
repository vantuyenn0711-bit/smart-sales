import os
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pytest
from django.db import close_old_connections, connections
from playwright.sync_api import Error, expect, sync_playwright

from accounts.models import User
from catalog.models import Category, Product
from customers.models import Customer
from inventory.services import adjust_stock
from orders.models import SalesOrder
from payments.models import Payment

pytestmark = [pytest.mark.browser, pytest.mark.django_db(transaction=True)]


@pytest.fixture
def browser(live_server, browser_data):
    with sync_playwright() as playwright:
        try:
            instance = playwright.chromium.launch(channel=os.environ.get("BROWSER_CHANNEL", "chrome"), headless=True)
        except Error as error:
            pytest.skip(f"Chrome browser unavailable: {error.message.splitlines()[0]}")
        yield instance
        instance.close()


def read_db(callback):
    """Run ORM assertions outside the event loop maintained by Playwright's sync API."""
    def worker():
        close_old_connections()
        try:
            return callback()
        finally:
            connections.close_all()
    with ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(worker).result(timeout=10)


@pytest.fixture
def browser_data():
    password = "Browser-Local-Test-582!"
    manager = User.objects.create_user(username="browser_manager", password=password, role="MANAGER", first_name="Quản lý")
    viewer = User.objects.create_user(username="browser_viewer", password=password, role="VIEWER", first_name="Người xem")
    customer = Customer.objects.create(name="Khách hàng trình duyệt", phone="0901234567")
    category = Category.objects.create(code="BROWSER", name="Phụ kiện máy tính")
    product = Product.objects.create(sku="BROWSE-50", name="Bàn phím trình duyệt", category=category, sale_price=50000, cost_price=20000)
    second = Product.objects.create(sku="BROWSE-EXTRA", name="Chuột trình duyệt", category=category, sale_price=25000, cost_price=10000)
    adjust_stock(actor=manager, product_id=product.pk, quantity=50, reason="Tồn kiểm thử trình duyệt")
    adjust_stock(actor=manager, product_id=second.pk, quantity=10, reason="Tồn kiểm thử trình duyệt")
    return SimpleNamespace(manager=manager, viewer=viewer, password=password, product=product, second=second, customer=customer)


def login(page, server, data, user):
    page.goto(server.url + "/login/")
    page.get_by_label("Tên đăng nhập").fill(user.username)
    page.get_by_label("Mật khẩu", exact=True).fill(data.password)
    page.get_by_role("button", name="Đăng nhập").click()
    expect(page).to_have_url(server.url + "/")
    expect(page.get_by_role("heading", name="Tổng quan kinh doanh")).to_be_visible()


def test_login_password_visibility_preserves_value_and_allows_retry(browser, live_server, browser_data):
    data = browser_data
    context = browser.new_context(viewport={"width": 375, "height": 900}, locale="vi-VN")
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        page.goto(live_server.url + "/login/")
        username = page.get_by_label("Tên đăng nhập")
        password = page.get_by_label("Mật khẩu", exact=True)
        toggle = page.get_by_role("button", name="Hiện mật khẩu", exact=True)
        expect(password).to_have_attribute("type", "password")
        expect(password).to_have_value("")
        expect(toggle).to_have_attribute("type", "button")
        expect(toggle).to_have_attribute("aria-controls", "id_password")
        expect(toggle).to_have_attribute("aria-pressed", "false")
        expect(page.locator("#password-help")).to_contain_text("phân biệt chữ hoa, chữ thường")
        username.fill(data.manager.username)
        wrong_password = data.password.swapcase()
        password.fill(wrong_password)
        password.press("Tab")
        expect(toggle).to_be_focused()
        toggle.press("Enter")
        hide = page.get_by_role("button", name="Ẩn mật khẩu", exact=True)
        expect(hide).to_have_attribute("aria-pressed", "true")
        expect(password).to_have_attribute("type", "text")
        expect(password).to_have_value(wrong_password)
        expect(page).to_have_url(live_server.url + "/login/")
        hide.press("Enter")
        expect(password).to_have_attribute("type", "password")
        expect(password).to_have_value(wrong_password)
        expect(toggle).to_have_attribute("aria-pressed", "false")
        page.get_by_role("button", name="Đăng nhập").click()
        expect(page.get_by_role("alert")).to_contain_text("Tên đăng nhập hoặc mật khẩu chưa đúng")
        expect(username).to_have_value(data.manager.username)
        expect(password).to_have_attribute("type", "password")
        expect(password).to_have_value("")
        expect(toggle).to_have_attribute("aria-pressed", "false")
        password.fill(data.password)
        toggle.click()
        expect(password).to_have_value(data.password)
        page.get_by_role("button", name="Ẩn mật khẩu", exact=True).click()
        expect(password).to_have_value(data.password)
        page.get_by_role("button", name="Đăng nhập").click()
        expect(page).to_have_url(live_server.url + "/")
        expect(page.get_by_role("heading", name="Tổng quan kinh doanh")).to_be_visible()
        assert errors == []
    finally:
        context.close()


def test_browser_order_rows_estimate_confirmation_and_partial_payment(browser, live_server, browser_data):
    data = browser_data
    context = browser.new_context(viewport={"width": 1440, "height": 1000}, locale="vi-VN")
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("dialog", lambda dialog: dialog.accept())
    try:
        login(page, live_server, data, data.manager)
        page.get_by_role("link", name="Tạo đơn hàng", exact=False).first.click()
        page.locator("#id_items-0-product").select_option(str(data.product.pk))
        page.locator("#id_items-0-quantity").fill("3")
        expect(page.locator("#order-estimate")).to_contain_text("150.000")
        page.get_by_role("button", name="Thêm sản phẩm").click()
        page.locator("#id_items-1-product").select_option(str(data.second.pk))
        page.locator("#id_items-1-quantity").fill("2")
        expect(page.locator("#order-estimate")).to_contain_text("200.000")
        page.locator(".order-row").nth(1).get_by_role("button", name="Xóa dòng sản phẩm").click()
        expect(page.locator(".order-row:visible")).to_have_count(1)
        expect(page.locator("#order-estimate")).to_contain_text("150.000")
        page.get_by_label("Khách hàng", exact=True).select_option(str(data.customer.pk))
        page.get_by_role("button", name="Lưu đơn nháp").click()
        expect(page.locator(".order-status-bar .status-DRAFT")).to_be_visible()
        order = read_db(lambda: SalesOrder.objects.get(created_by_id=data.manager.pk))
        assert read_db(lambda: order.items.count()) == 1
        assert order.total == 150000
        page.get_by_role("button", name="Xác nhận đơn & trừ tồn").click()
        expect(page.locator(".order-status-bar .status-CONFIRMED")).to_be_visible()
        assert read_db(lambda: Product.objects.get(pk=data.product.pk).stock.quantity_on_hand) == 47
        page.get_by_label("Số tiền thu (đ)").fill("50000")
        page.get_by_label("Mã tham chiếu", exact=True).fill("BROWSER-FIRST")
        page.get_by_role("button", name="Ghi nhận tiền thu").click()
        expect(page.locator(".order-status-bar .payment-partial")).to_be_visible()
        assert read_db(lambda: Payment.objects.get(order_id=order.pk).amount) == 50000
        page.get_by_label("Số tiền thu (đ)").fill("100001")
        page.get_by_label("Mã tham chiếu", exact=True).fill("BROWSER-TOO-MUCH")
        page.get_by_role("button", name="Ghi nhận tiền thu").click()
        expect(page.locator(".notice.error:visible")).to_contain_text("vượt quá")
        assert read_db(lambda: Payment.objects.filter(order_id=order.pk).count()) == 1
        page.get_by_label("Số tiền thu (đ)").fill("100000")
        page.get_by_label("Mã tham chiếu", exact=True).fill("BROWSER-FINAL")
        page.get_by_label("Phương thức").select_option("TRANSFER")
        page.get_by_role("button", name="Ghi nhận tiền thu").click()
        expect(page.locator(".order-status-bar .payment-paid")).to_be_visible()
        page.get_by_role("button", name="Bắt đầu xử lý").click()
        expect(page.locator(".order-status-bar .status-PROCESSING")).to_be_visible()
        page.get_by_role("button", name="Hoàn thành đơn", exact=True).click()
        expect(page.locator(".order-status-bar .status-COMPLETED")).to_be_visible()
        order = read_db(lambda: SalesOrder.objects.get(pk=order.pk))
        assert order.status == "COMPLETED" and read_db(lambda: order.balance_due) == 0
        assert "150.000" in page.locator(".order-totals").inner_text()
        assert errors == []
    finally:
        context.close()


@pytest.mark.parametrize("width", [375, 768, 1440])
def test_responsive_navigation_and_direct_viewer_denial(browser, live_server, browser_data, width):
    data = browser_data
    context = browser.new_context(viewport={"width": width, "height": 900}, locale="vi-VN")
    page = context.new_page()
    try:
        login(page, live_server, data, data.viewer)
        for path in ("/", "/products/", "/orders/", "/customers/", "/inventory/"):
            page.goto(live_server.url + path)
            assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
        if width < 800:
            toggle = page.get_by_role("button", name="Mở menu")
            toggle.click()
            expect(toggle).to_have_attribute("aria-expanded", "true")
            page.locator("#sidebar").get_by_role("link", name="Khách hàng", exact=True).click()
            expect(page.get_by_role("heading", name="Khách hàng", exact=True)).to_be_visible()
        response = page.goto(live_server.url + "/products/new/")
        assert response.status == 403
        expect(page.get_by_role("heading", name="Bạn chưa có quyền truy cập")).to_be_visible()
        assert not read_db(lambda: Product.objects.filter(sku="UNAUTHORIZED").exists())
    finally:
        context.close()


def test_htmx_product_filter_retains_page_and_network_error_input(browser, live_server, browser_data):
    data = browser_data
    context = browser.new_context(viewport={"width": 1440, "height": 900}, locale="vi-VN")
    page = context.new_page()
    try:
        login(page, live_server, data, data.viewer)
        page.goto(live_server.url + "/products/")
        page.evaluate("window.filterSentinel = 'preserved'")
        page.get_by_role("textbox", name="Tìm sản phẩm").fill("Bàn phím")
        with page.expect_response(lambda response: response.request.headers.get("hx-request") == "true"):
            page.get_by_role("button", name="Lọc", exact=True).click()
        expect(page.locator("#product-list-panel .data-table tbody tr")).to_have_count(1)
        expect(page.locator("#product-list-panel")).to_contain_text(data.product.name)
        assert page.evaluate("window.filterSentinel") == "preserved"
        assert "q=" in page.url
        page.route("**/products/?**", lambda route: route.abort())
        page.get_by_role("textbox", name="Tìm sản phẩm").fill("Vẫn giữ dữ liệu nhập")
        page.get_by_role("button", name="Lọc", exact=True).click()
        expect(page.locator("#connection-error")).to_be_visible()
        expect(page.get_by_role("textbox", name="Tìm sản phẩm")).to_have_value("Vẫn giữ dữ liệu nhập")
    finally:
        context.close()
