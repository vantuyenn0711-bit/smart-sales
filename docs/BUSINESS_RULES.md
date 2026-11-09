# Quy tắc nghiệp vụ và phân quyền

## Phân quyền

| Thao tác | Admin | Manager | Staff | Viewer |
| --- | --- | --- | --- | --- |
| Xem dữ liệu vận hành, báo cáo | Có | Có | Có | Có |
| Xem giá vốn, lợi nhuận | Có | Có | Không | Không |
| Quản lý danh mục, sản phẩm, tồn kho | Có | Có | Không | Không |
| Quản lý khách hàng | Có | Có | Có | Không |
| Tạo đơn, xác nhận, xử lý, hoàn thành | Có | Có | Có | Không |
| Cấp chiết khấu trực tiếp trên đơn | Có | Có | Không | Không |
| Hủy đơn hợp lệ | Có | Có | Không | Không |
| Thu tiền | Có | Có | Có | Không |
| Quản lý tài khoản | Có | Không | Không | Không |

Tài khoản bị ngừng hoạt động không được gọi các service thay đổi dữ liệu. Superuser được quyền quản trị; `createsuperuser` mặc định tạo vai trò Admin.

## Đơn hàng và tồn kho

1. Tạo đơn nháp không tác động tồn. Backend đọc lại sản phẩm từ database, chụp giá bán và giá vốn, tính tổng bằng Decimal. Sản phẩm, danh mục và khách hàng phải đang hoạt động. Không chấp nhận dòng trùng sản phẩm.
2. `DRAFT → CONFIRMED → PROCESSING → COMPLETED`. Không chuyển ngược hoặc bỏ qua bước. Doanh thu chỉ ghi nhận tại `completed_at` theo múi giờ Việt Nam.
3. Xác nhận khóa bản ghi đơn và các số dư tồn theo thứ tự product_id tăng dần. Kiểm tra tồn, trừ tồn, ghi movement, đổi trạng thái, ghi lịch sử và audit trong cùng transaction. Một dòng lỗi làm rollback toàn bộ đơn.
4. Admin/Manager có thể hủy đơn DRAFT, CONFIRMED hoặc PROCESSING chưa thu tiền khi có lý do. Đơn đã xuất kho được hoàn tồn đúng một lần. Đơn hoàn thành và đơn đã thu bất kỳ khoản tiền nào bị chặn hủy trong MVP.
5. Điều chỉnh kho yêu cầu Admin/Manager, số lượng nguyên có dấu và lý do. Số dư không được âm; thay đổi luôn có movement và audit.

## Thanh toán

- Chỉ ghi nhận thủ công tiền mặt/chuyển khoản của đơn CONFIRMED, PROCESSING hoặc COMPLETED. Không kết nối ngân hàng.
- Service khóa bản ghi đơn trước khi cộng tổng đã thu và kiểm tra số dư. Nhiều request không thể thu vượt tổng đơn.
- Tiền phải hữu hạn, dương, trong giới hạn Decimal(16, 0). VND làm tròn `ROUND_HALF_UP` về đồng.
- Mã tham chiếu chuẩn hóa viết hoa và duy nhất toàn hệ thống khi được nhập. Mỗi request gửi UUID chống gửi trùng. Gửi lại cùng UUID, cùng người và cùng nội dung trả về giao dịch đã có; thay đổi nội dung với UUID cũ bị từ chối.
- Trạng thái unpaid/partial/paid và số còn nợ được tính từ Payment; không sửa thủ công. Tiền đã thu và doanh thu là hai chỉ số riêng.

## Lịch sử

Payment, InventoryMovement, SalesOrderItem, OrderStatusHistory và AuditLog chỉ thêm mới trong mã ứng dụng; không có giao diện sửa/xóa. Ràng buộc database bảo vệ tính duy nhất và các điều kiện số học cơ bản. Tác vụ bảo trì trực tiếp SQL vẫn phải được kiểm soát bằng quyền database và quy trình sao lưu.

Trả hàng/hoàn tiền, POS, barcode và API tích hợp kho thuộc P2 và chưa phải chức năng MVP. Báo cáo phải ghi rõ chưa bao gồm trả hàng/hoàn tiền.
