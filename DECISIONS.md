# Decisions

- 2026-11-09: Build Smart Sales, matching the attached project 02 blueprint and the sales-management workspace. The attachment is preserved verbatim in SPEC.md.
- Django monolith with separate accounts, catalog, customers, inventory, orders, payments, analytics and core apps.
- VND uses Decimal rounded to whole đồng (ROUND_HALF_UP), timezone Asia/Ho_Chi_Minh. Revenue is attributed to completed_at; receipts to paid_at.
- One stock location. Draft orders do not affect stock. Confirmation deducts; cancellation of unpaid draft/confirmed/processing orders is allowed for manager/admin. Paid cancellation and completed cancellation are blocked until the P2 refund workflow exists.
- Manager/admin manage catalog and inventory and may grant discounts. Staff creates orders/customers and receives payments. Viewer reads operational data/reports only. Admin alone manages users. All roles can read; monetary cost/margin are restricted to manager/admin.
- Product/customer deletion means archive, preserving historical references. No transaction record deletion UI.
- Local development only; do not create hosting resources, push, or deploy. Docker availability and actual PostgreSQL/browser verification will be reported honestly.
- Smart Sales uses local port 8002 (container port remains 8000), because a separate warehouse project already listens on 8000. The other project's processes are left running.
