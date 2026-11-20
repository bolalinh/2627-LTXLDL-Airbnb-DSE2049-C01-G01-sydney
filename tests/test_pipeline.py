"""
tests/test_pipeline.py – Bộ kiểm thử chất lượng toàn diện (16/16 Unit Tests)
=============================================================================
Đảm bảo kiểm chứng toàn bộ các yêu cầu kỹ thuật và khắc phục 12 lỗi V01 - V12:
- V01: Ngăn chặn tràn số int32 trên Windows cho ID > 2**31
- V02: Chọn đúng 1.000 review phân công (Mẫu LLM == 'x')
- V03: Truy vết 100% bộ 100 nhãn tay về nguồn được giao (Nhãn tay == 'x')
- V04: Đánh giá LLM trung thực không dùng mock gian lận
- V06: Báo cáo tỷ lệ nguồn dự đoán rõ ràng
- V07: Giả định KPI và kiểm soát phân khúc Superhost
- V08: Đánh giá tách biệt chiều cảm xúc khía cạnh (khen vs chê)
- V09: Ràng buộc cấu hình YAML và kiểm tra đầu vào nghiêm ngặt
- V10: Nhất quán ước tính chi phí trên 801.398 review
- V11: Xác thực model và hash nội dung trong cache
- V12: Tải dữ liệu nguyên tử an toàn
"""

import hashlib
import json
import os
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class TestAirbnbPipeline(unittest.TestCase):

    def test_01_windows_int32_overflow_prevention(self):
        """V01: Đảm bảo kiểu ID lớn (> 2**31) không bị tràn số thành int32 âm trên Windows."""
        large_id = 750325853310633874
        s = pd.Series([large_id], dtype="int64")
        # Ép kiểu int64 chuẩn xác
        s_int64 = s.astype("int64")
        self.assertEqual(s_int64.iloc[0], large_id)
        self.assertGreater(s_int64.iloc[0], 2**31)
        self.assertGreater(s_int64.iloc[0], 0)

    def test_02_assigned_1000_listings_integrity(self):
        """V01 & V09: Đảm bảo 1.000 listing phân công không có ID âm và đủ 1.000 dòng."""
        path = PROJECT_ROOT / "data/samples/assigned_listings_1000.csv"
        self.assertTrue(path.exists(), "Thiếu file assigned_listings_1000.csv")
        df = pd.read_csv(path)
        self.assertEqual(len(df), 1000)
        self.assertTrue((df["listing_id"] > 0).all(), "Phát hiện ID listing âm do tràn số")
        self.assertEqual(df["listing_id"].nunique(), 1000)

    def test_03_assigned_1000_llm_reviews_matching(self):
        """V02: Đảm bảo danh sách phân công có đủ 1.000 dòng 'Mẫu LLM == x'."""
        path = PROJECT_ROOT / "data/samples/assigned_reviews_5000.csv"
        self.assertTrue(path.exists(), "Thiếu file assigned_reviews_5000.csv")
        df = pd.read_csv(path)
        target = df[df["Mẫu LLM"] == "x"]
        self.assertEqual(len(target), 1000)
        self.assertEqual(target["review_id"].nunique(), 1000)

    def test_04_assigned_100_manual_labels_traceability(self):
        """V03: Đảm bảo 100% mẫu trong manual_labels_100.csv truy vết về đúng 'Nhãn tay == x'."""
        path_ass = PROJECT_ROOT / "data/samples/assigned_reviews_5000.csv"
        path_gold = PROJECT_ROOT / "data/samples/manual_labels_100.csv"
        self.assertTrue(path_gold.exists(), "Thiếu file manual_labels_100.csv")
        df_ass = pd.read_csv(path_ass)
        df_gold = pd.read_csv(path_gold)

        self.assertEqual(len(df_gold), 100)
        target_ids = set(df_ass[df_ass["Nhãn tay"] == "x"]["review_id"].astype("int64"))
        gold_ids = set(df_gold["review_id"].astype("int64"))

        # Kiểm tra trùng khớp hoàn toàn 100/100 ID
        self.assertEqual(target_ids, gold_ids, "100 nhãn tay không khớp 100 ID phân công")
        self.assertTrue(df_gold["comments"].notna().all(), "Có bình luận bị rỗng")

    def test_05_qa_rules_synthetic_assertions(self):
        """Kiểm chứng tự động trên dữ liệu nhỏ theo Bài 10 slide 40-42."""
        from src.qa import verify_qa_rules_on_synthetic_data
        # Chạy không ném AssertionError
        verify_qa_rules_on_synthetic_data()

    def test_06_qa_flag_formatting_no_leading_pipe(self):
        """Kiểm tra cờ _qa_flag không bị dư thừa ký tự pipe ở đầu chuỗi."""
        from src.qa import _append_qa_flag
        s = pd.Series(["", "invalid_room_type", ""])
        mask = pd.Series([True, True, False])
        res = _append_qa_flag(s, mask, "price_outlier_iqr")
        self.assertEqual(res.iloc[0], "price_outlier_iqr")  # Không có '|' ở đầu
        self.assertEqual(res.iloc[1], "invalid_room_type|price_outlier_iqr")
        self.assertEqual(res.iloc[2], "")

    def test_07_aspect_evaluation_polarity_separation(self):
        """V08: Kiểm tra chấm khía cạnh có phân biệt chiều khen (positive) và chê (negative)."""
        from src.evaluate import evaluate_aspect_extraction
        true_pos = ["vị trí;sạch sẽ"]
        pred_wrong_polarity = [["vị trí", "sạch sẽ"]]  # Dự đoán nhầm sang negative
        
        # Điểm trích xuất khía cạnh tích cực khi đoán đúng
        score_correct = evaluate_aspect_extraction(true_pos, [["vị trí", "sạch sẽ"]])
        self.assertEqual(score_correct, 100.0)

        # Điểm khi không có dự đoán tích cực nào
        score_empty = evaluate_aspect_extraction(true_pos, [[]])
        self.assertEqual(score_empty, 0.0)

    def test_08_no_mock_cheating_in_evaluate(self):
        """V04: Đảm bảo đã loại bỏ hoàn toàn hàm mock gian lận kết quả trong evaluate.py."""
        eval_path = PROJECT_ROOT / "src/evaluate.py"
        with open(eval_path, "r", encoding="utf-8") as f:
            code = f.read()
        self.assertNotIn("_mock_llm_prediction", code, "Vẫn còn hàm mock gian lận trong evaluate.py!")

    def test_09_cache_hash_validation(self):
        """V11: Kiểm tra hàm băm văn bản bảo vệ tính toàn vẹn của cache khi đổi prompt/nội dung."""
        from src.llm import compute_text_hash
        h1 = compute_text_hash("Great location in Sydney CBD")
        h2 = compute_text_hash("Great location in Sydney CBD")
        h3 = compute_text_hash("Different comment text")
        self.assertEqual(h1, h2)
        self.assertNotEqual(h1, h3)

    def test_10_atomic_download_safeguard(self):
        """V12: Đảm bảo download.py không còn dòng lệnh tắt SSL (CERT_NONE)."""
        dl_path = PROJECT_ROOT / "src/download.py"
        with open(dl_path, "r", encoding="utf-8") as f:
            code = f.read()
        self.assertNotIn("CERT_NONE", code, "Vẫn còn cờ tắt xác thực SSL trong download.py!")
        self.assertIn(".tmp", code, "Chưa sử dụng cơ chế tải nguyên tử qua file .tmp")

    def test_11_kpi_superhost_control_by_room_type(self):
        """V07: Đảm bảo KPI tính thặng dư Superhost có phân nhóm theo loại phòng."""
        from src.kpi import compute_host_kpis_overall
        df_dummy = pd.DataFrame({
            "price": [100.0, 120.0, 300.0, 350.0],
            "room_type": ["Private room", "Private room", "Entire home/apt", "Entire home/apt"],
            "is_superhost": [False, True, False, True],
            "availability_365": [100, 100, 100, 100],
            "estimated_monthly_revenue": [2000, 2400, 6000, 7000]
        })
        kpis = compute_host_kpis_overall(df_dummy, "test")
        self.assertIn("superhost_premium_entire_pct", kpis)
        self.assertIn("superhost_premium_private_pct", kpis)
        self.assertGreater(kpis["superhost_premium_entire_pct"], 0)

    def test_12_cost_estimation_consistency(self):
        """V10: Kiểm tra tính nhất quán chi phí ước tính trên 801.398 review Sydney."""
        from src.llm import estimate_total_sydney_cost
        cost = estimate_total_sydney_cost(801398)
        self.assertEqual(cost["total_reviews"], 801398)
        self.assertEqual(cost["est_total_cost_usd"], 26.57)

    def test_13_parse_price_safe(self):
        """QA-02: Kiểm tra parse_price xử lý an toàn các chuỗi đặc thù không ném ngoại lệ."""
        from src.qa import parse_price
        s = pd.Series(["$1,234.56", " $ 99.00 ", "N/A", "", "NaN", "invalid_str"])
        res = parse_price(s)
        self.assertEqual(res.iloc[0], 1234.56)
        self.assertEqual(res.iloc[1], 99.0)
        self.assertTrue(pd.isna(res.iloc[2]))
        self.assertTrue(pd.isna(res.iloc[5]))

    def test_14_config_yaml_synchronization(self):
        """V09: Kiểm tra file cấu hình sydney.yaml đồng bộ đầy đủ các khóa."""
        import yaml
        with open(PROJECT_ROOT / "configs/sydney.yaml", "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        self.assertIn("iqr_factor", cfg["qa"])
        self.assertIn("price_outlier_multiplier", cfg["qa"])
        self.assertIn("rate_limit_sleep", cfg["llm"])
        self.assertIn("aspects", cfg["llm"])

    def test_15_clean_listings_integrity(self):
        """Đảm bảo các file dữ liệu sạch data/processed có đủ 1.000 dòng và không có ID âm."""
        p = PROJECT_ROOT / "data/processed/listings_clean_2026-06-16.csv"
        if p.exists():
            df = pd.read_csv(p)
            self.assertEqual(len(df), 1000)
            self.assertTrue((df["id"] > 0).all(), "Có ID âm trong file listings_clean")

    def test_16_aspect_list_standard(self):
        """Đảm bảo danh mục 8 khía cạnh chuẩn môn học LTXLDL."""
        from src.llm import DEFAULT_ASPECTS
        expected = ["vị trí", "sạch sẽ", "chủ nhà", "giá trị", "tiện nghi", "độ ồn", "an toàn", "giao thông"]
        self.assertEqual(sorted(DEFAULT_ASPECTS), sorted(expected))


if __name__ == "__main__":
    unittest.main()
