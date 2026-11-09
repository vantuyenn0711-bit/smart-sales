# Smart Sales — kết quả kiểm chứng

Ngày: **09/11/2026**, môi trường local, dữ liệu giả lập. Không push Git, deploy production, kết nối ngân hàng hoặc dùng dịch vụ có phí.

## Lượt tiếp tục: mở lại website và hoàn thiện đăng nhập

- Docker engine đang tắt khi bắt đầu. Đã mở lại Docker Desktop ở chế độ ẩn và khởi động đúng volumes Smart Sales hiện có, giữ nguyên dữ liệu/tài khoản/mật khẩu.
- Thêm `Start Smart Sales.cmd` và `scripts/start_sales.ps1`: người dùng nhấp đúp để mở Docker khi cần, build/khởi động, kiểm tra `/health/` cùng `/login/`, sau đó mở trình duyệt. Website vẫn chạy sau khi đóng launcher. Launcher đã chạy thành công thực tế; cú pháp PowerShell cũng đạt kiểm tra parser.
- Trang đăng nhập có nút Hiện/Ẩn mật khẩu, hỗ trợ bàn phím/ARIA và ghi chú phân biệt hoa/thường. Mặc định mật khẩu ẩn, nội dung giữ nguyên qua mỗi lần toggle; không điền/lưu credentials tự động.
- Đã đăng nhập thật bằng `demo_admin` với mật khẩu trong file local, tới dashboard HTTP 200, không lỗi JavaScript; kiểm tra nút trên viewport 375px đạt. Không đặt lại mật khẩu.
- `python -m pytest tests/test_browser.py tests/test_web.py -q`: **45 passed in 35.08s** (6 browser + 39 HTTP).
- `python -m pytest tests/test_domain.py tests/test_analytics.py tests/test_inventory_history.py -q`: **58 passed in 11.45s**. Tổng hai lệnh: **103 test đạt, không failed/skipped**, gồm 7 tình huống đồng thời.
- `ruff check .`, Django checks, Node syntax check: PASS. Ảnh trang đăng nhập đã cập nhật ở `docs/screenshots/login-1440.png` và `login-375.png`, mật khẩu để trống.
- Windows Application Control hiện chặn DLL của wheel `psycopg-binary` trong native environment. Kiểm thử dùng backend Python được Psycopg hỗ trợ cùng `libpq` chính thức tại `.tools/pgsql/bin`, qua biến môi trường của process. `run_local.ps1` đã hỗ trợ chế độ này và chạy thực tế tại cổng kiểm thử 18002, `/health/` HTTP 200. Không sửa chính sách Windows. Docker tiếp tục dùng backend binary bình thường.
- Website Docker tại **http://127.0.0.1:8002** được giữ chạy phục vụ người dùng. Web native tạm ở 18002 và PostgreSQL native dùng cho kiểm thử đã được dừng, dữ liệu giữ nguyên.

## Lệnh thực tế và kết quả

Các lệnh Python dùng `.venv\Scripts\python.exe` với `PYTHONUTF8=1`.

| Lệnh / kiểm tra | Kết quả |
| --- | --- |
| `python manage.py migrate --noinput` | PASS: toàn bộ migrations chạy trên PostgreSQL trống. |
| `python manage.py check` | PASS: 0 issues, 0 silenced. |
| `python manage.py makemigrations --check --dry-run` | PASS: No changes detected. |
| `python -m ruff check .` | PASS: All checks passed. |
| `DJANGO_DEBUG=false python manage.py check --deploy` | PASS: 0 issues; không phải triển khai production. |
| `python -m pytest -q` — trước lượt sửa đăng nhập | **102 passed in 62.12s**, không failed/skipped; PostgreSQL thật. Kết quả hiện tại 103 test ở hai lệnh phía trên. |
| `python manage.py collectstatic --noinput` | PASS: 10 tài nguyên CSS/JS/license, có xử lý nén. |
| `powershell -File scripts/build_css.ps1` | PASS: Tailwind CSS 4.3.3 được biên dịch local. |
| `uv lock --check --offline` | PASS: lockfile khớp pyproject, 25 packages. |
| `python scripts/create_demo.py` — 2 lần | PASS: tạo dữ liệu lần đầu; chạy lại không tạo trùng/đổi mật khẩu. |
| `python scripts/browser_smoke.py` | **38 checks PASS** tại 375/768/1440, không page errors hoặc tràn ngang trang. |
| `python scripts/verify_backup.py` | PASS: dump/restore vào database mới, đối chiếu khớp 9 bảng. |
| `powershell -File scripts/local_postgres.ps1 status` và `start` | PASS: xác minh đúng cluster local, không khởi tạo trùng. |
| `docker compose config --quiet` | PASS: cấu hình hợp lệ khi cấp secret local qua biến môi trường. |
| `docker compose build` | PASS: build image `smart-sales-web`, Python 3.13.18 / gunicorn 25.3.0, collectstatic thành công. |
| `docker compose up -d --no-build --wait` | PASS: tạo network/volumes mới, PostgreSQL 17.11 healthy, migrations tự chạy và web lắng nghe 127.0.0.1:8002. |
| Checks / seed / HTTP trong container | PASS: Django 0 issues, seed 2 lần không trùng, `/health/` trả200 và `status:ok`. |
| Chrome smoke lặp lại trên Docker | PASS: 38 checks tại 375/768/1440, download Excel và Viewer403, không page errors/tràn trang. |
| Portable PostgreSQL stop → start → status | PASS: dừng/khởi động lại đúng cluster, giữ nguyên dữ liệu. |

`.env`, password, cluster, dump và tool tải về được ignore. Không ghi nội dung secret vào báo cáo. Ảnh và biên bản Chrome tại `docs/screenshots/`.

## Phạm vi 102 test

- **42 domain**: 50→47, xác nhận lại, thiếu tồn, rollback nhiều dòng, snapshot giá/vốn, Decimal/âm/NaN, state machine, hủy/hoàn tồn một lần, chặn hủy đơn có tiền/hoàn thành, chống thu vượt/trùng, phân quyền service và ràng buộc DB.
- Trong domain có **7 concurrency cases** dùng kết nối PostgreSQL riêng: tranh tồn, xác nhận cùng đơn, thu vượt, cùng token, cùng tham chiếu giữa hai đơn, thanh toán đối đầu hủy, điều chỉnh kho đối đầu xác nhận.
- **15 analytics**: ngày hoàn thành so với ngày thu, không tính nháp/hủy, giá vốn snapshot, làm tròn VND, lọc danh mục không nhân đôi, Excel/khử formula injection, ẩn lợi nhuận với Viewer, validation bộ lọc, dữ liệu trống và login gate.
- **39 HTTP/web**: render từ DB, CRUD/lưu trữ, tồn đầu, validation ảnh/giới hạn kích thước, tìm/lọc/sort/phân trang, CSRF/safe redirect/XSS, direct endpoint 403, luồng đơn/thanh toán/hoàn tồn, hash password/chặn payload nâng quyền, audit giá trước/sau, hiển thị lỗi khi gửi form thanh toán cũ.
- **5 browser** trên Chrome headless và test DB riêng: thêm/xóa dòng, tổng dự kiến, tạo→xác nhận 50→47→thu một phần→chặn vượt→thu đủ→hoàn thành; responsive 375/768/1440, menu/Viewer403, HTMX lọc tại chỗ và lỗi mạng giữ nội dung nhập.
- **1 lịch sử kho**: 25 biến động vẫn tra cứu được bản ghi cũ qua phân trang/tìm; validate ngày, chỉ đọc và login gate.

## Môi trường và demo

Môi trường native: Python **3.13.9**, Django **5.2.19**, PostgreSQL **17.6**, Chrome **156.0.8078.80**. Docker Linux: Python **3.13.18**, Django **5.2.19**, PostgreSQL **17.11**, gunicorn **25.3.0**. Demo trong mỗi database: 4 tài khoản, 3 danh mục, 8 sản phẩm, 6 khách hàng, 42 đơn, 53 dòng đơn, 34 thanh toán, 8 số dư tồn, 59 biến động kho. Dashboard truy vấn chính các dữ liệu này.

Backup tạo database mới `smart_sales_restore_22dc99ff48`, đối chiếu 9 bảng khớp. Database nguồn và bản sao đều giữ nguyên. Dump và biên bản ở `.local/backups/` và `.local/backup-verification.json`.

## Lỗi đã sửa qua kiểm chứng

1. Biểu đồ nhân đôi doanh thu khi một đơn có nhiều sản phẩm cùng danh mục: dùng subquery order_id, regression đối chiếu metric và điểm biểu đồ.
2. PostgreSQL Windows không xử lý được đường dẫn Unicode khi gọi lại binaries: junction ASCII được xác minh trỏ đúng workspace, không di chuyển dữ liệu.
3. `pg_ctl status` bị hạn chế đọc process dù DB hoạt động: helper xác minh đăng nhập và `data_directory` đúng cluster trước khi start.
4. Console cp1252 không xuất được đường dẫn tiếng Việt: `PYTHONUTF8=1`.
5. CSS hiện lại dòng đơn đã xóa: tôn trọng thuộc tính `hidden`, browser xác nhận số dòng và tổng tiền.
6. Form thanh toán cũ gửi vào nháp/hủy/đã thu đủ: trả400 với lỗi hiển thị rõ, không ghi Payment.
7. Cổng 8000 đang có dự án kho: Smart Sales dùng **8002**; không dừng tiến trình dự án khác.

## Release gate V2

| Tiêu chí | Trạng thái / bằng chứng |
| --- | --- |
| PostgreSQL thật, migrations sạch | ĐẠT local: migrate + suite 102 từ test DB mới. |
| Bốn vai trò, URL trực tiếp | ĐẠT: service/HTTP/CSRF/browser. |
| Danh mục/sản phẩm/khách/ảnh/tìm lọc | ĐẠT: CRUD thật, validation, lưu trữ giữ lịch sử. |
| Đơn/tồn/snapshot/đồng thời | ĐẠT: rollback/locks, 7 concurrency cases. |
| Thu một phần/đủ, chống trùng/vượt | ĐẠT: service/HTTP/browser và số dư đối chiếu. |
| Dashboard/báo cáo/Excel thật | ĐẠT: analytics regression + chart/download browser. |
| Responsive/empty/loading/error | ĐẠT: 375/768/1440, HTMX/network error, empty HTTP. |
| README/SPEC/AGENTS/kế hoạch/ERD/migrations/demo/ảnh | ĐẠT: file thật và lệnh tương ứng đã chạy. |
| Docker / cài đặt từ đầu | ĐẠT local: build thật từ lockfile, chạy với volumes PostgreSQL/ảnh mới, migrate/seed/health/browser đều đạt. Không kiểm tra trên máy vật lý khác. |
| Bảo vệ dữ liệu/secrets | ĐẠT phạm vi local: không xóa dữ liệu cũ, không push/deploy/thu phí, secrets được ignore. |

## Mở local

Docker (đã build và seed trong workspace): `docker compose up -d`.

Hoặc native: `powershell -ExecutionPolicy Bypass -File scripts/run_local.ps1`.

Mở `http://127.0.0.1:8002`. Demo: `demo_admin`, `demo_manager`, `demo_sales`, `demo_viewer`. Mật khẩu local ở `.local/demo-password.txt`; không dán nội dung vào tài liệu/log.

P2 trả hàng/hoàn tiền/POS/barcode/API chưa triển khai, không tính là hoàn tất. Báo cáo ghi rõ chưa bao gồm trả hàng. Chưa triển khai production.

Toàn bộ tiêu chí chức năng MVP đã được kiểm chứng local theo bằng chứng trên. Dịch vụ kiểm thử được dừng sau QA; dữ liệu native, bản backup và Docker volumes được giữ để mở lại.

## Khởi động lại theo phản hồi người dùng — 09/11/2026

Người dùng gặp `ERR_CONNECTION_REFUSED` vì container đang dừng sau QA. Đã chạy `docker compose up -d --no-build --wait --wait-timeout 120` thành công, giữ nguyên dữ liệu. `/health/`, `/login/` và `/static/css/app.css` tại `http://127.0.0.1:8002` đều trả HTTP 200. Container được để chạy phục vụ người dùng.
