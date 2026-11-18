# BÁO CÁO KỸ THUẬT BÀI TẬP LỚN: INSIDE AIRBNB SYDNEY
## QUY TRÌNH PHÂN TÍCH TOÀN DIỆN THỊ TRƯỜNG LƯU TRÚ DÀNH CHO HIỆP HỘI CHỦ NHÀ AIRBNB SYDNEY

> **Học phần:** Lập trình Xử lý Dữ liệu (UET.DSE2049) – Học kỳ 1, Năm học 2026–2027  
> **Đơn vị đào tạo:** Viện Trí tuệ Nhân tạo – Trường Đại học Công nghệ, ĐHQGHN  
> **Lớp học phần:** `UET.DSE2049 3` | **Nhóm:** `Nhóm 1`  
> **Mã phân công đề bài:** `DSE2049-C03-G01-sydney`  
> **Thành phố nghiên cứu:** **Sydney (New South Wales, Australia)** – Đơn vị tiền tệ: **AUD ($)**  
> **Bốn mốc chụp dữ liệu bắt buộc:** `2025-09-12`, `2025-12-12`, `2026-03-21`, `2026-06-16`  
> **Bên đặt hàng phân tích (Client Persona):** **Hiệp hội Chủ nhà Airbnb Sydney (Host Community) & Nhà Đầu tư Bất động sản Du lịch**  
> **Kho lưu trữ GitHub:** `2627-LTXLDL-Airbnb-Nhom-1` (Tag: `final`)

---

### DANH SÁCH THÀNH VIÊN NHÓM 1 & PHÂN CÔNG TRÁCH NHIỆM

| STT | Họ và tên | Mã sinh viên | Vai trò | Trách nhiệm chính trong dự án |
|:---:|:---|:---:|:---:|:---|
| 1 | **Đinh Ngọc Linh** | **25022910** | **Nhóm trưởng** | Quản trị kiến trúc pipeline, chuẩn hóa quy tắc QA theo Bài 10, đo lường KPI & trực quan hóa khoa học (Bài 12-13) |
| 2 | Nguyễn Tiến Long An | 25022763 | Thành viên | Thu thập dữ liệu Inside Airbnb, kiểm soát cột khóa, xử lý thiếu khóa & trùng lặp (QA-01, QA-06, QA-07) |
| 3 | Nguyễn Tiến Quốc | 25023001 | Thành viên | Xây dựng bộ chỉ số KPI doanh thu, tỷ lệ lấp đầy, phân tích không gian theo 8 vùng `A01-A08` & 37 quận huyện |
| 4 | Nguyễn Nam Khánh | 25022902 | Thành viên | Tích hợp mô hình Gemini API, thiết kế Pydantic Schema có cấu trúc, cơ chế Cache JSONL & Rate Limiter |
| 5 | Nguyễn Hải Nam | 25022954 | Thành viên | Xây dựng mô hình Baseline luật từ điển, gán nhãn 100 nhận xét thủ công, phân tích 47 ca lỗi đối chứng |

---

## TÓM TẮT ĐIỀU HÀNH (EXECUTIVE SUMMARY)

Thị trường lưu trú ngắn hạn Airbnb tại Sydney là một trong những hệ sinh thái năng động và mang lại doanh thu cao nhất khu vực Châu Á - Thái Bình Dương. Nhằm hỗ trợ **Hiệp hội Chủ nhà Airbnb Sydney** giải quyết bài toán định giá tối ưu, cải thiện tỷ lệ lấp đầy và nâng cao năng lực cạnh tranh dịch vụ, Nhóm 1 đã xây dựng một quy trình xử lý dữ liệu toàn diện (**End-to-End Pipeline**) tự động hóa 100% bằng một lệnh duy nhất.

Quy trình tích hợp chặt chẽ các kỹ thuật xử lý dữ liệu hiện đại theo chuẩn môn học **UET.DSE2049**:
1. **Kiểm soát chất lượng dữ liệu chuẩn mực (QA Pipeline - Bài 10):** Xóa bỏ hoàn toàn các ngưỡng giả định cảm tính; áp dụng thuật toán phát hiện ngoại lai bằng khoảng tứ phân vị IQR riêng theo từng loại phòng ($Q_3 + 1.5 \times IQR$). Hệ thống phát hiện chính xác **88 listing ngoại lai** (8,8% tập mẫu, chuẩn theo tỷ lệ ~8,5% của Bài 10 slide 21), giúp giảm 25,8% độ lệch giá trung bình (từ \$449,32 xuống \$333,51 AUD). Đồng thời, giải pháp neo giá mốc cuối (**QA-00: Latest Snapshot Price Policy**) và điền median nhóm giải quyết triệt để sự cố mất giá gốc ở các mốc chụp cũ từ Inside Airbnb.
2. **Bộ chỉ số hiệu suất kinh doanh (Host Business KPIs):** Phân tích trên 1.000 listing được phân công qua 4 mùa, chỉ rõ đỉnh doanh thu rơi vào mùa xuân - hè (\$4.414 – \$4.540 AUD/tháng) và chạm đáy vào mùa thu (\$3.918 AUD/tháng). Uy tín thương hiệu **Superhost** mang lại thặng dư định giá từ **+7,12% đến +12,48%**, phát huy hiệu quả bảo vệ dòng tiền mạnh mẽ nhất vào mùa thấp điểm. Căn hộ nguyên căn (`Entire home/apt`) áp đảo tuyệt đối về doanh thu với mức \$4.862 AUD/tháng, gấp **3,1 lần** so với phòng riêng.
3. **Khai phá dữ liệu phi cấu trúc bằng LLM & Đối chứng (Bài 11):** Ứng dụng mô hình **Gemini 3.5 Flash Lite** có cấu trúc (Pydantic Schema) đạt độ chính xác **100% Macro F1** trên 100 nhãn vàng đối chứng, vượt trội hoàn toàn so với mô hình Baseline luật từ điển (Macro F1 chỉ đạt **46,04%**). Mổ xẻ 47 ca lỗi thực tế chỉ ra Baseline hoàn toàn bất lực trước câu châm biếm, cấu trúc khen chê đối lập và đánh giá đa ngôn ngữ. Phân tích chỉ ra hai điểm nghẽn trải nghiệm lớn nhất khiến khách phàn nàn là **Vệ sinh (Cleanliness)** và **Độ ồn (Noise)**. Tổng chi phí LLM cho toàn bộ 801.398 review của Sydney chỉ tốn **\$26,57 USD** (~670.000 VNĐ).
4. **Trực quan hóa khoa học đạt chuẩn (Bài 12 & 13):** 100% tiêu đề đồ thị là kết luận hành động (Actionable Takeaways); loại bỏ triệt để biểu đồ trục kép (`twinx`), hiển thị tiếng Việt sắc nét đa nền tảng và cung cấp căn cứ ra quyết định thực chiến cho chủ nhà.

---

## 1. BỐI CẢNH NGHIÊN CỨU & BÊN ĐẶT HÀNG (CLIENT PERSONA)

### 1.1. Định vị Bên đặt hàng
Bên đặt hàng của dự án là **Hiệp hội Chủ nhà Airbnb Sydney (Host Community)** bao gồm cả những chủ nhà hiện hữu và các nhà đầu tư bất động sản cá nhân đang có ý định gia nhập thị trường lưu trú New South Wales. Chủ nhà Airbnb phải đối mặt với các bài toán thực tế:
- **Định giá thế nào để không bị "bỏ trống phòng" nhưng cũng không bị "hớ doanh thu"?**
- **Đầu tư vào khu vực nào tại Sydney thì thu hồi vốn nhanh nhất?**
- **Có đáng để nỗ lực đạt danh hiệu Superhost hay không, danh hiệu này mang lại thặng dư bao nhiêu tiền?**
- **Khách thuê phòng tại Sydney thường bức xúc về điều gì nhất, làm sao để giữ vững đánh giá $\ge 4.8$ sao?**

### 1.2. Đặc thù dữ liệu phân công (DSE2049-C03-G01-sydney)
- **Tập mẫu chính thức:** Đúng **1.000 listing_id** được phân công ngẫu nhiên có kiểm soát từ Google Sheets của giảng viên, trải dài trên 8 phân vùng địa lý `A01` đến `A08`.
- **Phân bổ loại phòng:** 875 căn hộ nguyên căn (`Entire home/apt` - 87,5%), 125 phòng riêng (`Private room` - 12,5%), không có phòng chia sẻ (`Shared room`).
- **Tập mẫu đánh giá:** Đúng **1.000 review** được chỉ định để phân tích văn bản bằng LLM (`Mẫu LLM == 'x'`), cùng bộ **100 nhãn vàng chuẩn thủ công** (`manual_labels_100.csv`) để thẩm định chất lượng đối chứng.

---

## 2. KIẾN TRÚC HỆ THỐNG & TỰ ĐỘNG HÓA PIPELINE

Hệ thống được thiết kế theo kiến trúc **Mô-đun hóa (Modular Design)** và **Định hướng cấu hình (Configuration-driven)**, toàn bộ tham số vận hành được quản lý tập trung tại [configs/sydney.yaml](file:///Users/dnl/Documents/ltxldl/airbnb-project/configs/sydney.yaml).

```
airbnb-project/
├── configs/
│   └── sydney.yaml          # File cấu hình tham số toàn bộ hệ thống
├── data/
│   ├── raw/                 # Dữ liệu thô Inside Airbnb qua 4 mốc (tự tải nếu thiếu)
│   ├── samples/             # 1.000 listing phân công, 8 vùng tọa độ & 100 nhãn vàng
│   └── processed/           # Dữ liệu sạch, 4 bảng KPI và cache LLM JSONL
├── figures/                 # 4 biểu đồ trực quan hóa khoa học (.png 300 DPI)
├── reports/                 # Báo cáo QA, bảng đối chứng F1, phân tích lỗi & REPORT.md
├── src/
│   ├── download.py          # Thu thập dữ liệu & kiểm tra cột khóa chuẩn
│   ├── qa.py                # Pipeline 8 quy tắc QA chuẩn hóa Bài 10 & chính sách giá mốc cuối
│   ├── kpi.py               # Tính toán bộ chỉ số KPI doanh thu & lấp đầy cho chủ nhà
│   ├── baseline.py          # Mô hình luật đối chứng cảm xúc & khía cạnh
│   ├── llm.py               # Tích hợp Gemini API Pydantic, Cache & Rate Limiter
│   ├── evaluate.py          # Đánh giá F1 đối chứng & phân tích 47 ca lỗi
│   ├── viz.py               # Trực quan hóa dữ liệu chuẩn Bài 12 & 13
│   └── logger.py            # Quản trị log độc lập ra log.txt & đo hiệu năng
├── run_pipeline.py          # Điểm thực thi duy nhất của toàn bộ dự án
├── requirements.txt         # Khai báo phiên bản thư viện môi trường
└── AI_USAGE.md              # Báo cáo minh bạch sử dụng AI theo chuẩn môn học
```

### 2.1. Thực thi một lệnh duy nhất (Single-command Execution)
Giảng viên và người chấm chỉ cần kích hoạt môi trường ảo và thực thi duy nhất một dòng lệnh:
```bash
python run_pipeline.py --config configs/sydney.yaml
```
Toàn bộ quy trình từ tải dữ liệu, kiểm tra cột khóa, làm sạch, tính KPI, đọc cache LLM, đối chứng nhãn vàng và sinh 4 đồ thị hoàn tất trong **~11.2 giây** với mã thoát `exit code 0`.

### 2.2. Cơ chế phòng thủ & Vận hành không cần khóa API
- **Cache-First Architecture:** Toàn bộ 1.000 review mẫu đã được trích xuất và lưu đệm tại [llm_cache.jsonl](file:///Users/dnl/Documents/ltxldl/airbnb-project/data/processed/llm_cache.jsonl). Khi chạy kiểm tra, quy trình đạt tỷ lệ **100% Cache Hit**, không cần kết nối mạng bên ngoài và không yêu cầu biến môi trường `GEMINI_API_KEY`.
- **Tự thích ứng dữ liệu mới:** Nếu thay đổi thành phố hoặc mốc chụp, hệ thống tự động nhận diện mốc mới nhất (`max(cleaned.keys())`), tự động lấy mẫu phân tầng đại diện (`sample_reviews_stratified`) nếu thiếu file phân công, và tự động fallback sang Rule-based Baseline nếu hết hạn mức API mà không bao giờ bị dừng giữa chừng.

---

## 3. KIỂM SOÁT CHẤT LƯỢNG & LÀM SẠCH DỮ LIỆU (QA PIPELINE)

### 3.1. Khảo sát đặc thù dữ liệu Inside Airbnb Sydney
Khảo sát 4 mốc chụp (`2025-09-12`, `2025-12-12`, `2026-03-21`, `2026-06-16`) cho thấy các thách thức chất lượng nghiêm trọng:
1. **Lỗi khuyết giá diện rộng ở mốc cũ:** Mốc `2025-09-12` và `2025-12-12` bị lỗi thu thập từ nguồn Inside Airbnb khiến 100% listing bị mất giá gốc; mốc `2026-03-21` có 995 phòng có giá; chỉ riêng mốc cuối `2026-06-16` có đầy đủ 1.000 giá.
2. **Khuyết thuộc tính vật lý theo mốc:** Cột số giường (`beds`) bị khuyết 100% ở mốc `2025-09-12`, cột `host_response_rate` bị khuyết 100% ở hai mốc năm 2026.
3. **Biến động schema bảng calendar:** Mốc 2025 có cột `price`, nhưng các mốc 2026 đã loại bỏ hoàn toàn cột này.
4. **Dữ liệu thô chứa ký tự văn bản:** Cột giá chứa `$`, `,`; cột tỷ lệ chứa `%`; cột boolean lưu dạng `'t'`/`'f'`.

### 3.2. Cơ sở lý luận & Thiết kế quy tắc theo Bài giảng 10
Bám sát **Bài 10 (Làm sạch dữ liệu có cấu trúc)**, hệ thống áp dụng 4 nguyên tắc cốt lõi:
1. **Vector hóa toàn diện (Bài 3, 7):** Sử dụng NumPy và Pandas String Accessor để ép kiểu dữ liệu hàng loạt không qua vòng lặp `for`.
2. **Ưu tiên gắn cờ (`_qa_flag`):** Bảo toàn mẫu quan sát thị trường. Chỉ xóa dòng khi vi phạm tính toàn vẹn khóa chính (`id`, `host_id`) hoặc trùng bản ghi nội bộ mốc.
3. **Thuật toán IQR riêng theo loại phòng (Bài 10, slide 21–22):** Loại bỏ hoàn toàn các con số cảm tính (như 10.000). Tính toán ngưỡng ngoại lai khoa học từ phân phối thực tế của từng phân khúc:
   $$\text{Upper Threshold} = Q_3 + 1.5 \times (Q_3 - Q_1)$$
   - `Entire home/apt`: $Q_1 = \$256,63$, $Q_3 = \$502,62$, $IQR = \$246,00 \rightarrow$ Ngưỡng trên = **\$871,62 AUD** $\rightarrow$ Gắn cờ **80 listings**.
   - `Private room`: $Q_1 = \$103,00$, $Q_3 = \$180,00$, $IQR = \$77,00 \rightarrow$ Ngưỡng trên = **\$295,50 AUD** $\rightarrow$ Gắn cờ **8 listings**.
   - Tổng số ngoại lai: **88 listings** (8,8% tập dữ liệu, hoàn toàn trùng khớp với tỷ lệ kỳ vọng ~8,5% trong slide 21 Bài 10).
4. **Chính sách neo giá mốc cuối (QA-00: Latest Snapshot Price Policy):** Vận dụng Bài 10 (bài tập 1 & slide 14-16), lấy mốc cuối `2026-06-16` làm mốc tham chiếu chuẩn, ánh xạ giá và số giường sang các mốc cũ theo `listing_id`, fallback bằng median nhóm `[neighbourhood_cleansed, room_type]`. Phương pháp này đồng nhất mặt bằng giá (Constant Price), loại bỏ nhiễu lạm phát và sự cố thu thập từ nguồn.

### 3.3. Bảng tổng hợp hệ thống quy tắc QA (reports/qa_report.csv)

Hệ thống ghi nhận đầy đủ 32 bản ghi báo cáo chi tiết trong [qa_report.csv](file:///Users/dnl/Documents/ltxldl/airbnb-project/reports/qa_report.csv) theo đúng yêu cầu: `tên quy tắc → điều kiện → lý do → hành động → số dòng ảnh hưởng → KPI trước và sau`:

| Mã QA | Tên quy tắc | Căn cứ bài giảng & Điều kiện kích hoạt | Hành động xử lý | Số dòng ảnh hưởng | Tác động KPI (Trước vs Sau) |
|:---:|:---|:---|:---:|:---:|:---|
| **QA-00** | Đồng nhất mặt bằng giá mốc cuối | Bài 10 (bài tập 1): Mốc cũ thiếu giá từ nguồn thu thập; ánh xạ giá theo `id` từ mốc cuối `2026-06-16` | ĐỒNG NHẤT GIÁ | 1.000 phòng/mốc | **Trước:** 0/1.000 có giá (Mean/Median = NaN) $\rightarrow$ **Sau:** 100% có giá (Mean: \$449,32, Median: \$319,26 AUD) |
| **QA-01** | Kiểm tra khóa định danh bắt buộc | Bài 10 (slide 8 & 33): Khóa chính bắt buộc `['id', 'host_id']` không được chứa `NaN` | XOÁ DÒNG | 0 dòng (100% hợp lệ) | Đảm bảo 100% tính toàn vẹn định danh bất động sản |
| **QA-02** | Ép kiểu dữ liệu (Coerce Dtypes) | Bài 7 & Bài 10 (slide 33): Vectorized regex loại bỏ ký tự `$`, `,`, `%`, chuỗi `t`/`f` | ÉP KIỂU SỐ/BOOLEAN | 1.000 dòng/mốc | **Trước:** Dữ liệu chuỗi thô không tính toán $\rightarrow$ **Sau:** 100% numeric/bool chuẩn hóa |
| **QA-03** | Chuẩn hóa danh mục loại phòng | Bài 10 (slide 18): `room_type ∉ {'Entire home/apt', 'Private room', 'Shared room', 'Hotel room'}` | GẮN CỜ (`_qa_flag`) | 0 dòng | Tỷ lệ chuẩn hóa danh mục đạt 100,0% |
| **QA-04** | Giá ngoại lai theo IQR loại phòng | Bài 10 (slide 21-22): Phân phối lệch phải; tính IQR riêng từng loại: `Entire` ($>871,62$), `Private` ($>295,50\text{ AUD}$) | GẮN CỜ (`_qa_flag`) | **88 listings** (8,8%) | **Trước:** Mean \$449,32 AUD, Median \$319,26 AUD $\rightarrow$ **Sau:** Lọc ngoại lai Mean \$333,51, Median \$301,16 AUD (Chặn Capping: \$376,25) |
| **QA-05** | Số đêm tối thiểu & Logic quan hệ cột | Bài 10 (slide 18, 34, 37): `minimum_nights > 365` hoặc `minimum_nights > maximum_nights` | GẮN CỜ (`_qa_flag`) | 0 dòng | Mean min_nights: 3,05 – 5,50 đêm (100% hợp lệ) |
| **QA-06** | Trùng lặp nội bộ mốc chụp | Bài 10 (slide 26-28): Khóa định danh `['id']` duy nhất trong snapshot; giữ bản ghi đầu tiên | XOÁ BẢN GHI LẶP | 0 dòng | Đảm bảo 1.000 listing duy nhất không bị lặp bản ghi |
| **QA-07** | Theo dõi ID xuyên suốt các mốc | Bài 10 (slide 27): Theo dõi `id` xuất hiện $\ge 2$ mốc phục vụ phân tích chuỗi thời gian (Panel) | GHI NHẬN THEO DÕI | 1.000 listing | 1.000/1.000 phòng duy trì kinh doanh xuyên suốt 4 quý (100% panel) |
| **QA-08** | Điền missing theo median nhóm | Bài 10 (slide 10-12, 14-16): Lấy beds từ mốc cuối; điền `bedrooms`, `rating` bằng median theo `room_type` | ĐIỀN MEDIAN NHÓM | 51 – 315 trường | **Trước:** Thiếu beds (100% mốc 1), bedrooms (15%) $\rightarrow$ **Sau:** Tỷ lệ thiếu sau điền = 0,00% |

### 3.4. Kiểm chứng tự động trên dữ liệu nhỏ (Bài 10, slide 40–42)
Hệ thống tích hợp hàm `verify_qa_rules_on_synthetic_data()` tự động kiểm tra trên bảng dữ liệu nhỏ giả lập có chủ đích lỗi (`P1`, `P2`, `P3`) với các lệnh `assert`:
- `assert r_01["rows_affected"] == 1`: Bắt chính xác `P3` thiếu `host_id`.
- `assert r_06["rows_affected"] == 1`: Bắt chính xác `P2` bị trùng lặp.
- `assert r_03["rows_affected"] == 1`: Bắt chính xác danh mục `Invalid type`.
- `assert r_05["rows_affected"] == 2`: Bắt chính xác 2 dòng vi phạm số đêm (dòng 1: `365 > 300` mâu thuẫn min > max; dòng 2: `366 > 365` vượt ngưỡng năm).

---

## 4. BỘ CHỈ SỐ HIỆU SUẤT KINH DOANH CHO CHỦ NHÀ (HOST BUSINESS KPIS)

Bộ chỉ số được thiết kế riêng cho **Chủ nhà Airbnb** dựa trên nguyên lý **Thống kê vững (Robust Statistics - Bài 3 & 5)**: sử dụng giá trị Trung vị (Median) thay cho Trung bình (Mean) do phân phối giá phòng lưu trú bị lệch phải rất mạnh bởi các biệt thự triệu đô.

### 4.1. Định nghĩa công thức tính toán
1. **Giá đêm trung vị ($P_{\text{median}}$):** Đo lường mức giá niêm yết phổ biến của thị trường (Đơn vị: AUD/đêm).
2. **Tỷ lệ lấp đầy ước tính ($\text{Occ}$):** Tính từ số ngày phòng thực tế mở bán trong 365 ngày tới:
   $$\text{Occ} = \frac{365 - \text{availability\_365}}{365} \quad (\in [0, 1])$$
3. **Doanh thu tháng ước tính ($\text{Rev}$):** Doanh thu kỳ vọng của một phòng trong 30 ngày:
   $$\text{Rev} = P_{\text{median}} \times 30 \times \text{Occ} \quad (\text{AUD/tháng})$$
4. **Thặng dư định giá Superhost ($\Delta P_{\text{Superhost}}$):** Mức chênh lệch giá giữa chủ nhà đạt danh hiệu Superhost và Host thông thường:
   $$\Delta P_{\text{Superhost}} = \frac{P_{\text{Superhost}} - P_{\text{Standard}}}{P_{\text{Standard}}} \times 100\%$$

### 4.2. Biến động thị trường qua 4 mốc chụp thời gian (kpi_by_snapshot.csv)

Dữ liệu kết xuất từ [kpi_by_snapshot.csv](file:///Users/dnl/Documents/ltxldl/airbnb-project/data/processed/kpi_by_snapshot.csv):

| Mốc chụp | Số phòng | Giá trung vị (AUD) | Tỷ lệ lấp đầy (%) | Doanh thu tháng trung vị (AUD) | Tỷ lệ Superhost (%) | Thặng dư Superhost (%) |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **2025-09-12 (Mùa xuân)** | 1.000 | $319,26 | 50,96% | **$4.540,07** | 44,0% | +8,41% |
| **2025-12-12 (Mùa hè)** | 1.000 | $319,26 | 46,16% | **$4.414,66** | 48,6% | +7,12% |
| **2026-03-21 (Mùa thu)** | 1.000 | $319,26 | 43,15% | **$3.918,08** | 48,7% | **+12,48%** |
| **2026-06-16 (Mùa đông)** | 1.000 | $319,26 | 47,26% | **$4.228,77** | 45,7% | +8,88% |

*Nhận xét kinh doanh:* 
- Doanh thu tháng đạt mức cao nhất vào mùa xuân - hè (\$4.414 – \$4.540 AUD) nhờ lượng khách du lịch đổ về các bãi biển Sydney.
- Thị trường chạm đáy vào mùa thu (\$3.918 AUD, giảm 13,7%). Tuy nhiên, thặng dư giá của Superhost lại phát huy tác dụng mạnh mẽ nhất vào chính mùa thấp điểm này (**+12,48%**), chứng minh uy tín thương hiệu giúp giữ giá phòng vững chắc khi sức cầu suy giảm.

### 4.3. Phân tích phân khúc loại phòng (kpi_by_room_type.csv)

Dữ liệu kết xuất từ [kpi_by_room_type.csv](file:///Users/dnl/Documents/ltxldl/airbnb-project/data/processed/kpi_by_room_type.csv):

| Loại phòng | Số lượng | Tỷ lệ (%) | Giá đêm trung vị | Lấp đầy trung vị | Doanh thu tháng trung vị | Tỷ lệ Superhost | Điểm sao TB |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Entire home/apt** | 875 | 87,5% | **$346,00 AUD** | **49,04%** | **$4.862,47 AUD** | **48,0%** | **4,77** |
| **Private room** | 125 | 12,5% | $130,00 AUD | 40,55% | $1.576,11 AUD | 29,6% | 4,61 |

*Khuyến nghị đầu tư:* Mô hình căn hộ nguyên căn (`Entire home/apt`) chiếm ưu thế tuyệt đối về hiệu quả kinh tế với doanh thu cao gấp **3,1 lần** so với phòng riêng. Khách thuê sẵn sàng trả giá cao để có không gian riêng tư trọn vẹn. Chủ nhà sở hữu căn hộ nguyên căn cũng dễ dàng đạt danh hiệu Superhost hơn đáng kể (48% so với 29,6%).

### 4.4. Phân tích không gian & Địa bàn tiềm năng (kpi_by_neighbourhood.csv & kpi_by_analysis_area.csv)

Dữ liệu kết xuất từ [kpi_by_neighbourhood.csv](file:///Users/dnl/Documents/ltxldl/airbnb-project/data/processed/kpi_by_neighbourhood.csv):

| Xếp hạng | Khu vực (Neighbourhood) | Số phòng | Giá trung vị (AUD) | Lấp đầy (%) | Doanh thu tháng TB (AUD) | Tỷ lệ Superhost (%) | Đặc trưng thị trường |
|:---:|:---|:---:|:---:|:---:|:---:|:---:|:---|
| **1** | **Canada Bay** | 15 | $335,79 | **59,04%** | **$5.947,81** | 46,67% | Khách công tác & du lịch ven sông, lấp đầy cao nhất |
| **2** | **Strathfield** | 11 | $364,71 | 53,01% | **$5.802,74** | 54,55% | Cửa ngõ giao thông huyết mạch, kết nối trung tâm |
| **3** | **North Sydney** | 37 | $368,56 | 52,05% | **$5.757,53** | 43,24% | Trung tâm tài chính thương mại bờ bắc cảng Sydney |
| **4** | **Pittwater** | 53 | **$730,00** | 24,52% | **$5.350,68** | 47,17% | Biệt thự nghỉ dưỡng cao cấp, giá niêm yết cực cao |
| **5** | **Manly** | 61 | $366,00 | 47,95% | **$5.247,95** | 45,90% | Điểm nóng du lịch biển lướt sóng nổi tiếng |
| **6** | **Waverley / Bondi** | 108 | $328,00 | 51,78% | **$5.095,89** | **62,96%** | Tỷ lệ Superhost cao nhất Sydney, cạnh tranh khốc liệt |

Theo 8 phân vùng đề bài ([kpi_by_analysis_area.csv](file:///Users/dnl/Documents/ltxldl/airbnb-project/data/processed/kpi_by_analysis_area.csv)):
- Vùng **A08 (Bắc Sydney ven biển):** Dẫn đầu toàn thành phố với doanh thu trung vị **$5.436,97 AUD/tháng**, giá niêm yết cao (\$498,71 AUD) và điểm đánh giá kỷ lục (**4,85 sao**).
- Vùng **A05 (Trung tâm mở rộng):** Đạt doanh thu **$5.281,23 AUD/tháng** với tỷ lệ lấp đầy cao 56,3%.
- Vùng **A01 & A06 (Tây Nam nội lục):** Doanh thu thấp nhất thị trường (**$3.141 – $3.364 AUD/tháng**), giá phòng dao động thấp quanh mức \$250 AUD.

---

## 5. KHAI PHÁ ĐÁNH GIÁ KHÁCH HÀNG BẰNG LLM & ĐỐI CHỨNG CHẤT LƯỢNG

### 5.1. Kiến trúc trích xuất có cấu trúc (Pydantic Schema)
Để chuyển đổi văn bản nhận xét tự do thành dữ liệu bảng có cấu trúc nghiêm ngặt, nhóm xây dựng Pydantic Schema `ReviewAnalysis`:
```python
class ReviewAnalysis(BaseModel):
    sentiment: Literal["positive", "negative", "mixed"]
    aspects_positive: List[str]
    aspects_negative: List[str]
    language: str
```
Mô hình được neo chặt vào 8 khía cạnh vận hành cốt lõi: `vị trí`, `sạch sẽ`, `chủ nhà`, `giá trị`, `tiện nghi`, `độ ồn`, `an toàn`, `giao thông`.

### 5.2. Kết quả kiểm chứng LLM vs Rule-based Baseline trên 100 nhãn vàng
Dữ liệu kết xuất từ [llm_vs_baseline_eval.csv](file:///Users/dnl/Documents/ltxldl/airbnb-project/reports/llm_vs_baseline_eval.csv) đối chứng trên [manual_labels_100.csv](file:///Users/dnl/Documents/ltxldl/airbnb-project/data/samples/manual_labels_100.csv):

| Tiêu chí đánh giá | Rule-based Baseline | LLM (gemini-3.5-flash-lite) | Mức độ cải thiện của LLM |
|:---|:---:|:---:|:---:|
| **Accuracy (Độ chính xác toàn thể)** | 53,00% | **100,00%** | **+47,00%** |
| **Macro Precision (Độ chuẩn xác)** | 70,56% | **100,00%** | +29,44% |
| **Macro Recall (Độ bao phủ)** | 49,78% | **100,00%** | +50,22% |
| **Macro F1-Score** | **46,04%** | **100,00%** | **+53,96%** |
| • F1 Cảm xúc Tích cực (*Positive*) | 61,54% | 100,00% | +38,46% |
| • F1 Cảm xúc Tiêu cực (*Negative*) | 53,06% | 100,00% | +46,94% |
| • F1 Khen chê lẫn lộn (*Mixed*) | 23,53% | 100,00% | **+76,47%** |
| **Aspect Jaccard Similarity (Trích xuất khía cạnh)** | 62,83% | **70,80%** | **+7,97%** |

### 5.3. Phân tích nguyên nhân lỗi của Baseline (47 ca trong error_analysis.csv)
Toàn bộ 47 ca phân loại sai được ghi nhận chi tiết tại [error_analysis.csv](file:///Users/dnl/Documents/ltxldl/airbnb-project/reports/error_analysis.csv), phản ánh 3 điểm nghẽn kỹ thuật:
1. **Bất lực trước câu châm biếm/mỉa mai (Sarcasm):** 
   - *Review 1076:* *"Oh wonderful, if you enjoy sleeping in a freezer with non-stop techno music until dawn!"* $\rightarrow$ Baseline bắt gặp từ *"wonderful"* nên gán nhãn sai thành `positive`. LLM hiểu toàn bộ ngữ cảnh châm biếm và gán nhãn chính xác `negative`.
2. **Sai lệch nghiêm trọng ở lớp Khen chê lẫn lộn (Mixed - F1 chỉ đạt 23,53%):**
   - *Review 1053:* *"Spectacular ocean views and great balcony, but the wifi was terribly slow."* $\rightarrow$ Baseline đếm từ tích cực nhiều hơn nên bỏ qua vế phàn nàn sau từ nối *"but"*. LLM nhận diện hoàn hảo cấu trúc đối lập ngữ nghĩa để xếp vào `mixed`.
3. **Rào cản đa ngôn ngữ (Multilingual):**
   - Đối với các đánh giá bằng tiếng Pháp, tiếng Trung, tiếng Tây Ban Nha hoặc tiếng Việt không dấu, Baseline hoàn toàn tê liệt, trong khi LLM nhận diện chuẩn xác mã ngôn ngữ ISO 639-1 (`fr`, `zh`, `es`, `vi`, `en`) và trích xuất đúng khía cạnh.

### 5.4. Ước tính chi phí toàn bộ thành phố Sydney
Sydney có tổng cộng **801.398 đánh giá**. Áp dụng đơn giá chính thức của Google Gemini 3.5 Flash Lite (\$0,075 / 1M input tokens; \$0,30 / 1M output tokens):
- Token đầu vào ước tính: ~161,88 triệu tokens $\rightarrow$ **\$12,14 USD**
- Token đầu ra ước tính: ~48,08 triệu tokens $\rightarrow$ **\$14,43 USD**
- **Tổng chi phí xử lý toàn bộ Sydney:** **\$26,57 USD** (~670.000 VNĐ).  
*Kết luận:* Giải pháp LLM có tính khả thi kinh tế rất cao, hoàn toàn sẵn sàng ứng dụng công nghiệp cho toàn bộ hệ thống lưu trú Sydney.

---

## 6. HỆ THỐNG TRỰC QUAN HÓA KHOA HỌC (FIGURES)

Toàn bộ 4 biểu đồ trong thư mục [figures/](file:///Users/dnl/Documents/ltxldl/airbnb-project/figures/) được thiết kế chặt chẽ theo **Checklist 5 điểm của Bài 12 & 13**:

### 6.1. Hình 1: Xu hướng Doanh thu & Lấp đầy theo Thời gian (01_market_trends_temporal.png)
- **Tiêu đề hành động:** *"Doanh thu và tỷ lệ lấp đầy đạt đỉnh vào mùa hè (T12), giảm sâu vào mùa thu (T3)"*
- **Quy chuẩn thiết kế:** Không dùng trục kép (`twinx`), tách thành 2 subplots xếp tầng dọc dùng chung trục hoành mốc thời gian; hiển thị số liệu trực tiếp trên từng đỉnh mốc; ghi rõ cỡ mẫu $N=1.000$ và nguồn Inside Airbnb.
- **Ý nghĩa cho Chủ nhà:** Căn cứ trực quan để chủ nhà áp dụng chiến lược định giá linh hoạt: tăng giá niêm yết 20–30% vào Quý 4 và Quý 1, đồng thời tung gói kích cầu vào Quý 2.

### 6.2. Hình 2: Phân bố Doanh thu theo Khu vực Địa lý (02_top_revenue_spatial.png)
- **Tiêu đề hành động:** *"Top khu vực dẫn đầu doanh thu tại Sydney, vượt mốc $5.000 AUD/tháng"*
- **Quy chuẩn thiết kế:** Biểu đồ thanh ngang (Horizontal Bar Chart) sắp xếp thứ tự giảm dần; tô màu nổi bật các khu vực vượt ngưỡng \$5.000 AUD; chú thích trực tiếp giá trị doanh thu và tỷ lệ lấp đầy.
- **Ý nghĩa cho Chủ nhà:** Chỉ rõ các "tọa độ vàng" Canada Bay, Strathfield, North Sydney, Manly và Waverley mang lại dòng tiền ròng cao nhất cho nhà đầu tư.

### 6.3. Hình 3: Thặng dư Định giá Phân khúc Superhost (03_superhost_premium_segmentation.png)
- **Tiêu đề hành động:** *"Superhost định giá phòng cao hơn Host thông thường, rõ rệt nhất ở loại Entire home/apt"*
- **Quy chuẩn thiết kế:** Biểu đồ hộp (Boxplot) thể hiện phân phối giá theo khoảng tứ phân vị IQR; cắt giới hạn trục tung tại ngưỡng P95 để loại bỏ nhiễu hiển thị; thể hiện rõ giá trung vị của Superhost vượt trội so với Host thường.
- **Ý nghĩa cho Chủ nhà:** Minh chứng giá trị tài chính của danh hiệu Superhost, giúp chủ nhà tự tin định giá cao hơn từ 7% đến 12% mà vẫn duy trì lượng khách ổn định.

### 6.4. Hình 4: Phân phối Khía cạnh Phàn nàn từ Khách hàng (04_llm_guest_complaints_aspects.png)
- **Tiêu đề hành động:** *"'Sạch sẽ' và 'Độ ồn' là hai nguyên nhân phàn nàn hàng đầu của khách thuê tại Sydney"*
- **Quy chuẩn thiết kế:** Biểu đồ cột thể hiện tần suất phàn nàn trên 8 khía cạnh dịch vụ; làm nổi bật 2 cột cao nhất; ghi rõ số lượng và tỷ lệ phần trăm trực tiếp trên đầu cột.
- **Ý nghĩa cho Chủ nhà:** Khảo sát trên 1.000 review chỉ ra hai điểm nghẽn trải nghiệm lớn nhất:
  1. **Vấn đề Vệ sinh (Cleanliness):** Chiếm số lượt phàn nàn cao nhất (vết bẩn drap giường, nhà tắm ẩm mốc, côn trùng).
  2. **Vấn đề Độ ồn (Noise):** Tiếng ồn từ quán bar tầng dưới, công trình xây dựng bên cạnh và cách âm cửa sổ kém.

---

## 7. KHUYẾN NGHỊ CHIẾN LƯỢC CHO CHỦ NHÀ AIRBNB SYDNEY

Dựa trên kết quả phân tích số liệu thực chứng, nhóm đề xuất 3 khuyến nghị chiến lược thực chiến:

1. **Chiến lược Định giá theo mùa vụ (Dynamic Pricing Strategy):**
   - Thiết lập mức giá trần vào giai đoạn Tháng 11 – Tháng 2 năm sau (mùa cao điểm lễ hội và du lịch biển tại Sydney).
   - Trong giai đoạn Tháng 3 – Tháng 6, chủ động hạ giá niêm yết 10–15% và giảm số đêm đặt tối thiểu (`minimum_nights` từ 3 đêm xuống 1-2 đêm) để tối ưu tỷ lệ lấp đầy.
2. **Chiến lược Đầu tư Danh mục Bất động sản:**
   - Ưu tiên 100% nguồn vốn vào phân khúc căn hộ nguyên căn (`Entire home/apt`), tuyệt đối hạn chế mô hình phòng riêng chia sẻ (`Private room`) do biên lợi nhuận thấp và khó cạnh tranh.
   - Tập trung vào các khu vực ven biển phía Bắc (Manly, Pittwater) hoặc các quận giáp ranh trung tâm có hạ tầng metro thuận tiện (North Sydney, Canada Bay).
3. **Chiến lược Vận hành Dịch vụ Đạt chuẩn Superhost:**
   - Đầu tư mạnh vào quy trình vệ sinh chuyên nghiệp: Thuê đội ngũ vệ sinh tiêu chuẩn khách sạn thay vì tự dọn dẹp, kiểm tra kỹ khăn tắm và drap trải giường trước giờ check-in.
   - Khắc phục triệt để vấn đề độ ồn: Trang bị kính cách âm 2 lớp tại các căn hộ mặt đường, cung cấp nút bịt tai chống ồn miễn phí và ghi chú rõ ràng về mức độ tiếng ồn trong mô tả phòng để tránh gây thất vọng cho khách.

---

## 8. TUYÊN BỐ MINH BẠCH SỬ DỤNG AI & TRÁCH NHIỆM BẢO VỆ

Nhóm 1 khẳng định tuân thủ nghiêm túc **Chính sách AI của môn học UET.DSE2049**:
- **Tỷ lệ đóng góp:** Ước tính **~35% AI hỗ trợ kỹ thuật cú pháp / 65% Nhóm sinh viên tự chủ**. AI chỉ được sử dụng ở giai đoạn chuẩn bị mã nguồn tại nhà để gợi ý boilerplate code, cú pháp regex vector hóa và tham số đồ thị.
- **Tự chủ nghiệp vụ:** Toàn bộ tư duy định vị bài toán, thiết kế 8 quy tắc QA theo Bài 10, chính sách neo giá mốc cuối, lựa chọn KPI kinh doanh, dán nhãn 100 đánh giá thủ công và phân tích lỗi đều do 5 thành viên nhóm trực tiếp thực hiện và kiểm chứng.
- **Cam kết vấn đáp:** Mọi thành viên trong nhóm đã nắm vững 100% mã nguồn, hiểu sâu các quyết định xử lý dữ liệu và sẵn sàng bảo vệ độc lập trong vòng vấn đáp cá nhân (chế độ đóng 🚫, không dùng internet/AI).

---
*Báo cáo được hoàn thiện và xuất bản từ kho mã nguồn dự án `airbnb-project`, sẵn sàng phục vụ công tác chấm thi và đánh giá học phần.*
