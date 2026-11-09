# Smart Sales — mô hình dữ liệu MVP

```mermaid
erDiagram
    User ||--o{ SalesOrder : creates
    User ||--o{ Payment : records
    User ||--o{ InventoryMovement : performs
    User ||--o{ OrderStatusHistory : transitions
    User ||--o{ AuditLog : audits
    Category ||--o{ Product : groups
    Product ||--|| StockBalance : has
    Product ||--o{ SalesOrderItem : sold_as
    Product ||--o{ InventoryMovement : moves
    Customer o|--o{ SalesOrder : purchases
    SalesOrder ||--|{ SalesOrderItem : contains
    SalesOrder ||--o{ Payment : receives
    SalesOrder ||--o{ InventoryMovement : affects
    SalesOrder ||--|{ OrderStatusHistory : records
    User {
        bigint id PK
        string username UK
        string password_hash
        string role
        boolean is_active
    }
    Category {
        bigint id PK
        string code UK
        string name
        boolean is_active
    }
    Product {
        bigint id PK
        string sku UK
        bigint category_id FK
        string name
        decimal sale_price
        decimal cost_price
        string image
        boolean is_active
        int low_stock_threshold
    }
    Customer {
        bigint id PK
        string code UK
        string name
        string phone
        string email
        string address
        boolean is_active
    }
    StockBalance {
        bigint id PK
        bigint product_id FK,UK
        int quantity_on_hand
    }
    SalesOrder {
        bigint id PK
        string order_no UK
        bigint customer_id FK
        bigint created_by_id FK
        string status
        decimal subtotal
        decimal discount
        decimal total
        datetime created_at
        datetime completed_at
    }
    SalesOrderItem {
        bigint id PK
        bigint order_id FK
        bigint product_id FK
        int quantity
        decimal unit_price_snapshot
        decimal cost_snapshot
        decimal line_total
    }
    Payment {
        bigint id PK
        bigint order_id FK
        bigint created_by_id FK
        string method
        decimal amount
        string reference UK
        uuid idempotency_key UK
        datetime paid_at
    }
    InventoryMovement {
        bigint id PK
        bigint product_id FK
        bigint order_id FK
        bigint actor_id FK
        int signed_qty
        string kind
        string reason
        datetime created_at
    }
    OrderStatusHistory {
        bigint id PK
        bigint order_id FK
        bigint actor_id FK
        string from_status
        string to_status
        string reason
        datetime created_at
    }
    AuditLog {
        bigint id PK
        bigint actor_id FK
        string action
        string object_type
        string object_id
        json changes
        datetime created_at
    }
```

`SalesOrderItem(order_id, product_id)` là duy nhất. `InventoryMovement(order_id, product_id, kind)` là duy nhất khi có đơn hàng; một đơn chỉ xuất và hoàn tồn mỗi sản phẩm một lần. Mã tham chiếu thanh toán có thể để trống; mã chống gửi trùng luôn bắt buộc trong service.

Tất cả số tiền là `Decimal(16, 0)` tính bằng VND. Tổng đơn phải bằng tổng tiền hàng trừ chiết khấu; giá dòng hàng phải bằng số lượng nhân giá snapshot. Các tham chiếu chứng từ dùng `PROTECT` để tránh mất lịch sử. Lưu trữ sản phẩm, danh mục và khách hàng dùng trạng thái hoạt động.
