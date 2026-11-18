# 2627-LTXLDL-Airbnb-Nhom-1

## Phân tích Dữ liệu Inside Airbnb Sydney (Australia)
**Học phần:** Lập trình Xử lý Dữ liệu (UET.DSE2049) – Nhóm 1 (Lớp UET.DSE2049 3)  
**Mã phân công:** `DSE2049-C03-G01-sydney`  
**Bên đặt hàng:** Hiệp hội Chủ nhà Airbnb Sydney (Host Community) & Nhà Đầu tư Bất động sản Du lịch

Dự án phân tích chuyên sâu dữ liệu lưu trú Inside Airbnb tại Sydney qua 4 mốc chụp thời gian, nhằm cung cấp bức tranh toàn diện về xu hướng thị trường, định giá phòng tối ưu, lợi thế cạnh tranh của danh hiệu Superhost và khai phá phản hồi khách hàng bằng mô hình ngôn ngữ lớn (Gemini API).

---

## Cấu trúc Thư mục Dự án

```
airbnb-project/
├── configs/
│   └── sydney.yaml          # File cấu hình tham số toàn bộ hệ thống
├── data/
│   ├── raw/                 # Dữ liệu thô Inside Airbnb (listings, reviews qua 4 mốc)
│   ├── samples/             # 1.000 listing_id phân công & 100 nhãn vàng thủ công
│   └── processed/           # Dữ liệu sạch (listings_clean_*.csv, kpi_*.csv, llm_cache.jsonl)
├── figures/                 # 4 biểu đồ trực quan hóa dữ liệu chuẩn Bài 12 & 13 (.png)
├── reports/                 # Báo cáo kiểm soát chất lượng QA, đối chứng F1 & phân tích lỗi (.csv)
├── src/
│   ├── download.py          # Thu thập dữ liệu Inside Airbnb
│   ├── qa.py                # Pipeline kiểm soát chất lượng & 8 quy tắc QA
│   ├── kpi.py               # Tính toán bộ chỉ số KPI doanh thu & lấp đầy cho chủ nhà
│   ├── baseline.py          # Mô hình đối chứng cảm xúc & khía cạnh bằng tập luật
│   ├── llm.py               # Tích hợp Gemini API có cấu trúc (Pydantic) & cache JSONL
│   ├── evaluate.py          # Đánh giá F1 đối chứng trên 100 nhãn vàng & phân tích ca lỗi
│   ├── viz.py               # Trực quan hóa dữ liệu chuẩn khoa học
│   └── logger.py            # Hệ thống quản lý logging & đo lường hiệu năng thực thi
├── AI_USAGE.md              # Báo cáo minh bạch sử dụng AI theo chuẩn môn học
├── requirements.txt         # Khai báo phiên bản thư viện môi trường
└── run_pipeline.py          # Script thực thi toàn bộ quy trình bằng 1 lệnh duy nhất
```

---

## Cài đặt & Thực thi

### 1. Khởi tạo Môi trường Ảo
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Thiết lập Khóa API Gemini
Tạo file `.env` tại thư mục gốc của dự án:
```bash
GEMINI_API_KEY="your_actual_gemini_api_key_here"
```

### 3. Thực thi Pipeline Bằng 1 Lệnh Duy Nhất
```bash
# Chế độ chạy đầy đủ:
python run_pipeline.py --config configs/sydney.yaml

# Chế độ kiểm thử nhanh (tận dụng cache dữ liệu cục bộ):
python run_pipeline.py --config configs/sydney.yaml --skip-download --skip-llm
```
Toàn bộ nhật ký thực thi chi tiết được tự động ghi nhận vào file `log.txt`.
