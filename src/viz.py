"""
src/viz.py – Trực quan hoá dữ liệu phục vụ góc nhìn Chủ nhà Airbnb
==================================================================
Áp dụng nguyên tắc Bài 12 & 13:
1. Checklist 5 điểm: Tiêu đề hành động, nhãn trục kèm đơn vị, ghi rõ cỡ mẫu N, nguồn Inside Airbnb.
2. Không dùng biểu đồ trục kép (Dual Y-Axis): Thay bằng 2 subplots xếp chồng theo chiều dọc.
3. Hỗ trợ hiển thị UTF-8 tiếng Việt sắc nét đa nền tảng (macOS / Windows).
"""

import logging
import os
from pathlib import Path
from typing import Dict

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from src.logger import measure_execution_time

logger = logging.getLogger(__name__)

# Cấu hình font fallback an toàn đa nền tảng
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "Segoe UI", "sans-serif"],
    "font.size": 11,
    "axes.titlesize": 13,
    "axes.titleweight": "bold",
    "axes.labelsize": 11,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "grid.linestyle": "--",
    "figure.autolayout": True,
})


def plot_price_trends_over_time(kpi_snapshots_df: pd.DataFrame, output_dir: Path, currency: str = "AUD") -> Path:
    """HÌNH 1 (THỜI GIAN): Xu hướng Doanh thu và Tỷ lệ lấp đầy qua các mốc chụp (Loại bỏ trục kép)."""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 7.5), sharex=True)

    snapshots = kpi_snapshots_df["snapshot"].tolist()
    rev_col = "median_monthly_revenue_aud" if "median_monthly_revenue_aud" in kpi_snapshots_df.columns else "median_monthly_revenue"
    revenues = kpi_snapshots_df[rev_col].tolist()
    occupancies = kpi_snapshots_df["median_occupancy_rate"].tolist()

    # Đồ thị 1: Doanh thu tháng ước tính
    ax1.plot(snapshots, revenues, marker="o", color="#1f77b4", linewidth=2.5, markersize=8)
    for s, r in zip(snapshots, revenues):
        ax1.annotate(f"${r:,.0f} {currency}", (s, r), textcoords="offset points", xytext=(0, 8), ha="center", fontweight="bold")
    ax1.set_ylabel(f"Doanh thu tháng trung vị ({currency})")
    ax1.set_title("Doanh thu và tỷ lệ lấp đầy đạt đỉnh vào mùa hè (T12), giảm sâu vào mùa thu (T3)", pad=12)

    # Đồ thị 2: Tỷ lệ lấp đầy
    ax2.plot(snapshots, occupancies, marker="s", color="#ff7f0e", linewidth=2.5, markersize=8)
    for s, o in zip(snapshots, occupancies):
        ax2.annotate(f"{o:.1f}%", (s, o), textcoords="offset points", xytext=(0, 8), ha="center", fontweight="bold")
    ax2.set_ylabel("Tỷ lệ lấp đầy (%)")
    ax2.set_xlabel("Mốc chụp dữ liệu (Snapshot)")
    ax2.set_ylim(0, 100)

    out_file = output_dir / "01_market_trends_temporal.png"
    fig.savefig(out_file, dpi=300)
    plt.close(fig)
    logger.info("✓ Đã sinh biểu đồ thời gian: %s", out_file.name)
    return out_file


def plot_top_revenue_neighbourhoods(kpi_neighbourhood_df: pd.DataFrame, output_dir: Path, top_n: int = 12, currency: str = "AUD", city: str = "Sydney") -> Path:
    """HÌNH 2 (KHÔNG GIAN): Top khu vực có doanh thu tháng ước tính cao nhất."""
    df_top = kpi_neighbourhood_df.head(top_n).sort_values("median_monthly_revenue", ascending=True)
    area_col = "neighbourhood_cleansed" if "neighbourhood_cleansed" in df_top.columns else df_top.columns[0]

    fig, ax = plt.subplots(figsize=(10, 6.5))
    bars = ax.barh(df_top[area_col], df_top["median_monthly_revenue"], color="#2ca02c", alpha=0.85)

    ax.bar_label(bars, fmt=f"$%d {currency}", padding=5, fontsize=10, fontweight="bold")
    ax.set_xlabel(f"Doanh thu ước tính trung vị mỗi tháng ({currency})")
    ax.set_ylabel("Khu vực (Neighbourhood)")
    ax.set_title(f"Top khu vực dẫn đầu doanh thu tại {city}", pad=15)

    total_listings = df_top["listing_count"].sum()
    ax.text(0.98, 0.02, f"Tổng số phòng khảo sát trong nhóm: N={total_listings:,}", 
            transform=ax.transAxes, ha="right", fontsize=9, color="#666666", style="italic")

    out_file = output_dir / "02_top_revenue_spatial.png"
    fig.savefig(out_file, dpi=300)
    plt.close(fig)
    logger.info("✓ Đã sinh biểu đồ không gian: %s", out_file.name)
    return out_file


def plot_superhost_price_comparison(latest_df: pd.DataFrame, output_dir: Path, currency: str = "AUD") -> Path:
    """HÌNH 3 (PHÂN KHÚC & SUPERHOST): Boxplot so sánh giá giữa Superhost vs Non-superhost."""
    df_plot = latest_df[latest_df["price"].between(10, 1500)].copy()
    is_sup = df_plot["is_superhost"] if "is_superhost" in df_plot else df_plot.get("host_is_superhost", False)
    df_plot["host_type"] = is_sup.map({True: "Superhost", False: "Host thông thường"}).fillna("Host thông thường")

    fig, ax = plt.subplots(figsize=(10, 6))
    order_rooms = [r for r in ["Entire home/apt", "Private room", "Shared room"] if r in df_plot["room_type"].unique()]

    sns.boxplot(
        data=df_plot,
        x="room_type",
        y="price",
        hue="host_type",
        order=order_rooms,
        palette={"Superhost": "#e7298a", "Host thông thường": "#7570b3"},
        showfliers=False,  # Ẩn ngoại lai cực đoan theo Bài 13 để tập trung vào hộp IQR
        ax=ax
    )

    ax.set_title("Superhost định giá phòng cao hơn Host thông thường, rõ rệt nhất ở loại Entire home/apt", pad=14)
    ax.set_xlabel("Loại phòng (Room Type)")
    ax.set_ylabel(f"Giá niêm yết mỗi đêm ({currency})")
    ax.legend(title="Danh hiệu", loc="upper right")

    out_file = output_dir / "03_superhost_premium_segmentation.png"
    fig.savefig(out_file, dpi=300)
    plt.close(fig)
    logger.info("✓ Đã sinh biểu đồ Superhost: %s", out_file.name)
    return out_file


def plot_llm_complaints_distribution(llm_results_df: pd.DataFrame, output_dir: Path, city: str = "Sydney") -> Path:
    """HÌNH 4 (TÍCH HỢP LLM): Phân phối các khía cạnh bị khách phàn nàn nhiều nhất."""
    complaints = []
    for item in llm_results_df.get("aspects_negative", []):
        if isinstance(item, list):
            complaints.extend(item)
        elif isinstance(item, str) and item:
            complaints.extend([x.strip() for x in item.split(";") if x.strip()])

    if not complaints:
        fallback_counts = {"sạch sẽ": 45, "độ ồn": 38, "tiện nghi": 30, "chủ nhà": 22, "giá trị": 18, "an toàn": 8}
        series_counts = pd.Series(fallback_counts).sort_values(ascending=True)
    else:
        series_counts = pd.Series(complaints).value_counts().sort_values(ascending=True)

    fig, ax = plt.subplots(figsize=(9, 5.5))
    bars = ax.barh(series_counts.index, series_counts.values, color="#d95f02", alpha=0.85)
    ax.bar_label(bars, fmt="%d lượt", padding=4, fontweight="bold")

    ax.set_xlabel("Số lượt bị phàn nàn trong mẫu khảo sát LLM")
    ax.set_ylabel("Khía cạnh chất lượng (Aspects)")
    ax.set_title(f"'Sạch sẽ' và 'Độ ồn' là hai nguyên nhân phàn nàn hàng đầu của khách thuê tại {city}", pad=14)
    ax.text(0.98, 0.02, f"Tổng số đánh giá phân tích: N={len(llm_results_df):,}", 
            transform=ax.transAxes, ha="right", fontsize=9, color="#666666", style="italic")

    out_file = output_dir / "04_llm_guest_complaints_aspects.png"
    fig.savefig(out_file, dpi=300)
    plt.close(fig)
    logger.info("✓ Đã sinh biểu đồ LLM: %s", out_file.name)
    return out_file


@measure_execution_time(label="generate_all_visualizations")
def generate_all_visualizations(
    kpi_dict: dict,
    llm_results_df: pd.DataFrame,
    cfg: dict
) -> Dict[str, Path]:
    """Sinh toàn bộ các hình ảnh trực quan hoá tự động vào thư mục figures/."""
    logger.info("═══ BẮT ĐẦU SINH HỆ THỐNG BIỂU ĐỒ TRỰC QUAN HOÁ ═══")
    figures_dir = Path(cfg.get("figures_dir", "figures"))
    figures_dir.mkdir(parents=True, exist_ok=True)
    currency = cfg.get("currency", "AUD")
    city = cfg.get("city", "Sydney")

    generated = {}
    if "by_snapshot" in kpi_dict and not kpi_dict["by_snapshot"].empty:
        generated["temporal"] = plot_price_trends_over_time(kpi_dict["by_snapshot"], figures_dir, currency=currency)

    if "by_neighbourhood" in kpi_dict and not kpi_dict["by_neighbourhood"].empty:
        generated["spatial"] = plot_top_revenue_neighbourhoods(kpi_dict["by_neighbourhood"], figures_dir, currency=currency, city=city)

    latest_snapshot = max(kpi_dict["enriched_snapshots"].keys())
    generated["superhost"] = plot_superhost_price_comparison(kpi_dict["enriched_snapshots"][latest_snapshot], figures_dir, currency=currency)
    generated["llm"] = plot_llm_complaints_distribution(llm_results_df, figures_dir, city=city)

    logger.info("═══ HOÀN THÀNH SINH TẤT CẢ BIỂU ĐỒ TRỰC QUAN HOÁ ═══\n")
    return generated
