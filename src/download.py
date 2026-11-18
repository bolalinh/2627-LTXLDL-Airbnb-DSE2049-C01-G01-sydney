"""
src/download.py – Tự động tải dữ liệu Inside Airbnb (Chuẩn Bài 2 & Bài 6)
========================================================================
Nguyên tắc:
1. Đảm bảo tính tái lập (Reproducibility): Dựng URL tự động từ config.
2. Tiết kiệm băng thông (Idempotent): Kiểm tra file tồn tại trước khi tải.
3. Tối ưu I/O: Chỉ tải listings, reviews và GeoJSON, loại bỏ calendar không dùng đến.
"""

import logging
import ssl
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

import certifi
import pandas as pd
import requests

from src.logger import measure_execution_time

logger = logging.getLogger(__name__)

BASE_URL = "https://data.insideairbnb.com"

DATA_FILES = [
    ("data/listings.csv.gz", "listings"),
    ("data/calendar.csv.gz", "calendar"),
    ("data/reviews.csv.gz", "reviews"),
]
GEO_FILE = ("visualisations/neighbourhoods.geojson", "neighbourhoods")

REQUIRED_KEYS = {
    "listings": ["id", "name", "host_id", "neighbourhood_cleansed", "latitude", "longitude", "price"],
    "calendar": ["listing_id", "date", "available"],
    "reviews": ["listing_id", "id", "date", "comments"],
}


def _verify_columns(file_path: Path, table_name: str) -> bool:
    """Kiểm tra cột khoá có tồn tại trong file (đọc 5 dòng đầu để tối ưu tốc độ & RAM)."""
    if table_name not in REQUIRED_KEYS or not file_path.exists():
        return True
    try:
        df_head = pd.read_csv(file_path, nrows=5, compression="gzip" if str(file_path).endswith(".gz") else None)
        missing = [c for c in REQUIRED_KEYS[table_name] if c not in df_head.columns]
        if missing:
            logger.warning("  ⚠ %s thiếu cột khoá: %s", file_path.name, missing)
            return False
        logger.info("  ✓ %s: đủ %d cột khoá chuẩn", file_path.name, len(REQUIRED_KEYS[table_name]))
        return True
    except Exception as e:
        logger.warning("  ⚠ Không đọc được header %s: %s", file_path.name, e)
        return False


def _build_url(data_root: str, snapshot: str, file_path: str) -> str:
    """Tạo URL tải từ Inside Airbnb."""
    return f"{BASE_URL}/{data_root}/{snapshot}/{file_path}"


def _download_one(url: str, dest: Path) -> Path:
    """Tải một file bằng requests stream kết hợp certifi; bỏ qua nếu đã có sẵn."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 1024:
        logger.info("  ✓ Đã có sẵn: %s (%.1f MB)", dest.name, dest.stat().st_size / (1024 * 1024))
        return dest

    logger.info("  ↓ Đang tải: %s", url)
    try:
        resp = requests.get(url, stream=True, timeout=60, verify=certifi.where())
        resp.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)
        size_mb = dest.stat().st_size / (1024 * 1024)
        logger.info("  ✓ Đã tải xong: %s (%.1f MB)", dest.name, size_mb)
    except Exception as e:
        logger.warning("  ⚠ Requests gặp lỗi (%s), chuyển sang fallback urllib...", e)
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            with urlopen(url, context=ctx, timeout=60) as u_in, open(dest, "wb") as f_out:
                f_out.write(u_in.read())
            size_mb = dest.stat().st_size / (1024 * 1024)
            logger.info("  ✓ Đã tải xong (fallback): %s (%.1f MB)", dest.name, size_mb)
        except Exception as e2:
            logger.error("  ✗ Lỗi không thể tải %s: %s", url, e2)
            if dest.exists():
                dest.unlink()
            raise e2
    return dest


def download_snapshot(data_root: str, snapshot: str, raw_dir: Path) -> dict:
    """Tải dữ liệu cho 1 mốc chụp."""
    snapshot_dir = raw_dir / snapshot
    paths = {}
    logger.info("─── Mốc chụp: %s ───", snapshot)

    for file_path, table_name in DATA_FILES:
        url = _build_url(data_root, snapshot, file_path)
        dest = snapshot_dir / file_path.split("/")[-1]
        _download_one(url, dest)
        _verify_columns(dest, table_name)
        paths[table_name] = dest

    # GeoJSON tĩnh chỉ cần tải 1 lần cho toàn bộ dự án
    geo_url = _build_url(data_root, snapshot, GEO_FILE[0])
    geo_dest = raw_dir / "neighbourhoods.geojson"
    if not geo_dest.exists():
        _download_one(geo_url, geo_dest)
    paths["neighbourhoods"] = geo_dest

    return paths


@measure_execution_time(label="download_all")
def download_all(cfg: dict) -> dict:
    """Tải toàn bộ dữ liệu cho tất cả các mốc chụp trong cấu hình."""
    data_root = cfg["data_root"]
    raw_dir = Path("data/raw")
    all_paths = {}

    city_name = cfg.get("city", "Sydney").upper()
    logger.info("═══ BẮT ĐẦU THU THẬP DỮ LIỆU: %s ═══", city_name)
    for snapshot in cfg["snapshots"]:
        all_paths[snapshot] = download_snapshot(data_root, snapshot, raw_dir)

    logger.info("═══ HOÀN TẤT THU THẬP DỮ LIỆU ═══\n")
    return all_paths


if __name__ == "__main__":
    import yaml
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
    with open("configs/sydney.yaml", "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    download_all(cfg)
