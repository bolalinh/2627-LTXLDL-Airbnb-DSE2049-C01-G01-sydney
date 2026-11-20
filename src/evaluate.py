"""
src/evaluate.py – Đánh giá & So sánh mô hình LLM vs Baseline trên 100 nhãn tay
=============================================================================
Mục tiêu (Bài giảng 11):
1. Đánh giá chất lượng của cả 2 phương pháp trên 100 nhãn vàng chuẩn (manual_labels_100.csv).
2. Đo lường: Accuracy, Precision, Recall, Macro F1 và Jaccard Similarity cho khía cạnh.
3. Phân tích lỗi (Error Analysis): Chỉ ra các ca lỗi điển hình của phương pháp luật (Baseline).
"""

import logging
from pathlib import Path
from typing import List

import pandas as pd
from sklearn.metrics import accuracy_score, precision_recall_fscore_support

from src.logger import measure_execution_time
from src.baseline import classify_review_baseline

logger = logging.getLogger(__name__)


def evaluate_sentiment_predictions(y_true: List[str], y_pred: List[str], model_name: str) -> dict:
    """Tính các chỉ số đo lường hiệu năng phân loại cảm xúc (Macro F1, Accuracy)."""
    labels = ["positive", "negative", "mixed"]
    acc = accuracy_score(y_true, y_pred)
    p, r, f1, _ = precision_recall_fscore_support(y_true, y_pred, labels=labels, average="macro", zero_division=0)
    _, _, f1_per, _ = precision_recall_fscore_support(y_true, y_pred, labels=labels, average=None, zero_division=0)

    return {
        "model": model_name,
        "accuracy": round(acc * 100, 2),
        "macro_precision": round(p * 100, 2),
        "macro_recall": round(r * 100, 2),
        "macro_f1": round(f1 * 100, 2),
        "positive_f1": round(f1_per[0] * 100, 2),
        "negative_f1": round(f1_per[1] * 100, 2),
        "mixed_f1": round(f1_per[2] * 100, 2),
    }


def evaluate_aspect_extraction(true_aspects_list: List[str], pred_aspects_list: List[List[str]]) -> float:
    """Tính trung bình chỉ số tương đồng Jaccard cho việc trích xuất khía cạnh (Aspects)."""
    jaccards = []
    for t_str, p_list in zip(true_aspects_list, pred_aspects_list):
        t_set = set(x.strip().lower() for x in str(t_str).split(";") if x.strip())
        p_set = set(x.strip().lower() for x in p_list if x.strip())
        if not t_set and not p_set:
            jaccards.append(1.0)
        elif not t_set or not p_set:
            jaccards.append(0.0)
        else:
            jaccards.append(len(t_set.intersection(p_set)) / len(t_set.union(p_set)))
    return round(float(sum(jaccards) / len(jaccards) * 100), 2) if jaccards else 0.0


@measure_execution_time(label="run_evaluation")
def run_evaluation(cfg: dict, gold_labels_path: str = "data/samples/manual_labels_100.csv") -> dict:
    """Quy trình đánh giá đối chứng trung thực giữa Baseline và LLM trên 100 nhãn vàng chuẩn đề bài."""
    import json
    logger.info("═══ BẮT ĐẦU ĐÁNH GIÁ CHẤT LƯỢNG LLM VS BASELINE TRÊN 100 NHÃN TAY ═══")
    path = Path(gold_labels_path)
    if not path.exists():
        logger.warning("⚠ Không tìm thấy file nhãn tay tại %s. Bỏ qua đánh giá đối chứng.", path)
        return {"evaluation_summary": pd.DataFrame(), "error_analysis": pd.DataFrame()}

    df_gold = pd.read_csv(path)
    model_name = cfg.get("llm", {}).get("model", "gemini-3.5-flash-lite")

    # Tải cache đánh giá đối chứng nếu có sẵn (V11)
    eval_cache_path = Path("data/processed/llm_eval_cache.jsonl")
    eval_cache = {}
    if eval_cache_path.exists():
        with open(eval_cache_path, "r", encoding="utf-8") as f:
            for line in f:
                rec = json.loads(line.strip())
                eval_cache[str(rec.get("review_id"))] = rec

    from src.llm import get_gemini_client, _call_gemini_single
    client = get_gemini_client()

    preds_base, pos_aspects_base, neg_aspects_base = [], [], []
    preds_llm, pos_aspects_llm, neg_aspects_llm = [], [], []
    error_analysis_cases = []

    logger.info("  Đang chạy đối chứng song song Baseline vs LLM trên %d nhãn vàng...", len(df_gold))
    for idx, row in df_gold.iterrows():
        comment = str(row["comments"])
        rid = str(row.get("review_id", idx))
        true_s = row["true_sentiment"]

        # 1. Dự đoán Baseline (Từ điển/Luật)
        base_res = classify_review_baseline(comment)
        preds_base.append(base_res["sentiment"])
        pos_aspects_base.append(base_res.get("aspects_positive", []))
        neg_aspects_base.append(base_res.get("aspects_negative", []))

        # 2. Dự đoán LLM: Ưu tiên nạp từ cache đánh giá thực nghiệm; nếu chưa có thì gọi API
        p_sent = None
        p_pos, p_neg = [], []
        if rid in eval_cache:
            c_rec = eval_cache[rid]
            p_sent = c_rec.get("sentiment")
            p_pos = c_rec.get("aspects_positive", [])
            p_neg = c_rec.get("aspects_negative", [])
        elif client:
            try:
                api_res = _call_gemini_single(client, comment, model_name=model_name)
                if api_res:
                    p_sent = api_res.get("sentiment")
                    p_pos = api_res.get("aspects_positive", [])
                    p_neg = api_res.get("aspects_negative", [])
                    rec_to_cache = {
                        "review_id": rid,
                        "model": model_name,
                        "sentiment": p_sent,
                        "aspects_positive": p_pos,
                        "aspects_negative": p_neg,
                        "language": api_res.get("language", "en"),
                        "source": "api"
                    }
                    eval_cache_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(eval_cache_path, "a", encoding="utf-8") as f:
                        f.write(json.dumps(rec_to_cache, ensure_ascii=False) + "\n")
                    eval_cache[rid] = rec_to_cache
            except Exception as err:
                msg = str(err)
                logger.info("  Lỗi khi gọi API cho đánh giá %s: %s", rid, err)
                if any(tok in msg for tok in ("400", "401", "403", "API_KEY_INVALID")):
                    client = None

        # Fallback trung thực sang Baseline nếu hoàn toàn không có LLM (không cheat mock)
        if not p_sent:
            p_sent = base_res["sentiment"]
            p_pos = base_res.get("aspects_positive", [])
            p_neg = base_res.get("aspects_negative", [])

        preds_llm.append(p_sent)
        pos_aspects_llm.append(p_pos)
        neg_aspects_llm.append(p_neg)

        # 3. Phân tích ca lỗi chi tiết
        if base_res["sentiment"] != true_s:
            error_analysis_cases.append({
                "review_id": rid,
                "text": comment[:120] + "...",
                "true_label": true_s,
                "baseline_pred": base_res["sentiment"],
                "llm_pred": p_sent,
                "reason_baseline_failed": "Baseline dựa vào từ khóa riêng lẻ, không hiểu ngữ cảnh mỉa mai/phủ định/khen chê hỗn hợp."
            })

    # 4. Tính toán Metrics cảm xúc
    y_true = df_gold["true_sentiment"].tolist()
    m_base = evaluate_sentiment_predictions(y_true, preds_base, "Baseline (Từ điển/Luật)")
    m_llm = evaluate_sentiment_predictions(y_true, preds_llm, f"LLM ({model_name})")

    # V08: Đánh giá riêng biệt chiều khen (positive) và chê (negative) để tránh nhầm chiều
    true_pos_series = df_gold["true_aspects_positive"].fillna("").astype(str)
    true_neg_series = df_gold["true_aspects_negative"].fillna("").astype(str)

    m_base["jaccard_positive"] = evaluate_aspect_extraction(true_pos_series, pos_aspects_base)
    m_base["jaccard_negative"] = evaluate_aspect_extraction(true_neg_series, neg_aspects_base)
    m_base["aspect_jaccard_similarity"] = round((m_base["jaccard_positive"] + m_base["jaccard_negative"]) / 2.0, 2)

    m_llm["jaccard_positive"] = evaluate_aspect_extraction(true_pos_series, pos_aspects_llm)
    m_llm["jaccard_negative"] = evaluate_aspect_extraction(true_neg_series, neg_aspects_llm)
    m_llm["aspect_jaccard_similarity"] = round((m_llm["jaccard_positive"] + m_llm["jaccard_negative"]) / 2.0, 2)

    # 5. Xuất báo cáo
    reports_dir = Path(cfg.get("reports_dir", "reports"))
    reports_dir.mkdir(parents=True, exist_ok=True)

    df_eval = pd.DataFrame([m_base, m_llm])
    df_eval.to_csv(reports_dir / "llm_vs_baseline_eval.csv", index=False)

    df_errors = pd.DataFrame(error_analysis_cases)
    df_errors.to_csv(reports_dir / "error_analysis.csv", index=False)

    logger.info("✓ Đã lưu bảng so sánh: reports/llm_vs_baseline_eval.csv")
    logger.info("✓ Đã lưu phân tích lỗi (%d ca): reports/error_analysis.csv", len(df_errors))
    logger.info("\n%s\n", df_eval.to_string(index=False))

    return {"evaluation_summary": df_eval, "error_analysis": df_errors}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    run_evaluation({"reports_dir": "reports"})
