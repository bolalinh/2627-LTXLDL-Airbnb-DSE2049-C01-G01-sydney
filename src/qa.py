from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import tempfile
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

FILE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = FILE_DIR.parent if FILE_DIR.name == "src" else FILE_DIR
DEFAULT_CONFIG = PROJECT_ROOT / "configs" / "sydney.yaml"
LEVELS = ("ERROR", "WARNING", "INFO", "PASS")
ACTIONABLE_FLAGS = {
    "MISSING_REQUIRED_FIELD",
    "MISSING_PRICE",
    "INVALID_PRICE",
    "INVALID_COORDINATES",
    "INVALID_REVIEW_SCORE",
    "INVALID_REVIEW_COUNT",
    "DUPLICATE_RECORD",
    "DUPLICATE_ROW",
    "DUPLICATE_LISTING_ID",
    "MISSING_FILE",
    "MISSING_SNAPSHOT",
    "INVALID_SCHEMA",
    "INVALID_GEOJSON",
    "GEOJSON_TYPE",
    "GEOJSON_FEATURES",
    "GEOJSON_GEOMETRY",
    "DATA_QUALITY_ISSUE",
    "INVALID_FIELD",
}
OPTIONAL_REQUIRED_ACTIONS = {"FIX", "FIX_OR_EXCLUDE", "REQUIRED", "MANDATORY", "REQUIRED_FIELD"}
OPTIONAL_REQUIRED_CHECKS = {"missing_number_of_reviews", "missing_review_scores_rating"}

REQUIRED_COLUMNS = {
    "listings.csv": ["id", "latitude", "longitude"],
    "calendar.csv": ["listing_id", "date", "available"],
    "reviews.csv": ["listing_id", "id", "date", "comments"],
    "neighbourhoods.csv": ["neighbourhood"],
}

OPTIONAL_INFO_COLUMNS = {
    "description",
    "neighborhood_overview",
    "host_since",
    "host_location",
    "host_about",
    "host_response_time",
    "host_response_rate",
    "host_acceptance_rate",
    "host_thumbnail_url",
    "host_picture_url",
    "host_neighbourhood",
    "host_name",
    "host_profile_url",
    "host_profile_id",
    "host_listings_count",
    "host_total_listings_count",
    "host_verifications",
    "host_has_profile_pic",
    "host_identity_verified",
    "host_is_superhost",
    "hosts_time_as_user_years",
    "hosts_time_as_user_months",
    "hosts_time_as_host_years",
    "hosts_time_as_host_months",
    "license",
    "calendar_updated",
    "price_quote_checkin_date",
    "price_quote_checkout_date",
    "price_quote_total_price",
    "price_quote_price_per_night",
    "price_quote_raw",
    "adjusted_price",
    "reviewer_name",
}


def read_config(path: str | Path):
    with open(path, "r", encoding="utf-8-sig") as f:
        config = yaml.safe_load(f)
    if not isinstance(config, dict):
        raise ValueError("Cấu hình YAML phải là một mapping.")
    return config


def resolve_project_path(value: str | Path, root: Path = PROJECT_ROOT) -> Path:
    candidate = Path(value)
    if candidate.is_absolute():
        return candidate
    return root / candidate


def _coerce_numeric(value: Any, field: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{field} must be numeric, not bool.")
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be numeric.") from exc


def _coerce_bool(value: Any, field: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{field} must be a boolean.")
    return value


def _coerce_int(value: Any, field: str, minimum: int = 0) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{field} must be an integer.")
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be an integer.") from exc
    if result < minimum:
        raise ValueError(f"{field} must be >= {minimum}.")
    return result


def _coerce_string_list(value: Any, field: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{field} must be a list of strings.")
    if not all(isinstance(item, str) for item in value):
        raise ValueError(f"{field} must contain only strings.")
    return list(value)


def _require_mapping(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be a mapping.")
    return value


def _resolve_legacy_qa_config(config: dict[str, Any]) -> dict[str, Any]:
    qa_cfg = config.get("qa", {})
    if qa_cfg is None:
        qa_cfg = {}
    if not isinstance(qa_cfg, dict):
        raise ValueError("qa must be a mapping.")

    legacy = config.get("qa_params", {})
    if isinstance(legacy, dict) and "min_length" in legacy and "comments" not in qa_cfg:
        qa_cfg = {**qa_cfg, "comments": {"min_length": legacy["min_length"]}}
    elif isinstance(qa_cfg, dict) and "min_length" in qa_cfg and "comments" not in qa_cfg:
        qa_cfg = {**qa_cfg, "comments": {"min_length": qa_cfg["min_length"]}}

    if isinstance(qa_cfg.get("comments"), dict) and "min_length" in qa_cfg and "min_length" not in qa_cfg["comments"]:
        qa_cfg["comments"] = {**qa_cfg["comments"], "min_length": qa_cfg["min_length"]}
    if "min_length" in qa_cfg and isinstance(qa_cfg["comments"], dict):
        qa_cfg.pop("min_length", None)

    return qa_cfg


def load_qa_config(config_path: str | Path | dict[str, Any]) -> dict[str, Any]:
    if isinstance(config_path, dict):
        raw = config_path
    else:
        raw = read_config(config_path)

    if not isinstance(raw, dict):
        raise ValueError("Configuration must be a dictionary.")

    qa_cfg = _resolve_legacy_qa_config(raw)
    if not isinstance(qa_cfg, dict):
        raise ValueError("qa configuration must be a dictionary.")

    extra = set(qa_cfg) - {
        "clean",
        "chunk_size",
        "diagnostic_sample_size",
        "price",
        "price_outlier",
        "coordinates",
        "review_score",
        "number_of_reviews",
        "comments",
        "duplicates",
        "files",
    }
    if extra:
        raise ValueError(f"Unsupported QA parameter(s): {sorted(extra)}")

    validated: dict[str, Any] = {}
    validated["clean"] = _coerce_bool(qa_cfg.get("clean", True), "qa.clean")
    validated["chunk_size"] = _coerce_int(qa_cfg.get("chunk_size", 100_000), "qa.chunk_size", minimum=1)
    validated["diagnostic_sample_size"] = _coerce_int(
        qa_cfg.get("diagnostic_sample_size", 200_000), "qa.diagnostic_sample_size", minimum=1
    )

    price_cfg = _require_mapping(qa_cfg.get("price", {}), "qa.price")
    validated["price"] = {
        "min_valid": _coerce_numeric(price_cfg.get("min_valid", 0), "qa.price.min_valid"),
        "exclusive_min": _coerce_bool(price_cfg.get("exclusive_min", True), "qa.price.exclusive_min"),
        "missing_allowed": _coerce_bool(price_cfg.get("missing_allowed", True), "qa.price.missing_allowed"),
        "symbols_to_strip": _coerce_string_list(price_cfg.get("symbols_to_strip", ["$", ","]), "qa.price.symbols_to_strip"),
        "null_representations": _coerce_string_list(
            price_cfg.get("null_representations", ["nan", "None", "", "NaN"]), "qa.price.null_representations"
        ),
    }

    price_outlier_cfg = _require_mapping(qa_cfg.get("price_outlier", {}), "qa.price_outlier")
    method = str(price_outlier_cfg.get("method", "IQR")).upper()
    if method not in {"IQR", "PERCENTILE"}:
        raise ValueError("qa.price_outlier.method must be 'IQR' or 'PERCENTILE'.")
    action = str(price_outlier_cfg.get("action", "report_only")).lower()
    if action not in {"report_only", "remove", "delete", "report_delete"}:
        raise ValueError("qa.price_outlier.action must be one of report_only/remove/delete/report_delete.")
    pct = _coerce_numeric(price_outlier_cfg.get("percentile_threshold", 0.99), "qa.price_outlier.percentile_threshold")
    if not 0 < pct < 1:
        raise ValueError("qa.price_outlier.percentile_threshold must be between 0 and 1.")
    validated["price_outlier"] = {
        "method": method,
        "multiplier": _coerce_numeric(price_outlier_cfg.get("multiplier", 1.5), "qa.price_outlier.multiplier"),
        "action": action,
        "percentile_threshold": pct,
    }

    coord_cfg = _require_mapping(qa_cfg.get("coordinates", {}), "qa.coordinates")
    lat_cfg = _require_mapping(coord_cfg.get("latitude", {}), "qa.coordinates.latitude")
    lon_cfg = _require_mapping(coord_cfg.get("longitude", {}), "qa.coordinates.longitude")
    lat_min = _coerce_numeric(lat_cfg.get("min", -90), "qa.coordinates.latitude.min")
    lat_max = _coerce_numeric(lat_cfg.get("max", 90), "qa.coordinates.latitude.max")
    lon_min = _coerce_numeric(lon_cfg.get("min", -180), "qa.coordinates.longitude.min")
    lon_max = _coerce_numeric(lon_cfg.get("max", 180), "qa.coordinates.longitude.max")
    if lat_min > lat_max:
        raise ValueError("qa.coordinates.latitude.min cannot exceed qa.coordinates.latitude.max.")
    if lon_min > lon_max:
        raise ValueError("qa.coordinates.longitude.min cannot exceed qa.coordinates.longitude.max.")
    validated["coordinates"] = {
        "latitude": {"min": lat_min, "max": lat_max},
        "longitude": {"min": lon_min, "max": lon_max},
        "missing_allowed": _coerce_bool(coord_cfg.get("missing_allowed", False), "qa.coordinates.missing_allowed"),
    }

    review_cfg = _require_mapping(qa_cfg.get("review_score", {}), "qa.review_score")
    review_min = _coerce_numeric(review_cfg.get("min", 0), "qa.review_score.min")
    review_max = _coerce_numeric(review_cfg.get("max", 100), "qa.review_score.max")
    if review_min > review_max:
        raise ValueError("qa.review_score.min cannot exceed qa.review_score.max.")
    validated["review_score"] = {"min": review_min, "max": review_max}

    review_count_cfg = _require_mapping(qa_cfg.get("number_of_reviews", {}), "qa.number_of_reviews")
    validated["number_of_reviews"] = {"min": _coerce_numeric(review_count_cfg.get("min", 0), "qa.number_of_reviews.min")}

    comments_cfg = _require_mapping(qa_cfg.get("comments", {}), "qa.comments")
    empty_allowed = _coerce_bool(comments_cfg.get("empty_allowed", True), "qa.comments.empty_allowed")
    min_length = _coerce_int(comments_cfg.get("min_length", 5), "qa.comments.min_length", minimum=0)
    short_warn = _coerce_int(
        comments_cfg.get("short_comment_warning_length", min_length), "qa.comments.short_comment_warning_length", minimum=0
    )
    if short_warn > min_length:
        raise ValueError(
            "qa.comments.short_comment_warning_length must be <= qa.comments.min_length. "
            "The warning threshold should be at or below the strict minimum."
        )
    validated["comments"] = {
        "empty_allowed": empty_allowed,
        "min_length": min_length,
        "short_comment_warning_length": short_warn,
    }

    duplicates_cfg = _require_mapping(qa_cfg.get("duplicates", {}), "qa.duplicates")
    listings_cfg = _require_mapping(duplicates_cfg.get("listings", {}), "qa.duplicates.listings")
    calendar_cfg = _require_mapping(duplicates_cfg.get("calendar", {}), "qa.duplicates.calendar")
    full_rows_cfg = _require_mapping(duplicates_cfg.get("full_rows", {}), "qa.duplicates.full_rows")
    validated["duplicates"] = {
        "listings": {"key": _coerce_string_list(listings_cfg.get("key", ["id"]), "qa.duplicates.listings.key")},
        "calendar": {"key": _coerce_string_list(calendar_cfg.get("key", ["listing_id", "date"]), "qa.duplicates.calendar.key")},
        "full_rows": {
            "enabled": _coerce_bool(full_rows_cfg.get("enabled", True), "qa.duplicates.full_rows.enabled"),
            "scope": str(full_rows_cfg.get("scope", "full_dataset")).lower(),
        },
    }
    if validated["duplicates"]["full_rows"]["scope"] not in {"within_chunk_only", "full_dataset"}:
        raise ValueError("qa.duplicates.full_rows.scope must be 'within_chunk_only' or 'full_dataset'.")

    files_cfg = _require_mapping(qa_cfg.get("files", {}), "qa.files")
    validated["files"] = {
        "required": _coerce_string_list(files_cfg.get("required", ["listings.csv", "calendar.csv", "reviews.csv"]), "qa.files.required"),
        "optional": _coerce_string_list(files_cfg.get("optional", ["neighbourhoods.csv", "neighbourhoods.geojson"]), "qa.files.optional"),
        "processed_dir": str(files_cfg.get("processed_dir", "data/processed")),
        "report_dir": str(files_cfg.get("report_dir", "reports")),
        "report_filename": str(files_cfg.get("report_filename", "qa_report.csv")),
    }

    return validated


def normalize_entity_type(filename):
    """Map a QA file name to the dataset/entity category used in the final CSV."""
    if not filename or str(filename) == "-":
        return "dataset"
    name = str(filename).lower()
    if name == "listings.csv":
        return "listing"
    if name == "calendar.csv":
        return "calendar"
    if name == "reviews.csv":
        return "review"
    if name.startswith("neighbourhood"):
        return "neighbourhood"
    return name.replace(".csv", "").replace(".geojson", "")



def add(report,level,snapshot,filename,check,message,report_level="CHECK_LEVEL",record_id="",date="",listing_id="",price=None,):
    """
    Add one QA result to the report.

    Supports both:
    - CHECK_LEVEL: dataset-level summary
    - RECORD_LEVEL: individual problematic records

    record_id is retained temporarily for backward compatibility.
    listing_id is the standardized identifier for listings.
    """

    def clean_value(value):
        if value is None:
            return ""

        try:
            if pd.isna(value):
                return ""
        except (TypeError, ValueError):
            pass

        return str(value).strip()

    # Backward compatibility:
    # Old calls using record_id will still populate listing_id.
    normalized_record_id = clean_value(record_id)
    normalized_listing_id = clean_value(listing_id)

    if not normalized_listing_id and normalized_record_id:
        normalized_listing_id = normalized_record_id
    if not normalized_record_id and normalized_listing_id:
        normalized_record_id = normalized_listing_id

    report.append({
        "level": str(level).upper(),
        "snapshot": clean_value(snapshot),
        "date": clean_value(date),
        "listing_id": normalized_listing_id,
        "price": clean_value(price),
        "file": clean_value(filename),
        "check": clean_value(check),
        "message": clean_value(message),
        "report_level": str(report_level).upper(),
        "record_id": normalized_record_id,
    })



def safe_int(value):
    """Convert a numeric-like value to int while handling blanks and commas."""
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return 0
    try:
        return int(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return 0


def extract_affected_rows(check_name, status, message):
    """Infer affected-row count from existing QA messages whenever present."""
    check = str(check_name or "").strip()
    if str(status).upper() == "PASS":
        return 0
    if check in {"row_count", "file_exists", "snapshot_exists", "geojson_feature_count", "cleaned_output", "required_columns"}:
        return 0
    if check == "price_iqr_outliers_sample":
        match = re.search(r";\s*(\d[\d,]*)\s+giá\s+trong\s+mẫu", str(message), flags=re.IGNORECASE)
        if match:
            return safe_int(match.group(1))
        return 0
    if check.startswith("missing_") and check not in {"missing_comments"}:
        match = re.search(r"(\d[\d,]*)\s*(?:/|\))?", str(message or ""))
        if match:
            return safe_int(match.group(1))
        return 0
    if "Không phát hiện" in str(message or "") or ("không" in str(message or "").lower() and "phát hiện" in str(message or "").lower()):
        return 0
    match = re.search(r"(\d[\d,]*)", str(message or ""))
    return safe_int(match.group(1)) if match else 0


def map_quality_flag(check_name, status, message=""):
    """Map each QA check to a machine-readable flag, severity, and action recommendation."""
    check = str(check_name or "").strip()
    status = str(status or "").upper()
    message = str(message or "")

    if status == "PASS":
        return "NONE", "LOW", "NONE"

    direct_map = {
        "file_exists": ("MISSING_FILE", "HIGH" if status == "ERROR" else "MEDIUM", "INVESTIGATE") if "Thiếu file" in message else ("NONE", "LOW", "NONE"),
        "snapshot_exists": ("MISSING_SNAPSHOT", "HIGH", "INVESTIGATE") if "Không tìm thấy" in message else ("NONE", "LOW", "NONE"),
        "required_columns": ("MISSING_REQUIRED_FIELD", "HIGH" if "Thiếu" in message else "MEDIUM", "FIX_OR_EXCLUDE" if "Thiếu" in message else "REVIEW"),
        "price_all_missing": ("MISSING_PRICE", "HIGH", "FIX_OR_EXCLUDE"),
        "price_missing": ("MISSING_PRICE", "MEDIUM" if status == "WARNING" else "INFO", "REVIEW"),
        "price_unparseable": ("INVALID_PRICE", "MEDIUM", "FIX"),
        "price_nonpositive": ("INVALID_PRICE", "HIGH", "FIX_OR_EXCLUDE"),
        "price_iqr_outliers_sample": ("PRICE_OUTLIER", "MEDIUM", "INVESTIGATE"),
        "coordinates_missing": ("MISSING_REQUIRED_FIELD", "MEDIUM", "REVIEW"),
        "coordinates_out_of_range": ("INVALID_COORDINATES", "MEDIUM", "REVIEW"),
        "available_missing": ("MISSING_REQUIRED_FIELD", "MEDIUM", "REVIEW"),
        "missing_comments": ("MISSING_REQUIRED_FIELD", "MEDIUM", "REVIEW"),
        "short_comments": ("SHORT_COMMENT", "LOW", "NONE"),
        "negative_number_of_reviews": ("INVALID_REVIEW_COUNT", "MEDIUM", "FIX_OR_EXCLUDE"),
        "review_scores_rating_range": ("INVALID_REVIEW_SCORE", "MEDIUM", "REVIEW"),
        "duplicate_rows_within_chunk": ("DUPLICATE_ROW", "HIGH", "INVESTIGATE"),
        "duplicate_rows_within_chunk_only": ("DUPLICATE_ROW", "HIGH", "INVESTIGATE"),
        "duplicate_listing_date": ("DUPLICATE_LISTING_ID", "HIGH", "INVESTIGATE"),
    }
    if check in direct_map:
        return direct_map[check]

    if "allowed" in check.lower() or "allowed" in message.lower():
        return "NONE", "LOW", "NONE"
    if "empty_flag" in check.lower() or "missing flag" in message.lower():
        return "", "LOW", "NONE"

    if check.startswith("missing_"):
        field = check.replace("missing_", "", 1)
        if field in {"id", "listing_id", "date", "price", "latitude", "longitude", "comments", "available", "minimum_nights", "maximum_nights", "review_scores_rating", "number_of_reviews"}:
            severity = "HIGH" if status == "ERROR" else "MEDIUM"
            return "MISSING_REQUIRED_FIELD", severity, "FIX_OR_EXCLUDE" if severity == "HIGH" else "REVIEW"
        severity = "LOW" if status == "INFO" else "MEDIUM"
        return "MISSING_OPTIONAL_FIELD", severity, "REVIEW"

    if "duplicate" in check.lower():
        return "DUPLICATE_RECORD", "HIGH", "INVESTIGATE"
    if "invalid" in check.lower() or "range" in check.lower() or "domain" in check.lower():
        return "INVALID_FIELD", "MEDIUM", "FIX"
    if "missing" in check.lower():
        return "MISSING_REQUIRED_FIELD", "MEDIUM", "REVIEW"
    if status in {"WARNING", "ERROR"}:
        return "DATA_QUALITY_ISSUE", "HIGH" if status == "ERROR" else "MEDIUM", "INVESTIGATE"
    return "NONE", "LOW", "NONE"


def normalize_check_name(check_name, filename):
    """Disambiguate dataset-level checks that can occur for multiple files in one entity."""
    check = str(check_name or "").strip()
    if check != "file_exists":
        return check
    file_value = str(filename or "").strip()
    if not file_value or file_value == "-":
        return check
    suffix = re.sub(r"[^a-z0-9]+", "_", file_value.lower()).strip("_")
    return f"{check}_{suffix}" if suffix else check


def get_id_column(columns):
    """Return the actual identifier column for a dataset, if present."""
    for candidate in ("id", "listing_id"):
        if candidate in columns:
            return candidate
    return None


def format_missing_field_name(field_name):
    """Convert a database column name to a concise human-readable field label."""
    field = str(field_name or "").strip()
    if not field:
        return "value"
    return field.replace("_", " ").replace("-", " ").strip()


def format_record_missing_message(field_name):
    """Short record-level message without repeating the record ID."""
    return f"Missing value in {format_missing_field_name(field_name)}."


def format_check_missing_message(field_name, count, total):
    """Compact CHECK_LEVEL count message preserving the affected-count statistics."""
    if total <= 0:
        return f"{count:,} listings missing {format_missing_field_name(field_name)}."
    pct = (count / total) * 100 if total else 0.0
    return f"{count:,} listings missing {format_missing_field_name(field_name)} ({pct:.2f}%)."


def standardize_missing_check_name(field_name):
    """Use the canonical missing-data check name for both summary and record-level rows."""
    field = str(field_name or "").strip()
    if field == "price":
        return "price_missing"
    return f"missing_{field}"


def missing_field_status(field_name):
    """Match the same status/severity policy used by the CHECK_LEVEL summary rows."""
    field = str(field_name or "").strip()
    if field in {"id", "listing_id"}:
        return "ERROR", "MISSING_REQUIRED_FIELD", "HIGH", "FIX_OR_EXCLUDE"
    if field in OPTIONAL_INFO_COLUMNS:
        return "INFO", "MISSING_OPTIONAL_FIELD", "LOW", "REVIEW"
    return "WARNING", "MISSING_REQUIRED_FIELD", "MEDIUM", "REVIEW"


def normalize_record_id(value):
    """Convert an ID value to a clean string without fabricating missing IDs."""
    if value is None:
        return ""
    if isinstance(value, float) and pd.isna(value):
        return ""
    if pd.isna(value):
        return ""
    text = str(value).strip()
    return text if text else ""


def validate_record_level_ids(csv_path, source_listing_path):
    """Validate that exported record IDs match valid IDs in the original source listing file."""
    df = pd.read_csv(csv_path, dtype={"record_id": "string", "snapshot": "string"}, keep_default_na=False)
    listing_df = pd.read_csv(source_listing_path, dtype={"id": "string"}, keep_default_na=False)
    exported = df[(df["report_level"] == "RECORD_LEVEL") & (df["entity_type"] == "listing") & df["record_id"].notna()]
    if exported.empty:
        return True
    source_ids = set(listing_df["id"].astype(str).tolist())
    missing_in_source = sorted(set(exported["record_id"].astype(str).tolist()) - source_ids)
    if missing_in_source:
        raise ValueError(
            "RECORD_LEVEL listing IDs do not match source IDs: "
            f"missing_in_source={missing_in_source[:10]}"
        )
    return True


def latest_snapshot_name(snapshots):
    """Trả về snapshot có ngày lớn nhất theo định dạng YYYY-MM-DD; lỗi nếu có giá trị không hợp lệ."""
    if not snapshots:
        raise ValueError("Không có snapshot nào trong cấu hình để kiểm tra.")

    parsed = []
    invalid = []
    for snapshot in snapshots:
        text = str(snapshot).strip()
        try:
            parsed.append((pd.to_datetime(text, format="%Y-%m-%d", errors="raise"), text))
        except Exception:
            invalid.append(text)

    if invalid:
        raise ValueError("Snapshot không hợp lệ (yêu cầu YYYY-MM-DD): " + ", ".join(invalid))

    return max(parsed, key=lambda item: item[0])[1]


def numeric_price(series, qa_config: dict[str, Any]) -> pd.Series:
    price_cfg = qa_config["price"]
    symbols = tuple(str(item) for item in price_cfg["symbols_to_strip"])
    nulls = {str(item).strip().lower() for item in price_cfg["null_representations"] if str(item).strip()}
    cleaned = series.astype("string").str.strip()
    for symbol in symbols:
        if symbol:
            cleaned = cleaned.str.replace(re.escape(symbol), "", regex=True)
    cleaned = cleaned.str.replace(r"^\s*$", "", regex=True)
    cleaned = cleaned.str.strip().str.lower()
    for rep in sorted(nulls, key=len, reverse=True):
        cleaned = cleaned.mask(cleaned == rep, pd.NA)
    return pd.to_numeric(cleaned, errors="coerce")


def normalize_available(series):
    raw = series.astype("string").str.strip().str.lower()
    mapping = {"t": True, "true": True, "1": True, "yes": True, "f": False, "false": False, "0": False, "no": False}
    normalized = raw.map(mapping).astype("boolean")
    invalid = series.notna() & normalized.isna()
    return normalized, invalid


def detect_price_outliers(price_series: pd.Series, qa_config: dict[str, Any]):
    valid = price_series.dropna().astype(float)
    if valid.empty:
        return 0, None, str(qa_config["price_outlier"]["method"]).upper(), 0

    method = str(qa_config["price_outlier"]["method"]).upper()
    if method == "IQR":
        q1, q3 = valid.quantile([0.25, 0.75])
        iqr = q3 - q1
        upper = q3 + float(qa_config["price_outlier"]["multiplier"]) * iqr
        return int((valid > upper).sum()), float(upper), method, int(valid.size)

    threshold = valid.quantile(float(qa_config["price_outlier"]["percentile_threshold"]))
    return int((valid > threshold).sum()), float(threshold), method, int(valid.size)


def _row_signature(row: pd.Series | tuple | list) -> str:
    payload = []
    values = row if isinstance(row, (tuple, list)) else row.tolist()
    for value in values:
        if value is None or pd.isna(value):
            payload.append("")
        else:
            payload.append(str(value))
    return hashlib.md5(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def check_csv(path, snapshot, report, min_length=5, clean=False, processed_root=None, qa_config=None):
    qa_config = qa_config or load_qa_config(DEFAULT_CONFIG)
    name = path.name
    required = REQUIRED_COLUMNS.get(name, [])
    try:
        columns = list(pd.read_csv(path, nrows=0).columns)
    except Exception as exc:
        add(report, "ERROR", snapshot, name, "read_header", f"Không đọc được header: {exc}")
        return

    missing_cols = sorted(set(required) - set(columns))
    if missing_cols:
        add(report, "ERROR", snapshot, name, "required_columns", f"Thiếu cột bắt buộc: {missing_cols}")
        return
    add(report, "PASS", snapshot, name, "required_columns", f"Đủ cột bắt buộc: {required}")

    total = 0
    missing = {c: 0 for c in columns}
    duplicate_rows = 0
    duplicate_ids = 0
    seen_ids = set()
    invalid_dates = 0
    invalid_coords = 0
    missing_coords = 0
    price_missing = 0
    price_unparseable = 0
    price_nonpositive = 0
    price_values = []
    available_invalid = 0
    available_missing = 0
    calendar_dup_keys = 0
    missing_comments = 0
    short_comments = 0
    review_negative_count = 0
    review_score_invalid = 0
    output_path = None
    missing_record_ids: dict[str, set[str]] = {}
    id_column = get_id_column(columns)
    if name == "listings.csv":
        missing_record_ids = {col: set() for col in columns if col != id_column}
    elif name == "reviews.csv" and "comments" in columns:
        missing_record_ids = {"comments": set()}

    processed_root = Path(processed_root) if processed_root is not None else PROJECT_ROOT / "data" / "processed"
    if clean:
        output_path = processed_root / str(snapshot) / name
        output_path.parent.mkdir(parents=True, exist_ok=True)

    read_kwargs = {"chunksize": int(qa_config["chunk_size"]), "low_memory": False}
    dtypes = {}
    if id_column is not None:
        dtypes[id_column] = "string"
    if name == "reviews.csv" and "listing_id" in columns:
        dtypes["listing_id"] = "string"
    if dtypes:
        read_kwargs["dtype"] = dtypes

    db: sqlite3.Connection | None = None
    db_path: Path | None = None
    row_hash_db: sqlite3.Connection | None = None
    row_hash_db_path: Path | None = None

    if name == "calendar.csv":
        tmp = tempfile.NamedTemporaryFile(prefix="airbnb_qa_keys_", suffix=".sqlite", delete=False)
        db_path = Path(tmp.name)
        tmp.close()
        db = sqlite3.connect(db_path)
        db.execute("CREATE TABLE keys (listing_id TEXT NOT NULL, date TEXT NOT NULL, PRIMARY KEY (listing_id, date))")

    if qa_config["duplicates"]["full_rows"]["enabled"] and name in {"listings.csv", "calendar.csv", "reviews.csv"}:
        tmp = tempfile.NamedTemporaryFile(prefix="airbnb_qa_row_hashes_", suffix=".sqlite", delete=False)
        row_hash_db_path = Path(tmp.name)
        tmp.close()
        row_hash_db = sqlite3.connect(row_hash_db_path)
        row_hash_db.execute("CREATE TABLE row_hashes (row_hash TEXT PRIMARY KEY)")

    try:
        for chunk in pd.read_csv(path, **read_kwargs):
            total += len(chunk)
            for col in columns:
                missing[col] += int(chunk[col].isna().sum())

            if row_hash_db is not None:
                signatures = [(_row_signature(row),) for row in chunk.itertuples(index=False, name=None)]
                before = row_hash_db.total_changes
                row_hash_db.executemany("INSERT OR IGNORE INTO row_hashes(row_hash) VALUES (?)", signatures)
                row_hash_db.commit()
                duplicate_rows += len(signatures) - (row_hash_db.total_changes - before)

            if name in {"listings.csv", "reviews.csv"} and id_column in chunk:
                ids = chunk[id_column].dropna().astype(str).str.strip()
                duplicate_ids += int(ids.duplicated().sum())
                duplicate_ids += int(ids.isin(seen_ids).sum())
                seen_ids.update(ids.tolist())

            if name == "listings.csv" and id_column is not None:
                for col in columns:
                    if col == id_column or col not in missing_record_ids:
                        continue
                    if col == "comments":
                        mask = chunk[col].isna() | chunk[col].astype("string").str.strip().eq("")
                    else:
                        mask = chunk[col].isna()
                    if not mask.any():
                        continue
                    for record_id in chunk.loc[mask, id_column].tolist():
                        record_id = normalize_record_id(record_id)
                        if record_id:
                            missing_record_ids[col].add(record_id)

            if "date" in chunk:
                dates = pd.to_datetime(chunk["date"], errors="coerce")
                invalid_dates += int((chunk["date"].notna() & dates.isna()).sum())
                if name == "calendar.csv" and "listing_id" in chunk:
                    valid = chunk["listing_id"].notna() & dates.notna()
                    keys = list(zip(chunk.loc[valid, "listing_id"].astype(str), dates.loc[valid].dt.strftime("%Y-%m-%d")))
                    before = db.total_changes if db is not None else 0
                    if db is not None:
                        db.executemany("INSERT OR IGNORE INTO keys VALUES (?, ?)", keys)
                        db.commit()
                        calendar_dup_keys += len(keys) - (db.total_changes - before)

            if {"latitude", "longitude"}.issubset(chunk.columns):
                lat = pd.to_numeric(chunk["latitude"], errors="coerce")
                lon = pd.to_numeric(chunk["longitude"], errors="coerce")
                lat_missing = chunk["latitude"].isna() | (chunk["latitude"].astype("string").str.strip().eq(""))
                lon_missing = chunk["longitude"].isna() | (chunk["longitude"].astype("string").str.strip().eq(""))
                missing_coords += int((lat_missing | lon_missing).sum())
                invalid_coords += int(
                    (
                        lat.notna()
                        & lon.notna()
                        & (
                            ~lat.between(qa_config["coordinates"]["latitude"]["min"], qa_config["coordinates"]["latitude"]["max"]) 
                            | ~lon.between(qa_config["coordinates"]["longitude"]["min"], qa_config["coordinates"]["longitude"]["max"])
                        )
                    ).sum()
                )

            if "price" in chunk:
                parsed = numeric_price(chunk["price"], qa_config)
                null_values = {str(v).strip().lower() for v in qa_config["price"]["null_representations"]}
                price_missing += int((chunk["price"].isna() | chunk["price"].astype("string").str.strip().str.lower().isin(null_values)).sum())
                price_unparseable += int((chunk["price"].notna() & ~chunk["price"].astype("string").str.strip().str.lower().isin(null_values) & parsed.isna()).sum())
                if qa_config["price"]["exclusive_min"]:
                    price_nonpositive += int((parsed.notna() & (parsed <= qa_config["price"]["min_valid"])).sum())
                else:
                    price_nonpositive += int((parsed.notna() & (parsed < qa_config["price"]["min_valid"])).sum())
                valid_prices = parsed.dropna()
                if qa_config["price"]["exclusive_min"]:
                    valid_prices = valid_prices[valid_prices > qa_config["price"]["min_valid"]]
                else:
                    valid_prices = valid_prices[valid_prices >= qa_config["price"]["min_valid"]]
                if len(price_values) < int(qa_config["diagnostic_sample_size"]):
                    remaining = int(qa_config["diagnostic_sample_size"]) - len(price_values)
                    price_values.extend(valid_prices.head(remaining).tolist())

            if "available" in chunk:
                normalized, invalid = normalize_available(chunk["available"])
                available_invalid += int(invalid.sum())
                available_missing += int(chunk["available"].isna().sum())

            if "comments" in chunk:
                comments = chunk["comments"]
                comment_strings = comments.astype("string").str.strip()
                missing_mask = comments.isna() | comment_strings.eq("")
                missing_comments += int(missing_mask.sum())
                text = comments.dropna().astype(str).str.strip()
                short_comments += int((text.str.len() < int(qa_config["comments"]["short_comment_warning_length"])).sum())
                if name == "reviews.csv" and "comments" in missing_record_ids and missing_mask.any():
                    source_id_col = "listing_id" if "listing_id" in chunk.columns else id_column
                    if source_id_col is not None:
                        for record_id in chunk.loc[missing_mask, source_id_col].tolist():
                            clean_id = normalize_record_id(record_id)
                            if clean_id:
                                missing_record_ids["comments"].add(clean_id)

            if "number_of_reviews" in chunk:
                n = pd.to_numeric(chunk["number_of_reviews"], errors="coerce")
                review_negative_count += int((n < qa_config["number_of_reviews"]["min"]).sum())
            if "review_scores_rating" in chunk:
                scores = pd.to_numeric(chunk["review_scores_rating"], errors="coerce")
                review_score_invalid += int((scores.notna() & ~scores.between(qa_config["review_score"]["min"], qa_config["review_score"]["max"])).sum())

            if clean:
                cleaned = chunk.copy()
                if name == "listings.csv":
                    if "price" in cleaned:
                        p = numeric_price(cleaned["price"], qa_config)
                        if qa_config["price"]["exclusive_min"]:
                            p = p.mask(p <= qa_config["price"]["min_valid"])
                        else:
                            p = p.mask(p < qa_config["price"]["min_valid"])
                        cleaned["price"] = p
                    if {"latitude", "longitude"}.issubset(cleaned.columns):
                        lat = pd.to_numeric(cleaned["latitude"], errors="coerce")
                        lon = pd.to_numeric(cleaned["longitude"], errors="coerce")
                        lat_missing = cleaned["latitude"].isna() | (cleaned["latitude"].astype("string").str.strip().eq(""))
                        lon_missing = cleaned["longitude"].isna() | (cleaned["longitude"].astype("string").str.strip().eq(""))
                        bad = lat_missing | lon_missing | ~lat.between(qa_config["coordinates"]["latitude"]["min"], qa_config["coordinates"]["latitude"]["max"]) | ~lon.between(qa_config["coordinates"]["longitude"]["min"], qa_config["coordinates"]["longitude"]["max"])
                        cleaned["latitude"] = lat.mask(bad)
                        cleaned["longitude"] = lon.mask(bad)
                    if "number_of_reviews" in cleaned:
                        n = pd.to_numeric(cleaned["number_of_reviews"], errors="coerce")
                        cleaned["number_of_reviews"] = n.mask(n < qa_config["number_of_reviews"]["min"]) 
                    if "review_scores_rating" in cleaned:
                        scores = pd.to_numeric(cleaned["review_scores_rating"], errors="coerce")
                        cleaned["review_scores_rating"] = scores.mask(~scores.between(qa_config["review_score"]["min"], qa_config["review_score"]["max"]))
                elif name == "calendar.csv":
                    if "date" in cleaned:
                        cleaned["date"] = pd.to_datetime(cleaned["date"], errors="coerce").dt.strftime("%Y-%m-%d")
                    if "available" in cleaned:
                        normalized, _ = normalize_available(cleaned["available"])
                        cleaned["available"] = normalized
                    if "price" in cleaned:
                        p = numeric_price(cleaned["price"], qa_config)
                        if qa_config["price"]["exclusive_min"]:
                            p = p.mask(p <= qa_config["price"]["min_valid"])
                        else:
                            p = p.mask(p < qa_config["price"]["min_valid"])
                        cleaned["price"] = p
                elif name == "reviews.csv":
                    if "date" in cleaned:
                        cleaned["date"] = pd.to_datetime(cleaned["date"], errors="coerce").dt.strftime("%Y-%m-%d")
                    if "comments" in cleaned:
                        cleaned["comments"] = cleaned["comments"].astype("string").str.strip()
                        if qa_config["comments"]["empty_allowed"]:
                            cleaned["comments"] = cleaned["comments"].replace(r"^\s*$", pd.NA, regex=True)
                        elif qa_config["comments"]["min_length"] > 0:
                            cleaned["comments"] = cleaned["comments"].mask(cleaned["comments"].astype("string").str.len() < qa_config["comments"]["min_length"], pd.NA)
                cleaned.to_csv(output_path, mode="a", index=False, header=not output_path.exists(), encoding="utf-8")
    except Exception as exc:
        add(report, "ERROR", snapshot, name, "read_or_process", f"Lỗi khi đọc/xử lý CSV: {exc}")
        return
    finally:
        if db is not None:
            db.close()
        if db_path is not None:
            db_path.unlink(missing_ok=True)
        if row_hash_db is not None:
            row_hash_db.close()
        if row_hash_db_path is not None:
            row_hash_db_path.unlink(missing_ok=True)

    add(report, "INFO", snapshot, name, "row_count", f"Đọc được {total:,} dòng.")

    if name in {"listings.csv", "reviews.csv"}:
        for col_name, ids in sorted(missing_record_ids.items()):
            if not ids:
                continue
            check_name = standardize_missing_check_name(col_name)
            for record_id in sorted(ids, key=lambda value: str(value)):
                add(report, "WARNING", snapshot, name, check_name, format_record_missing_message(col_name), report_level="RECORD_LEVEL", record_id=record_id)

    for col, count in missing.items():
        if count == 0:
            continue
        if col in {"price", "comments", "available", "latitude", "longitude"}:
            continue
        unique_missing_count = len(missing_record_ids.get(col, set())) if name == "listings.csv" and id_column is not None else count
        check_name = standardize_missing_check_name(col)
        level = "ERROR" if col in {"id", "listing_id"} else ("INFO" if col in OPTIONAL_INFO_COLUMNS else "WARNING")
        add(report, level, snapshot, name, check_name, format_check_missing_message(col, unique_missing_count, total))

    if "price" in columns and name == "listings.csv":
        unique_price_missing = len(missing_record_ids.get("price", set())) if id_column is not None else price_missing
        if price_missing == total and total > 0:
            add(report, "ERROR", snapshot, name, "price_all_missing", "Toàn bộ price bị thiếu; KPI giá không thể tính từ cột này.")
        if price_missing:
            add(report, "WARNING", snapshot, name, "price_missing", format_check_missing_message("price", unique_price_missing, total))
        if price_unparseable:
            add(report, "WARNING", snapshot, name, "price_unparseable", f"Có {price_unparseable:,} giá không chuyển được thành số.")
        if price_nonpositive:
            add(report, "WARNING", snapshot, name, "price_nonpositive", f"Có {price_nonpositive:,} giá không hợp lệ theo ngưỡng tối thiểu cấu hình.")
        if price_values:
            outlier_count, threshold, method, sample_size = detect_price_outliers(pd.Series(price_values), qa_config)
            add(report, "INFO", snapshot, name, "price_iqr_outliers_sample", f"Mẫu tối đa {sample_size:,} giá hợp lệ: ngưỡng {method}={threshold:.2f}; {outlier_count:,} giá trong mẫu vượt ngưỡng. Không tự động xóa ngoại lai.")

    if {"latitude", "longitude"}.issubset(columns):
        if missing_coords:
            add(report, "INFO" if qa_config["coordinates"]["missing_allowed"] else "WARNING", snapshot, name, "coordinates_missing", f"Có {missing_coords:,} bản ghi thiếu tọa độ hoặc tọa độ trống.")
        if invalid_coords:
            add(report, "WARNING", snapshot, name, "coordinates_out_of_range", f"Có {invalid_coords:,} bản ghi có tọa độ ngoài phạm vi cho phép.")
        status = "WARNING" if invalid_coords or (missing_coords and not qa_config["coordinates"]["missing_allowed"]) else "PASS"
        add(report, status, snapshot, name, "coordinates", f"Coord không hợp lệ: {invalid_coords:,}; thiếu: {missing_coords:,}.")

    if "available" in columns:
        add(report, "WARNING" if available_invalid else "PASS", snapshot, name, "available_domain", f"Có {available_invalid:,} giá trị available không nhận diện được." if available_invalid else "Các giá trị available đều thuộc miền Boolean nhận diện được.")
        if available_missing:
            add(report, "WARNING", snapshot, name, "available_missing", format_check_missing_message("available", available_missing, total))

    if name == "calendar.csv":
        add(report, "WARNING" if calendar_dup_keys else "PASS", snapshot, name, "duplicate_listing_date", f"Phát hiện {calendar_dup_keys:,} khóa (listing_id, date) trùng." if calendar_dup_keys else "Không phát hiện khóa (listing_id, date) trùng.")

    if "comments" in columns:
        if missing_comments:
            unique_affected = len(missing_record_ids.get("comments", set())) if "comments" in missing_record_ids and missing_record_ids["comments"] else missing_comments
            add(report, "WARNING", snapshot, name, "missing_comments", format_check_missing_message("comments", unique_affected, total))
        add(report, "INFO", snapshot, name, "short_comments", f"Có {short_comments:,} comments ngắn hơn {qa_config['comments']['short_comment_warning_length']} ký tự.")

    if review_negative_count:
        add(report, "WARNING", snapshot, name, "negative_number_of_reviews", f"Có {review_negative_count:,} number_of_reviews âm.")
    if review_score_invalid:
        add(report, "WARNING", snapshot, name, "review_scores_rating_range", f"Có {review_score_invalid:,} review_scores_rating ngoài {qa_config['review_score']['min']}–{qa_config['review_score']['max']}.");

    if duplicate_rows:
        add(report, "WARNING", snapshot, name, "duplicate_rows_within_chunk", f"[PHẠM VI: CHỈ TRONG CHUNK] Có {duplicate_rows:,} dòng trùng hoàn toàn tại chuỗi dữ liệu đang xử lý.")
        add(report, "WARNING", snapshot, name, "duplicate_rows_within_chunk_only", f"[PHẠM VI: TOÀN BỘ FILE] Có {duplicate_rows:,} dòng trùng hoàn toàn trong toàn bộ file, phát hiện qua nhiều chunk.")
    else:
        add(report, "PASS", snapshot, name, "duplicate_rows_within_chunk", "[PHẠM VI: CHỈ TRONG CHUNK] Không phát hiện dòng trùng hoàn toàn.")
        add(report, "PASS", snapshot, name, "duplicate_rows_within_chunk_only", "[PHẠM VI: TOÀN BỘ FILE] Không phát hiện dòng trùng hoàn toàn trong toàn bộ file.")

    if clean and output_path is not None:
        add(report, "INFO", snapshot, name, "cleaned_output", f"Đã ghi bản làm sạch vào {output_path.relative_to(PROJECT_ROOT)}; dữ liệu gốc được giữ nguyên.")


def check_geojson(path, snapshot, report):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict) or data.get("type") != "FeatureCollection":
            add(report, "ERROR", snapshot, path.name, "geojson_type", "GeoJSON phải có type=FeatureCollection.")
            return
        features = data.get("features")
        if not isinstance(features, list):
            add(report, "ERROR", snapshot, path.name, "geojson_features", "Trường features không phải danh sách.")
            return
        invalid = 0
        missing_geometry = 0
        for feature in features:
            if not isinstance(feature, dict) or feature.get("type") != "Feature":
                invalid += 1
                continue
            geom = feature.get("geometry")
            if not isinstance(geom, dict) or not geom.get("type") or geom.get("coordinates") is None:
                missing_geometry += 1
        add(report, "INFO", snapshot, path.name, "geojson_feature_count", f"Có {len(features):,} features.")
        add(report, "WARNING" if invalid else "PASS", snapshot, path.name, "geojson_features", f"Feature không hợp lệ: {invalid:,}.")
        add(report, "WARNING" if missing_geometry else "PASS", snapshot, path.name, "geojson_geometry", f"Feature thiếu geometry/tọa độ: {missing_geometry:,}.")
    except Exception as exc:
        add(report, "ERROR", snapshot, path.name, "geojson_read", f"Không đọc được GeoJSON: {exc}")



def write_reports(report, output_dir):
    """
    Export QA results into a standardized CSV report.

    Supports CHECK_LEVEL and RECORD_LEVEL reports.
    Preserves backward compatibility with the old record_id field.
    """

    output_dir.mkdir(parents=True, exist_ok=True)

    summary = {
        level: sum(
            str(item.get("level", "")).upper() == level
            for item in report
        )
        for level in LEVELS
    }

    csv_path = output_dir / "qa_report.csv"

    rows = []
    seen = set()

    for item in report:
        status = str(item.get("level", "PASS")).upper()

        raw_check_name = str(item.get("check", ""))
        check_name = normalize_check_name(
            raw_check_name,
            item.get("file", "")
        )

        message = str(item.get("message", ""))

        flag, severity, action = map_quality_flag(
            raw_check_name,
            status,
            message
        )

        report_level = str(
            item.get("report_level", "CHECK_LEVEL")
        ).upper()

        if report_level not in {"RECORD_LEVEL", "CHECK_LEVEL"}:
            report_level = "CHECK_LEVEL"

        record_id = str(item.get("record_id", "") or "")

        # Use listing_id as the standardized record identifier.
        listing_id = str(item.get("listing_id", "") or "")

        # Backward compatibility with existing add() calls.
        if not listing_id and report_level == "RECORD_LEVEL":
            listing_id = record_id

        date = str(item.get("date", "") or "")
        price = str(item.get("price", "") or "")

        # Summary rows do not represent individual records.
        if report_level == "CHECK_LEVEL":
            listing_id = ""
            price = ""
            record_id = ""

        # A record-level issue affects one individual record.
        if report_level == "RECORD_LEVEL":
            affected_rows = 1
        else:
            affected_rows = extract_affected_rows(
                raw_check_name,
                status,
                message
            )

        row = {
            "snapshot": str(item.get("snapshot", "")),
            "date": date,
            "report_level": report_level,
            "entity_type": normalize_entity_type(
                item.get("file", "")
            ),
            "listing_id": listing_id,
            "price": price,
            "check_name": check_name,
            "status": status,
            "flag": flag,
            "severity": severity,
            "action_required": action,
            "affected_rows": affected_rows,
            "message": message,

            # Temporary compatibility field.
            "record_id": record_id,
        }

        dedupe_key = (
            row["snapshot"],
            row["date"],
            row["report_level"],
            row["entity_type"],
            row["listing_id"],
            row["price"],
            row["check_name"],
            row["status"],
            row["flag"],
            row["message"],
        )

        if dedupe_key in seen:
            continue

        seen.add(dedupe_key)
        rows.append(row)

    columns = [
        "snapshot",
        "date",
        "report_level",
        "entity_type",
        "listing_id",
        "price",
        "check_name",
        "status",
        "flag",
        "severity",
        "action_required",
        "affected_rows",
        "message",
        "record_id",
    ]

    df = pd.DataFrame(rows, columns=columns)

    df = df.drop_duplicates(
        subset=[
            "snapshot",
            "date",
            "report_level",
            "entity_type",
            "listing_id",
            "price",
            "check_name",
            "status",
            "flag",
            "message",
        ],
        keep="first",
    )

    df.to_csv(
        csv_path,
        index=False,
        encoding="utf-8-sig"
    )

    print("\n=== QA SUMMARY ===")

    for level, count in summary.items():
        print(f"{level}: {count}")

    print(f"\nReport saved to: {csv_path}")

    return csv_path



def _normalize_report_token(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = str(value).strip()
    return text.upper() if text else ""


def _is_no_action_required(action_value: Any) -> bool:
    action = _normalize_report_token(action_value)
    if not action:
        return True
    no_action_values = {
        "NONE",
        "NO",
        "N/A",
        "NA",
        "NOT_REQUIRED",
        "NOT_NEEDED",
        "IGNORE",
        "OK",
        "PASS",
        "ACCEPTED",
        "ALLOWED",
        "ALLOWABLE",
        "OPTIONAL",
        "NO_ACTION",
    }
    return action in no_action_values


def _is_explicit_optional_required(row: dict[str, Any]) -> bool:
    flag = _normalize_report_token(row.get("flag"))
    if flag != "MISSING_OPTIONAL_FIELD":
        return False
    action_required = _normalize_report_token(row.get("action_required"))
    if action_required in OPTIONAL_REQUIRED_ACTIONS:
        return True
    check_name = str(row.get("check_name", "")).strip().lower()
    return check_name in OPTIONAL_REQUIRED_CHECKS


def _is_actionable_report_row(row: dict[str, Any]) -> bool:
    status = _normalize_report_token(row.get("status"))
    flag = _normalize_report_token(row.get("flag"))
    action_required = _normalize_report_token(row.get("action_required"))

    if not status and not flag and not action_required:
        return False

    if status in {"INFO", "PASS", "NONE"} or flag in {"", "NONE", "PASS", "INFO", "MISSING_OPTIONAL_FIELD"}:
        return False

    if _is_no_action_required(action_required):
        return False

    if flag in ACTIONABLE_FLAGS:
        return True

    return status in {"ERROR", "WARNING"} and not _is_no_action_required(action_required)


def _final_actionable_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    filtered = df[df.apply(_is_actionable_report_row, axis=1)].copy()
    return filtered.reset_index(drop=True)


def run_qa(config_path=DEFAULT_CONFIG, clean=None):
    config_path = Path(config_path)
    if not config_path.is_absolute():
        config_path = PROJECT_ROOT / config_path
    config = read_config(config_path)
    qa_config = load_qa_config(config)

    data_root = Path(config.get("data_root", {}).get("raw", "data/raw"))
    if not data_root.is_absolute():
        data_root = PROJECT_ROOT / data_root

    processed_root = resolve_project_path(qa_config["files"]["processed_dir"], PROJECT_ROOT)
    report_dir = resolve_project_path(qa_config["files"]["report_dir"], PROJECT_ROOT)
    report_filename = qa_config["files"]["report_filename"]
    snapshots = config.get("snapshots", [])
    report = []

    if not snapshots:
        add(report, "ERROR", "-", "-", "snapshots_config", "Không có snapshot nào trong YAML.")
        write_reports(report, report_dir, report_filename)
        return report

    discovered_snapshots = [str(s).strip() for s in snapshots]
    print(f"Discovered snapshots: {discovered_snapshots}")
    latest_snapshot = latest_snapshot_name(discovered_snapshots)
    print(f"Selected latest snapshot: {latest_snapshot}")
    snapshot_value = str(latest_snapshot)
    snapshot_dir = data_root / snapshot_value
    print(f"\nProcessing snapshot: {snapshot_value}")

    if not snapshot_dir.is_dir():
        add(report, "ERROR", snapshot_value, "-", "snapshot_exists", f"Không tìm thấy thư mục {snapshot_dir}."
        )
        write_reports(report, report_dir, report_filename)
        return report

    add(report, "PASS", snapshot_value, "-", "snapshot_exists", "Thư mục snapshot tồn tại.")

    required_files = list(qa_config["files"]["required"])
    optional_files = list(qa_config["files"]["optional"])
    effective_clean = qa_config["clean"] if clean is None else bool(clean)

    for filename in required_files + optional_files:
        path = snapshot_dir / filename
        if not path.is_file():
            level = "ERROR" if filename in required_files else "WARNING"
            add(report, level, snapshot_value, filename, "file_exists", "Thiếu file; kiểm tra tên file/đường dẫn và tải lại nếu cần.")
            continue
        add(report, "PASS", snapshot_value, filename, "file_exists", "File tồn tại.")
        if filename.endswith(".csv"):
            check_csv(
                path,
                snapshot_value,
                report,
                min_length=int(qa_config["comments"]["min_length"]),
                clean=effective_clean and filename in {"listings.csv", "calendar.csv", "reviews.csv"},
                processed_root=processed_root,
                qa_config=qa_config,
            )
        elif filename.endswith(".geojson"):
            check_geojson(path, snapshot_value, report)

    csv_path = write_reports(report, report_dir, report_filename)
    source_listing_path = snapshot_dir / "listings.csv"
    if source_listing_path.exists():
        validate_record_level_ids(csv_path, source_listing_path)
    if effective_clean:
        print(f"Cleaned CSV files (where source files exist) are saved under: {processed_root}")
    return report


if __name__ == "__main__":
    run_qa()