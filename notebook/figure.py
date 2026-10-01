"""
visualize_scores.py
===================
Vẽ biểu đồ phân tích điểm thi THPT Quốc gia.

Output (thư mục outputs/charts/):
  1. hist_<mon>.png            – cột: số thí sinh theo điểm nguyên (0..10), từng môn
  2. hist_all.png              – gộp 9 biểu đồ cột ở trên vào 1 ảnh
  3. pie_diem10.png            – tròn: tỉ lệ điểm 10 giữa các môn
  4. top10_diem_tb.png         – top 10 tỉnh điểm TB cao nhất, từng môn (3x3)
  5. top10_diem10.png          – top 10 tỉnh nhiều điểm 10 nhất, từng môn (3x3)

Chạy:  python visualize_scores.py [đường_dẫn_cleaned.csv]
Cần :  pip install pandas matplotlib
"""

import os
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# ── Cấu hình ────────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)   # script nằm trong notebooks/ hoặc src/ -> gốc project
OUT_DIR = os.path.join(ROOT_DIR, "outputs", "charts")


def find_input():
    """Tìm file dữ liệu: ưu tiên tham số dòng lệnh, sau đó thử các vị trí thường gặp."""
    if len(sys.argv) > 1:
        return sys.argv[1]
    candidates = []
    for base in (SCRIPT_DIR, ROOT_DIR, os.getcwd()):
        for sub in ("data", ""):
            for name in ("cleaned.txt", "cleaned.csv"):
                candidates.append(os.path.join(base, sub, name))
    for c in candidates:
        # bỏ qua file con trỏ Git LFS (vài chục byte) - không phải dữ liệu thật
        if os.path.isfile(c) and os.path.getsize(c) > 1024:
            return c
    sys.exit("Không tìm thấy file dữ liệu thật. Hãy chép cleaned.txt (hoặc cleaned.csv đầy đủ) "
             "vào thư mục data/, hoặc chạy: python visualize_scores.py <đường_dẫn_file>")


INPUT_PATH = find_input()
MIN_STUDENTS = 30   # tỉnh phải có >= 30 thí sinh thi môn đó mới được xếp hạng điểm TB

SUBJECTS = {
    "toan": "Toán", "ngu_van": "Ngữ văn", "ngoai_ngu": "Ngoại ngữ",
    "vat_li": "Vật lí", "hoa_hoc": "Hóa học", "sinh_hoc": "Sinh học",
    "lich_su": "Lịch sử", "dia_li": "Địa lí", "gdcd": "GDCD",
}

# Cột `tinh` trong dữ liệu là MÃ tỉnh (2 số đầu của SBD). Bảng mã chuẩn của Bộ GD&ĐT.
PROVINCES = {
    1: "Hà Nội", 2: "TP.HCM", 3: "Hải Phòng", 4: "Đà Nẵng", 5: "Hà Giang",
    6: "Cao Bằng", 7: "Lai Châu", 8: "Lào Cai", 9: "Tuyên Quang", 10: "Lạng Sơn",
    11: "Bắc Kạn", 12: "Thái Nguyên", 13: "Yên Bái", 14: "Sơn La", 15: "Phú Thọ",
    16: "Vĩnh Phúc", 17: "Quảng Ninh", 18: "Bắc Giang", 19: "Bắc Ninh",
    21: "Hải Dương", 22: "Hưng Yên", 23: "Hòa Bình", 24: "Hà Nam",
    25: "Nam Định", 26: "Thái Bình", 27: "Ninh Bình", 28: "Thanh Hóa",
}

plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})


def province_name(code):
    return PROVINCES.get(int(code), f"Mã {int(code)}")


def save(fig, name):
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, name)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("Đã lưu:", path)


# ── 1. Biểu đồ cột phổ điểm (điểm làm tròn về số nguyên) ────────────────────
def draw_hist(ax, series, title):
    s = series.dropna()
    rounded = np.floor(s + 0.5).astype(int)          # làm tròn half-up: 7.5 -> 8
    counts = rounded.value_counts().reindex(range(11), fill_value=0)
    bars = ax.bar(counts.index, counts.values, color="#3b82f6", edgecolor="white")
    ax.set_xticks(range(11))
    ax.set_title(f"{title} (n={len(s):,})")
    ax.set_xlabel("Điểm (làm tròn)")
    ax.set_ylabel("Số thí sinh")
    ax.bar_label(bars, labels=[f"{v:,}" if v else "" for v in counts.values],
                 fontsize=7, padding=1, rotation=90)
    ax.margins(y=0.18)


def plot_histograms(df):
    for col, name in SUBJECTS.items():
        fig, ax = plt.subplots(figsize=(8, 5))
        draw_hist(ax, df[col], f"Phổ điểm {name}")
        save(fig, f"hist_{col}.png")

    fig, axes = plt.subplots(3, 3, figsize=(18, 14))
    for ax, (col, name) in zip(axes.ravel(), SUBJECTS.items()):
        draw_hist(ax, df[col], name)
    fig.suptitle("Phổ điểm các môn thi THPT Quốc gia", fontsize=16)
    fig.tight_layout()
    save(fig, "hist_all.png")


# ── 2. Biểu đồ tròn: số điểm 10 của mỗi môn ─────────────────────────────────
def plot_pie_diem10(df):
    counts = {name: int((df[col] == 10).sum()) for col, name in SUBJECTS.items()}
    counts = {k: v for k, v in counts.items() if v > 0}   # bỏ môn không có điểm 10
    total = sum(counts.values())

    fig, ax = plt.subplots(figsize=(9, 8))
    ax.pie(
        counts.values(),
        labels=[f"{k}\n({v:,})" for k, v in counts.items()],
        autopct=lambda p: f"{p:.1f}%" if p >= 2 else "",
        startangle=90, counterclock=False, pctdistance=0.8,
        wedgeprops={"edgecolor": "white"},
    )
    ax.set_title(f"Tỉ lệ điểm 10 giữa các môn (tổng {total:,} điểm 10)", fontsize=13)
    save(fig, "pie_diem10.png")


# ── 3. Top 10 tỉnh điểm TB cao nhất, từng môn ───────────────────────────────
def plot_top10_mean(df):
    fig, axes = plt.subplots(3, 3, figsize=(18, 15))
    for ax, (col, name) in zip(axes.ravel(), SUBJECTS.items()):
        g = df.groupby("tinh")[col].agg(["mean", "count"])
        g = g[g["count"] >= MIN_STUDENTS].nlargest(10, "mean").iloc[::-1]
        labels = [province_name(c) for c in g.index]
        bars = ax.barh(labels, g["mean"], color="#10b981")
        ax.bar_label(bars, fmt="%.2f", padding=2, fontsize=8)
        ax.set_title(f"Top 10 điểm TB – {name}")
        ax.set_xlim(max(g["mean"].min() - 1, 0), g["mean"].max() + 0.5)
        ax.set_xlabel("Điểm trung bình")
    fig.suptitle(f"Top 10 tỉnh có điểm trung bình cao nhất theo môn "
                 f"(tỉnh có ≥ {MIN_STUDENTS} thí sinh)", fontsize=16)
    fig.tight_layout()
    save(fig, "top10_diem_tb.png")


# ── 4. Top 10 tỉnh nhiều điểm 10 nhất, từng môn ─────────────────────────────
def plot_top10_diem10(df):
    fig, axes = plt.subplots(3, 3, figsize=(18, 15))
    for ax, (col, name) in zip(axes.ravel(), SUBJECTS.items()):
        g = df[df[col] == 10].groupby("tinh").size().nlargest(10).iloc[::-1]
        ax.set_title(f"Top 10 số điểm 10 – {name}")
        if g.empty:
            ax.text(0.5, 0.5, "Không có điểm 10", ha="center", va="center",
                    transform=ax.transAxes)
            ax.set_axis_off()
            continue
        bars = ax.barh([province_name(c) for c in g.index], g.values, color="#f59e0b")
        ax.bar_label(bars, padding=2, fontsize=8)
        ax.set_xlabel("Số điểm 10")
        ax.margins(x=0.12)
    fig.suptitle("Top 10 tỉnh có nhiều điểm 10 nhất theo môn", fontsize=16)
    fig.tight_layout()
    save(fig, "top10_diem10.png")


def main():
    df = pd.read_csv(INPUT_PATH)
    print(f"Đọc {len(df):,} dòng từ {INPUT_PATH}")
    plot_histograms(df)
    plot_pie_diem10(df)
    plot_top10_mean(df)
    plot_top10_diem10(df)


if __name__ == "__main__":
    main()