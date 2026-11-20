"""
src/llm.py – Phân tích đánh giá bằng Gemini API & Lưu đệm Cache JSONL
=====================================================================
Nguyên lý thiết kế (Bài giảng 11):
1. Ràng buộc Schema có cấu trúc: Dùng Pydantic BaseModel định hình đầu ra chuẩn xác.
2. Cache-First Pattern: Lưu vào data/processed/llm_cache.jsonl, kiểm tra trước khi gọi API.
3. Lấy mẫu phân tầng (Stratified Sampling): Đại diện đồng đều theo từng khu vực tại Sydney.
4. Dự phòng an toàn (Graceful Fallback): Tự động chuyển sang Rule-based Baseline khi cúp mạng/hết quota.
5. Ước tính chi phí: Dự phóng lượng token và chi phí USD toàn thành phố Sydney.
"""

import hashlib
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

import pandas as pd
from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.logger import measure_execution_time

logger = logging.getLogger(__name__)
DEFAULT_MODEL = "gemini-3.5-flash-lite"
DEFAULT_ASPECTS = ["vị trí", "sạch sẽ", "chủ nhà", "giá trị", "tiện nghi", "độ ồn", "an toàn", "giao thông"]
VALID_SENTIMENTS = {"positive", "negative", "mixed"}


def compute_text_hash(text: str) -> str:
    """Băm SHA256 16 ký tự để xác thực tính toàn vẹn của nội dung bình luận trong cache (V11)."""
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()[:16]


# ══════════════════════════════════════════════════════════════
# 1. PYDANTIC SCHEMA ĐẦU RA CÓ CẤU TRÚC (BÀI 11)
# ══════════════════════════════════════════════════════════════

class ReviewAnalysis(BaseModel):
    sentiment: Literal["positive", "negative", "mixed"] = Field(
        description="Cảm xúc tổng thể của đánh giá: 'positive', 'negative' hoặc 'mixed'."
    )
    aspects_positive: List[str] = Field(
        default_factory=list,
        description="Danh sách các khía cạnh dịch vụ được khen ngợi."
    )
    aspects_negative: List[str] = Field(
        default_factory=list,
        description="Danh sách các khía cạnh dịch vụ bị phàn nàn/chê."
    )
    language: str = Field(
        default="en",
        description="Mã ngôn ngữ 2 ký tự ISO 639-1 (ví dụ: en, vi, zh, fr, es) hoặc 'und'."
    )


# ══════════════════════════════════════════════════════════════
# 2. HỆ THỐNG LƯU ĐỆM CACHE JSONL (ĐẢM BẢO TÁI LẬP & TIẾT KIỆM)
# ══════════════════════════════════════════════════════════════

def load_cache(cache_file: Path) -> Dict[str, dict]:
    """Tải toàn bộ kết quả đã lưu trong file cache JSONL vào bộ nhớ."""
    cache: Dict[str, dict] = {}
    if cache_file.exists():
        with open(cache_file, "r", encoding="utf-8") as f:
            for line in f:
                line_str = line.strip()
                if line_str:
                    try:
                        record = json.loads(line_str)
                        cache[str(record.get("review_id"))] = record
                    except Exception:
                        continue
        logger.info("  ✓ Đã nạp %d bản ghi từ cache %s", len(cache), cache_file.name)
    return cache


def append_to_cache(cache_file: Path, record: dict) -> None:
    """Ghi bổ sung một bản ghi phân tích vào file JSONL."""
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


# ══════════════════════════════════════════════════════════════
# 3. KẾT NỐI GEMINI API & TRÍCH XUẤT CÓ CẤU TRÚC
# ══════════════════════════════════════════════════════════════

def get_gemini_client(model_name: str = DEFAULT_MODEL) -> Optional[Any]:
    """Khởi tạo Client kết nối Gemini API từ biến môi trường hoặc .env."""
    try:
        from dotenv import load_dotenv
        load_dotenv(PROJECT_ROOT / ".env", override=False)
    except ImportError:
        pass

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key or api_key == "your_gemini_api_key_here":
        logger.warning("⚠ Không tìm thấy biến môi trường GEMINI_API_KEY hợp lệ!")
        return None

    # Ưu tiên SDK google-genai mới chính thức
    try:
        from google import genai
        return genai.Client(api_key=api_key)
    except ImportError:
        pass

    # Fallback thư viện legacy google-generativeai
    try:
        import google.generativeai as genai_legacy
        genai_legacy.configure(api_key=api_key)
        return genai_legacy.GenerativeModel(model_name)
    except ImportError:
        logger.warning("⚠ Chưa cài thư viện google-genai hoặc google-generativeai.")
        return None


def _normalize_analysis(payload: dict, aspects: List[str]) -> dict:
    """Chuẩn hóa dữ liệu đầu ra từ LLM bảo đảm tính toàn vẹn."""
    sentiment = str(payload.get("sentiment", "mixed")).strip().lower()
    if sentiment == "neutral" or sentiment not in VALID_SENTIMENTS:
        sentiment = "mixed"

    allowed = set(a.lower() for a in aspects)

    def _filter_aspects(items):
        if not isinstance(items, list):
            return []
        res = []
        for x in items:
            s = str(x).strip().lower()
            if s in allowed and s not in res and s not in ("nan", "none", "null", ""):
                res.append(s)
        return res

    raw_lang = str(payload.get("language", "und")).strip().lower()
    lang = raw_lang if (len(raw_lang) == 2 and raw_lang.isalpha()) else "und"

    return {
        "sentiment": sentiment,
        "aspects_positive": _filter_aspects(payload.get("aspects_positive")),
        "aspects_negative": _filter_aspects(payload.get("aspects_negative")),
        "language": lang,
    }


_LAST_CALL_TIME = 0.0

def _rate_limit_delay(min_interval: float = 0.1) -> None:
    """Đảm bảo tốc độ gọi API tối ưu (mặc định 0.1s cho tài khoản trả phí)."""
    global _LAST_CALL_TIME
    elapsed = time.time() - _LAST_CALL_TIME
    if elapsed < min_interval:
        time.sleep(min_interval - elapsed)
    _LAST_CALL_TIME = time.time()


def _call_gemini_single(
    client: Any,
    text: str,
    model_name: str = DEFAULT_MODEL,
    temperature: float = 0.0,
    aspects: Optional[List[str]] = None,
    max_retries: int = 3,
    delay: float = 0.1,
    **kwargs
) -> Optional[dict]:
    """Gọi Gemini API trích xuất có cấu trúc, có Rate Limiting & Auto-Backoff chống lỗi 429."""
    aspect_list = aspects or DEFAULT_ASPECTS
    aspects_str = ", ".join(f"'{a}'" for a in aspect_list)
    prompt = (
        f"Bạn là chuyên gia phân tích dữ liệu cho chủ nhà Airbnb.\n"
        f"Hãy phân tích đánh giá sau và trả về JSON đúng schema:\n"
        f"1. sentiment: 'positive', 'negative' hoặc 'mixed'.\n"
        f"2. aspects_positive: danh sách khía cạnh khen ngợi (chọn trong: {aspects_str}).\n"
        f"3. aspects_negative: danh sách khía cạnh phàn nàn (chọn trong: {aspects_str}).\n"
        f"4. language: mã ngôn ngữ 2 ký tự ISO 639-1 (en, vi, zh...) hoặc 'und'.\n\n"
        f"Đánh giá:\n\"\"\"{text}\"\"\""
    )

    for attempt in range(max_retries):
        _rate_limit_delay(delay)  # Nhịp gọi tối ưu theo tài khoản
        try:
            if hasattr(client, "models"):
                from google.genai import types
                cfg = types.GenerateContentConfig(
                    temperature=temperature,
                    response_mime_type="application/json",
                    response_schema=ReviewAnalysis,
                )
                res = client.models.generate_content(model=model_name, contents=prompt, config=cfg)
                data = res.parsed.model_dump() if getattr(res, "parsed", None) else json.loads(res.text)
            else:
                res = client.generate_content(
                    prompt,
                    generation_config={"temperature": temperature, "response_mime_type": "application/json"}
                )
                data = json.loads(res.text)

            return _normalize_analysis(data, aspect_list)
        except Exception as e:
            msg = str(e)
            if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
                # Tự động đợi 15 giây để Google reset hạn mức 1 phút rồi thử lại
                logger.info("  [Rate Limit 15 RPM]: Google yêu cầu tạm nghỉ, tự động đợi 15s rồi thử lại lần %d/%d...", attempt + 1, max_retries)
                time.sleep(15.0)
                continue
            if any(tok in msg for tok in ("400", "401", "403", "404", "API_KEY_INVALID")):
                logger.warning("  Lỗi cố định khi gọi Gemini (%s): %s", model_name, e)
                raise
            if attempt == max_retries - 1:
                logger.warning("  Không thể kết nối Gemini sau %d lần thử: %s", max_retries, e)
                return None
            time.sleep(2.0)
    return None


# ══════════════════════════════════════════════════════════════
# 4. LẤY MẪU PHÂN TẦNG & DỰ PHÓNG CHI PHÍ
# ══════════════════════════════════════════════════════════════

@measure_execution_time(label="sample_reviews_stratified")
def sample_reviews_stratified(
    reviews_df: pd.DataFrame,
    listings_df: pd.DataFrame,
    sample_size: int = 1000,
    seed: int = 42,
) -> pd.DataFrame:
    """Lấy mẫu phân tầng (Stratified Sampling) theo khu vực (neighbourhood)."""
    logger.info("  Thực hiện lấy mẫu phân tầng %d đánh giá theo khu vực...", sample_size)
    if "neighbourhood_cleansed" in listings_df.columns and "listing_id" in reviews_df.columns:
        areas = listings_df[["id", "neighbourhood_cleansed"]].drop_duplicates("id").rename(columns={"id": "listing_id"})
        merged = reviews_df.merge(areas, on="listing_id", how="inner")
        if len(merged) <= sample_size:
            return merged.copy()

        # Phân bổ tỷ lệ mẫu theo từng khu vực
        total = len(merged)
        sampled = merged.groupby("neighbourhood_cleansed", group_keys=False).apply(
            lambda g: g.sample(n=max(1, int(len(g) / total * sample_size)), random_state=seed)
        )
        if len(sampled) < sample_size:
            rem = merged.drop(index=sampled.index, errors="ignore")
            extra = rem.sample(n=min(len(rem), sample_size - len(sampled)), random_state=seed)
            sampled = pd.concat([sampled, extra], ignore_index=True)
        return sampled.head(sample_size).reset_index(drop=True)

    return reviews_df.sample(n=min(sample_size, len(reviews_df)), random_state=seed).copy()


def estimate_total_sydney_cost(total_reviews_count: int = 801398, avg_words_per_review: float = 40.0) -> dict:
    """Ước tính lượng Token và chi phí USD nếu chạy toàn bộ đánh giá của Sydney theo giá Gemini 3.5 Flash Lite (Đồng bộ V10)."""
    tokens_in = total_reviews_count * (avg_words_per_review * 1.3 + 150)
    tokens_out = total_reviews_count * 60
    # Đơn giá Gemini 3.5 Flash Lite: $0.075 / 1M input, $0.30 / 1M output
    cost_in = (tokens_in / 1_000_000) * 0.075
    cost_out = (tokens_out / 1_000_000) * 0.30
    total_tokens = int(tokens_in + tokens_out)
    total_cost = round(cost_in + cost_out, 2)
    return {
        "total_reviews": total_reviews_count,
        "est_total_input_tokens": int(tokens_in),
        "est_total_output_tokens": int(tokens_out),
        "est_total_tokens": total_tokens,
        "est_cost_input_usd": round(cost_in, 2),
        "est_cost_output_usd": round(cost_out, 2),
        "est_total_cost_usd": total_cost,
    }


# ══════════════════════════════════════════════════════════════
# 5. HÀM ĐIỀU PHỐI CHÍNH (ORCHESTRATOR)
# ══════════════════════════════════════════════════════════════

@measure_execution_time(label="process_reviews_with_llm")
def process_reviews_with_llm(
    reviews_sample: pd.DataFrame,
    cfg: dict,
    skip_llm: bool = False,
) -> pd.DataFrame:
    """Xử lý trích xuất LLM trên tập mẫu đánh giá kết hợp Cache và Baseline Fallback."""
    llm_cfg = cfg.get("llm", {})
    cache_path = PROJECT_ROOT / Path(llm_cfg.get("cache", "data/processed/llm_cache.jsonl"))
    model_name = llm_cfg.get("model", DEFAULT_MODEL)
    temperature = float(llm_cfg.get("temperature", 0.0))
    aspects = llm_cfg.get("aspects") or llm_cfg.get("schema", {}).get("aspects") or DEFAULT_ASPECTS
    max_api_calls = int(llm_cfg.get("max_api_calls", 1000))
    sleep_interval = float(llm_cfg.get("rate_limit_sleep", llm_cfg.get("sleep_seconds", 4.1)))

    cache = load_cache(cache_path)
    client = None if skip_llm else get_gemini_client(model_name=model_name)

    results = []
    new_api_calls, cache_hits = 0, 0
    logger.info("─── XỬ LÝ LLM (%s) CHO %d ĐÁNH GIÁ ───", model_name, len(reviews_sample))

    for idx, row in reviews_sample.iterrows():
        rid = str(row.get("id", row.get("review_id", idx)))
        raw_comment = row.get("comments", "")
        comment = "" if pd.isna(raw_comment) else str(raw_comment).strip()
        current_hash = compute_text_hash(comment)

        # 1. Kiểm tra cache trước (V11: Cache-First có kiểm tra tính hợp lệ của model và nội dung)
        cached_rec = cache.get(rid)
        if cached_rec:
            c_model = cached_rec.get("model", "")
            c_hash = cached_rec.get("text_hash", "")
            if (not c_model or c_model == model_name) and (not c_hash or c_hash == current_hash):
                # Re-normalize cached record to filter out stale "nan" strings
                cached_rec["aspects_positive"] = [
                    a for a in cached_rec.get("aspects_positive", [])
                    if isinstance(a, str) and a.strip().lower() not in ("nan", "none", "null", "")
                ]
                cached_rec["aspects_negative"] = [
                    a for a in cached_rec.get("aspects_negative", [])
                    if isinstance(a, str) and a.strip().lower() not in ("nan", "none", "null", "")
                ]
                results.append(cached_rec)
                cache_hits += 1
                continue

        # 2. Gọi API nếu có client và chưa chạm hạn mức
        parsed_record, used_api = None, False
        if client and new_api_calls < max_api_calls and len(comment) > 10:
            try:
                parsed_record = _call_gemini_single(
                    client, comment[:2000], model_name=model_name,
                    temperature=temperature, aspects=aspects, delay=sleep_interval
                )
                if parsed_record:
                    used_api = True
                    new_api_calls += 1
                else:
                    logger.warning("  Không thể gọi Gemini API (%s). Chuyển sang baseline fallback.", model_name)
                    client = None
            except Exception as err:
                logger.warning("  Sự cố gọi Gemini API (%s): %s. Tự động chuyển toàn bộ sang Baseline Fallback.", model_name, err)
                client = None
                parsed_record = None

        # 3. Fallback sang Rule-based Baseline nếu không dùng được API
        if parsed_record is None:
            from src.baseline import classify_review_baseline
            parsed_record = classify_review_baseline(comment)

        record = {
            "review_id": rid,
            "listing_id": row.get("listing_id"),
            "date": row.get("date"),
            "sentiment": parsed_record.get("sentiment", "positive"),
            "aspects_positive": parsed_record.get("aspects_positive", []),
            "aspects_negative": parsed_record.get("aspects_negative", []),
            "language": parsed_record.get("language", "en"),
            "source": "api" if used_api else "baseline_fallback",
            "model": model_name,
            "text_hash": current_hash,
        }

        if used_api:
            append_to_cache(cache_path, record)
            cache[rid] = record
        results.append(record)

    df_results = pd.DataFrame(results)
    logger.info("✓ Hoàn tất LLM: %d bản ghi (Cache: %d, API mới: %d, Baseline Fallback: %d)",
                len(df_results), cache_hits, new_api_calls, len(df_results) - cache_hits - new_api_calls)
    return df_results


if __name__ == "__main__":
    import argparse
    import yaml

    parser = argparse.ArgumentParser(description="Chạy module LLM phân tích review Airbnb.")
    parser.add_argument("--config", type=str, default="configs/sydney.yaml")
    parser.add_argument("--skip-llm", action="store_true")
    args = parser.parse_args()

    cfg_path = PROJECT_ROOT / args.config
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    sample_df = pd.read_csv(PROJECT_ROOT / "data/samples/manual_labels_100.csv").rename(columns={"review_id": "id"})
    res = process_reviews_with_llm(sample_df.head(10), cfg, skip_llm=args.skip_llm)
    print(res[["review_id", "sentiment", "source"]])
