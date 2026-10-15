"""
figure.py
=========
Vẽ biểu đồ phân tích điểm thi THPT Quốc gia 2018-2025.

Đầu vào : data/cleaned/cleaned_<năm>.csv  (mỗi năm 1 file, đã làm sạch bằng src/clean_data.py)

Đầu ra (outputs/charts/):
  <năm>/                                  – mỗi năm 1 thư mục
      bar_<mon>.png                       – bar chart dọc phổ điểm (bước 0,5 từ 0 đến 10):
                                            trục hoành = điểm, trục tung = số thí sinh,
                                            kèm đường Mean, Median và dải ±1 độ lệch chuẩn (Std)
      top10_diem10_<mon>.png              – horizontal bar chart: top 10 tỉnh nhiều điểm 10 nhất
      corr_heatmap.png                    – tương quan điểm giữa các môn
  so_sanh_cac_nam/                        – thư mục chung so sánh giữa các năm
      so_sanh_<mon>.png                   – KDE plot: phổ điểm của môn đó, mỗi năm 1 đường cong màu
      mon_theo_nam_diem_tb.png            – bar chart dọc: điểm TB của từng môn qua các năm
      mon_theo_nam_trung_vi.png           – bar chart dọc: điểm trung vị của từng môn qua các năm
      mon_theo_nam_do_lech_chuan.png      – bar chart dọc: độ lệch chuẩn của từng môn qua các năm
      thong_ke_cac_nam.csv                – bảng số liệu (n, mean, median, std) theo môn x năm

Chạy:  python figure.py [thư_mục_cleaned]
Cần :  pip install pandas matplotlib numpy
"""

import glob
import os
import re
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# ── Cấu hình ────────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
CLEANED_DIR = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT_DIR, "data", "cleaned")
OUT_DIR = os.path.join(ROOT_DIR, "outputs", "charts")
COMPARE_DIR = os.path.join(OUT_DIR, "so_sanh_cac_nam")

BINS = np.arange(0, 10.5, 0.5)   # 0, 0.5, 1.0, ..., 10  (21 mốc)

SUBJECTS = {
    "toan": "Toán", "ngu_van": "Ngữ văn", "ngoai_ngu": "Ngoại ngữ",
    "vat_li": "Vật lí", "hoa_hoc": "Hóa học", "sinh_hoc": "Sinh học",
    "lich_su": "Lịch sử", "dia_li": "Địa lí", "gdcd": "GDCD",
}

# Cột `tinh` là MÃ tỉnh (2 số đầu của SBD) theo bảng mã của Bộ GD&ĐT.
PROVINCES = {
    1: "Hà Nội", 2: "TP.HCM", 3: "Hải Phòng", 4: "Đà Nẵng", 5: "Hà Giang",
    6: "Cao Bằng", 7: "Lai Châu", 8: "Lào Cai", 9: "Tuyên Quang", 10: "Lạng Sơn",
    11: "Bắc Kạn", 12: "Thái Nguyên", 13: "Yên Bái", 14: "Sơn La", 15: "Phú Thọ",
    16: "Vĩnh Phúc", 17: "Quảng Ninh", 18: "Bắc Giang", 19: "Bắc Ninh",
    21: "Hải Dương", 22: "Hưng Yên", 23: "Hòa Bình", 24: "Hà Nam",
    25: "Nam Định", 26: "Thái Bình", 27: "Ninh Bình", 28: "Thanh Hóa",
    29: "Nghệ An", 30: "Hà Tĩnh", 31: "Quảng Bình", 32: "Quảng Trị", 33: "Huế",
    34: "Quảng Nam", 35: "Quảng Ngãi", 36: "Kon Tum", 37: "Bình Định",
    38: "Gia Lai", 39: "Phú Yên", 40: "Đắk Lắk", 41: "Khánh Hòa", 42: "Lâm Đồng",
    43: "Bình Phước", 44: "Bình Dương", 45: "Ninh Thuận", 46: "Tây Ninh",
    47: "Bình Thuận", 48: "Đồng Nai", 49: "Long An", 50: "Đồng Tháp",
    51: "An Giang", 52: "Bà Rịa - Vũng Tàu", 53: "Tiền Giang", 54: "Kiên Giang",
    55: "Cần Thơ", 56: "Bến Tre", 57: "Vĩnh Long", 58: "Trà Vinh",
    59: "Sóc Trăng", 60: "Bạc Liêu", 61: "Cà Mau", 62: "Điện Biên",
    63: "Đắk Nông", 64: "Hậu Giang",
}

MIN_STUDENTS = 30   # môn phải có >= 30 thí sinh trong năm mới được vẽ / tính thống kê

plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})


# ── Tiện ích ────────────────────────────────────────────────────────────────
def province_name(code):
    try:
        return PROVINCES.get(int(float(code)), f"Mã {int(float(code))}")
    except (TypeError, ValueError):
        return str(code)


def save(fig, folder, name):
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, name)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("Đã lưu:", os.path.relpath(path, ROOT_DIR))


def load_years():
    """Đọc mọi file cleaned_<năm>.csv. Trả về {năm: DataFrame}."""
    data = {}
    for path in sorted(glob.glob(os.path.join(CLEANED_DIR, "cleaned_*.csv"))):
        m = re.search(r"(\d{4})", os.path.basename(path))
        if not m:
            continue
        if os.path.getsize(path) < 1024:   # file con trỏ Git LFS, không phải dữ liệu thật
            print(f"Bỏ qua {os.path.basename(path)}: là file con trỏ Git LFS "
                  f"(chạy `git lfs pull` để tải dữ liệu thật).")
            continue
        year = int(m.group(1))
        df = pd.read_csv(path, usecols=lambda c: c in ["tinh", *SUBJECTS])
        data[year] = df
        print(f"Đọc {len(df):,} dòng – năm {year}")
    if not data:
        sys.exit(f"Không có dữ liệu thật trong {CLEANED_DIR}. "
                 "Hãy chạy `git lfs pull` hoặc truyền đường dẫn: python figure.py <thư_mục>")
    return data


def valid_scores(df, col):
    """Điểm hợp lệ của môn; None nếu môn đó không đủ thí sinh trong năm."""
    if col not in df:
        return None
    s = pd.to_numeric(df[col], errors="coerce").dropna()
    return s if len(s) >= MIN_STUDENTS else None


def score_counts(s):
    """Số thí sinh theo từng mốc điểm cách nhau 0,5 (làm tròn tới mốc 0,5 gần nhất)."""
    snapped = np.round(s.to_numpy() * 2) / 2
    idx = (snapped * 2).astype(int)
    return np.bincount(idx, minlength=len(BINS))[: len(BINS)]


def describe(s):
    return {"n": len(s), "mean": s.mean(), "median": s.median(), "std": s.std()}


# ── 1. Bar chart phổ điểm từng môn, từng năm ───────────────────────────────
def plot_bar_subject(year, col, name, s):
    counts = score_counts(s)
    st = describe(s)
    fig, ax = plt.subplots(figsize=(10, 5.5))

    ax.bar(BINS, counts, width=0.42, color="#3b82f6", edgecolor="white", label="Số thí sinh")
    ax.axvspan(max(st["mean"] - st["std"], 0), min(st["mean"] + st["std"], 10),
               color="#f59e0b", alpha=0.15, label=f"Mean ± Std ({st['std']:.2f})")
    ax.axvline(st["mean"], color="#dc2626", linestyle="--", linewidth=1.6,
               label=f"Mean (trung bình) = {st['mean']:.2f}")
    ax.axvline(st["median"], color="#16a34a", linestyle="-.", linewidth=1.6,
               label=f"Median (trung vị) = {st['median']:.2f}")

    ax.set_xticks(np.arange(0, 10.5, 0.5))
    ax.set_xticklabels([f"{v:g}" for v in np.arange(0, 10.5, 0.5)], fontsize=8)
    ax.set_xlim(-0.2, 10.2)
    ax.set_ylim(bottom=0)
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{int(v):,}"))
    ax.set_xlabel("Điểm (làm tròn tới 0,5)")
    ax.set_ylabel("Số thí sinh")
    ax.set_title(f"Phổ điểm {name} – năm {year}  (n = {st['n']:,})", fontsize=13)
    ax.grid(axis="y", alpha=0.3)
    ax.legend(loc="upper left", fontsize=9, frameon=False)
    save(fig, os.path.join(OUT_DIR, str(year)), f"bar_{col}.png")


# ── 2. Horizontal bar: top 10 tỉnh nhiều điểm 10 nhất ───────────────────────
def plot_top10_diem10(year, df, col, name):
    s = pd.to_numeric(df[col], errors="coerce")
    g = df.loc[s == 10].groupby("tinh").size().nlargest(10).iloc[::-1]
    if g.empty:
        print(f"  {year} – {name}: không có điểm 10, bỏ qua top 10")
        return
    fig, ax = plt.subplots(figsize=(8, 5.5))
    bars = ax.barh([province_name(c) for c in g.index], g.values, color="#f59e0b")
    ax.bar_label(bars, labels=[f"{v:,}" for v in g.values], padding=3, fontsize=9)
    ax.set_xlabel("Số điểm 10")
    ax.margins(x=0.12)
    ax.set_title(f"Top {len(g)} tỉnh/thành nhiều điểm 10 môn {name} – năm {year}\n"
                 f"(tổng cả nước: {int((s == 10).sum()):,} điểm 10)", fontsize=12)
    save(fig, os.path.join(OUT_DIR, str(year)), f"top10_diem10_{col}.png")


# ── 3. Heatmap tương quan giữa các môn (mỗi năm) ────────────────────────────
def plot_correlation(year, df):
    cols = [c for c in SUBJECTS if c in df and df[c].notna().sum() >= MIN_STUDENTS]
    if len(cols) < 2:
        return
    names = [SUBJECTS[c] for c in cols]
    corr = df[cols].corr(min_periods=MIN_STUDENTS)
    fig, ax = plt.subplots(figsize=(9, 8))
    im = ax.imshow(corr.values, cmap="RdYlBu_r", vmin=-1, vmax=1)
    ax.set_xticks(range(len(names)))
    ax.set_xticklabels(names, rotation=45, ha="right")
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels(names)
    for i in range(len(names)):
        for j in range(len(names)):
            v = corr.values[i, j]
            if not np.isnan(v):
                ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=8)
    fig.colorbar(im, ax=ax, label="Hệ số tương quan Pearson")
    ax.set_title(f"Tương quan điểm giữa các môn – năm {year}")
    save(fig, os.path.join(OUT_DIR, str(year)), "corr_heatmap.png")


# ── 4. So sánh phổ điểm của 1 môn giữa các năm ──────────────────────────────
def kde_curve(s, bw=0.25, step=0.01):
    """KDE Gaussian trên [0, 10], tính nhanh bằng cách làm mượt histogram mịn (bước 0,01).
    Phản xạ ở hai biên 0 và 10 để mật độ không bị hụt gần điểm 0 / điểm 10.
    Trả về (x, mật độ); diện tích dưới đường = 1 nên so sánh được giữa các năm có n khác nhau."""
    edges = np.arange(0, 10 + step / 2, step)
    h, _ = np.histogram(s.to_numpy(), bins=edges)
    pad = int(4 * bw / step)
    kx = np.arange(-pad, pad + 1) * step
    kernel = np.exp(-0.5 * (kx / bw) ** 2)
    kernel /= kernel.sum()
    smooth = np.convolve(np.pad(h.astype(float), pad, mode="symmetric"), kernel, mode="valid")
    return (edges[:-1] + step / 2), smooth / (h.sum() * step)


def plot_compare_subject(col, name, per_year):
    """KDE plot so sánh phổ điểm của 1 môn giữa các năm. per_year: {năm: Series điểm}"""
    if not per_year:
        return
    years = sorted(per_year)
    cmap = plt.get_cmap("viridis")
    fig, ax = plt.subplots(figsize=(11, 6.5))
    for i, y in enumerate(years):
        s = per_year[y]
        st = describe(s)
        x, d = kde_curve(s)
        color = cmap(i / max(len(years) - 1, 1))
        ax.fill_between(x, d, color=color, alpha=0.04, linewidth=0)
        ax.plot(x, d, color=color, linewidth=2,
                label=f"{y}  (n={st['n']:,} | Mean={st['mean']:.2f} | "
                      f"Median={st['median']:.2f} | Std={st['std']:.2f})")
    ax.set_xticks(np.arange(0, 10.5, 0.5))
    ax.set_xticklabels([f"{v:g}" for v in np.arange(0, 10.5, 0.5)], fontsize=8)
    ax.set_xlim(0, 10)
    ax.set_ylim(bottom=0)
    ax.set_xlabel("Điểm")
    ax.set_ylabel("Mật độ (KDE)")
    ax.set_title(f"KDE plot – so sánh phổ điểm {name} giữa các năm", fontsize=13)
    ax.grid(axis="y", alpha=0.3)
    ax.legend(fontsize=8.5, frameon=False, loc="upper center",
              bbox_to_anchor=(0.5, -0.12), ncol=2)
    save(fig, COMPARE_DIR, f"so_sanh_{col}.png")


# ── 5. Bar chart so sánh các môn theo năm ──────────────────────────────────
def plot_subjects_over_years(stats):
    """stats: DataFrame cột [nam, mon, n, mean, median, std]"""
    metrics = [
        ("mean", "Điểm trung bình (Mean)", "mon_theo_nam_diem_tb.png"),
        ("median", "Điểm trung vị (Median)", "mon_theo_nam_trung_vi.png"),
        ("std", "Độ lệch chuẩn (Std)", "mon_theo_nam_do_lech_chuan.png"),
    ]
    years = sorted(stats["nam"].unique())
    for key, label, fname in metrics:
        fig, ax = plt.subplots(figsize=(14, 6.5))
        present = [(c, n) for c, n in SUBJECTS.items() if (stats["mon"] == c).any()]
        k = len(present)
        w = 0.8 / max(k, 1)                       # 9 cột môn học trong mỗi năm
        for i, (col, name) in enumerate(present):
            sub = stats[stats["mon"] == col].sort_values("nam")
            xs = sub["nam"].to_numpy() + (i - (k - 1) / 2) * w
            bars = ax.bar(xs, sub[key], width=w, label=name)
            ax.bar_label(bars, fmt="%.2f", rotation=90, fontsize=6, padding=2)
        ax.margins(y=0.12)
        ax.set_xticks(years)
        ax.set_xlabel("Năm")
        ax.set_ylabel(label)
        ax.set_title(f"{label} của từng môn qua các năm", fontsize=13)
        ax.grid(alpha=0.3)
        ax.legend(ncol=9, fontsize=9, frameon=False, loc="upper center",
                  bbox_to_anchor=(0.5, -0.1))
        save(fig, COMPARE_DIR, fname)


def main():
    data = load_years()
    rows = []
    compare = {col: {} for col in SUBJECTS}

    for year in sorted(data):
        df = data[year]
        print(f"\n=== Năm {year} ===")
        for col, name in SUBJECTS.items():
            s = valid_scores(df, col)
            if s is None:
                print(f"  {year} – {name}: không đủ dữ liệu (< {MIN_STUDENTS} thí sinh), bỏ qua")
                continue
            plot_bar_subject(year, col, name, s)
            plot_top10_diem10(year, df, col, name)
            compare[col][year] = s
            rows.append({"nam": year, "mon": col, **describe(s)})
        plot_correlation(year, df)

    print("\n=== So sánh giữa các năm ===")
    for col, name in SUBJECTS.items():
        plot_compare_subject(col, name, compare[col])

    stats = pd.DataFrame(rows)
    plot_subjects_over_years(stats)
    os.makedirs(COMPARE_DIR, exist_ok=True)
    out_csv = os.path.join(COMPARE_DIR, "thong_ke_cac_nam.csv")
    stats.round(4).to_csv(out_csv, index=False, encoding="utf-8-sig")
    print("Đã lưu:", os.path.relpath(out_csv, ROOT_DIR))


if __name__ == "__main__":
    main()