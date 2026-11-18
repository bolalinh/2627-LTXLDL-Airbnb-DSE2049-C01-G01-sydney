# AI_USAGE.md – Báo cáo Minh bạch Sử dụng AI (AI Transparency Report)

> **Học phần:** Lập trình Xử lý Dữ liệu (UET.DSE2049) – Học kỳ 1, Năm học 2026–2027  
> **Lớp:** `UET.DSE2049 3` | **Nhóm:** `Nhóm 1`  
> **Mã dữ liệu phân công:** `DSE2049-C03-G01-sydney`  
> **Thành phố nghiên cứu:** **Sydney (Australia)** – Đơn vị tiền tệ: **AUD**  
> **Bốn mốc chụp dữ liệu:** `2025-09-12`, `2025-12-12`, `2026-03-21`, `2026-06-16`  
> **Bên đặt hàng phân tích (Client Persona):** Hiệp hội Chủ nhà Airbnb Sydney (Host Community) & Nhà Đầu tư Bất động sản Du lịch  
> **Mức độ sử dụng AI ước tính:** **~35% AI / 65% Nhóm sinh viên tự chủ** (AI chỉ đóng vai trò trợ lý kỹ thuật hỗ trợ gợi ý cú pháp; nhóm sinh viên trực tiếp thiết kế bài toán, quyết định nghiệp vụ, kiểm chứng số liệu và chịu trách nhiệm 100% trong vòng vấn đáp độc lập).

---

## Danh sách Thành viên Nhóm 1 (Lớp UET.DSE2049 3)

| STT | Họ và tên | Mã sinh viên | Vai trò trong nhóm | Trách nhiệm chính |
|:---:|:---|:---:|:---:|:---|
| 1 | **Đinh Ngọc Linh** | **25022910** | **Nhóm trưởng** | Quản trị mã nguồn, kiến trúc pipeline, tối ưu hóa I/O, trực quan hoá (Bài 12-13) |
| 2 | Nguyễn Tiến Long An | 25022763 | Thành viên | Thu thập dữ liệu Inside Airbnb, kiểm soát chất lượng QA và xử lý thiếu khoá/trùng lặp |
| 3 | Nguyễn Tiến Quốc | 25023001 | Thành viên | Thiết kế bộ chỉ số KPI doanh thu, tỷ lệ lấp đầy, phân tích không gian 8 vùng |
| 4 | Nguyễn Nam Khánh | 25022902 | Thành viên | Tích hợp mô hình Gemini API, xây dựng Pydantic Schema, cơ chế cache JSONL |
| 5 | Nguyễn Hải Nam | 25022954 | Thành viên | Xây dựng mô hình Baseline luật, dán nhãn 100 đánh giá thủ công, phân tích lỗi |

---

## 1. Mức độ Sử dụng AI & Phân định Trách nhiệm (Tỷ lệ ~35% AI / 65% Nhóm)

Nhóm cam kết tuân thủ chặt chẽ **Chính sách AI của môn học**: AI được phép sử dụng ở giai đoạn chuẩn bị mã nguồn tại nhà, nhưng mọi thành viên trong nhóm phải nắm vững từng dòng mã, hiểu sâu nguyên lý toán học/thống kê để bảo vệ độc lập trong vòng vấn đáp cá nhân (~20 phút, không dùng internet/AI).

```
                    PHÂN ĐỊNH TRÁCH NHIỆM DỰ ÁN
    ┌───────────────────────────────┬───────────────────────────────┐
    │     AI HỖ TRỢ KỸ THUẬT (~35%) │    NHÓM SINH VIÊN TỰ CHỦ (~65%) │
    ├───────────────────────────────┼───────────────────────────────┤
    │ • Gợi ý cú pháp thư viện      │ • Định vị đề tài & Persona    │
    │ • Boilerplate code Pydantic   │ • Thiết kế logic 8 quy tắc QA │
    │ • Cú pháp vector hoá regex    │ • Khớp chuẩn 1.000 ID phân bổ │
    │ • Tham khảo tham số biểu đồ   │ • Gán nhãn vàng 100 review    │
    │ • Hỗ trợ đo lường Timer       │ • Phân tích lỗi & Bảo vệ code │
    └───────────────────────────────┴───────────────────────────────┘
```

### Bảng phân định chi tiết qua 6 công đoạn của Pipeline:

| Công đoạn thực hiện | Tỷ lệ AI | AI đã hỗ trợ những gì? (~35%) | Nhóm sinh viên tự chủ và kiểm chứng những gì? (~65%) |
|---|:---:|---|---|
| **[1/6] Nạp dữ liệu & 1.000 ID phân công** | 20% | Gợi ý cú pháp `argparse` cho CLI, cấu trúc đọc file cấu hình YAML phòng thủ. | **100% nhóm tự tra cứu bảng phân công**, tải đúng 1.000 listing_id và 8 vùng `A01-A08` từ Google Sheets của giảng viên, đưa vào `data/samples/`. |
| **[2/6] Kiểm soát chất lượng (QA Pipeline)** | 30% | Gợi ý regex bóc tách ký tự tiền tệ (`$`, `,`), cú pháp hàm `.pipe()` trong Pandas. | Tự thiết kế chuẩn 8 quy tắc QA (QA-01 đến QA-08). Thiết lập **Chính sách neo giá mốc cuối (Latest Snapshot Policy)** và bộ 4 bài test tự kiểm tra bắt buộc. |
| **[3/6] Bộ chỉ số KPI cho Chủ nhà** | 25% | Gợi ý cú pháp Groupby nhiều cấp kết hợp `observed=True` tối ưu bộ nhớ. | Tự định nghĩa 6 KPI cốt lõi (Median Price, Estimated Occupancy từ `availability_365`, Monthly Revenue, Superhost Premium, Phân tích 8 vùng đề bài). |
| **[4/6] Trích xuất có cấu trúc bằng LLM** | 50% | Cung cấp SDK `google-genai` (Gemini 2.0 Flash / Flash-Lite), sinh boilerplate Pydantic BaseModel. | Thiết kế cấu trúc Prompt phân tích khía cạnh, lọc đúng 1.000 review mẫu LLM theo đề bài, xây dựng cơ chế lưu đệm `llm_cache.jsonl` và xử lý Retry/Backoff. |
| **[5/6] Đánh giá đối chứng & Phân tích lỗi** | 25% | Hỗ trợ cú pháp tính toán ma trận F1, Precision, Recall, Accuracy của `scikit-learn`. | **100% nhóm tự tay gán nhãn 100 nhận xét thực tế** (`manual_labels_100.csv`). Trực tiếp mổ xẻ 47 ca lỗi của Baseline để chứng minh giá trị của LLM. |
| **[6/6] Trực quan hoá dữ liệu (Bài 12 & 13)** | 35% | Gợi ý cú pháp vẽ Seaborn Boxplot và nhãn trực tiếp trên thanh `ax.bar_label()`. | **Chuyển 100% tiêu đề thành Kết luận rút ra (Actionable Takeaways)**, cấu hình font UTF-8 đa nền tảng, đảm bảo checklist 5 điểm của Bài 12-13. |

---

## 2. Danh mục Công cụ AI Đã Sử Dụng

| Tên công cụ / Nền tảng | Phiên bản / Môi trường | Mục đích sử dụng cụ thể trong dự án |
|---|---|---|
| **Google Gemini API** | `gemini-3.5-flash-lite` | Đóng vai trò là thành phần của hệ thống dữ liệu: Phân tích cảm xúc (`positive`, `negative`, `mixed`), trích xuất khía cạnh dịch vụ (`aspects_positive`, `aspects_negative`), nhận diện ngôn ngữ (`language`). |
| **Antigravity / Gemini CLI** | Môi trường phát triển AI Agent | Hỗ trợ rà soát chuẩn mực PEP 8, tối ưu hoá I/O lọc cột bằng `usecols`, kiểm tra xung đột thư viện trên Python 3.14. |
| **GitHub Copilot / Assistant** | VS Code Extension | Gợi ý tự động hoàn thiện type hint, docstring theo chuẩn Google Style Guide và các câu lệnh lặp đơn giản. |

---

## 3. Nhật ký Prompt Then Chốt (Key Prompts)

Dưới đây là 7 prompt kỹ thuật quan trọng nhất thể hiện rõ vai trò định hướng nghiệp vụ của nhóm đối với trợ lý AI:

### Prompt 1: Lọc dữ liệu chuẩn xác theo danh sách 1.000 ID phân công
* **Vị trí tác động:** `src/qa.py` (Hàm `run_qa`)
* **Mục tiêu:** Đảm bảo chỉ đọc đúng 1.000 listing được giao cho nhóm, không phân tích thừa dữ liệu thành phố.
* **Nội dung Prompt:**
  > *"Chúng tôi là Nhóm 1 (Lớp UET.DSE2049 3) được giao phân tích Sydney với đúng 1.000 listing_id trong file `data/samples/assigned_listings_1000.csv`. Hãy sửa hàm `run_qa` trong `src/qa.py` sao cho: khi đọc file `listings.csv.gz` thô của từng mốc chụp, chương trình chỉ lọc giữ lại đúng các dòng có ID nằm trong bảng phân công này, đồng thời ánh xạ thêm cột `analysis_area` (từ A01 đến A08) vào DataFrame và xuất ra file sạch `listings_clean_{snapshot}.csv`."*

### Prompt 2: Tối ưu hoá nạp dữ liệu bằng `usecols` để giảm RAM và tăng tốc
* **Vị trí tác động:** `src/qa.py` & `run_pipeline.py`
* **Mục tiêu:** Khắc phục tình trạng đọc cả 90 cột thô gây chậm chạp và tốn hàng trăm MB RAM.
* **Nội dung Prompt:**
  > *"File `listings.csv.gz` của Inside Airbnb chứa tới 90 cột, trong đó có các cột text rất dài như `description`, `amenities`, `neighborhood_overview` không dùng đến. Hãy rà soát toàn bộ các quy tắc QA và tính KPI để trích xuất danh sách các cột thực sự cần thiết, sau đó dùng tham số `usecols` trong `pd.read_csv` để chỉ nạp đúng các cột này. Đảm bảo thời gian đọc mỗi mốc dưới 0.5s."*

### Prompt 3: Thiết lập Chính sách neo giá mốc cuối (Latest Snapshot Price Policy)
* **Vị trí tác động:** `src/qa.py` (Hàm `apply_latest_snapshot_price_policy`)
* **Mục tiêu:** Xử lý tình trạng thiếu giá ở các mốc chụp cũ (như mốc 2025) theo yêu cầu đề bài.
* **Nội dung Prompt:**
  > *"Theo quy định của đề bài: chỉ dùng giá ở mốc cuối cùng (2026-06-16) do nguồn dữ liệu ở các mốc trước không đồng đều. Hãy viết hàm `apply_latest_snapshot_price_policy` trong `src/qa.py`: ánh xạ 100% giá từ bảng giá mốc cuối sang các mốc trước theo ID. Nếu listing cũ nào thiếu giá mốc cuối, hãy điền bổ sung bằng giá trung vị (Median) theo nhóm `[neighbourhood_cleansed, room_type]`."*

### Prompt 4: Ràng buộc Schema có cấu trúc Pydantic cho LLM
* **Vị trí tác động:** `src/llm.py` (Class `ReviewAnalysis`)
* **Mục tiêu:** Đảm bảo output của LLM luôn trả về đúng JSON Schema hợp lệ, không bị lỗi cú pháp văn bản tự do.
* **Nội dung Prompt:**
  > *"Viết một Pydantic BaseModel tên là `ReviewAnalysis` cho bài toán phân tích đánh giá Airbnb với 4 trường: `sentiment` (chỉ nhận một trong 3 giá trị 'positive', 'negative', 'mixed'), `aspects_positive` (danh sách các khía cạnh khen ngợi), `aspects_negative` (danh sách các khía cạnh phàn nàn), và `language` (chuỗi mã ngôn ngữ 2 ký tự). Hãy cấu hình để Gemini API sử dụng schema này qua thuộc tính `response_schema`."*

### Prompt 5: Khớp chuẩn 1.000 review mẫu LLM phân công
* **Vị trí tác động:** `run_pipeline.py` (Bước [4/6])
* **Mục tiêu:** Tránh lấy mẫu ngẫu nhiên sai lệch với dữ liệu được giáo viên giao.
* **Nội dung Prompt:**
  > *"File `data/samples/assigned_reviews_5000.csv` chứa 5.000 review của nhóm, trong đó đúng 1.000 dòng có cột `Mẫu LLM == 'x'`. Hãy sửa Bước 4 trong `run_pipeline.py` để thay vì lấy mẫu ngẫu nhiên 3.000 review, hệ thống sẽ đọc `reviews.csv.gz` và lọc ra đúng 1.000 review ID này để gửi qua mô hình LLM."*

### Prompt 6: Chuyển tiêu đề biểu đồ thành Kết luận rút ra (Actionable Takeaways)
* **Vị trí tác động:** `src/viz.py`
* **Mục tiêu:** Đạt điểm tối đa theo Checklist 5 điểm của Bài giảng 12 & 13.
* **Nội dung Prompt:**
  > *"Theo nguyên tắc trực quan hoá Bài 12-13, tiêu đề biểu đồ phải mang thông điệp kinh doanh rõ ràng (Actionable Takeaways) thay vì mô tả nội dung chung chung. Hãy xem xét kết quả phân tích số liệu của Sydney và sửa lại toàn bộ 4 tiêu đề trong `src/viz.py` thành kết luận rút ra từ dữ liệu (ví dụ: mốc mùa vụ đạt đỉnh, khu vực dẫn đầu doanh thu, mức chênh lệch giá Superhost, và vấn đề khách phàn nàn nhiều nhất)."*

### Prompt 7: Hỗ trợ hiển thị tiếng Việt đa nền tảng cho Matplotlib
* **Vị trí tác động:** `src/viz.py`
* **Mục tiêu:** Đảm bảo biểu đồ không bị lỗi font ô vuông khi chạy trên máy Windows của thành viên khác.
* **Nội dung Prompt:**
  > *"Khi chạy Matplotlib trên máy Windows có tiêu đề tiếng Việt có dấu, đồ thị thường bị lỗi ô vuông do thiếu font UTF-8 tương thích. Hãy bổ sung cấu hình fallback font trong `plt.rcParams` bao gồm Arial, DejaVu Sans, Segoe UI để đồ thị hiển thị sắc nét trên cả macOS và Windows."*

---

## 4. Các Trường Hợp AI Gợi Ý Sai / Ảo Giác và Cách Nhóm Tự Phát Hiện & Sửa Chữa

Đây là minh chứng rõ ràng nhất cho thấy nhóm sinh viên làm chủ hoàn toàn dự án, không phụ thuộc mù quáng vào AI:

```
                           SỰ CAN THIỆP CỦA CON NGƯỜI
    ┌───────────────────────────────┐        ┌───────────────────────────────┐
    │    Ý TƯỞNG SAI CỦA AI         │        │    GIẢI PHÁP ĐÚNG CỦA NHÓM    │
    ├───────────────────────────────┤        ├───────────────────────────────┤
    │ • Doanh thu = Price * Reviews │ ───►   │ • Occupancy = (365-Avail)/365 │
    │ • Dùng Mean Price kéo lệch    │ ───►   │ • Dùng Median Price chuẩn hoá │
    │ • Biểu đồ trục kép (twinx)    │ ───►   │ • 2 Subplots xếp tầng dọc     │
    │ • Nạp ngẫu nhiên 50.000 dòng  │ ───►   │ • Lọc đúng 1.000 ID phân công │
    └───────────────────────────────┘        └───────────────────────────────┘
```

### Ví dụ 1: AI đề xuất công thức doanh thu San Francisco sai lệch
* **Gợi ý sai của AI:** AI đề xuất công thức ước tính doanh thu tháng:  
  $$\text{Doanh thu} = \text{price} \times 30 \times \left(\frac{\text{reviews\_per\_month}}{30}\right)$$
* **Phát hiện của nhóm:** Công thức này dựa trên mô hình San Francisco cũ, sai lệch nghiêm trọng vì chỉ có khoảng 50% – 70% khách thực tế để lại đánh giá trên Airbnb. Dùng số review để tính doanh thu sẽ làm giảm dòng tiền thực tế tới 40%.
* **Cách nhóm tự sửa:** Nhóm tra cứu tài liệu Inside Airbnb và thay thế bằng công thức chuẩn dựa trên số ngày thực mở phòng trong 365 ngày tới:
  $$\text{Tỷ lệ lấp đầy (Occupancy Rate)} = \frac{365 - \text{availability\_365}}{365} \times 100\%$$
  $$\text{Doanh thu tháng ước tính} = \text{price} \times 30 \times \left(\frac{\text{Occupancy Rate}}{100}\right)$$

### Ví dụ 2: AI đề xuất dùng Mean Price làm thước đo thị trường
* **Gợi ý sai của AI:** Khi tổng hợp giá theo khu vực, AI viết `df.groupby('neighbourhood_cleansed')['price'].mean()`.
* **Phát hiện của nhóm:** Sydney có những căn biệt thự ven vịnh và penthouse hạng sang có giá lên tới \$5,000 – \$15,000 AUD/đêm (phân vị 99%). Dùng giá trung bình (Mean) bị kéo lệch nghiêm trọng (Mean Sydney lên tới \$449 AUD trong khi Median thực tế chỉ là \$319 AUD).
* **Cách nhóm tự sửa:** Vận dụng nguyên lý **Thống kê vững (Robust Statistics - Bài 3 & 10)**, nhóm chuyển toàn bộ chỉ số định giá sang giá trung vị `median()`, chỉ giữ `mean()` làm số liệu phụ trợ.

### Ví dụ 3: AI gợi ý vẽ biểu đồ trục kép (Dual Y-Axis)
* **Gợi ý sai của AI:** AI sinh code Matplotlib sử dụng `ax.twinx()` để ghép chung đường Doanh thu (AUD) và đường Lấp đầy (%) vào một biểu đồ.
* **Phát hiện của nhóm:** Bài giảng 13 nhấn mạnh trục kép là lỗi thiết kế trực quan nguy hiểm, dễ gây hiểu lầm về tương quan giữa 2 đại lượng có đơn vị đo khác biệt.
* **Cách nhóm tự sửa:** Nhóm chuyển thành 2 đồ thị con (Subplots) xếp chồng theo chiều dọc có chung trục hoành mốc chụp thời gian, hiển thị nhãn số liệu trực tiếp trên từng điểm đo.

### Ví dụ 4: AI bỏ qua danh sách phân công, nạp ngẫu nhiên cả thành phố
* **Gợi ý sai của AI:** Trong bản phác thảo đầu tiên, AI viết code đọc toàn bộ 20.000 dòng của Sydney và thực hiện lấy mẫu ngẫu nhiên để phân tích.
* **Phát hiện của nhóm:** Điều này vi phạm trực tiếp quy định của đề tài: mỗi nhóm có một danh sách **1.000 listing_id** và **5.000 review_id** riêng biệt được gán nhãn trong Google Sheets.
* **Cách nhóm tự sửa:** Nhóm xây dựng hàm nạp file `data/samples/assigned_listings_1000.csv`, lọc chính xác 1.000 ID ở cả 4 mốc chụp và xây dựng bộ hàm tự kiểm tra 4 ràng buộc của đề bài (`_validate_assigned_1000`).

---

## 5. Quy trình Làm việc & Kiểm chứng theo Chuẩn Môn học (Bài giảng 1)

Nhóm áp dụng triệt để **Quy trình 5 bước khi làm việc với AI** được giảng dạy trong Bài 1:

```
                      QUY TRÌNH 5 BƯỚC LÀM VIỆC VỚI AI (BÀI 1)
  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
  │ 1. TỰ PHÁC   │ ──► │ 2. HỎI AI    │ ──► │ 3. ĐỌC HIỂU  │ ──► │ 4. KIỂM CHỨNG│ ──► │ 5. KHAI BÁO  │
  │ Định làm gì, │     │ Prompt rõ    │     │ Từng dòng mã,│     │ Thử trên mẫu │     │ Ghi vào      │
  │ kết quả gì?  │     │ bối cảnh     │     │ tra cứu docs │     │ tính tay thật│     │ AI_USAGE.md  │
  └──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
```

Đặc biệt ở **Bước 4 (Kiểm chứng)** và **Bước 5 (Khai báo)**, nhóm thực hiện 4 cơ chế kiểm soát chất lượng nghiêm ngặt:

1. **Rà soát mã nguồn từng dòng (Peer Code Review):**
   * Mọi đoạn mã AI gợi ý đều được các thành viên trong nhóm đọc hiểu cặn kẽ, kiểm tra kỹ lưỡng các trường hợp ngoại lệ (`NaN`, chia cho 0, kiểu dữ liệu hỗn hợp).
2. **Kiểm tra tính tái lập tuyệt đối (Reproducibility Check):**
   * Xoá sạch toàn bộ thư mục `data/processed/`, chạy lại toàn bộ quy trình trên môi trường ảo sạch (`.venv`) chỉ với một câu lệnh:
     ```bash
     python run_pipeline.py --config configs/sydney.yaml --skip-download --skip-llm
     ```
   * Xác nhận toàn bộ 6 bước thực thi trơn tru trong **~14 giây** và sinh đủ tất cả deliverables.
3. **Thẩm định độc lập trên 100 nhãn vàng thủ công (Gold Standard):**
   * 100% câu đánh giá trong `data/samples/manual_labels_100.csv` được nhóm tự đọc và dán nhãn thủ công.
   * Chạy mô hình Baseline và LLM song song, kiểm tra bảng ma trận phân loại và trực tiếp mổ xẻ 47 ca phân loại sai của Baseline trong `reports/error_analysis.csv`.
4. **Đối chiếu số liệu kinh doanh với thực tế thị trường Sydney:**
   * Đối chiếu kết quả phân tích (giá trung vị \$319 AUD/đêm, tỷ lệ lấp đầy 43% – 51%, mùa hè tháng 12 đạt đỉnh) với các báo cáo thực tế của Destination NSW và Inside Airbnb để bảo đảm tính logic thực tiễn.

---

## 6. Cam kết Liêm chính Học thuật (Academic Integrity Declaration)

Tập thể thành viên **Nhóm 1 – Lớp UET.DSE2049 3** cam kết:

1. Báo cáo này phản ánh trung thực 100% mức độ và phương thức sử dụng AI trong suốt quá trình thực hiện bài tập lớn.
2. Không có bất kỳ đoạn mã hay số liệu nào được đưa vào sản phẩm cuối cùng mà không qua sự thẩm định, kiểm chứng và thấu hiểu của các thành viên trong nhóm.
3. Toàn bộ 5 thành viên trong nhóm đều sẵn sàng trả lời độc lập mọi câu hỏi vấn đáp chuyên sâu về thuật toán, logic xử lý dữ liệu và kết luận kinh doanh mà không cần sự trợ giúp của AI hay tài liệu bên ngoài.

*Hà Nội, ngày 18 tháng 11 năm 2026*  
**Đại diện Nhóm 1 (Nhóm trưởng):** Đinh Ngọc Linh *(MSSV: 25022910)*
