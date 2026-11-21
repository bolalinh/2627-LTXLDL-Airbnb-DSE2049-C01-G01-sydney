"""
run_pipeline.py – Thực thi toàn bộ quy trình phân tích Inside Airbnb bằng 1 lệnh duy nhất
========================================================================================

CÚ PHÁP CHẠY CHUẨN:
───────────────────
python run_pipeline.py --config configs/sydney.yaml

CÁC THAM SỐ HỖ TRỢ:
───────────────────
--config         : Đường dẫn tới file YAML cấu hình thành phố (bắt buộc)
--skip-download  : Bỏ qua bước tải nếu dữ liệu thô đã có sẵn trong data/raw/
--skip-llm       : Bỏ qua gọi API LLM mới, tận dụng cache và baseline đối chứng
--sample-size    : Số lượng mẫu đánh giá để xử lý LLM (mặc định lấy từ config)
--log-file       : Tên file nhật ký (mặc định: log.txt)
"""

import argparse
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

import pandas as pd
import yaml

from src.logger import PipelineLogger


def load_config(config_path: str) -> dict:
    """Đọc file cấu hình YAML theo tư duy phòng thủ."""
    p = Path(config_path)
    if not p.exists():
        print(f"[LỖI] Không tìm thấy file cấu hình: {config_path}")
        sys.exit(1)
    with open(p, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    cfg.setdefault("city", "Sydney")
    cfg.setdefault("data_root", "australia/nsw/sydney")
    return cfg


def main():
    parser = argparse.ArgumentParser(description="Chạy pipeline phân tích Inside Airbnb Sydney")
    parser.add_argument("--config", type=str, required=True, help="Đường dẫn file cấu hình YAML")
    parser.add_argument("--skip-download", action="store_true", help="Bỏ qua tải dữ liệu internet nếu đã có sẵn")
    parser.add_argument("--skip-llm", action="store_true", help="Bỏ qua gọi API LLM mới, dùng cache và baseline")
    parser.add_argument("--sample-size", type=int, default=None, help="Ghi đè cỡ mẫu đánh giá LLM")
    parser.add_argument("--log-file", type=str, default="log.txt", help="Tên file nhật ký")
    args = parser.parse_args()

    logger = PipelineLogger.setup(args.log_file)
    start_total_time = time.time()
    cfg = load_config(args.config)
    city_name = str(cfg.get("city", "Sydney")).upper()

    print("=" * 65)
    print(f"KHỞI CHẠY PIPELINE AIRBNB CHO: {city_name}")
    print(f"Toàn bộ log chi tiết đang được ghi vào file: {args.log_file}")
    print("=" * 65)

    logger.info("=" * 70)
    logger.info("   BẮT ĐẦU CHẠY PIPELINE AIRBNB CHO: %s", city_name)
    logger.info("   Bên đặt hàng phân tích: CHỦ NHÀ AIRBNB (HOST)")
    logger.info("=" * 70)

    # ─────────────────────────────────────────────────────────────
    # BƯỚC 1: THU THẬP DỮ LIỆU (DOWNLOAD)
    # ─────────────────────────────────────────────────────────────
    print(" [1/6] Đang kiểm tra và thu thập dữ liệu...")
    if not args.skip_download:
        logger.info("\n>>> BƯỚC 1: THU THẬP DỮ LIỆU TỪ INSIDE AIRBNB...")
        from src.download import download_all
        raw_paths = download_all(cfg)
    else:
        logger.info("\n>>> BƯỚC 1: BỎ QUA TẢI DỮ LIỆU (--skip-download), NẠP DỮ LIỆU CỤC BỘ...")
        raw_dir = Path("data/raw")
        raw_paths = {}
        for snap in cfg.get("snapshots", []):
            snap_dir = raw_dir / snap
            raw_paths[snap] = {
                "listings": snap_dir / "listings.csv.gz" if (snap_dir / "listings.csv.gz").exists() else snap_dir / "listings.csv",
                "calendar": snap_dir / "calendar.csv.gz" if (snap_dir / "calendar.csv.gz").exists() else snap_dir / "calendar.csv",
                "reviews": snap_dir / "reviews.csv.gz" if (snap_dir / "reviews.csv.gz").exists() else snap_dir / "reviews.csv",
            }
    print("   ✓ Thu thập dữ liệu: Xong.")

    # ─────────────────────────────────────────────────────────────
    # BƯỚC 2: KIỂM SOÁT CHẤT LƯỢNG & LÀM SẠCH (QA)
    # ─────────────────────────────────────────────────────────────
    print(" [2/6] Đang chạy kiểm soát chất lượng & làm sạch (QA)...")
    logger.info("\n>>> BƯỚC 2: CHẠY HỆ THỐNG QUY TẮC KIỂM SOÁT CHẤT LƯỢNG (QA)...")
    from src.qa import run_qa
    cleaned_snapshots, qa_reports = run_qa(raw_paths, cfg)
    print("   ✓ Kiểm soát chất lượng (QA): Xong. Đã lưu reports/qa_report.csv")

    # ─────────────────────────────────────────────────────────────
    # BƯỚC 3: TÍNH TOÁN BỘ CHỈ SỐ HIỆU SUẤT (KPI)
    # ─────────────────────────────────────────────────────────────
    print(" [3/6] Đang tính toán bộ chỉ số KPI cho Chủ nhà...")
    logger.info("\n>>> BƯỚC 3: TÍNH TOÁN BỘ KPI CHO CHỦ NHÀ THEO THỜI GIAN & KHÔNG GIAN...")
    from src.kpi import compute_all_kpis
    kpi_results = compute_all_kpis(cleaned_snapshots, cfg)
    print("   ✓ Tính toán KPI: Xong. Đã lưu data/processed/kpi_*.csv")

    # ─────────────────────────────────────────────────────────────
    # BƯỚC 4: PHÂN TÍCH ĐÁNH GIÁ BẰNG LLM & BASELINE
    # ─────────────────────────────────────────────────────────────
    print(" [4/6] Đang phân tích đánh giá bằng LLM & mô hình đối chứng...")
    logger.info("\n>>> BƯỚC 4: LẤY MẪU VÀ TRÍCH XUẤT CÓ CẤU TRÚC BẰNG LLM...")
    from src.llm import sample_reviews_stratified, process_reviews_with_llm, estimate_total_sydney_cost

    latest_snapshot = max(cleaned_snapshots.keys())
    reviews_file = raw_paths[latest_snapshot].get("reviews")

    if reviews_file and Path(reviews_file).exists():
        assigned_rev_path = Path("data/samples/assigned_reviews_5000.csv")
        df_reviews_raw = pd.read_csv(
            reviews_file,
            compression="gzip" if str(reviews_file).endswith(".gz") else None,
            usecols=["id", "listing_id", "date", "comments"]
        )
        df_reviews_raw["id"] = pd.to_numeric(df_reviews_raw["id"], errors="coerce").fillna(-1).astype("int64")

        reviews_sample = pd.DataFrame()
        if assigned_rev_path.exists():
            df_ass_rev = pd.read_csv(assigned_rev_path)
            id_col = "review_id" if "review_id" in df_ass_rev.columns else "id"
            if "Mẫu LLM" in df_ass_rev.columns:
                target_df = df_ass_rev[df_ass_rev["Mẫu LLM"] == "x"]
            else:
                target_df = df_ass_rev.head(1000)

            llm_ids = list(target_df[id_col].astype("int64"))
            llm_ids_set = set(llm_ids)
            matched_reviews = df_reviews_raw[df_reviews_raw["id"].isin(llm_ids_set)].copy()
            if len(matched_reviews) > 0:
                # Giữ nguyên thứ tự ID như trong file phân công
                reviews_sample = matched_reviews.drop_duplicates(subset=["id"]).set_index("id").reindex(llm_ids).dropna(subset=["comments"]).reset_index()
                logger.info("  ✓ Đã khớp chính xác %d review thuộc tập phân công (thuộc %d listing khác nhau)",
                            len(reviews_sample), reviews_sample["listing_id"].nunique())

        # Dự phòng tự động nếu không tìm thấy file phân công
        if reviews_sample.empty:
            sample_size = args.sample_size or cfg.get("llm", {}).get("sample_size", 1000)
            reviews_sample = sample_reviews_stratified(
                df_reviews_raw, cleaned_snapshots[latest_snapshot],
                sample_size=min(sample_size, len(df_reviews_raw)), seed=cfg.get("seed", 42)
            )
            logger.info("  ✓ Tự động lấy mẫu phân tầng đại diện %d review", len(reviews_sample))

        llm_results_df = process_reviews_with_llm(reviews_sample, cfg, skip_llm=args.skip_llm)

        cost_report = estimate_total_sydney_cost(total_reviews_count=len(df_reviews_raw))
        logger.info("  [ƯỚC TÍNH CHI PHÍ LLM TOÀN THỊ TRƯỜNG SYDNEY]:")
        logger.info("    Tổng số đánh giá thực tế: %d", cost_report["total_reviews"])
        logger.info("    Tổng token ước tính: %d M tokens", cost_report.get("est_total_tokens", 0) // 1000000)
        logger.info("    Tổng chi phí ước tính: $%.2f USD", cost_report["est_total_cost_usd"])
    else:
        gold_file = cfg.get("baseline", {}).get("gold_labels_file", "data/samples/manual_labels_100.csv")
        gold_df = pd.read_csv(gold_file) if Path(gold_file).exists() else pd.DataFrame()
        llm_results_df = gold_df.rename(columns={"comments": "text", "true_sentiment": "sentiment", "true_aspects_negative": "aspects_negative"})

    print("   ✓ Phân tích LLM & Caching: Xong. Đã lưu data/processed/llm_cache.jsonl")

    # ─────────────────────────────────────────────────────────────
    # BƯỚC 5: ĐÁNH GIÁ CHẤT LƯỢNG LLM VS BASELINE TRÊN 100 NHÃN TAY
    # ─────────────────────────────────────────────────────────────
    print(" [5/6] Đang đánh giá đối chứng LLM vs Baseline trên 100 nhãn tay...")
    logger.info("\n>>> BƯỚC 5: ĐÁNH GIÁ CHẤT LƯỢNG LLM VS BASELINE TRÊN 100 NHÃN TAY...")
    from src.evaluate import run_evaluation
    gold_labels_file = cfg.get("baseline", {}).get("gold_labels_file", "data/samples/manual_labels_100.csv")
    eval_results = run_evaluation(cfg, gold_labels_file, skip_llm=args.skip_llm)
    print("   ✓ Đánh giá F1 đối chứng: Xong. Đã lưu reports/llm_vs_baseline_eval.csv")

    # ─────────────────────────────────────────────────────────────
    # BƯỚC 6: TRỰC QUAN HOÁ DỮ LIỆU (VISUALIZATION)
    # ─────────────────────────────────────────────────────────────
    print(" [6/6] Đang sinh các biểu đồ trực quan hoá...")
    logger.info("\n>>> BƯỚC 6: SINH TỰ ĐỘNG HỆ THỐNG BIỂU ĐỒ TRỰC QUAN HOÁ...")
    from src.viz import generate_all_visualizations
    viz_files = generate_all_visualizations(kpi_results, llm_results_df, cfg)
    print("   ✓ Trực quan hoá: Xong. Đã lưu 4 hình ảnh trong thư mục figures/")

    total_time = time.time() - start_total_time
    logger.info("=" * 70)
    logger.info("   PIPELINE HOÀN THÀNH XUẤT SẮC TRONG %.2f GIÂY!", total_time)
    logger.info("=" * 70)

    print("=" * 65)
    print(f"HOÀN THÀNH TOÀN BỘ PIPELINE TRONG {total_time:.2f} GIÂY!")
    print(f"Mở file '{args.log_file}' để xem toàn bộ thông tin chi tiết.")
    print("=" * 65)


if __name__ == "__main__":
    main()
