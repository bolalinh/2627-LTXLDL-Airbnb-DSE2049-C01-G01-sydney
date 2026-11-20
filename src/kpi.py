"""
src/kpi.py – Tính toán bộ chỉ số hiệu suất chính (KPIs) cho Chủ nhà Airbnb
==========================================================================
Nguyên lý thiết kế (Bài 3, 5, 10):
1. Thống kê vững: Dùng Median thay vì Mean do phân phối giá bị lệch phải rất mạnh.
2. Occupancy Rate: Ước tính từ availability_365: (365 - availability_365) / 365.
3. Doanh thu tháng: price * 30 * occupancy_rate.
4. Thặng dư Superhost: Đo lường mức chênh lệch giá giữa Superhost vs Host thông thường.
"""

import logging
from pathlib import Path
import numpy as np
import pandas as pd

from src.logger import measure_execution_time

logger = logging.getLogger(__name__)


def calculate_listing_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Bổ sung các cột chỉ số phái sinh cấp dòng (row-level metrics)."""
    df = df.copy()

    # 1. Tỷ lệ lấp đầy ước tính (Occupancy Rate) trong đoạn [0, 1]
    if "availability_365" in df.columns:
        df["occupancy_rate"] = (1.0 - (df["availability_365"].clip(0, 365) / 365.0)).clip(0.0, 1.0)
    else:
        df["occupancy_rate"] = np.nan

    # 2. Doanh thu ước tính mỗi tháng (AUD)
    if "price" in df.columns and "occupancy_rate" in df.columns:
        df["estimated_monthly_revenue"] = df["price"] * 30.0 * df["occupancy_rate"]
    else:
        df["estimated_monthly_revenue"] = np.nan

    # 3. Chuẩn hóa cờ Superhost thành boolean
    if "is_superhost" in df.columns:
        pass
    elif "host_is_superhost" in df.columns:
        df["is_superhost"] = df["host_is_superhost"].fillna(False).astype(bool)
    else:
        df["is_superhost"] = False

    return df


def compute_host_kpis_overall(df: pd.DataFrame, snapshot_label: str = "all") -> dict:
    """Tính các KPI toàn thị trường phục vụ định giá và theo dõi mùa vụ."""
    def _v(series_name, func, scale=1.0):
        if series_name in df.columns and not df[series_name].dropna().empty:
            return round(float(func(df[series_name]) * scale), 2)
        return np.nan

    kpis = {
        "snapshot": snapshot_label,
        "total_active_listings": int(len(df)),
        "median_price_aud": _v("price", np.median),
        "mean_price_aud": _v("price", np.mean),
        "median_occupancy_rate": _v("occupancy_rate", np.median, scale=100.0),
        "mean_occupancy_rate": _v("occupancy_rate", np.mean, scale=100.0),
        "median_monthly_revenue_aud": _v("estimated_monthly_revenue", np.median),
        "superhost_percentage": _v("is_superhost", np.mean, scale=100.0),
        "avg_rating_score": _v("review_scores_rating", np.mean),
        "avg_cleanliness_score": _v("review_scores_cleanliness", np.mean),
    }

    # Superhost Price Premium (%): Tương quan định giá (Descriptive Correlation)
    # V07: Tính cả thặng dư chung và thặng dư kiểm soát theo từng loại phòng (Entire home vs Private room)
    if "is_superhost" in df.columns and "price" in df.columns:
        p_sup = df[df["is_superhost"]]["price"].median()
        p_norm = df[~df["is_superhost"]]["price"].median()
        kpis["superhost_median_price"] = round(float(p_sup), 2)
        kpis["non_superhost_median_price"] = round(float(p_norm), 2)
        kpis["superhost_price_premium_pct"] = round(float(((p_sup - p_norm) / p_norm) * 100), 2) if p_norm > 0 else 0.0

        # Kiểm soát theo phân khúc Entire home/apt
        df_entire = df[df["room_type"] == "Entire home/apt"]
        if not df_entire.empty:
            p_sup_ent = df_entire[df_entire["is_superhost"]]["price"].median()
            p_norm_ent = df_entire[~df_entire["is_superhost"]]["price"].median()
            kpis["superhost_premium_entire_pct"] = round(float(((p_sup_ent - p_norm_ent) / p_norm_ent) * 100), 2) if p_norm_ent > 0 else 0.0

        # Kiểm soát theo phân khúc Private room
        df_priv = df[df["room_type"] == "Private room"]
        if not df_priv.empty:
            p_sup_priv = df_priv[df_priv["is_superhost"]]["price"].median()
            p_norm_priv = df_priv[~df_priv["is_superhost"]]["price"].median()
            kpis["superhost_premium_private_pct"] = round(float(((p_sup_priv - p_norm_priv) / p_norm_priv) * 100), 2) if p_norm_priv > 0 else 0.0

    return kpis


def compute_neighbourhood_kpis(df: pd.DataFrame, area_col: str = "neighbourhood_cleansed") -> pd.DataFrame:
    """Tính KPI theo từng khu vực tại Sydney, sắp xếp theo doanh thu giảm dần."""
    if area_col not in df.columns:
        raise ValueError(f"Không tìm thấy cột phân vùng {area_col}")

    grouped = df.groupby(area_col, observed=True).agg(
        listing_count=("id", "count"),
        median_price=("price", lambda s: round(float(s.median()), 2)),
        mean_price=("price", lambda s: round(float(s.mean()), 2)),
        median_occupancy_pct=("occupancy_rate", lambda s: round(float(s.median() * 100), 2)),
        mean_occupancy_pct=("occupancy_rate", lambda s: round(float(s.mean() * 100), 2)),
        median_monthly_revenue=("estimated_monthly_revenue", lambda s: round(float(s.median()), 2)),
        superhost_pct=("is_superhost", lambda s: round(float(s.mean() * 100), 2)),
        avg_rating=("review_scores_rating", lambda s: round(float(s.mean()), 2)),
        avg_review_count=("number_of_reviews", lambda s: round(float(s.mean()), 2)),
    ).reset_index()

    return grouped.sort_values(by="median_monthly_revenue", ascending=False)


def compute_room_type_kpis(df: pd.DataFrame) -> pd.DataFrame:
    """Tính KPI theo từng loại phòng (Entire home vs Private room)."""
    if "room_type" not in df.columns:
        return pd.DataFrame()

    grouped = df.groupby("room_type", observed=True).agg(
        listing_count=("id", "count"),
        median_price=("price", lambda s: round(float(s.median()), 2)),
        median_occupancy_pct=("occupancy_rate", lambda s: round(float(s.median() * 100), 2)),
        median_revenue=("estimated_monthly_revenue", lambda s: round(float(s.median()), 2)),
        superhost_pct=("is_superhost", lambda s: round(float(s.mean() * 100), 2)),
        avg_rating=("review_scores_rating", lambda s: round(float(s.mean()), 2)),
    ).reset_index()

    return grouped.sort_values(by="median_revenue", ascending=False)


@measure_execution_time(label="compute_all_kpis")
def compute_all_kpis(cleaned_snapshots: dict, cfg: dict) -> dict:
    """Điều phối tính toàn bộ KPI và xuất ra thư mục data/processed/."""
    logger.info("═══ BẮT ĐẦU TÍNH TOÁN BỘ KPI CHO CHỦ NHÀ ═══")
    processed_dir = Path("data/processed")
    processed_dir.mkdir(parents=True, exist_ok=True)

    snapshot_kpis = []
    enriched_dfs = {}

    for snapshot, df in cleaned_snapshots.items():
        enriched = calculate_listing_metrics(df)
        enriched_dfs[snapshot] = enriched
        snapshot_kpis.append(compute_host_kpis_overall(enriched, snapshot_label=snapshot))

    df_snapshot_kpis = pd.DataFrame(snapshot_kpis)
    df_snapshot_kpis.to_csv(processed_dir / "kpi_by_snapshot.csv", index=False)
    logger.info("✓ Đã xuất: data/processed/kpi_by_snapshot.csv")

    latest_snapshot = max(cleaned_snapshots.keys())
    df_latest = enriched_dfs[latest_snapshot]

    # KPI theo khu vực & theo 8 phân vùng
    area_col = cfg.get("kpi", {}).get("area_col", "neighbourhood_cleansed")
    df_neighbourhood = compute_neighbourhood_kpis(df_latest, area_col=area_col)
    df_neighbourhood.to_csv(processed_dir / "kpi_by_neighbourhood.csv", index=False)
    logger.info("✓ Đã xuất: data/processed/kpi_by_neighbourhood.csv")

    if "analysis_area" in df_latest.columns and df_latest["analysis_area"].notna().any():
        df_analysis_area = compute_neighbourhood_kpis(df_latest, area_col="analysis_area")
        df_analysis_area.to_csv(processed_dir / "kpi_by_analysis_area.csv", index=False)
        logger.info("✓ Đã xuất: data/processed/kpi_by_analysis_area.csv")

    df_room_type = compute_room_type_kpis(df_latest)
    df_room_type.to_csv(processed_dir / "kpi_by_room_type.csv", index=False)
    logger.info("✓ Đã xuất: data/processed/kpi_by_room_type.csv")

    logger.info("═══ HOÀN THÀNH TÍNH KPI ═══\n")
    return {
        "by_snapshot": df_snapshot_kpis,
        "by_neighbourhood": df_neighbourhood,
        "by_room_type": df_room_type,
        "enriched_snapshots": enriched_dfs,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
    print("KPI module ready.")
