"""Read-only browser QA against the local seeded app; screenshots contain demo data only."""
import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8002")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    password = (root / ".local" / "demo-password.txt").read_text(encoding="utf-8").strip()
    output = root / "docs" / "screenshots"
    output.mkdir(parents=True, exist_ok=True)
    result = {"browser": "Chrome", "viewports": [], "checks": [], "page_errors": []}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="chrome", headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 1000}, locale="vi-VN")
        page = context.new_page()
        page.on("pageerror", lambda error: result["page_errors"].append(str(error)))
        page.goto(args.url + "/login/")
        page.screenshot(path=str(output / "login-1440.png"), full_page=True)
        page.get_by_label("Tên đăng nhập", exact=True).fill("demo_admin")
        page.get_by_label("Mật khẩu", exact=True).fill(password)
        page.get_by_role("button", name="Đăng nhập").click()
        page.wait_for_url(args.url + "/")
        for width in (375, 768, 1440):
            page.set_viewport_size({"width": width, "height": 1000})
            for route, name in [("/", "dashboard"), ("/products/", "products"), ("/orders/", "orders"), ("/orders/new/", "order-create"), ("/customers/", "customers"), ("/inventory/", "inventory"), ("/inventory/movements/", "movement-history"), ("/payments/", "payments"), ("/reports/", "reports"), ("/categories/", "categories"), ("/team/", "team"), ("/audit/", "audit")]:
                response = page.goto(args.url + route)
                assert response.status == 200, (route, response.status)
                page.wait_for_load_state("networkidle")
                dimensions = page.evaluate("({scroll:document.documentElement.scrollWidth,width:document.documentElement.clientWidth})")
                assert dimensions["scroll"] <= dimensions["width"] + 1, (width, route, dimensions)
                result["checks"].append({"viewport": width, "route": route, "status": response.status, "no_overflow": True})
                if name in {"dashboard", "products", "reports", "order-create"}:
                    page.screenshot(path=str(output / f"{name}-{width}.png"), full_page=True)
                if route == "/":
                    assert page.evaluate("!!window.Chart?.getChart(document.getElementById('revenue-chart'))")
                    actual = page.evaluate("Chart.getChart(document.getElementById('revenue-chart')).data.datasets[0].data")
                    data = json.loads(page.locator("#revenue-data").text_content())
                    assert actual == data["revenue"]
            if width == 375:
                page.goto(args.url + "/")
                menu = page.get_by_role("button", name="Mở menu")
                menu.click()
                assert menu.get_attribute("aria-expanded") == "true"
                page.keyboard.press("Escape")
                assert menu.get_attribute("aria-expanded") == "false"
            result["viewports"].append(width)
        with page.expect_download() as download_info:
            page.goto(args.url + "/reports/")
            page.get_by_role("link", name="Xuất Excel").click()
        assert download_info.value.suggested_filename.endswith(".xlsx")
        result["checks"].append({"excel_browser_download": "pass"})
        page.get_by_role("button", name="Đăng xuất").click()
        page.wait_for_url(args.url + "/login/")
        page.get_by_label("Tên đăng nhập", exact=True).fill("demo_viewer")
        page.get_by_label("Mật khẩu", exact=True).fill(password)
        page.get_by_role("button", name="Đăng nhập").click()
        page.wait_for_url(args.url + "/")
        for route in ("/products/new/", "/orders/new/", "/team/", "/audit/"):
            response = page.goto(args.url + route)
            assert response.status == 403, (route, response.status)
        result["checks"].append({"viewer_direct_write_and_admin_routes": "403"})
        assert not result["page_errors"], result["page_errors"]
        context.close()
        browser.close()
    (output / "browser-smoke.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Browser smoke passed: {len(result['checks'])} checks, viewports 375/768/1440, no page errors. Screenshots: docs/screenshots/")


if __name__ == "__main__":
    main()
