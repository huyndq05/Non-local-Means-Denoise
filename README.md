# Khử nhiễu ảnh bằng Non-Local Means

Web app thực nghiệm xử lý ảnh bằng Python và Streamlit, có NLM tự cài đặt, các bộ lọc đối chứng và dữ liệu kiểm chứng bằng Fiji/ImageJ.

## Cài đặt và chạy

Dùng Python 3.12. Tại thư mục dự án trên Windows:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run src/nlm_lab.py
```

Sau khi cài đặt, có thể dùng `./run_nlm.ps1`. Mở http://localhost:8501 và giữ terminal chạy; nhấn Ctrl+C để dừng.

Trên Linux/macOS, tạo môi trường bằng `python3 -m venv .venv`, cài thư viện bằng `.venv/bin/python -m pip install -r requirements.txt` và chạy `.venv/bin/python -m streamlit run src/nlm_lab.py`.

## Chức năng

- Sinh nhiễu Gaussian, muối tiêu và Poisson với seed tái lập.
- Chạy NLM tự cài, NLM scikit-image, mean, Gaussian, median và bilateral trên cùng đầu vào. Có thêm hai pipeline thử nghiệm Median + NLM và Anscombe + NLM.
- Nhận ảnh RGB, ảnh xám, PNG/TIFF không dấu 8/16-bit và JPEG 8-bit. Mặc định crop giữa 256 × 256 trước khi sinh nhiễu.
- So sánh ảnh trước–sau, kính lúp, phóng to và kéo đồng bộ hai khung ảnh.
- Tính MSE, PSNR, SSIM khi có ảnh sạch tham chiếu; đo trung vị thời gian chạy và xuất PNG/CSV/JSON trong ZIP.
- Khảo sát tham số và nhập kết quả Fiji để đối chiếu.

## Thử một lượt thực nghiệm

1. Chọn ảnh mẫu và chế độ giữ màu hoặc chuyển xám. Chỉ xác nhận ground truth nếu ảnh nguồn thực sự sạch.
2. Chọn Gaussian, sigma 20, seed 42; bấm **Tạo nhiễu từ ảnh gốc**.
3. Đặt sigma giả định 20, h/sigma 0,40, patch 5 và bán kính tìm kiếm 5. Tắt ước lượng wavelet nếu muốn dùng đúng sigma mô phỏng.
4. Chọn **NLM tự cài đặt** cùng các phương pháp cần đối chiếu, rồi bấm **Khử nhiễu và so sánh**.
5. Quan sát ảnh và số đo. Đổi tham số cần chạy lại. Tải gói kết quả để lưu đầu vào, đầu ra, tham số và các lần đo thời gian.

Sigma, h và sigma cường độ bilateral nhập theo thang tương đương 0–255; trên ảnh 16-bit, sigma 20 tương ứng 5140 mức cường độ gốc. Tham số không gian tính bằng pixel. PNG xuất giữ độ sâu bit; preview 16-bit chỉ quy đổi tuyến tính để hiển thị. Không có ground truth thì ứng dụng không suy ra PSNR/SSIM chất lượng từ chính ảnh nhiễu.

## Cấu trúc thư mục và mã nguồn

| Thành phần | Vai trò |
|---|---|
| `docs/` | Báo cáo bài tập lớn (`.docx`, `.pdf`) và slide thuyết trình (`.pptx`, `.pdf`) của Nhóm 10 |
| `src/nlm_lab.py` | Điểm chạy Streamlit, NLM tự cài, sinh nhiễu, bộ lọc và phép đo |
| `src/image_io.py` | Đọc/ghi ảnh màu, ảnh xám và độ sâu bit |
| `src/app_ui.py`, `src/ui_theme.py` | Giao diện Streamlit |
| `src/sync_viewer.py`, `src/viewer_component/` | Bộ xem ảnh đồng bộ chạy trong trình duyệt |
| `src/experiment.py` | Đo thời gian, tính metric và đóng gói kết quả |
| `scripts/benchmark_nlm.py`, `scripts/sweep_nlm.py` | Benchmark và khảo sát tham số |
| `scripts/fiji/fiji_psnr.ijm`, `scripts/fiji/run_fiji_benchmark.groovy` | Macro MSE/PSNR và script đối chiếu trên Fiji/ImageJ |
| `scripts/experiments/` | Chuẩn bị, kiểm chứng đối chiếu Fiji và tạo hình phân tích |
| `tests/` | Kiểm chứng số học, ảnh màu/16-bit, giao diện và tương tác |
| `data/` | Ảnh sạch màu (`data/clean/`) và ảnh xám (`data/clean_gray/`) |
| `results/` | Kết quả benchmark, khảo sát tham số, đối chứng Fiji và ảnh demo web app |

NLM tự cài dùng khoảng cách patch đều, bù 2σ², hàm trọng số mũ, trọng số điểm tâm bằng 1 và biên phản chiếu. Lọc hộp giúp tính nhanh khoảng cách. NLM scikit-image là một phương pháp đối chứng riêng. Với RGB, khoảng cách patch lấy trung bình qua các kênh và dùng chung trọng số cho ba kênh.

## Dữ liệu và kết quả

- `data/clean/`: ảnh mẫu màu; `data/clean/resource.txt` ghi nguồn Kodak. Chưa có ánh xạ đầy đủ giữa tên cục bộ và mã ảnh gốc.
- `data/clean_gray/`: ảnh xám dùng cho benchmark.
- `results/baseline_v2/`: 117 đầu vào, gồm 13 crop × 9 điều kiện nhiễu, seed 42. Ảnh 02/06/09 dùng hiệu chỉnh; 10 ảnh còn lại dùng đánh giá. ZIP lưu PNG, tham số, phiên bản thư viện và hash.
- `results/sweep_v2/`: 42 cấu hình khảo sát trên ba ảnh hiệu chỉnh.
- `results/fiji_reference_20261116/`: PNG, số đo và ảnh chụp thực tế trong Fiji. Thư mục `gaussian_benchmark/` có 30 ca đánh giá Gaussian và ba ca minh họa riêng.
- `results/webapp_demo_20261116/`: ảnh chụp web app chạy thật và gói kết quả tải từ giao diện.

MSE và PSNR của hai đầu ra NLM được đo bằng Fiji và tính lại bằng NumPy trên cùng PNG, sai khác dưới 10⁻⁸. SSIM của cả hai được tính bằng Python. Hai biến thể NLM có cấu hình và cách tính trọng số khác nhau, nên không yêu cầu ảnh đầu ra trùng từng pixel. Macro `scripts/fiji/fiji_psnr.ijm` chỉ dùng cho ảnh xám 8-bit; kết quả benchmark hiện tại cũng thuộc phạm vi này.

Tài liệu nộp cuối cùng của nhóm (báo cáo `.docx`/`.pdf` và slide `.pptx`/`.pdf`) được đặt gọn trong `docs/`.

## Tái lập và kiểm tra

Chạy tại thư mục gốc dự án:

```powershell
.\.venv\Scripts\python.exe tests/check_nlm.py
.\.venv\Scripts\python.exe tests/check_workflow.py
.\.venv\Scripts\python.exe tests/check_color_depth.py
.\.venv\Scripts\python.exe tests/check_wavelet.py
.\.venv\Scripts\python.exe tests/check_redesign.py
node --test tests/viewer_math.test.cjs tests/viewer_interactions.test.cjs
```

Hai bài kiểm tra JavaScript cần Node.js. Không cần Node.js để chạy web app.

```powershell
.\.venv\Scripts\python.exe scripts/benchmark_nlm.py
.\.venv\Scripts\python.exe scripts/sweep_nlm.py
.\.venv\Scripts\python.exe scripts/experiments/verify_fiji_benchmark.py
```

Để chạy lại Fiji, chuẩn bị đầu vào bằng `scripts/experiments/prepare_fiji_benchmark.py`, mở script `scripts/fiji/run_fiji_benchmark.groovy` trong Script Editor của Fiji, chọn ngôn ngữ Groovy rồi chạy. Chọn thư mục `results/fiji_reference_20261116/gaussian_benchmark/` khi hộp thoại xuất hiện. Cần cài plugin Non Local Means Denoise; script ghi lại PNG, số đo và ảnh chụp cửa sổ thực tế.

Thời gian chạy phụ thuộc máy. Các phương pháp chưa được tối ưu tham số đồng đều; kết quả một ảnh minh họa không thay thế trung bình tập đánh giá. Anscombe dùng phép biến đổi ngược đại số và cần đúng peak, có thể thiên lệch ở số đếm thấp.
