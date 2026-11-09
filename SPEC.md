ROJECT BLUEPRINT   /   PYTHON • DJANGO • POSTGRESQL

HỒ SƠ DỰ ÁN SỐ 02

SMART SALES

ĐẶC TẢ V2 ĐÃ RÀ SOÁT • Website quản lý bán hàng bằng Python/Django • Dùng để giao ChatGPT triển khai từng giai đoạn • Kèm quy trình tự động cho Codex

MỤC TIÊU

Xây dựng phần mềm bán hàng nội bộ dành cho cửa hàng/doanh nghiệp nhỏ, quản lý sản phẩm, khách hàng, đơn hàng, thanh toán, trả hàng, hàng tồn và phân tích doanh thu. Dự án dùng để chứng minh tư duy lập trình, cơ sở dữ liệu, xử lý giao dịch và báo cáo.

Thông tin

Nội dung

Sản phẩm

Ứng dụng web quản lý bán hàng nội bộ; không phải sàn thương mại điện tử công khai.

Đối tượng

Admin, quản lý cửa hàng, nhân viên bán hàng, nhân viên xem báo cáo.

Phạm vi MVP

Sản phẩm, khách hàng, đơn hàng, tồn hàng, thanh toán ghi nhận thủ công, dashboard, báo cáo.

Mở rộng P2

Trả hàng/hoàn tiền chi tiết, POS, barcode, giảm giá, API liên kết kho.

Nguyên tắc

Không tích hợp ngân hàng hoặc cổng thanh toán thật trong MVP; chú trọng chính xác số liệu.

1. Nền tảng kỹ thuật và cấu trúc dự án

Hạng mục

Lựa chọn

Ngôn ngữ và backend

Python 3.13 + Django 5.2 LTS; dùng Django ORM và hệ thống migrations.

Cơ sở dữ liệu

PostgreSQL; dùng Decimal cho tiền, khóa ngoại và index cho trường tìm kiếm.

Frontend

Django Templates + Tailwind CSS + HTMX + JavaScript; Chart.js cho biểu đồ.

Báo cáo

openpyxl cho Excel; thư viện PDF phù hợp khi hoàn thành chức năng cốt lõi.

Kiểm thử

pytest + pytest-django; tích hợp test nghiệp vụ, quyền và các trường hợp lỗi.

Phát triển / triển khai

Git, Docker Compose, .env.example, README; chạy local trước, triển khai sau.

Chọn kiến trúc Django nguyên khối (monolith) để học và triển khai nhanh, giảm độ phức tạp so với tách frontend/backend ngay từ đầu. Không dùng Django Admin làm giao diện nghiệp vụ chính.

NGUYÊN TẮC THỰC HIỆN

Không sử dụng dữ liệu giả để giả mạo chức năng đã chạy. Dữ liệu mẫu phải được tạo trong database; dashboard, bảng và báo cáo đều truy xuất dữ liệu thật.

Cấu trúc Django đề xuất

smart_sales/
  config/                # settings, urls, wsgi/asgi
  accounts/              # users, roles
  catalog/               # product, category, prices
  customers/             # customer profiles
  orders/                # orders, items, status history
  payments/              # payment records, refunds
  inventory/             # stock balances/movements
  analytics/             # dashboard and exports
  core/                  # audit, helpers, permissions
  templates/ static/ tests/
  compose.yaml  Dockerfile  .env.example  README.md

Phân quyền và nhật ký thao tác

Vai trò

Quyền điển hình

Admin

Quản lý cấu hình, tài khoản, quyền và toàn bộ nghiệp vụ.

Manager

Xem báo cáo, duyệt hủy/trả/hoàn tiền theo chính sách.

Sales Staff

Tạo đơn, cập nhật khách hàng, ghi nhận giao dịch được cấp quyền.

Viewer

Chỉ xem dữ liệu được cấp quyền.

Kiểm tra quyền tại backend cho mọi request; không dùng việc ẩn nút giao diện để thay cho phân quyền.

Ghi nhật ký tối thiểu: người thao tác, thời điểm, loại hành động, đối tượng, dữ liệu thay đổi quan trọng.

2. Danh mục chức năng / màn hình

Module

Màn hình / chức năng

Ưu tiên

Dashboard

Doanh thu, đơn hàng, sản phẩm bán chạy, đơn hủy, đơn theo trạng thái, biểu đồ theo thời gian.

MVP

Sản phẩm

SKU, tên, danh mục, giá bán, giá vốn, tồn, hình ảnh, trạng thái, tìm/lọc.

MVP

Khách hàng

Mã KH, tên, số điện thoại, liên hệ, địa chỉ, lịch sử mua.

MVP

Đơn hàng

Tạo đơn, thêm nhiều dòng sản phẩm, tính tổng, xác nhận, quản lý trạng thái, chi tiết.

MVP

Thanh toán

Tiền mặt/chuyển khoản ghi nhận thủ công, thanh toán từng phần, số dư còn lại.

MVP

Tồn sản phẩm

Giữ/trừ/trả tồn theo quy trình nhất quán; lịch sử biến động.

MVP

Báo cáo

Doanh thu, đơn hàng, sản phẩm bán chạy, doanh thu ròng, xuất Excel.

MVP

Trả hàng/hoàn tiền

Yêu cầu trả hàng có lý do, điều chỉnh tồn theo chất lượng hàng trả, trả tiền.

P2

POS

Màn hình bán hàng nhanh, tìm hàng, barcode, in phiếu nội bộ.

P2

Giảm giá / tích hợp

Mã giảm giá, API lấy tồn kho, đồng bộ đơn xuất kho an toàn.

P2

Quy chuẩn UI/UX

Thanh menu trái và header; giao diện tiếng Việt, bố cục rõ ràng, màu xanh navy – trắng – xám, hỗ trợ mobile.

Bảng dữ liệu có tìm kiếm, lọc, phân trang, sắp xếp; trạng thái hiển thị bằng nhãn dễ phân biệt.

Form có hướng dẫn, thông báo lỗi theo từng trường, xác nhận khi thao tác ảnh hưởng dữ liệu.

Dashboard có số liệu thực và biểu đồ lọc theo thời gian, không dùng biểu đồ trang trí cố định.

Hiệu ứng vừa phải; ưu tiên tốc độ tải, dễ sử dụng và khả năng truy cập bằng bàn phím.

3. Thiết kế database (bản đầu tiên)

Bảng / Model

Trường trọng tâm và ghi chú

User / Role

Tài khoản, vai trò, trạng thái, timestamps.

Category

code, name, is_active.

Product

sku unique, name, category, sale_price, cost_price, is_active, image.

Customer

code unique, name, phone, email?, address?, note?, timestamps.

StockBalance

product_id unique [MVP 1 kho], quantity_on_hand, quantity_reserved [nếu sử dụng].

InventoryMovement

product_id, order/return reference, signed_qty, created_at; nhật ký tồn bất biến.

SalesOrder

order_no unique, customer_id, status, subtotal, discount, total, created_by, timestamps.

SalesOrderItem

order_id, product_id, quantity, unit_price_snapshot, cost_snapshot, line_total.

Payment

order_id, method, amount, reference unique khi cần, status, paid_at, created_by.

OrderStatusHistory

order_id, from_status, to_status, actor, reason, created_at.

SalesReturn / ReturnItem [P2]

order, item, quantity, reason, condition, refund_amount, approval status.

AuditLog

actor, action, object, changes, created_at.

Ràng buộc: đơn giá, giảm giá, số tiền thanh toán dùng Decimal; giá bán và giá vốn phải được chụp (snapshot) tại thời điểm lập đơn. Mã đơn, SKU không trùng. Ngăn số lượng <= 0 và đơn giá âm.

4. Quy trình nghiệp vụ cốt lõi

4.1 Tạo và xác nhận đơn

Nhân viên chọn khách hàng (hoặc khách lẻ), thêm mặt hàng và số lượng; nhập giảm giá nếu được cấp quyền.

Backend tra cứu giá hiện hành và ghi giá snapshot vào dòng đơn; tự tính tổng tiền, không tin tổng tiền do trình duyệt gửi lên.

Lưu nháp; khi xác nhận phải kiểm tra trạng thái và số lượng hàng khả dụng dưới transaction/lock.

Chọn một quy tắc trừ tồn rõ ràng: bản MVP trừ tồn đúng một lần tại bước XÁC NHẬN; đơn hủy sau xác nhận phải sinh giao dịch hoàn tồn khi phù hợp.

Tạo lịch sử trạng thái và movement. Không được xác nhận lại để trừ tồn hai lần.

4.2 Vòng đời đơn hàng (state machine)

DRAFT → CONFIRMED → PROCESSING → COMPLETED
   ↘ CANCELLED      ↘ CANCELLED (nếu chính sách cho phép)
Lưu lịch sử mọi lần chuyển trạng thái.
Không cho chuyển ngược hoặc hủy đơn hoàn thành tùy tiện;
trả hàng phải thực hiện qua nghiệp vụ riêng.

4.3 Thanh toán và công nợ đơn

MVP ghi nhận tiền mặt hoặc chuyển khoản đã kiểm tra thủ công; chưa kết nối ngân hàng hoặc xác nhận tự động.

Cho phép ghi nhiều lần thanh toán nhưng tổng tiền thu hợp lệ không vượt số còn phải thanh toán.

Mỗi thanh toán có người nhập, thời gian, phương thức và mã tham chiếu nếu có; ngăn gửi trùng.

Trạng thái thanh toán (unpaid/partial/paid/refunded) là kết quả tính từ các giao dịch, không cập nhật thủ công trái quy tắc.

4.4 Trả hàng và hoàn tiền (giai đoạn P2)

Chỉ trả sản phẩm thuộc đơn hợp lệ; không vượt số lượng đã bán trừ số lượng đã trả trước đó.

Kiểm tra hàng trả: còn bán được thì có thể nhập lại tồn; hàng lỗi thì đưa vào khu vực/hàng hỏng theo quy tắc riêng.

Tiền hoàn chỉ sinh khi yêu cầu trả được duyệt; không hoàn vượt giá trị được phép.

4.5 Công thức báo cáo

Chỉ số

Nguyên tắc tính

Tổng tiền dòng hàng

quantity × unit_price_snapshot, làm tròn theo chính sách tiền tệ.

Tổng đơn

Tổng dòng hàng – chiết khấu hợp lệ (+ thuế/phí nếu được triển khai và quy định rõ).

Doanh thu bán

Chỉ tính đơn theo trạng thái quy định, ví dụ COMPLETED; không tính đơn nháp/hủy.

Doanh thu ròng

Doanh thu bán – số hoàn trả/hoàn tiền tương ứng; tránh tính trùng.

Giá vốn hàng bán

Tổng quantity × cost_snapshot của hàng đã bán, điều chỉnh theo hàng trả.

Lợi nhuận gộp ước tính

Doanh thu ròng – giá vốn hàng bán điều chỉnh; chưa trừ chi phí vận hành.

5. Báo cáo và tình huống demo

Dashboard lọc theo thời gian, danh mục, nhân viên; biểu đồ doanh thu và top sản phẩm bán chạy.

Báo cáo đơn hàng theo trạng thái, khách hàng và doanh thu; xuất Excel với cột rõ ràng.

Demo: tạo sản phẩm tồn 50, lập đơn 3 sản phẩm, xác nhận còn 47, thanh toán một phần, hoàn tất đơn và xem báo cáo.

Demo lỗi: tạo đơn yêu cầu 60 khi tồn 47 phải báo không đủ hàng; xác nhận lặp lại không được trừ tiếp.

P2: hoàn 1 hàng còn bán được, tồn tăng đúng 1, doanh thu ròng và nhật ký hoàn tiền điều chỉnh nhất quán.

Bảo mật, vận hành và chất lượng

Mật khẩu được lưu theo cơ chế hash của Django; có CSRF, session an toàn, xác thực và ủy quyền theo quyền.

Tất cả secret lấy từ biến môi trường; không commit .env thật, khóa bí mật, dữ liệu khách hàng lên GitHub.

Validate dữ liệu cả phía trình duyệt và server; chống nhập số âm, giá trị vượt giới hạn và dữ liệu trùng.

Dùng transaction.atomic(), điều kiện trạng thái và row lock phù hợp trong các nghiệp vụ cập nhật tồn kho/tiền.

Có trang lỗi 403/404/500 và logging phù hợp; không lộ stack trace trên môi trường production.

Viết unit/integration tests cho các nghiệp vụ rủi ro, kiểm tra quyền, dữ liệu sai và tình huống đồng thời.

Tối ưu truy vấn bằng select_related/prefetch_related, phân trang và index, tránh N+1 query khi hiển thị bảng.

Docker Compose cho app + PostgreSQL; chuẩn bị backup/restore, migrations và dữ liệu demo qua management command.

6. Ma trận kiểm thử bắt buộc

Kịch bản

Kết quả mong đợi

Tồn 50, xác nhận đơn 3

Tồn 47; chỉ 1 movement trừ 3 và 1 lần chuyển trạng thái.

Đơn 60 sản phẩm khi tồn 47

Bị chặn; không trừ tồn, không xác nhận.

Xác nhận lại đơn CONFIRMED

Không trừ tồn lặp lại; lỗi trạng thái phù hợp.

Đổi giá sản phẩm sau tạo đơn

Tổng tiền đơn đã xác nhận vẫn giữ theo giá snapshot.

Thanh toán hai lần cùng tham chiếu

Chặn trùng; số tiền thu không tăng hai lần.

Thanh toán vượt số còn phải trả

Từ chối; lịch sử thanh toán không bị sai.

Hủy đơn hợp lệ

Tồn được hoàn chính xác một lần; trạng thái và lịch sử đồng bộ.

Viewer truy cập endpoint sửa giá

403; dữ liệu không thay đổi.

Hai người mua đồng thời cùng hàng

Khóa/transaction ngăn bán vượt tồn.

Trả hàng [P2]

Không trả vượt số lượng đã mua; refund và tồn cập nhật đúng.

7. Kế hoạch triển khai theo giai đoạn

Giai đoạn

Công việc / đầu ra

Hoàn thành khi

0 – Chuẩn bị

ERD, Django project, PostgreSQL, Docker, login/role, UI layout.

Setup và migrations chạy thành công.

1 – Danh mục

CRUD sản phẩm, danh mục, khách hàng, giá, ảnh, tìm kiếm.

Dữ liệu từ DB; test validate và quyền.

2 – Bán hàng

Tạo/xác nhận/hủy đơn, dòng đơn, trừ/hoàn tồn, lịch sử.

Test không oversell/không trừ trùng.

3 – Thanh toán

Ghi nhận tiền, thanh toán từng phần, chống trùng, trạng thái.

Test đối soát tổng tiền và quyền.

4 – Dashboard

Thống kê doanh thu, top hàng, xuất Excel, lọc thời gian.

Số liệu khớp giao dịch.

5 – Hoàn thiện

Responsive, test, demo data, README, deploy.

Demo đầu-cuối chạy theo README.

6 – Mở rộng

Trả hàng, refund, POS, barcode, API tích hợp kho.

Mỗi tính năng có test nghiệp vụ và UI.

Tiêu chí nghiệm thu và sản phẩm bàn giao

Có mã nguồn chạy được và cấu trúc thư mục Django rõ ràng; không chỉ có ảnh chụp màn hình.

Cài đặt từ đầu theo README thành công; migration chạy trên PostgreSQL trống, tạo dữ liệu demo bằng một lệnh.

Luồng nghiệp vụ cốt lõi hoạt động trọn vẹn từ giao diện đến database, có kiểm tra quyền và xử lý lỗi.

Có test tự động cho các quy tắc dữ liệu quan trọng; README ghi chính xác những test đã chạy.

Dashboard và báo cáo phản ánh cùng dữ liệu với chứng từ nguồn; không có số liệu giả cố định.

Có ảnh chụp các màn hình chính, sơ đồ ERD, hướng dẫn sử dụng, danh sách chức năng đã/đang/chưa hoàn thành.

Có Docker Compose, .env.example, .gitignore, tài khoản demo được tạo an toàn (không ghi mật khẩu thật lên repo).

Không dùng bất kỳ tích hợp thanh toán/ngân hàng hay dữ liệu nhạy cảm thật nếu chưa triển khai bảo mật phù hợp.

8. Câu lệnh khởi đầu cho Codex (bản ngắn)

HƯỚNG DẪN SỬ DỤNG

Sao chép phần dưới và gửi kèm file Word này sang cuộc trò chuyện lập trình. Dự án này chạy độc lập, không phụ thuộc website kho nào khác.

CODEX — HÃY XÂY DỰNG WEBSITE THEO TOÀN BỘ ĐẶC TẢ NÀY.
Mở SPEC.md và AGENTS.md trong thư mục dự án. Nếu chưa có repository, tạo Django project từ đầu. Viết PLAN.md với các milestone nhỏ có tiêu chí hoàn thành; sau đó trực tiếp tạo và sửa source code, migrations, Docker Compose, giao diện, dữ liệu demo và tài liệu.
Sau mỗi milestone hãy chạy lint, Django checks, pytest và smoke test; nếu có công cụ browser, kiểm tra desktop/mobile. Tự sửa lỗi rồi chạy test lại; tiếp tục milestone kế tiếp nếu đã đạt. Ghi bằng chứng kết quả vào IMPLEMENTATION_STATUS.md. Chỉ báo hoàn thành khi toàn bộ mục MUST-HAVE được kiểm chứng.
Không tự push, deploy production, xóa dữ liệu ngoài repository, phát sinh chi phí hoặc sử dụng secrets không được cấp phép. Nếu bị chặn vì quyền, môi trường hoặc tài khoản, báo rõ blocker.
Bản prompt vận hành đầy đủ ở START_CODEX_PROMPT.txt trong bộ file ZIP.

9. Rà soát V2: các tiêu chí chất lượng không thể bỏ qua

9.1. Chuẩn giao diện “cao cấp nhưng dễ sử dụng”

Trang điều khiển, danh sách, form, chi tiết và báo cáo dùng cùng hệ thống màu, typography, khoảng cách và trạng thái. Giao diện tiếng Việt rõ ràng, không lạm dụng hiệu ứng.

Thử tối thiểu các độ rộng 375 px, 768 px và 1440 px; không vỡ layout, không cuộn ngang vô lý; bảng dài có chiến lược hiển thị trên mobile.

Mọi màn hình phải có trạng thái loading, dữ liệu trống, lỗi kết nối và thao tác thành công; form chỉ rõ trường bị lỗi; kiểm tra focus bàn phím, tương phản và nhãn nhập liệu.

Không dùng bảng số liệu, biểu đồ, hoạt động “gần đây” giả trong bản thật; dữ liệu demo phải được đánh dấu demo.

9.2. Chuẩn mã nguồn, vận hành và an toàn

Tách nghiệp vụ vào service layer; views mỏng; ràng buộc database; migrations có thể chạy từ database trống. Không viết logic trừ tồn/tính tiền phân tán ở nhiều view.

Tạo trang lỗi 403/404/500, log có ngữ cảnh nhưng không lộ mật khẩu/token, cấu hình production tắt DEBUG; giới hạn upload loại file và dung lượng nếu có ảnh.

Thiết lập kiểm tra tự động: ruff, pytest/pytest-django, Django system checks, smoke test qua HTTP, kiểm thử luồng chính bằng trình duyệt nếu công cụ sẵn có.

README có cách cài trên máy mới, lệnh chạy, file .env.example, migrations, seed data, tạo tài khoản demo và cách chạy test; Docker Compose chỉ dùng dịch vụ cần thiết.

Đối với mọi nâng cấp vượt MVP: giữ phạm vi rõ ràng, không làm hỏng nghiệp vụ đã hoạt động; ưu tiên hiệu năng, tính nhất quán dữ liệu và khả năng trình diễn trước hiệu ứng.

9.3. Chứng cứ trước khi báo “hoàn tất”

Codex phải thực sự chạy các lệnh khi môi trường hỗ trợ, lưu lại lệnh và kết quả vào IMPLEMENTATION_STATUS.md; không tự nhận “pass” khi chưa kiểm thử.

Có màn hình chụp/smoke test của luồng quan trọng, danh sách lỗi còn tồn tại, đường dẫn và bước demo; chụp màn hình là minh chứng, không thay thế test backend.

Có bản tự đánh giá dựa trên checklist chức năng, đúng dữ liệu, phân quyền, UI/UX, test và tài liệu. Chỉ tuyên bố hoàn thành khi tất cả mục bắt buộc thực sự đạt.

10. Bổ sung riêng cho Smart Sales

MVP chọn chính sách rõ: đơn DRAFT không trừ tồn, đơn CONFIRMED trừ tồn đúng một lần; hủy đơn đã xác nhận có nghiệp vụ hoàn tồn một lần. Nếu đơn đã thanh toán, hủy phải qua quyền/luồng hoàn tiền phù hợp.

Bắt buộc dùng snapshot unit_price và cost_price trong SalesOrderItem; không phụ thuộc giá hiện tại khi xem lại báo cáo đơn cũ.

Tiền tệ mặc định VND; số tiền dùng Decimal và chính sách làm tròn rõ ràng; timezone Asia/Ho_Chi_Minh; thống kê theo mốc thời gian được định nghĩa.

Không đánh đồng tiền đã thu và doanh thu: doanh thu chỉ ghi nhận trên các đơn được xác định là hoàn thành; tiền thu theo Payment; thống kê có nhãn rõ.

Đơn hủy, trả hàng, hoàn tiền là sự kiện nghiệp vụ không được xóa lịch sử. Mã tham chiếu thanh toán/idempotency phải ngăn gửi lại gây ghi nhận tiền trùng.

Không hiển thị “doanh thu ròng sau trả hàng” như số liệu chính xác nếu module trả hàng chưa được triển khai; hoặc ghi rõ báo cáo chưa bao gồm trả hàng.

Mẫu hóa đơn nội bộ phải ghi rõ là phiếu/biên nhận nội bộ, không tự tuyên bố là hóa đơn điện tử hợp pháp.

10.1. Demo nghiệm thu bắt buộc

1. Tạo sản phẩm có tồn 50 và giá bán xác định, thêm khách hàng.

2. Tạo đơn 3 sản phẩm, xác nhận -> tồn còn 47 đúng một lần.

3. Thử tạo/xác nhận đơn 60 sản phẩm bị từ chối, tồn không đổi.

4. Đổi giá sản phẩm sau xác nhận đơn, giá đơn cũ vẫn giữ nguyên.

5. Ghi nhận thanh toán một phần, sau đó thanh toán đủ; chặn cùng mã tham chiếu và thanh toán vượt.

6. Hủy đơn hợp lệ -> hoàn tồn một lần theo chính sách, không làm sai số tiền.

7. Xem dashboard, báo cáo thời gian và xuất Excel theo dữ liệu giao dịch thực.

8. Nếu triển khai trả hàng P2: trả 1 sản phẩm, hoàn tiền/tồn/giá vốn được cập nhật nhất quán.

11. Bảng kiểm nghiệm thu bắt buộc (Release Gate)

Codex chỉ đánh dấu từng hàng ĐẠT sau khi có bằng chứng kiểm tra được lưu trong IMPLEMENTATION_STATUS.md. Tính năng P2 là mở rộng, không được giả mạo thành đã hoàn tất ở bản MVP.

TIÊU CHÍ

ĐIỀU KIỆN ĐẠT

Môi trường

Cài dependencies và Docker Compose trên máy mới; migrate database PostgreSQL trống thành công.

Đăng nhập / quyền

Admin, Manager, Staff, Viewer chỉ thao tác đúng quyền; URL gọi thẳng vẫn bị chặn.

Dữ liệu thật

Mọi dashboard, bảng và báo cáo đều truy vấn DB; không có số liệu hiển thị giả dạng kết quả thật.

Nghiệp vụ

Tất cả luồng MVP chạy end-to-end; trường hợp lỗi không làm dữ liệu sai/nhân đôi.

Đồng thời

Thử hai request cùng thay đổi tồn và giao dịch lặp; số lượng không âm và không ghi nhận trùng.

Giao diện

Responsive 375/768/1440; có trạng thái trống/loading/lỗi; biểu mẫu có thông báo rõ.

Tests

pytest và Django checks chạy thật không có lỗi chặn; lint đạt; test cho logic rủi ro.

Tài liệu

README, .env.example, migrations, seed demo, kế hoạch, báo cáo tiến độ và bước demo có thật.

An toàn

Không lộ secret, không dùng dữ liệu thật; không chạy production/deploy/push khi chưa được phép.

12. Runbook Codex: tự làm, tự kiểm thử, tự sửa

Dùng Codex trong thư mục repository có SPEC.md và AGENTS.md. Tài liệu Word giúp người đọc; SPEC.md là bản văn bản thuận tiện cho Codex tra cứu.

Tạo PLAN.md (milestone và tiêu chí pass), DECISIONS.md (giả định chính), IMPLEMENTATION_STATUS.md (lệnh thực sự đã chạy, kết quả, blocker). Sau mỗi milestone chạy test và chỉ tiếp tục khi đạt.

Bảo đảm có tài liệu setup máy sạch; không dừng ở mức “đã viết mã” nếu môi trường cho phép chạy dự án. Không được báo hoàn thành khi test còn đỏ hoặc chức năng vẫn chỉ là UI giả.

Tính năng tự tiếp tục trong Codex có giới hạn phiên, ngân sách, quyền truy cập và các điều kiện phải xin duyệt. Mọi yêu cầu xóa dữ liệu, dịch vụ trả phí, secrets, push hoặc production deployment cần người dùng phê duyệt.

Tài liệu tham khảo: OpenAI Codex CLI; OpenAI Cookbook “Iterating Development Workflows with Codex”; “Using Goals in Codex”.

