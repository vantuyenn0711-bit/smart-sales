# Internal integration contract

Apps at repository root. All models below use ordinary Django fields and migrations.

- accounts.User(AbstractUser): role choices ADMIN/MANAGER/STAFF/VIEWER; full name via get_full_name. Role enum User.Role. Admin superusers bypass role checks.
- core.AuditLog: actor FK User nullable, action, object_type, object_id (string), changes JSON, created_at.
- core.permissions.roles_required(*roles), authenticated and PermissionDenied; context processor provides can_manage (ADMIN/MANAGER), can_sell (ADMIN/MANAGER/STAFF), is_admin.
- catalog.Category: code unique, name, is_active. Product: sku unique, name, category PROTECT, sale_price, cost_price (Decimal 16,0), image ImageField optional, is_active, low_stock_threshold default 10, created_at/updated_at. product.stock is StockBalance reverse one-to-one.
- customers.Customer: code unique (auto if blank), name, phone, email, address, note, is_active, created_at/updated_at.
- inventory.StockBalance: product one-to-one related_name stock; quantity_on_hand >=0. InventoryMovement: product, order nullable, signed_qty nonzero, kind (OPENING/ADJUSTMENT/SALE/CANCELLATION), reason, actor, created_at. Immutable through application services.
- orders.SalesOrder: order_no unique generated, customer nullable, status enum Status DRAFT/CONFIRMED/PROCESSING/COMPLETED/CANCELLED, subtotal/discount/total Decimal, created_by, note, created_at/updated_at/completed_at nullable. related names items, payments, history. Properties amount_paid, balance_due, payment_status.
- orders.SalesOrderItem: order, product, quantity positive, unit_price_snapshot, cost_snapshot, line_total. Unique product within order.
- orders.OrderStatusHistory: order, from_status, to_status, actor, reason, created_at.
- payments.Payment: order related payments, method choices CASH/TRANSFER via Method enum, amount positive, reference unique nullable, idempotency_key UUID unique, paid_at, created_by.

Service API (all keyword parameters, ValidationError for business errors, PermissionDenied for unauthorized actors):

```
orders.services.create_order(*, actor, customer=None, items=[{"product": Product, "quantity": int}], discount=Decimal(0), note="") -> SalesOrder
orders.services.transition_order(*, actor, order_id, target_status, reason="") -> SalesOrder
payments.services.record_payment(*, actor, order_id, amount, method, reference="", idempotency_key) -> Payment
inventory.services.adjust_stock(*, actor, product_id, quantity: signed int, reason) -> StockBalance
```

Web agent owns core/forms.py, core/views.py, core/urls.py, core/templatetags/, accounts/views.py, templates/ and static/css/app.css, static/js/app.js. Root owns config/, core/context_processors.py, analytics/ (except models unnecessary), tool/dependency setup and browser/HTTP integration tests. Domain agent owns all models, domain service modules, core/permissions.py and tests/test_domain.py. Domain migrations generated after models settle by domain agent. Root owns seed_demo command unless delegated.

URL namespace `core`: dashboard `/`, product_list `/products/`, product_create, product_edit (pk), category_list `/categories/`, category_create, category_edit(pk), customer_list `/customers/`, customer_create, customer_edit(pk), customer_detail(pk), order_list `/orders/`, order_create, order_detail(pk), order_transition(pk) POST, payment_create(pk) POST, payment_list `/payments/`, inventory_list `/inventory/`, stock_adjust(pk) POST, audit_list `/audit/`, user_list `/team/`, user_create, user_edit(pk). Namespace `analytics`: reports `/reports/`, export `/reports/export/`. `login` `/login/`, `logout` POST `/logout/`.

Analytics dashboard context: start/end (date), filters (dict), categories, staff_members; metrics.revenue/receipts/order_count/average_order/profit, previous_metrics; chart_data JSON-compatible {labels:[],revenue:[],receipts:[]}; status_counts list {status,label,count}; top_products list {product__name,product__sku,quantity,revenue}; recent_orders queryset; low_stock queryset Product; recent_activity AuditLog. Filter GET from,to,category,staff; dashboard template `analytics/dashboard.html` and reports `analytics/reports.html` owned by root. Base block content/title/page_title/page_subtitle/actions/extra_js. Navigation uses request.resolver_match.url_name. Shared filter money. Root owns analytics templates only.
