"""
clean_data.py
=============
Script làm sạch dữ liệu điểm thi THPT Quốc gia.
Sử dụng hoàn toàn thư viện chuẩn Python (không cần pandas).

Input : data/raw.csv
Output: data/cleaned.csv
        data/cleaning_report.txt
"""

import csv
import os
from collections import defaultdict

# ── Cấu hình đường dẫn ──────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_PATH  = os.path.join(BASE_DIR, "data", "raw.csv")
OUTPUT_PATH = os.path.join(BASE_DIR, "data", "cleaned.csv")
REPORT_PATH = os.path.join(BASE_DIR, "data", "cleaning_report.txt")

# ── Cột điểm môn học (giá trị hợp lệ: 0.0 – 10.0) ──────────────────────────
SCORE_COLS = ["toan", "ngu_van", "ngoai_ngu", "vat_li",
              "hoa_hoc", "sinh_hoc", "lich_su", "dia_li", "gdcd"]

# ── Cột chuỗi cần strip whitespace ──────────────────────────────────────────
STR_COLS = ["ma_ngoai_ngu", "tinh", "kv"]


def to_float(value: str):
    """Chuyển chuỗi sang float; trả về None nếu rỗng/lỗi."""
    v = value.strip()
    if not v:
        return None
    try:
        return float(v)
    except ValueError:
        return None


def is_valid_score(score) -> bool:
    """Kiểm tra điểm nằm trong khoảng [0, 10]."""
    return score is not None and 0.0 <= score <= 10.0


def clean_row(row: dict, headers: list, stats: dict) -> dict:
    """Làm sạch một dòng dữ liệu và cập nhật thống kê."""
    cleaned = {}

    # 1. SBD – giữ nguyên dạng chuỗi
    cleaned["sbd"] = row["sbd"].strip()

    # 2. Cột điểm môn học
    for col in SCORE_COLS:
        val = to_float(row.get(col, ""))
        if val is None:
            stats["missing"][col] += 1
            cleaned[col] = ""
        elif not is_valid_score(val):
            stats["invalid_score"][col] += 1
            cleaned[col] = ""
        else:
            cleaned[col] = val

    # 3. Cột chuỗi
    for col in STR_COLS:
        cleaned[col] = row.get(col, "").strip()

    # 4. Cột điểm tổ hợp
    COMBO_PREFIXES = ("A", "B", "C", "D")
    combo_cols = [h for h in headers
                  if h[:1] in COMBO_PREFIXES
                  and h not in SCORE_COLS + STR_COLS + ["sbd"]]
    for col in combo_cols:
        val = to_float(row.get(col, ""))
        if val is not None and (val < 0 or val > 30):
            stats["invalid_combo"][col] += 1
            cleaned[col] = ""
        else:
            cleaned[col] = "" if val is None else val

    return cleaned


def main():
    print("=" * 60)
    print("  DATA CLEANING – DIEM THI THPT QUOC GIA")
    print("=" * 60)

    # ── Đọc dữ liệu gốc ────────────────────────────────────────────
    print(f"\n[1] Doc file: {INPUT_PATH}")
    with open(INPUT_PATH, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        raw_rows = list(reader)

    total_raw = len(raw_rows)
    print(f"    -> Tong so dong goc : {total_raw:,}")
    print(f"    -> Tong so cot      : {len(headers)}")

    # ── Thống kê ───────────────────────────────────────────────────
    stats = {
        "missing":       defaultdict(int),
        "invalid_score": defaultdict(int),
        "invalid_combo": defaultdict(int),
    }

    # ── Bước 1: Loại bỏ duplicate ──────────────────────────────────
    seen_sbd = set()
    dedup_rows = []
    dup_count = 0
    for row in raw_rows:
        sbd = row["sbd"].strip()
        if sbd in seen_sbd:
            dup_count += 1
        else:
            seen_sbd.add(sbd)
            dedup_rows.append(row)

    print(f"\n[2] Loai duplicate:")
    print(f"    -> Dong trung lap da xoa: {dup_count:,}")
    print(f"    -> Con lai              : {len(dedup_rows):,} dong")

    # ── Bước 2: Làm sạch từng dòng ────────────────────────────────
    print(f"\n[3] Lam sach gia tri...")
    cleaned_rows = [clean_row(r, headers, stats) for r in dedup_rows]

    # ── Bước 3: Thống kê ───────────────────────────────────────────
    print(f"\n[4] Thong ke missing values (diem mon hoc):")
    for col in SCORE_COLS:
        count = stats["missing"][col]
        pct = count / len(dedup_rows) * 100
        print(f"    {col:<12}: {count:>7,} dong thieu ({pct:.1f}%)")

    if stats["invalid_score"]:
        print(f"\n[!] Diem mon hoc ngoai pham vi [0-10] – Da xoa:")
        for col, count in stats["invalid_score"].items():
            print(f"    {col}: {count:,}")

    # ── Bước 4: Ghi file cleaned ───────────────────────────────────
    out_headers = list(cleaned_rows[0].keys())
    print(f"\n[5] Ghi file: {OUTPUT_PATH}")
    with open(OUTPUT_PATH, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=out_headers)
        writer.writeheader()
        writer.writerows(cleaned_rows)

    total_cleaned = len(cleaned_rows)
    print(f"    -> Da ghi {total_cleaned:,} dong")

    # ── Bước 5: Báo cáo ───────────────────────────────────────────
    report_lines = [
        "=" * 60,
        "  BAO CAO LAM SACH DU LIEU – THPT QUOC GIA",
        "=" * 60,
        f"File goc      : {INPUT_PATH}",
        f"File da clean : {OUTPUT_PATH}",
        "",
        f"Tong dong goc      : {total_raw:,}",
        f"Dong duplicate xoa : {dup_count:,}",
        f"Dong sau cleaning  : {total_cleaned:,}",
        "",
        "MISSING VALUES (diem mon hoc) – Giu trong (hoc sinh khong thi mon nay):",
    ]
    for col in SCORE_COLS:
        count = stats["missing"][col]
        pct = count / len(dedup_rows) * 100
        report_lines.append(f"  {col:<12}: {count:>7,} ({pct:.1f}%)")

    if stats["invalid_score"]:
        report_lines += ["", "DIEM NGOAI PHAM VI [0-10] – Da xoa:"]
        for col, count in stats["invalid_score"].items():
            report_lines.append(f"  {col}: {count:,}")

    report_lines += [
        "",
        "CAC BUOC CLEANING DA THUC HIEN:",
        "  1. Loai bo dong trung lap (theo cot sbd)",
        "  2. Chuyen diem so sang kieu float; giu trong neu rong/loi",
        "  3. Xoa diem mon ngoai pham vi [0, 10]",
        "  4. Xoa diem to hop ngoai pham vi [0, 30]",
        "  5. Strip whitespace cho cot chuoi (tinh, kv, ma_ngoai_ngu)",
    ]

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))

    print(f"\n[6] Bao cao: {REPORT_PATH}")
    print("\n  Hoan tat lam sach du lieu!")
    print("=" * 60)


if __name__ == "__main__":
    main()
