"""
src/qa.py – Pipeline Kiểm soát chất lượng & Làm sạch dữ liệu Airbnb
===================================================================
Nguyên lý thiết kế (Bài giảng 3, 5, 7, 10):
1. Vector hóa toàn diện (NumPy/Pandas str accessor): Xử lý nhanh, không lặp dòng.
2. Thiết kế dạng đường ống (Transformation Pipeline): Từng quy tắc độc lập, dễ kiểm thử.
3. Ưu tiên gắn cờ (_qa_flag): Bảo toàn thông tin, chỉ xóa khi vi phạm tính toàn vẹn (khóa chính, trùng lặp).
4. Chính sách neo giá mốc cuối (Latest Snapshot Price Policy): Đồng nhất giá giữa các mốc.
"""

import logging
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.logger import measure_execution_time

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════
# 1. PARSE & ÉP KIỂU DỮ LIỆU (COERCE DTYPES)
# ══════════════════════════════════════════════════════════════

def parse_price(series: pd.Series) -> pd.Series:
    """Chuyển chuỗi tiền tệ '$1,234.56' thành số thực float bằng Vectorized Regex (Bài 7)."""
    if pd.api.types.is_numeric_dtype(series):
        return series.astype(float)
    return (
        series.astype(str)
        .str.replace(r"[$,]", "", regex=True)
        .str.strip()
        .replace(["", "nan", "N/A", "None"], np.nan)
        .astype(float)
    )


def coerce_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    """Ép kiểu dữ liệu chuẩn xác cho các trường quan trọng (Bài 10)."""
    df = df.copy()
    if "price" in df:
        df["price"] = parse_price(df["price"])

    # Tỷ lệ phần trăm: '95%' -> 0.95
    for col in ["host_response_rate", "host_acceptance_rate"]:
        if col in df and not pd.api.types.is_numeric_dtype(df[col]):
            df[col] = (
                df[col].astype(str)
                .str.replace("%", "", regex=False)
                .replace(["N/A", "nan", ""], np.nan)
                .astype(float) / 100.0
            )

    # Boolean: 't'/'f' -> True/False
    bool_cols = ["host_is_superhost", "instant_bookable", "has_availability"]
    bool_map = {"t": True, "f": False, True: True, False: False, "True": True, "False": False}
    for col in [c for c in bool_cols if c in df]:
        if not pd.api.types.is_bool_dtype(df[col]):
            df[col] = df[col].map(bool_map)

    # Cột số
    num_cols = [
        "latitude", "longitude", "minimum_nights", "maximum_nights",
        "number_of_reviews", "availability_365", "reviews_per_month",
        "review_scores_rating", "review_scores_cleanliness", "bedrooms", "beds", "accommodates"
    ]
    for col in [c for c in num_cols if c in df]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


# ══════════════════════════════════════════════════════════════
# 2. HỆ THỐNG QUY TẮC QA ĐỘC LẬP (QA-01 ĐẾN QA-08)
# ══════════════════════════════════════════════════════════════

def _make_report(rule: str, condition: str, reason: str, action: str,
                 before: int, after: int, affected: int, snapshot: str = None) -> dict:
    """Tạo bản ghi báo cáo chuẩn hóa cho qa_report.csv."""
    rep = {
        "rule": rule, "condition": condition, "reason": reason, "action": action,
        "rows_before": before, "rows_after": after, "rows_affected": int(affected)
    }
    if snapshot:
        rep["snapshot"] = snapshot
    return rep


def rule_missing_key_columns(df: pd.DataFrame, cfg: dict) -> Tuple[pd.DataFrame, dict]:
    """QA-01: Xóa dòng thiếu khóa định danh bắt buộc (id, host_id)."""
    keys = [c for c in ["id", "host_id"] if c in df.columns]
    mask = df[keys].isna().any(axis=1)
    before = len(df)
    df_clean = df[~mask].copy()
    return df_clean, _make_report(
        "QA-01: Thiếu cột khoá định danh", f"NaN trong {keys}",
        "Không thể định danh listing nếu thiếu id/host_id", "XOÁ",
        before, len(df_clean), mask.sum()
    )


def rule_price_outliers(df: pd.DataFrame, cfg: dict) -> Tuple[pd.DataFrame, dict]:
    """QA-02: Gắn cờ giá ngoại lai (< min hoặc > max từ config)."""
    qa_cfg = cfg.get("qa", {})
    p_min, p_max = qa_cfg.get("price_min", 10), qa_cfg.get("price_max", 10000)
    mask = (df["price"] < p_min) | (df["price"] > p_max)
    df.loc[mask, "_qa_flag"] = df.loc[mask, "_qa_flag"].astype(str) + "|price_outlier"
    return df, _make_report(
        "QA-02: Giá ngoại lai", f"price < {p_min} hoặc > {p_max} {cfg.get('currency', 'AUD')}",
        "Giá quá thấp = lỗi nhập; quá cao = ngoại lai", "GẮN CỜ",
        len(df), len(df), mask.sum()
    )


def rule_minimum_nights_cap(df: pd.DataFrame, cfg: dict) -> Tuple[pd.DataFrame, dict]:
    """QA-03: Gắn cờ minimum_nights bất thường (> 365 ngày)."""
    cap = cfg.get("qa", {}).get("min_nights_cap", 365)
    mask = df["minimum_nights"] > cap if "minimum_nights" in df.columns else pd.Series(False, index=df.index)
    df.loc[mask, "_qa_flag"] = df.loc[mask, "_qa_flag"].astype(str) + "|high_min_nights"
    return df, _make_report(
        "QA-03: minimum_nights bất thường", f"minimum_nights > {cap}",
        "Listing có thể bị ẩn hoặc nhập sai", "GẮN CỜ",
        len(df), len(df), mask.sum()
    )


def rule_duplicates_within(df: pd.DataFrame, cfg: dict) -> Tuple[pd.DataFrame, dict]:
    """QA-04: Xóa trùng lặp trong cùng mốc chụp trên bộ khóa (id, last_scraped)."""
    keys = [c for c in cfg.get("qa", {}).get("dedupe_keys", ["id", "last_scraped"]) if c in df.columns]
    before = len(df)
    mask = df.duplicated(subset=keys, keep="first") if keys else pd.Series(False, index=df.index)
    df_clean = df[~mask].copy()
    return df_clean, _make_report(
        "QA-04: Trùng lặp trong mốc", f"duplicated({keys})",
        "Cùng bản ghi xuất hiện nhiều lần → giữ 1", "XOÁ",
        before, len(df_clean), mask.sum()
    )


def rule_duplicates_across(listings_all: Dict[str, pd.DataFrame], cfg: dict) -> Tuple[None, dict]:
    """QA-05: Ghi nhận số lượng ID tồn tại xuyên suốt nhiều mốc chụp."""
    all_ids: Dict[int, int] = {}
    total_rows = sum(len(d) for d in listings_all.values())
    for d in listings_all.values():
        for lid in d["id"].unique():
            all_ids[lid] = all_ids.get(lid, 0) + 1
    multi_cnt = sum(1 for v in all_ids.values() if v > 1)
    return None, _make_report(
        "QA-05: Trùng ID giữa các mốc", "Cùng id xuất hiện ở ≥2 mốc",
        "Bình thường – listing tồn tại qua nhiều quý", "GHI NHẬN (không xoá)",
        total_rows, total_rows, multi_cnt, snapshot="all"
    )


def rule_category_validation(df: pd.DataFrame, cfg: dict) -> Tuple[pd.DataFrame, dict]:
    """QA-06: Kiểm tra hợp lệ danh mục loại phòng (room_type)."""
    valid = {"Entire home/apt", "Private room", "Shared room", "Hotel room"}
    mask = ~df["room_type"].isin(valid) if "room_type" in df.columns else pd.Series(False, index=df.index)
    df.loc[mask, "_qa_flag"] = df.loc[mask, "_qa_flag"].astype(str) + "|invalid_room_type"
    return df, _make_report(
        "QA-06: Danh mục room_type lệch", f"room_type ∉ {valid}",
        "Giá trị không nằm trong 4 loại chính thức", "GẮN CỜ",
        len(df), len(df), mask.sum()
    )


def rule_missing_stats(df: pd.DataFrame, cfg: dict) -> Tuple[pd.DataFrame, dict]:
    """QA-07: Thống kê tỷ lệ thiếu dữ liệu trên các cột trọng yếu."""
    cols = [c for c in ["price", "review_scores_rating", "bedrooms", "beds", "host_response_rate", "reviews_per_month"] if c in df.columns]
    missing = df[cols].isna().sum()
    details = "; ".join(f"{c}: {(missing[c] / len(df) * 100):.1f}%" for c in cols if missing[c] > 0)
    return df, _make_report(
        "QA-07: Thống kê tỷ lệ thiếu", "isna() trên các cột quan trọng",
        "Ghi nhận để quyết định chiến lược điền giá trị", f"GHI NHẬN: {details}",
        len(df), len(df), missing.sum()
    )


def rule_impute_missing(df: pd.DataFrame, cfg: dict) -> Tuple[pd.DataFrame, dict]:
    """QA-08: Điền giá trị thiếu bằng trung vị (median) theo nhóm room_type (Bài 10)."""
    cols = [c for c in ["bedrooms", "beds", "review_scores_rating", "reviews_per_month"] if c in df.columns]
    total_filled = 0
    for col in cols:
        na_before = df[col].isna().sum()
        if "room_type" in df.columns:
            df[col] = df.groupby("room_type", observed=True)[col].transform(lambda s: s.fillna(s.median()))
        df[col] = df[col].fillna(df[col].median())
        total_filled += (na_before - df[col].isna().sum())
    return df, _make_report(
        "QA-08: Điền giá trị thiếu (median theo room_type)", "NaN trong cột số quan trọng",
        "Median theo nhóm chính xác hơn mean toàn bộ", "ĐIỀN GIÁ TRỊ",
        len(df), len(df), total_filled
    )


# ══════════════════════════════════════════════════════════════
# 3. CHÍNH SÁCH NEO GIÁ MỐC CUỐI & THỰC THI PIPELINE
# ══════════════════════════════════════════════════════════════

def clean_listings(df: pd.DataFrame, cfg: dict) -> Tuple[pd.DataFrame, List[dict]]:
    """Chạy toàn bộ pipeline QA trên DataFrame của 1 mốc chụp."""
    df["_qa_flag"] = ""
    df = coerce_dtypes(df)

    rules = [
        rule_missing_key_columns,
        rule_duplicates_within,
        rule_price_outliers,
        rule_minimum_nights_cap,
        rule_category_validation,
        rule_missing_stats,
        rule_impute_missing,
    ]
    reports = []
    for rule_fn in rules:
        df, rep = rule_fn(df, cfg)
        if rep:
            reports.append(rep)
    return df, reports


def apply_latest_snapshot_price_policy(all_dfs: Dict[str, pd.DataFrame], cfg: dict) -> List[dict]:
    """QA-00: Ánh xạ giá từ mốc chụp cuối cùng sang toàn bộ các mốc trước theo ID."""
    latest_snapshot = max(all_dfs.keys())
    ref_df = all_dfs[latest_snapshot]

    # Tính median dự phòng theo nhóm [khu vực, loại phòng] từ mốc cuối
    group_medians = ref_df.groupby(["neighbourhood_cleansed", "room_type"], observed=True)["price"].median().to_dict()
    global_median = ref_df["price"].median()

    # Điền giá thiếu cho chính mốc cuối nếu có
    ref_keys = list(zip(ref_df["neighbourhood_cleansed"], ref_df["room_type"]))
    ref_df["price"] = ref_df["price"].fillna(pd.Series([group_medians.get(k, global_median) for k in ref_keys], index=ref_df.index))

    id_to_price = ref_df.set_index("id")["price"].dropna().to_dict()
    reports = []

    for snap, df in all_dfs.items():
        if snap == latest_snapshot:
            continue
        orig_count = df["price"].notna().sum()
        snap_keys = list(zip(df["neighbourhood_cleansed"], df["room_type"]))
        fallback_prices = pd.Series([group_medians.get(k, global_median) for k in snap_keys], index=df.index)

        # Ghi đè 100% bằng giá mốc cuối theo ID, fallback bằng median nhóm
        df["price"] = df["id"].map(id_to_price).fillna(fallback_prices)
        reports.append({
            "rule": f"QA-00: Thay thế toàn bộ giá bằng giá mốc cuối cùng ({latest_snapshot})",
            "condition": f"Mốc {snap} có {orig_count} phòng có giá gốc -> Thay thế 100% bằng giá mốc {latest_snapshot}",
            "reason": "Chính sách phân tích: chỉ dùng giá của mốc cuối cùng, xoá bỏ giá các mốc trước để đồng nhất thị trường",
            "action": "THAY THẾ TOÀN BỘ BẰNG GIÁ MỐC CUỐI",
            "rows_before": len(df), "rows_after": len(df), "rows_affected": len(df),
            "snapshot": snap
        })
    return reports


def _validate_assigned_1000(df: pd.DataFrame, snapshot: str) -> None:
    """Kiểm tra hợp lệ 1.000 listing theo đúng 4 tiêu chuẩn đề bài."""
    n_entire = (df["room_type"] == "Entire home/apt").sum() if "room_type" in df.columns else 0
    n_private = (df["room_type"] == "Private room").sum() if "room_type" in df.columns else 0
    n_no_rev = (df["number_of_reviews"] == 0).sum() if "number_of_reviews" in df.columns else 0
    logger.info("  [KIỂM SOÁT 1.000 ID - MỐC %s]: %d Entire home/apt, %d Private room, %d review=0",
                snapshot, n_entire, n_private, n_no_rev)


@measure_execution_time(label="run_qa")
def run_qa(raw_paths: dict, cfg: dict) -> Tuple[Dict[str, pd.DataFrame], List[dict]]:
    """Thực thi toàn bộ quy trình QA cho tất cả các mốc chụp."""
    logger.info("═══ BẮT ĐẦU QA PIPELINE ═══")

    assigned_file = Path("data/samples/assigned_listings_1000.csv")
    assigned_df = pd.read_csv(assigned_file) if assigned_file.exists() else None
    assigned_ids = set(assigned_df["listing_id"].astype(int)) if assigned_df is not None else None
    area_map = dict(zip(assigned_df["listing_id"].astype(int), assigned_df["analysis_area"])) if assigned_df is not None else {}

    needed_cols = {
        "id", "name", "host_id", "host_is_superhost", "host_response_rate", "host_acceptance_rate",
        "neighbourhood_cleansed", "latitude", "longitude", "room_type", "accommodates", "bedrooms",
        "beds", "price", "minimum_nights", "maximum_nights", "availability_365", "number_of_reviews",
        "review_scores_rating", "review_scores_cleanliness", "reviews_per_month", "instant_bookable", "has_availability"
    }

    all_raw: Dict[str, pd.DataFrame] = {}
    for snapshot, paths in raw_paths.items():
        listings_path = paths["listings"]
        df = pd.read_csv(
            listings_path,
            usecols=lambda c: c in needed_cols,
            compression="gzip" if str(listings_path).endswith(".gz") else None
        )
        df["_snapshot"] = snapshot

        # Lọc đúng 1.000 ID phân công & gán mã vùng analysis_area (A01 - A08) nếu khớp
        if assigned_ids:
            df["id"] = pd.to_numeric(df["id"], errors="coerce").fillna(-1).astype(int)
            matched = df[df["id"].isin(assigned_ids)].copy()
            if len(matched) > 0:
                df = matched
                df["analysis_area"] = df["id"].map(area_map)
                _validate_assigned_1000(df, snapshot)
            else:
                logger.info("  [QA - MỐC %s]: Không có ID phân công nào khớp, giữ nguyên toàn bộ dữ liệu (%d listings)", snapshot, len(df))

        all_raw[snapshot] = coerce_dtypes(df)

    # 1. Áp dụng chính sách giá mốc cuối
    all_reports = apply_latest_snapshot_price_policy(all_raw, cfg)

    # 2. Chạy quy tắc QA trên từng mốc
    all_clean: Dict[str, pd.DataFrame] = {}
    for snapshot, df in all_raw.items():
        df_clean, reports = clean_listings(df, cfg)
        for r in reports:
            r["snapshot"] = snapshot
        all_reports.extend(reports)
        all_clean[snapshot] = df_clean

    # 3. Ghi nhận trùng ID xuyên mốc (QA-05)
    _, cross_rep = rule_duplicates_across(all_clean, cfg)
    all_reports.append(cross_rep)

    # 4. Xuất báo cáo reports/qa_report.csv
    report_dir = Path(cfg.get("reports_dir", "reports"))
    report_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(all_reports).to_csv(report_dir / "qa_report.csv", index=False)

    # 5. Xuất dữ liệu sạch data/processed/listings_clean_{snapshot}.csv
    processed_dir = Path("data/processed")
    processed_dir.mkdir(parents=True, exist_ok=True)
    analysis_cols = [
        "id", "name", "host_id", "host_is_superhost", "host_response_rate",
        "neighbourhood_cleansed", "analysis_area", "latitude", "longitude", "room_type",
        "accommodates", "bedrooms", "beds", "price", "minimum_nights",
        "maximum_nights", "availability_365", "number_of_reviews",
        "review_scores_rating", "review_scores_cleanliness", "reviews_per_month",
        "_qa_flag", "_snapshot"
    ]
    for snapshot, df_clean in all_clean.items():
        cols = [c for c in analysis_cols if c in df_clean.columns]
        df_clean[cols].to_csv(processed_dir / f"listings_clean_{snapshot}.csv", index=False)

    logger.info("═══ HOÀN TẤT QA PIPELINE (Đã lưu dữ liệu sạch & qa_report.csv) ═══")
    return all_clean, all_reports
