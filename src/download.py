"""
src/download.py : Tự động tải dữ liệu Inside Airbnb (Chuẩn Bài 2 & Bài 6)
4 Nguyên tắc :
  - 1/Đảm bảo tái lập --> Không tải bằng tay mà dựng URL = config tự động ----> Không nhầm nếu tải nhiều
  - 2/Tiết kiệm tài nguyên --> Kiển tra nếu có rồi thì không tải lại -----> Tiết kiệm thời gian và bộ nhớ tránh tải quá nhiều lần
  - 3/Tải nguyên tử an toàn --> Nếu trong quá trình tải gặp sự cố thì xoá cả file đang tải -----> Tránh tải file rác
  - 4/Kiểm chứng sơ qua --> Nếu file đã tải thiếu 1 số cột cần quan trọng -----> Báo để tránh lỗi sau

"""

import logging # thư viện ghi log
import ssl 
from pathlib import Path # thư viện sử lí đường dẫn
from urllib.error import URLError 
from urllib.request import urlopen 
# 2 thư viện phụ trợ của py phòng thủ dự phòng 

import certifi   # khắc phục lỗi ssl
import pandas as pd 
import requests

from src.logger import measure_execution_time

logger = logging.getLogger(__name__) # khởi tạo đối tượng log

# Khai báo hằng số và cấu hình khoá

BASE_URL = "https://data.insideairbnb.com" # Máy chủ lưu chữ toàn cầu của Inside Airbnb (Địa trỉ)

DATA_FILES = [
    ("data/listings.csv.gz", "listings"),
    ("data/calendar.csv.gz", "calendar"),
    ("data/reviews.csv.gz", "reviews"),
] # Bộ dữ liệu cần tải theo đề
GEO_FILE = ("visualisations/neighbourhoods.geojson", "neighbourhoods") 
# Bao gồm (đường dẫn , tên bảng)

REQUIRED_KEYS = {
    "listings": ["id", "name", "host_id", "neighbourhood_cleansed", "latitude", "longitude", "price"],
    "calendar": ["listing_id", "date", "available"],
    "reviews": ["listing_id", "id", "date", "comments"],
} # Danh sách các cột cần thiết để kiểm tra nhanh

'''
Hàm kiểm tra sơ bộ các cột --> kiểm tra nhanh
 - Khai báo hàm _... --> báo hiệu là hàm nội bộ
    +> Hàm nội bộ là hàm chỉ đc viết ra để phục vụ riêng tệp đó, chứ không sinh ra để các tệp ngoài gọi trực tiếp
    +> Đây là quy ước của cộng đồng lập trình viên --> Giống với ngữ dụng của PPLLT
    +> Tiêu trí OOP
 - Quy ước :
    +> Nếu trả vè True và không quăng exception và không ghi log warning thì là không thiều bất kì cột nào
    +> Ngược lại là thiếu
'''
def _verify_columns(file_path: Path, table_name: str) -> bool: 
    """Kiểm tra cột khoá có tồn tại trong file (đọc 5 dòng đầu để tối ưu tốc độ & RAM)."""
    if table_name not in REQUIRED_KEYS or not file_path.exists():
        return True
# Kiểm tra nếu bảng đó k yêu cầu kiểm tra hoặc chưa có đường dẫn đến thì trả vè True
    try:
        df_head = pd.read_csv(file_path, nrows=5, compression="gzip" if str(file_path).endswith(".gz") else None)
        missing = [c for c in REQUIRED_KEYS[table_name] if c not in df_head.columns]
        # Chỉ đọc 5 dòng đầu và tự động giải nén và tìm các cột buộc pải có nhưng nó không có trong file tải vè lưu tên vào list missing
        if missing:
            logger.warning("  ⚠ %s thiếu cột khoá: %s", file_path.name, missing)
            return False
        # Nếu thiếu báo lỗi log và trả vè False
        logger.info("  ✓ %s: đủ %d cột khoá chuẩn", file_path.name, len(REQUIRED_KEYS[table_name]))
        return True
        # Không thiếu gì thì báo True tức đủ cột cần
    except Exception as e:
        logger.warning("  ⚠ Không đọc được header %s: %s", file_path.name, e)
        return False
        # lỗi trong quá trình thì False


def _build_url(data_root: str, snapshot: str, file_path: str) -> str:
    """Tạo URL tải từ Inside Airbnb."""
    return f"{BASE_URL}/{data_root}/{snapshot}/{file_path}"


def _download_one(url: str, dest: Path) -> Path:
    """Tải một file nguyên tử (atomic download qua file .tmp) với xác thực SSL chuẩn certifi."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 1024:
        logger.info("  ✓ Đã có sẵn: %s (%.1f MB)", dest.name, dest.stat().st_size / (1024 * 1024))
        return dest

    tmp_dest = dest.with_name(dest.name + ".tmp")
    logger.info("  ↓ Đang tải an toàn: %s", url)
    try:
        resp = requests.get(url, stream=True, timeout=60, verify=certifi.where())
        resp.raise_for_status()
        with open(tmp_dest, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)

        # Kiểm tra tính toàn vẹn cơ bản trước khi đổi tên chính thức
        if tmp_dest.stat().st_size < 100:
            raise ValueError(f"File tải về quá nhỏ ({tmp_dest.stat().st_size} bytes), có thể bị lỗi.")

        # Đổi tên nguyên tử
        tmp_dest.replace(dest)
        size_mb = dest.stat().st_size / (1024 * 1024)
        logger.info("  ✓ Đã tải xong và xác thực an toàn: %s (%.1f MB)", dest.name, size_mb)
    except Exception as e:
        logger.error("  ✗ Lỗi không thể tải %s: %s", url, e)
        if tmp_dest.exists():
            tmp_dest.unlink()
        raise e
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
