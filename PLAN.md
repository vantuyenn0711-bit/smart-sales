# Smart Sales MVP implementation plan

1. Foundation: Python 3.13, Django 5.2, PostgreSQL configuration, Docker Compose, roles, migrations. Pass: Django checks and fresh migration.
2. Catalog: categories, product prices/images, customer profiles, validation, search/filter/pagination. Pass: persisted CRUD and direct endpoint authorization tests.
3. Orders/inventory: server-side snapshots/totals, multi-line drafts, locked confirmation, cancellation, stock ledger/history. Pass: 50→47, insufficient stock, repeated actions, rollback and concurrency tests.
4. Payments: partial payments, unique references and idempotency tokens, balance checks under order lock. Pass: duplicate/overpayment/concurrent payment tests.
5. Analytics: completed-order revenue, payment receipts separately, date/category/staff filters, top products and Excel. Pass: totals reconciled against DB and matching export.
6. Presentation and handoff: Vietnamese responsive dashboard, accessible forms and error/empty/loading states, demo command, README, ERD and screenshots. Pass: HTTP/browser flows at 375/768/1440, ruff, pytest and migration drift checks.

Only mark release criteria verified when recorded in IMPLEMENTATION_STATUS.md. No production deployment is authorized.

## Tiến độ kiểm chứng — 09/11/2026

- Milestone 0–4: đạt kiểm tra local trên PostgreSQL thật.
- Milestone 5: đạt 102 tests, 38 bước browser smoke, lint/check/migrations, ảnh 375/768/1440, backup/restore, tài liệu; Docker build và chạy trên volumes mới đã được xác minh, lặp lại 38 bước Chrome thành công.
- Milestone 6/P2: chưa triển khai, ngoài MVP.
- Bằng chứng và giới hạn: IMPLEMENTATION_STATUS.md.

## Lượt tiếp tục sau phản hồi đăng nhập

- Đã khôi phục Docker và giữ website chạy ở cổng 8002 với dữ liệu cũ; đăng nhập thật bằng demo_admin đạt.
- Đã thêm launcher nhấp đúp, nút hiện/ẩn mật khẩu và hướng dẫn chạy native khi Windows chặn DLL của adapter binary.
- Regression hiện tại: 45 test browser/HTTP + 58 test domain/analytics/lịch sử kho = 103 test đạt, không skipped. Bằng chứng và lệnh ở IMPLEMENTATION_STATUS.md.
