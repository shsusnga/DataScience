from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable, List

import numpy as np
import pandas as pd


SUBJECTS = [
    "toan",
    "ngu_van",
    "ngoai_ngu",
    "vat_li",
    "hoa_hoc",
    "sinh_hoc",
    "lich_su",
    "dia_li",
    "gdcd",
]

SCIENCE_SUBJECTS = ["toan", "vat_li", "hoa_hoc", "sinh_hoc"]
HUMANITY_SUBJECTS = ["ngu_van", "lich_su", "dia_li", "gdcd"]
LANG_SUBJECTS = ["ngoai_ngu"]


def read_cleaned_csvs(cleaned_dir: Path) -> pd.DataFrame:
    """Đọc và nối tất cả file cleaned_<nam>.csv trong thư mục data/cleaned."""
    files = sorted(cleaned_dir.glob("cleaned_*.csv"))
    if not files:
        raise FileNotFoundError(f"Không tìm thấy file cleaned_*.csv trong: {cleaned_dir}")

    frames = []
    for file in files:
        df = pd.read_csv(file)
        frames.append(df)

    combined = pd.concat(frames, ignore_index=True)
    return combined


def coerce_numeric_scores(df: pd.DataFrame, subject_cols: Iterable[str]) -> pd.DataFrame:
    """Chuyển các cột điểm sang numeric, giữ NaN nếu thiếu."""
    out = df.copy()
    for col in subject_cols:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
    return out


def add_subject_summary_features(df: pd.DataFrame) -> pd.DataFrame:
    """Tạo các feature tổng hợp từ các điểm môn."""
    out = df.copy()

    subject_cols = [c for c in SUBJECTS if c in out.columns]
    if not subject_cols:
        raise ValueError("Không tìm thấy cột điểm môn nào trong dữ liệu đầu vào.")

    score_df = out[subject_cols].copy()

    out["avg_score"] = score_df.mean(axis=1)
    out["score_std"] = score_df.std(axis=1, ddof=0)
    out["score_min"] = score_df.min(axis=1)
    out["score_max"] = score_df.max(axis=1)

    out["num_subject_above_7"] = (score_df > 7).sum(axis=1)
    out["num_subject_above_8"] = (score_df > 8).sum(axis=1)
    out["num_subject_above_9"] = (score_df > 9).sum(axis=1)
    out["num_subject_missing"] = score_df.isna().sum(axis=1)

    # Tìm môn tốt nhất / yếu nhất
    out["best_subject"] = score_df.idxmax(axis=1)
    out["weakest_subject"] = score_df.idxmin(axis=1)

    # Điểm trung bình theo nhóm môn
    science_cols = [c for c in SCIENCE_SUBJECTS if c in score_df.columns]
    humanity_cols = [c for c in HUMANITY_SUBJECTS if c in score_df.columns]
    lang_cols = [c for c in LANG_SUBJECTS if c in score_df.columns]

    if science_cols:
        out["science_avg"] = score_df[science_cols].mean(axis=1)
    else:
        out["science_avg"] = np.nan

    if humanity_cols:
        out["humanity_avg"] = score_df[humanity_cols].mean(axis=1)
    else:
        out["humanity_avg"] = np.nan

    if lang_cols:
        out["language_avg"] = score_df[lang_cols].mean(axis=1)
    else:
        out["language_avg"] = np.nan

    # Điểm chênh lệch giữa Toán và Ngoại ngữ
    if "toan" in out and "ngoai_ngu" in out:
        out["math_language_gap"] = out["toan"] - out["ngoai_ngu"]
    else:
        out["math_language_gap"] = np.nan

    # Tính tổng điểm trên 9 môn (nếu có đầy đủ)
    out["total_score"] = score_df.sum(axis=1)

    # Tạo nhãn ban đầu cho mô hình phân loại (có thể dùng trực tiếp hoặc bỏ đi)
    out["label_top_student"] = (out["avg_score"] >= 8.0).astype(int)
    out["label_excellent"] = (out["avg_score"] >= 9.0).astype(int)
    out["label_good"] = (out["avg_score"] >= 7.0).astype(int)

    return out


def add_province_features(df: pd.DataFrame) -> pd.DataFrame:
    """Tạo feature dựa trên mã tỉnh nếu cột `tinh` có dạng 2 chữ số đầu trong SBD."""
    out = df.copy()
    if "tinh" not in out.columns:
        return out

    # Chuyển về numeric nếu có thể, nếu không giữ nguyên text
    out["tinh_numeric"] = pd.to_numeric(out["tinh"], errors="coerce")
    out["tinh_is_valid"] = out["tinh_numeric"].notna().astype(int)

    # Tạo nhóm tỉnh dựa trên mức độ điểm trung bình địa phương (được tính sau khi feature đã có)
    if "avg_score" in out.columns:
        province_avg = out.groupby("tinh_numeric", dropna=True)["avg_score"].transform("mean")
        out["province_avg_score"] = province_avg
        out["province_score_gap"] = out["avg_score"] - out["province_avg_score"]

    return out


def add_year_features(df: pd.DataFrame) -> pd.DataFrame:
    """Chuẩn hóa năm và thêm feature chu kỳ / trend nếu có cột nam."""
    out = df.copy()
    if "nam" in out.columns:
        out["nam"] = pd.to_numeric(out["nam"], errors="coerce")
        out["year_since_2018"] = out["nam"] - 2018
    return out


def build_feature_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """Pipeline chuẩn: đọc, chuẩn hóa, engineering, trả về DataFrame sẵn dùng cho mô hình."""
    out = coerce_numeric_scores(df, SUBJECTS)
    out = add_subject_summary_features(out)
    out = add_province_features(out)
    out = add_year_features(out)

    # Sắp xếp lại cột để dễ train model hơn
    preferred_cols = [
        "sbd",
        "nam",
        "tinh",
        "tinh_numeric",
        "avg_score",
        "score_std",
        "score_min",
        "score_max",
        "total_score",
        "num_subject_above_7",
        "num_subject_above_8",
        "num_subject_above_9",
        "num_subject_missing",
        "best_subject",
        "weakest_subject",
        "science_avg",
        "humanity_avg",
        "language_avg",
        "math_language_gap",
        "province_avg_score",
        "province_score_gap",
        "year_since_2018",
        "label_top_student",
        "label_excellent",
        "label_good",
        *SUBJECTS,
    ]

    # Chỉ giữ cột tồn tại
    final_cols = [c for c in preferred_cols if c in out.columns]
    out = out[final_cols]
    return out


def save_engineered_dataset(df: pd.DataFrame, output_path: Path) -> None:
    """Lưu dữ liệu feature-engineered dưới dạng CSV."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")


def main() -> None:
    parser = argparse.ArgumentParser(description="Feature Engineering cho dữ liệu điểm thi THPT Quốc gia")
    parser.add_argument(
        "--input-dir",
        type=str,
        default="data/cleaned",
        help="Thư mục chứa các file cleaned_<nam>.csv",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/engineered/feature_engineered.csv",
        help="Đường dẫn file CSV đầu ra",
    )
    args = parser.parse_args()

    cleaned_dir = Path(args.input_dir).resolve()
    output_path = Path(args.output).resolve()

    df = read_cleaned_csvs(cleaned_dir)
    engineered = build_feature_dataset(df)
    save_engineered_dataset(engineered, output_path)

    print(f"Đọc dữ liệu gốc: {len(df):,} dòng")
    print(f"Số cột sau feature engineering: {engineered.shape[1]}")
    print(f"Đã lưu: {output_path}")
    print("Các feature chính: avg_score, score_std, num_subject_above_8, science_avg, humanity_avg, province_avg_score")


if __name__ == "__main__":
    main()
