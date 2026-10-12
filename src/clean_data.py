"""
clean_data.py
=============
Script lam sach va dong bo du lieu diem thi THPT Quoc gia (2018-2025).
Su dung hoan toan thu vien chuan Python (khong can pandas).

Hai dinh dang nguon duoc ho tro:
  - Format A (2024): sbd,toan,ngu_van,ngoai_ngu,vat_li,hoa_hoc,sinh_hoc,lich_su,dia_li,gdcd,ma_ngoai_ngu,tinh,kv,...
  - Format B (2018-2023, 2025): SBD,Nam,Tinh,SBD_New,Toan,NguVan,VatLy,HoaHoc,SinhHoc,LichSu,DiaLy,GDCD,NgoaiNgu,MaMonNgoaiNgu,...

Output:
  data/cleaned/cleaned_<nam>.csv      -- du lieu da lam sach tung nam
  outputs/reports/cleaning_report.txt -- bao cao tong hop
"""

import csv
import os
import re
from collections import defaultdict
from datetime import datetime

# -- Cau hinh duong dan ---------------------------------------------------------
BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR     = os.path.join(BASE_DIR, "data", "raw.csv")
CLEANED_DIR = os.path.join(BASE_DIR, "data", "cleaned")
REPORT_PATH = os.path.join(BASE_DIR, "outputs", "reports", "cleaning_report.txt")

# -- Schema chuan hoa (output) --------------------------------------------------
STANDARD_COLS = [
    "sbd", "nam", "tinh", "toan", "ngu_van", "ngoai_ngu",
    "vat_li", "hoa_hoc", "sinh_hoc", "lich_su", "dia_li", "gdcd",
    "ma_ngoai_ngu",
]

SCORE_COLS = ["toan", "ngu_van", "ngoai_ngu", "vat_li",
              "hoa_hoc", "sinh_hoc", "lich_su", "dia_li", "gdcd"]

# -- Mapping ten cot: Format B -> Schema chuan ----------------------------------
FORMAT_B_MAP = {
    "Toan":           "toan",
    "NguVan":         "ngu_van",
    "VatLy":          "vat_li",
    "HoaHoc":         "hoa_hoc",
    "SinhHoc":        "sinh_hoc",
    "LichSu":         "lich_su",
    "DiaLy":          "dia_li",
    "GDCD":           "gdcd",
    "NgoaiNgu":       "ngoai_ngu",
    "KinhTePhapLuat": "gdcd",   # 2025
}


# -- Ham tien ich ---------------------------------------------------------------
def to_float(value: str):
    v = value.strip()
    if not v:
        return None
    try:
        return float(v)
    except ValueError:
        return None


def is_valid_score(score) -> bool:
    return score is not None and 0.0 <= score <= 10.0


def detect_year_from_filename(filename: str) -> str:
    m = re.search(r"(20\d{2})", filename)
    return m.group(1) if m else "unknown"


def is_format_b(headers: list) -> bool:
    return "Nam" in headers or ("SBD" in headers and "toan" not in headers)


# -- Dong bo / chuan hoa hang du lieu ------------------------------------------
def normalize_row_format_a(row: dict, year: str) -> dict:
    norm = {}
    norm["sbd"]          = row.get("sbd", "").strip()
    norm["nam"]          = year
    norm["tinh"]         = row.get("tinh", "").strip()
    norm["ma_ngoai_ngu"] = row.get("ma_ngoai_ngu", "").strip()
    for col in SCORE_COLS:
        norm[col] = row.get(col, "").strip()
    return norm


def normalize_row_format_b(row: dict, year: str) -> dict:
    norm = {}
    norm["sbd"]          = row.get("SBD", row.get("sbd", "")).strip()
    norm["nam"]          = str(row.get("Nam", year)).strip() or year
    norm["tinh"]         = str(row.get("Tinh", "")).strip()
    norm["ma_ngoai_ngu"] = row.get("MaMonNgoaiNgu", row.get("ma_ngoai_ngu", "")).strip()
    for src_col, dst_col in FORMAT_B_MAP.items():
        if dst_col in SCORE_COLS:
            norm.setdefault(dst_col, row.get(src_col, "").strip())
    for col in SCORE_COLS:
        norm.setdefault(col, "")
    return norm


# -- Lam sach mot hang da chuan hoa --------------------------------------------
def clean_row(norm: dict, stats: dict) -> dict:
    cleaned = {col: norm.get(col, "") for col in ["sbd", "nam", "tinh", "ma_ngoai_ngu"]}
    for col in SCORE_COLS:
        val = to_float(norm.get(col, ""))
        if val is None:
            stats["missing"][col] += 1
            cleaned[col] = ""
        elif not is_valid_score(val):
            stats["invalid_score"][col] += 1
            cleaned[col] = ""
        else:
            cleaned[col] = val
    return cleaned


# -- Xu ly tung file nam --------------------------------------------------------
def process_file(filepath: str) -> dict:
    filename = os.path.basename(filepath)
    year     = detect_year_from_filename(filename)

    print(f"\n{'-'*60}")
    print(f"  Nam {year} | {filename}")
    print(f"{'-'*60}")

    with open(filepath, encoding="utf-8-sig", newline="") as f:
        reader   = csv.DictReader(f)
        headers  = list(reader.fieldnames or [])
        raw_rows = list(reader)

    total_raw = len(raw_rows)
    fmt       = "B" if is_format_b(headers) else "A"
    print(f"  Format: {fmt} | Tong dong goc: {total_raw:,} | So cot: {len(headers)}")

    if fmt == "A":
        norm_rows = [normalize_row_format_a(r, year) for r in raw_rows]
    else:
        norm_rows = [normalize_row_format_b(r, year) for r in raw_rows]

    seen_sbd   = set()
    dedup_rows = []
    dup_count  = 0
    for row in norm_rows:
        sbd = row["sbd"]
        if sbd in seen_sbd:
            dup_count += 1
        else:
            seen_sbd.add(sbd)
            dedup_rows.append(row)

    print(f"  Duplicate da xoa: {dup_count:,} | Con lai: {len(dedup_rows):,} dong")

    stats = {"missing": defaultdict(int), "invalid_score": defaultdict(int)}
    cleaned_rows = [clean_row(r, stats) for r in dedup_rows]

    print("  Missing values (diem mon hoc):")
    for col in SCORE_COLS:
        count = stats["missing"][col]
        pct   = count / len(dedup_rows) * 100 if dedup_rows else 0
        print(f"    {col:<12}: {count:>7,} ({pct:.1f}%)")

    return {
        "year":         year,
        "filename":     filename,
        "total_raw":    total_raw,
        "format":       fmt,
        "dup_count":    dup_count,
        "cleaned_rows": cleaned_rows,
        "stats":        stats,
    }


# -- Ghi file cleaned tung nam -------------------------------------------------
def write_cleaned(result: dict) -> str:
    os.makedirs(CLEANED_DIR, exist_ok=True)
    out_path = os.path.join(CLEANED_DIR, f"cleaned_{result['year']}.csv")
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=STANDARD_COLS)
        writer.writeheader()
        writer.writerows(result["cleaned_rows"])
    print(f"  -> Da ghi: {out_path} ({len(result['cleaned_rows']):,} dong)")
    return out_path


# -- Tao bao cao tong hop -------------------------------------------------------
def write_report(all_results: list):
    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    now  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sep  = "=" * 70
    sep2 = "-" * 70

    lines = [
        sep,
        "  BAO CAO LAM SACH DU LIEU - KY THI THPT QUOC GIA",
        f"  Ngay tao: {now}",
        sep,
        "",
        f"  Thu muc du lieu goc  : {RAW_DIR}",
        f"  Thu muc du lieu clean: {CLEANED_DIR}",
        "",
    ]

    total_raw_all     = sum(r["total_raw"]          for r in all_results)
    total_dup_all     = sum(r["dup_count"]          for r in all_results)
    total_cleaned_all = sum(len(r["cleaned_rows"])  for r in all_results)

    lines += [
        "TONG QUAN",
        sep2,
        f"  {'Nam':<6} {'Format':<10} {'Dong goc':>12} {'Duplicate':>11} {'Dong cleaned':>14}",
        sep2,
    ]
    for r in all_results:
        lines.append(
            f"  {r['year']:<6} {'Format ' + r['format']:<10} "
            f"{r['total_raw']:>12,} {r['dup_count']:>11,} {len(r['cleaned_rows']):>14,}"
        )
    lines += [
        sep2,
        f"  {'TONG':<6} {'':<10} {total_raw_all:>12,} {total_dup_all:>11,} {total_cleaned_all:>14,}",
        sep2,
        "",
        "CHI TIET TUNG NAM",
    ]

    for r in all_results:
        dedup_count = r["total_raw"] - r["dup_count"]
        lines += [
            "",
            sep2,
            f"  NAM {r['year']} | {r['filename']} | Format {r['format']}",
            sep2,
            f"  Tong dong goc       : {r['total_raw']:,}",
            f"  Duplicate da xoa    : {r['dup_count']:,}",
            f"  Dong sau cleaning   : {len(r['cleaned_rows']):,}",
            "",
            "  MISSING VALUES (diem mon hoc - hoc sinh khong thi mon do):",
            f"  {'Mon':<14} {'So dong':>9} {'Ti le':>8}",
        ]
        for col in SCORE_COLS:
            count = r["stats"]["missing"][col]
            pct   = count / dedup_count * 100 if dedup_count else 0
            lines.append(f"  {col:<14} {count:>9,} {pct:>7.1f}%")
        if r["stats"]["invalid_score"]:
            lines += ["", "  DIEM NGOAI PHAM VI [0-10] - Da xoa:"]
            for col, count in r["stats"]["invalid_score"].items():
                lines.append(f"  {col}: {count:,}")

    lines += [
        "",
        sep,
        "CAC BUOC CLEANING DA THUC HIEN",
        sep,
        "  1. Phat hien format nguon (Format A / Format B)",
        "  2. Dong bo schema: chuan hoa ten cot ve lowercase chuan",
        "  3. Them cot 'nam' tu ten file / du lieu nguon",
        "  4. Loai bo dong trung lap (theo cot sbd)",
        "  5. Chuyen diem so sang kieu float; giu trong neu rong/loi",
        "  6. Xoa diem mon ngoai pham vi [0, 10]",
        "  7. Strip whitespace cho cot chuoi (tinh, ma_ngoai_ngu)",
        "  8. Ghi file cleaned_<nam>.csv voi schema chuan 13 cot:",
        f"     {', '.join(STANDARD_COLS)}",
        sep,
    ]

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\n  Bao cao da ghi: {REPORT_PATH}")


# -- Main -----------------------------------------------------------------------
def main():
    print("=" * 60)
    print("  DATA CLEANING - DIEM THI THPT QUOC GIA (2018-2025)")
    print("=" * 60)

    if not os.path.isdir(RAW_DIR):
        print(f"[LOI] Khong tim thay thu muc raw: {RAW_DIR}")
        return

    csv_files = sorted([
        os.path.join(RAW_DIR, f)
        for f in os.listdir(RAW_DIR)
        if f.lower().endswith(".csv")
    ])

    if not csv_files:
        print(f"[LOI] Khong co file CSV nao trong {RAW_DIR}")
        return

    print(f"\nTim thay {len(csv_files)} file CSV:")
    for fp in csv_files:
        size_mb = os.path.getsize(fp) / 1024 / 1024
        print(f"  {os.path.basename(fp):<45} ({size_mb:.1f} MB)")

    all_results = []
    for fp in csv_files:
        result = process_file(fp)
        write_cleaned(result)
        all_results.append(result)

    print(f"\n{'='*60}")
    print("  TONG KET")
    print(f"{'='*60}")
    total = sum(len(r["cleaned_rows"]) for r in all_results)
    print(f"  Tong dong da clean (tat ca nam): {total:,}")
    print(f"  Thu muc output: {CLEANED_DIR}")

    write_report(all_results)

    print("\n  Hoan tat lam sach du lieu!")
    print("=" * 60)


if __name__ == "__main__":
    main()
