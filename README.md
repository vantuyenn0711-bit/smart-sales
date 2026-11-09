# Smart Sales

Ứng dụng bán hàng nội bộ bằng Python 3.13, Django 5.2 LTS và PostgreSQL. Giao diện tiếng Việt sử dụng Django Templates, Tailwind CSS, HTMX và Chart.js; tất cả tài nguyên giao diện được lưu local. Mọi bảng, biểu đồ và báo cáo đọc dữ liệu từ database.

## Phạm vi

- Đăng nhập và 4 vai trò: Admin, Manager, Staff, Viewer. Admin quản lý tài khoản ngay trong giao diện nghiệp vụ.
- Danh mục, sản phẩm, giá bán/giá vốn, ảnh, cảnh báo tồn thấp; khách hàng và lịch sử mua; tìm kiếm, lọc, sắp xếp, phân trang.
- Đơn nhiều sản phẩm, giá snapshot, chiết khấu dành cho quản lý, xác nhận/xử lý/hoàn thành, hủy đơn chưa thu tiền và hoàn tồn.
- Nhập/xuất điều chỉnh tồn có lý do, lịch sử biến động; thu tiền mặt/chuyển khoản thủ công, thu từng phần, chống trùng và thu vượt.
- Dashboard và báo cáo theo ngày/danh mục/nhân viên, doanh thu tách khỏi tiền thu, xuất Excel.

Trả hàng/hoàn tiền, POS, barcode, coupon và API đồng bộ kho thuộc P2. Báo cáo MVP ghi rõ chưa bao gồm trả hàng. Đây là báo cáo/phiếu nội bộ, không phải hệ thống hóa đơn điện tử.

## Mở lại website trên máy này

Nhấp đúp **Start Smart Sales.cmd** trong thư mục dự án. Launcher mở Docker Desktop khi cần, chờ engine sẵn sàng, build/khởi động app bằng database Docker đã có và kiểm tra trang đăng nhập trước khi mở trình duyệt tại **http://127.0.0.1:8002**. Website tiếp tục chạy sau khi đóng cửa sổ launcher.

Hoặc chạy `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start_sales.ps1 -OpenBrowser`. Tài khoản demo là `demo_admin`, mật khẩu ở `.local/demo-password.txt`. Launcher không tạo lại dữ liệu hay đặt lại mật khẩu. Dùng `docker compose stop` để dừng app khi không dùng nữa.

## Chạy bằng Docker Compose trên máy mới

Cần Docker Desktop/Engine đang hoạt động. Python và PostgreSQL nằm trong container; không cần cài riêng.

1. Sao chép `.env.example` thành `.env`. Điền `DJANGO_SECRET_KEY` ngẫu nhiên ít nhất 50 ký tự và thêm `POSTGRES_PASSWORD` ngẫu nhiên chỉ gồm chữ/số. Đặt `DEMO_MODE=true` nếu muốn dữ liệu trình diễn. Không đưa `.env` vào Git.
2. Chạy `docker compose up --build -d`. App đợi PostgreSQL khỏe, chạy migrations rồi phục vụ tại **http://127.0.0.1:8002**. Compose chỉ mở cổng web trên loopback; cấu hình này dùng cho local.
3. Tạo tài khoản riêng: `docker compose exec web .venv/bin/python manage.py createsuperuser`. Superuser truy cập mọi chức năng, kể cả mục Nhân sự.
4. Hoặc nạp demo: `docker compose exec -e DEMO_PASSWORD web .venv/bin/python manage.py seed_demo`. Trước đó đặt biến môi trường `DEMO_PASSWORD` trong shell bằng một mật khẩu mạnh từ 12 ký tự. Mật khẩu không được in ra và chỉ dùng khi tạo lần đầu.
5. Kiểm tra: `docker compose ps`, mở `/health/`. Dừng app bằng `docker compose stop`; dữ liệu vẫn nằm trong named volumes.

Không chạy lệnh xóa volume khi cần giữ dữ liệu. Xem trạng thái kiểm chứng Docker thực tế trong [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md).

## Chạy trực tiếp trên Windows

Cần Python 3.13, [uv](https://docs.astral.sh/uv/), PostgreSQL và một database phát triển riêng. Nếu sử dụng môi trường portable đã chuẩn bị trong workspace này:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/local_postgres.ps1 start
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8002 --noreload
```

Script PostgreSQL chỉ quản lý cluster riêng trong `.local/postgres-data`, lắng nghe `127.0.0.1:55432`. Nó tạo mật khẩu ngẫu nhiên và `.env` khi chưa tồn tại; không reset cluster hay ghi đè `.env` cũ. Binaries portable nằm trong `.tools/pgsql` và không thuộc source code. Máy mới có thể dùng Docker hoặc PostgreSQL đã cài sẵn.

PowerShell có thể cần ` $env:PYTHONUTF8='1' ` để xuất đường dẫn tiếng Việt khi chạy lệnh. Trong workspace này, `python scripts/create_demo.py` tạo mật khẩu demo ngẫu nhiên và lưu riêng ở `.local/demo-password.txt`; mở file đó trên máy để đăng nhập, không đưa nội dung vào Git hay log.

Nếu Windows Application Control chặn DLL của `psycopg-binary`, môi trường portable có thể dùng adapter Python với `libpq` chính thức đã cài trong dự án. Đây là [chế độ cài đặt do Psycopg hỗ trợ](https://www.psycopg.org/psycopg3/docs/basic/install.html#pure-python-installation); không cần thay đổi chính sách Windows. `scripts/run_local.ps1` tự chọn chế độ này khi tìm thấy `libpq.dll`. Khi chạy kiểm thử trực tiếp, đặt các biến trong shell hiện tại:

```powershell
$env:PSYCOPG_IMPL='python'
$env:PATH=(Join-Path (Get-Location) '.tools\pgsql\bin')+';'+$env:PATH
```

Lệnh khởi động gọn cho workspace đã chuẩn bị: `powershell -ExecutionPolicy Bypass -File scripts/run_local.ps1`. Script chạy PostgreSQL portable khi cluster local có sẵn, migrations và web trên cổng **8002**, tránh đụng cổng 8000 của dự án kho. Thêm `-SeedDemo` nếu cần nạp demo lần đầu. Nhấn Ctrl+C để dừng web.

Với Python/PostgreSQL tự cài:

```powershell
uv sync --frozen
Copy-Item .env.example .env
# Sửa .env: SECRET_KEY, DATABASE_URL, DEBUG và DEMO_MODE.
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py createsuperuser
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8002
```

Ứng dụng không mặc định chuyển sang SQLite khi PostgreSQL lỗi. Không sử dụng database production để chạy kiểm thử. Linux/macOS dùng `.venv/bin/python` tương ứng.

## Dữ liệu demo và trình diễn

Đặt `DEMO_MODE=true` trong `.env`, đặt `DEMO_PASSWORD` trong shell rồi chạy:

```powershell
.\.venv\Scripts\python.exe manage.py seed_demo --password-env DEMO_PASSWORD
```

Tài khoản: `demo_admin`, `demo_manager`, `demo_sales`, `demo_viewer`. Mật khẩu lấy từ biến môi trường lúc seed, không ghi trong tài liệu. Chạy seed lại không tạo trùng, không đổi mật khẩu. Dữ liệu mẫu gồm 3 danh mục, 8 sản phẩm, 6 khách hàng, 42 đơn và các khoản thanh toán thật trong database, rải theo thời gian để kiểm tra bộ lọc. Dữ liệu này được đánh dấu demo; tên/liên hệ đều giả lập.

Luồng trình diễn bắt buộc:

1. Đăng nhập Admin/Manager → Sản phẩm → Thêm sản phẩm: SKU riêng, tồn 50, giá bán 100.000, giá vốn 60.000; thêm khách hàng.
2. Tạo đơn 3 sản phẩm, lưu nháp. Tồn vẫn 50. Mở chi tiết → Xác nhận; tồn còn 47. Gửi lại xác nhận bị chặn, tồn giữ 47.
3. Tạo đơn khác với 60 sản phẩm → Xác nhận bị từ chối; không phát sinh xuất kho.
4. Sửa giá sản phẩm; mở lại đơn trước để thấy giá snapshot và tổng 300.000 giữ nguyên.
5. Trên đơn đã xác nhận, ghi thu 100.000 với một tham chiếu, sau đó thu 200.000 tham chiếu khác. Xem số còn lại bằng 0; thu vượt hoặc trùng tham chiếu bị chặn.
6. Chuyển đơn sang Đang xử lý rồi Hoàn thành. Xem Dashboard/Báo cáo, chọn đúng ngày hoàn thành và xuất Excel. Tiền thu dựa theo ngày thu; doanh thu dựa theo ngày hoàn thành.
7. Tạo/xác nhận một đơn chưa thu tiền, hủy với lý do bằng Manager/Admin; tồn hoàn chính xác một lần. Đơn đã thu tiền hoặc đã hoàn thành không hủy qua MVP.
8. Đăng nhập Viewer, thử URL sửa sản phẩm/tạo đơn: bị chặn 403 tại server. Đăng nhập Staff: tạo đơn/khách/thu tiền được; đổi giá/điều chỉnh tồn/quản lý tài khoản bị chặn.

## Kiểm thử

Database test được pytest-django tạo riêng với tiền tố `test_`; tài khoản PostgreSQL phát triển cần quyền tạo database. Các test concurrency yêu cầu PostgreSQL thật và không được xem là đạt nếu bị skip.

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m pytest
```

Các test kiểm tra 50→47, thiếu tồn/rollback nhiều dòng, snapshot giá, state machine, hủy và hoàn tồn, thanh toán trùng/vượt/đồng thời, vai trò và CSRF, dữ liệu báo cáo và Excel. Kết quả lệnh đã chạy được ghi trong [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md), không suy ra từ việc có file test.

6 kiểm thử trình duyệt dùng Playwright với Chrome local ở chế độ headless; cài Chrome hoặc chọn `BROWSER_CHANNEL=msedge` nếu dùng Edge. Có kiểm tra nút hiện/ẩn mật khẩu, giá trị giữ nguyên và đăng nhập lại sau khi nhập sai. Không có browser tương thích thì các test này được báo skip, chưa thể coi là đạt. `python scripts/browser_smoke.py` kiểm tra riêng giao diện demo trên cổng 8002 và lưu ảnh chụp cùng JSON vào `docs/screenshots/`.

Để sửa giao diện, chạy lại `scripts/build_css.ps1` sau khi thay đổi class Tailwind. CSS đã biên dịch nằm trong source nên chạy app không cần Node hoặc CDN. Phiên bản/license thư viện nằm trong `static/vendor/`.

## Quy tắc số liệu

VND dùng Decimal, làm tròn nửa lên tới đồng. Giá bán và giá vốn được chụp khi tạo đơn; trình duyệt chỉ xem trước tổng tiền, server tính lại. Mọi thay đổi tiền/tồn đi qua service transaction. Kho trừ tại xác nhận, không trừ ở nháp. Thu tiền và hủy cùng khóa đơn; các sản phẩm được khóa theo thứ tự thống nhất để tránh deadlock.

Doanh thu = tổng `total` của đơn COMPLETED theo `completed_at`. Tiền thu = tổng Payment theo `paid_at`. Lợi nhuận gộp ước tính = doanh thu trừ tổng số lượng × giá vốn snapshot, chỉ hiện cho Admin/Manager. Bộ lọc danh mục chọn toàn bộ đơn có chứa sản phẩm thuộc danh mục; không phân bổ chiết khấu giữa danh mục. Top sản phẩm hiển thị giá trị dòng trước chiết khấu đơn.

Múi giờ `Asia/Ho_Chi_Minh`. Mọi chỉnh sửa trạng thái, tồn và thanh toán lưu nhật ký; không có nút xóa lịch sử. Ngừng kinh doanh sản phẩm/khách hàng thay cho xóa dữ liệu được tham chiếu.

## Backup và khôi phục

Với Docker, dùng `docker compose exec db pg_dump -U smart_sales -Fc smart_sales -f /tmp/smart_sales.dump`, sau đó `docker compose cp db:/tmp/smart_sales.dump ./backup.dump`. File dump chứa dữ liệu nhạy cảm: lưu riêng, không commit. Sao lưu cả volume ảnh nếu có.

Chỉ khôi phục vào database **mới, rỗng**: tạo database mới bằng `createdb`, sao chép dump vào container rồi dùng `pg_restore --no-owner --no-privileges -U smart_sales -d TEN_DATABASE_MOI /tmp/smart_sales.dump`. Kiểm tra bản sao trước khi trỏ cấu hình sang database đó. Không dùng `--clean` lên database đang sử dụng.

Với môi trường portable local đã chuẩn bị: `python scripts/verify_backup.py` tạo dump, khôi phục vào database mới tên ngẫu nhiên và đối chiếu 9 bảng. Kết quả lưu ở `.local/backup-verification.json`; database nguồn và bản khôi phục đều được giữ nguyên. Helper chỉ hoạt động với PostgreSQL loopback và DEBUG/DEMO được bật rõ ràng.

## Cấu trúc và tài liệu

`accounts/`, `catalog/`, `customers/`, `inventory/`, `orders/`, `payments/`, `analytics/`, `core/` tách vai trò và nghiệp vụ. `config/` cấu hình; `templates/` và `static/` giao diện; `tests/` kiểm thử.

- [SPEC.md](SPEC.md): nguyên văn đặc tả V2 đính kèm.
- [PLAN.md](PLAN.md), [DECISIONS.md](DECISIONS.md): kế hoạch và quyết định.
- [docs/ERD.md](docs/ERD.md), [docs/BUSINESS_RULES.md](docs/BUSINESS_RULES.md): dữ liệu và nghiệp vụ.
- [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md): bằng chứng, giới hạn kiểm chứng và tiêu chí nghiệm thu.

Chưa triển khai production. Khi chuẩn bị triển khai cần cấu hình HTTPS, `DEBUG=false`, secret riêng, allowed hosts/CSRF, phục vụ upload, backup và chạy `manage.py check --deploy`; việc đó cần một phạm vi triển khai được cho phép riêng.
