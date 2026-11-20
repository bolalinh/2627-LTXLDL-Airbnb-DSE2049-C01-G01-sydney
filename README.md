# Phân tích Dữ liệu Inside Airbnb Sydney (Australia)
> **Đồ án môn học:** Lập trình Xử lý Dữ liệu (UET.DSE2049) – Trường Đại học Công nghệ, ĐHQGHN  
> **Lớp học phần:** `UET.DSE2049 3` | **Nhóm:** `Nhóm 1`  
> **Mã phân công đề bài:** `DSE2049-C03-G01-sydney`  
> **Thành phố nghiên cứu:** Sydney (Australia) – Đơn vị tiền tệ: **AUD**  
> **Bên đặt hàng (Client Persona):** Hiệp hội Chủ nhà Airbnb Sydney (Host Community) & Nhà Đầu tư Bất động sản Du lịch  

---

## 1. Giới thiệu Tổng quan Đề tài

Dự án thực hiện phân tích chuyên sâu dữ liệu thị trường dịch vụ lưu trú **Inside Airbnb tại Sydney (Úc)** qua 4 mốc chụp thời gian (`2025-09-12`, `2025-12-12`, `2026-03-21`, `2026-06-16`).

Mục tiêu chính là xây dựng một **Pipeline xử lý dữ liệu tự động, khép kín và tái lập 100% (Reproducible)** từ dữ liệu thô đến sản phẩm báo cáo:
1. **Thu thập dữ liệu thô:** Tải và nạp dữ liệu từ Inside Airbnb, lọc chuẩn 1.000 listing_id và 8 tiểu vùng (`A01-A08`) được phân công.
2. **Kiểm soát chất lượng (QA Pipeline):** Chuẩn hóa dữ liệu qua 8 quy tắc kỹ thuật nghiêm ngặt (QA-01 đến QA-08) theo chuẩn Bài giảng 10.
3. **Bộ chỉ số hiệu suất (KPI):** Tính toán giá trung vị (Median Price), tỷ lệ lấp đầy ước tính (Estimated Occupancy), doanh thu tháng (Estimated Monthly Revenue) và lợi thế giá của Superhost.
4. **Khai phá đánh giá bằng LLM:** Ứng dụng mô hình ngôn ngữ lớn (Google Gemini API) với Pydantic Structured Output để phân loại cảm xúc (sentiment) và bóc tách khía cạnh phàn nàn/khen ngợi (aspects) của khách hàng; kết hợp cơ chế bộ nhớ đệm Cache-First JSONL.
5. **Đánh giá đối chứng mô hình (Evaluation):** So sánh F1, Precision, Recall giữa LLM và mô hình đối chứng (Baseline từ điển/luật) trên tập 100 mẫu gán nhãn vàng thủ công.
6. **Trực quan hoá dữ liệu (Visualization):** Xuất bản 4 biểu đồ trực quan hóa dữ liệu chuẩn khoa học nhằm giải quyết các quyết định kinh doanh cốt lõi của Chủ nhà.

---

## Danh sách Thành viên Thực hiện (Nhóm 1)

| STT | Họ và tên | Mã sinh viên | Vai trò & Trách nhiệm chính |
|:---:|:---|:---:|:---|
| 1 | **Đinh Ngọc Linh** | **25022910** | **Nhóm trưởng** – Quản trị mã nguồn, kiến trúc pipeline, tối ưu hóa I/O, trực quan hoá |
| 2 | **Nguyễn Tiến Long An** | **25022763** | Thu thập dữ liệu Inside Airbnb, kiểm soát chất lượng QA, xử lý trùng lặp & thiếu khoá |
| 3 | **Nguyễn Tiến Quốc** | **25023001** | Thiết kế bộ chỉ số KPI doanh thu, tỷ lệ lấp đầy, phân tích không gian 8 phân vùng |
| 4 | **Nguyễn Nam Khánh** | **25022902** | Tích hợp Gemini API có cấu trúc, Rate Limiting, xử lý bộ nhớ đệm Cache JSONL |
| 5 | **Nguyễn Hải Nam** | **25022954** | Xây dựng Baseline luật/từ điển, gán nhãn 100 review thủ công, phân tích ca lỗi |

---

## 2. Cấu trúc Thư mục Dự án

```text
Nh-m-1-LTXLDL---AI3/
├── configs/
│   └── sydney.yaml                 # File cấu hình trung tâm (tham số QA, KPI, LLM, đường dẫn)
├── data/
│   ├── raw/                        # Dữ liệu thô tải từ Inside Airbnb (listings, reviews, calendar)
│   ├── samples/                    # Tập 1.000 listing_id phân công, 8 vùng & 100 nhãn vàng thủ công
│   └── processed/                  # Dữ liệu đã làm sạch, các bảng KPI tổng hợp & llm_cache.jsonl
├── figures/                        # 4 biểu đồ trực quan hóa dữ liệu khoa học (.png)
├── notebooks/                      # Sổ tay Jupyter thử nghiệm và phân tích dữ liệu
├── reports/                        # Báo cáo QA, bảng F1 đối chứng, phân tích lỗi và REPORT.pdf
├── src/                            # Mã nguồn module hóa theo nguyên tắc trách nhiệm đơn lẻ
│   ├── download.py                 # Tự động tải dữ liệu và kiểm tra khóa chính
│   ├── qa.py                       # Pipeline 8 quy tắc kiểm soát chất lượng dữ liệu
│   ├── kpi.py                      # Tính toán bộ chỉ số KPI thị trường theo thời gian và không gian
│   ├── baseline.py                 # Mô hình đối chứng cảm xúc & khía cạnh dựa trên tập luật
│   ├── llm.py                      # Tích hợp Gemini API có cấu trúc (Pydantic) & cache JSONL
│   ├── evaluate.py                 # Đánh giá đối chứng F1, ma trận nhầm lẫn & phân tích ca lỗi
│   ├── viz.py                      # Sinh hệ thống biểu đồ trực quan hóa dữ liệu
│   └── logger.py                   # Quản lý nhật ký thực thi (log.txt) và đo lường thời gian
├── AI_USAGE.md                     # Báo cáo minh bạch sử dụng AI theo chính sách môn học
├── requirements.txt                # Danh sách thư viện và phiên bản chuẩn
├── run_pipeline.py                 # Điểm khởi chạy toàn bộ quy trình bằng 1 lệnh duy nhất
└── README.md                       # Hướng dẫn tổng quan và cài đặt dự án
```

---

## 3. Yêu cầu Hệ thống & Môi trường

* **Hệ điều hành:** Hỗ trợ mọi hệ điều hành (Windows 10/11, macOS, Linux/Ubuntu).
* **Python:** Phiên bản **Python 3.10, 3.11 hoặc 3.12** (Khuyến nghị: Python 3.11 hoặc 3.12).
* **Công cụ:** Git, kết nối Internet (để tải dữ liệu thô và gọi API).

---

## 4. Hướng dẫn Cài đặt Từng bước (Step-by-step Setup)

### Bước 1: Clone kho mã nguồn và di chuyển vào thư mục dự án
Mở Terminal (trên macOS/Linux) hoặc PowerShell (trên Windows):
```bash
git clone https://github.com/bolalinh/Nh-m-1-LTXLDL---AI3.git
cd Nh-m-1-LTXLDL---AI3
```
> [!IMPORTANT]
> **Rất quan trọng:** Luôn đảm bảo bạn đang đứng bên trong thư mục `Nh-m-1-LTXLDL---AI3` trước khi thực hiện các lệnh tiếp theo.

---

### Bước 2: Thiết lập Môi trường Ảo (Virtual Environment)

Chọn hướng dẫn tương ứng với hệ điều hành của máy bạn:

#### Cách A: Dành cho Windows (PowerShell)
```powershell
# 1. Tạo môi trường ảo .venv
python -m venv .venv

# 2. Cấp quyền chạy script cho phiên làm việc hiện tại (nếu gặp lỗi ExecutionPolicy)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process

# 3. Kích hoạt môi trường ảo
.\.venv\Scripts\Activate.ps1

# 4. Nâng cấp pip và cài đặt toàn bộ thư viện
python -m pip install --upgrade pip
pip install -r requirements.txt
```

#### Cách B: Dành cho macOS / Linux (Terminal / Bash / Zsh)
```bash
# 1. Tạo môi trường ảo .venv
python3 -m venv .venv

# 2. Kích hoạt môi trường ảo
source .venv/bin/activate

# 3. Nâng cấp pip và cài đặt toàn bộ thư viện
python3 -m pip install --upgrade pip
pip install -r requirements.txt
```

---

### Bước 3: Thiết lập Khóa API Gemini (Tùy chọn)

Để thực hiện trích xuất LLM mới ở Bước 4:
1. Lấy API Key miễn phí từ [Google AI Studio](https://aistudio.google.com/).
2. Tạo file `.env` tại thư mục gốc `Nh-m-1-LTXLDL---AI3/`:
   ```env
   GEMINI_API_KEY="dien_khoa_api_cua_ban_o_day"
   ```
> [!NOTE]
> **Nếu bạn không có API Key:** Bạn hoàn toàn vẫn có thể chạy toàn bộ dự án mà không gặp bất kỳ lỗi nào! Hệ thống đã tích hợp sẵn cơ chế **Cache-First** (nạp từ `llm_cache.jsonl` có sẵn) và cơ chế **Graceful Fallback** sang mô hình đối chứng `baseline`.

---

## 5. Hướng dẫn Chạy Dự án (Execution)

Lệnh này sẽ tự động tải dữ liệu từ Inside Airbnb, làm sạch QA, tính KPI, gọi LLM, tính F1 đối chứng và xuất toàn bộ biểu đồ:
```bash
python run_pipeline.py --config configs/sydney.yaml
```
*(Lưu ý: Lần đầu tiên chạy cần kết nối mạng để tải dữ liệu thô về thư mục `data/raw/`).*

---

### Bảng tra cứu các cờ tham số dòng lệnh (CLI Arguments):

| Tham số | Ý nghĩa & Mô tả | Mặc định |
|---|---|:---:|
| `--config <đường_dẫn>` | **(Bắt buộc)** Đường dẫn tới file cấu hình YAML (`configs/sydney.yaml`) | Không có |
| `--skip-download` | Bỏ qua bước tải từ web nếu `data/raw/` đã có file | `False` |
| `--skip-llm` | Bỏ qua gọi API LLM mới, tận dụng cache và mô hình đối chứng | `False` |
| `--sample-size <N>` | Ghi đè số lượng mẫu review đưa vào phân tích LLM | Lấy từ file YAML |
| `--log-file <tên_file>` | Tên file xuất nhật ký chi tiết | `log.txt` |

---

## 6. Kết quả Đầu ra Sau khi Chạy Hoàn tất

Sau khi lệnh chạy kết thúc thành công, hệ thống sinh ra đầy đủ các tiêu chuẩn đầu ra theo yêu cầu của đề tài:

1. **Dữ liệu sạch (Cleaned Data):**
   * `data/processed/listings_clean_*.csv`: Dữ liệu 4 mốc chụp đã được làm sạch, xử lý giá và loại bỏ ngoại lai.
   * `data/processed/llm_cache.jsonl`: Cơ sở dữ liệu JSONL lưu vết kết quả phân tích LLM theo cơ chế Cache-First.
2. **Báo cáo phân tích & Đánh giá (Reports):**
   * `reports/qa_report.csv`: Bảng tổng hợp kiểm soát chất lượng qua 8 quy tắc QA cho 4 mốc thời gian.
   * `reports/llm_vs_baseline_eval.csv`: Bảng so sánh chỉ số F1, Precision, Recall giữa LLM và Baseline.
   * `reports/error_analysis.csv`: Danh sách phân tích nguyên nhân các ca đoán sai của mô hình luật.
   * `reports/REPORT.pdf`: Báo cáo kỹ thuật phân tích thị trường hoàn chỉnh dành cho Chủ nhà Airbnb Sydney.
3. **Hệ thống 4 Biểu đồ Khoa học (Figures):**
   * `figures/01_market_trends_temporal.png`: Biến động giá trung vị và tỷ lệ lấp đầy theo 4 mùa du lịch.
   * `figures/02_top_revenue_spatial.png`: Xếp hạng doanh thu tiềm năng trên 8 khu vực trọng điểm của Sydney.
   * `figures/03_superhost_premium_segmentation.png`: Lợi thế cạnh tranh và tỷ lệ thặng dư giá của phòng Superhost.
   * `figures/04_llm_guest_complaints_aspects.png`: Phân bổ các khía cạnh dịch vụ khiến khách hàng phàn nàn nhiều nhất (Độ ồn, Sạch sẽ, Tiện nghi...).
4. **Nhật ký thực thi:** Toàn bộ lịch sử chạy, thời gian thực thi từng module và thông tin debug được ghi vào file `log.txt`.

## Giấy phép & Tuyên bố Miễn trừ (License & AI Transparency)
* Dữ liệu thuộc bản quyền công khai của cộng đồng **Inside Airbnb** ([insideairbnb.com](https://insideairbnb.com/)).
* Báo cáo tuân thủ nghiêm ngặt chính sách minh bạch sử dụng trí tuệ nhân tạo (AI) của môn học UET.DSE2049. Chi tiết phân định trách nhiệm xem tại file [AI_USAGE.md](AI_USAGE.md).