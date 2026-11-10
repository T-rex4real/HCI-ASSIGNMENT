"""Summarise results.csv for the Task 2 report.

Usage:  python analyze.py [path/to/results.csv]

Prints (and saves to analysis_summary.txt) the averages needed for the report:
  * Target Hitting: time by target size, distance and visual condition, plus a
    Fitts' Law check (time against the index of difficulty log2(D/W + 1)).
  * Identification: what people reported and how long it took, by condition.
  * Ease-of-use ratings by condition.
Charts (PNG) are also saved if matplotlib is installed.

Uses only the standard library, apart from the optional charts.
"""

import csv
import math
import os
import sys
from collections import defaultdict
from statistics import mean, stdev

import logger

FITTS = "Target Hitting"
IDENT = "Identification"
CONTRAST_ORDER = ["High", "Medium", "Low"]
SIZE_ORDER = ["Small", "Medium", "Large"]
BRIGHTNESS_BANDS = [("85-100%", 85, 100), ("60-84%", 60, 84), ("30-59%", 30, 59)]


# ------------------------------------------------------------------ loading
def to_number(text):
    """Convert a CSV cell to a float, or None if it is empty."""
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def load_rows(path):
    """Read the CSV and convert the numeric columns."""
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        for key in ("trial", "brightness_pct", "contrast_ratio", "distance_px",
                    "target_size_px", "time_sec", "misses", "ease_1to5"):
            row[key] = to_number(row.get(key))
    return rows


# ----------------------------------------------------------------- helpers
def brightness_band(percent):
    for name, low, high in BRIGHTNESS_BANDS:
        if low <= percent <= high:
            return name
    return "other"


def group(rows, key_func):
    """Group rows into {key: [rows]} (rows whose key is None are skipped)."""
    groups = defaultdict(list)
    for row in rows:
        key = key_func(row)
        if key is not None:
            groups[key].append(row)
    return groups


def values(rows, field):
    return [r[field] for r in rows if r[field] is not None]


def summary(numbers, unit=" s", decimals=3):
    """'mean (SD, n)' text for a list of numbers."""
    if not numbers:
        return "-"
    sd = f"{stdev(numbers):.{decimals}f}" if len(numbers) > 1 else "n/a"
    return f"{mean(numbers):.{decimals}f}{unit} (SD {sd}, n={len(numbers)})"


def ordered(keys, order=None):
    """Sort keys using a preferred order, then anything else."""
    if order:
        known = [k for k in order if k in keys]
        return known + sorted(k for k in keys if k not in order)
    return sorted(keys)


def fit_line(xs, ys):
    """Least-squares line y = a + b*x. Returns (a, b, r_squared) or None."""
    n = len(xs)
    if n < 3:
        return None
    mx, my = mean(xs), mean(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx == 0 or syy == 0:
        return None
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    b = sxy / sxx
    return my - b * mx, b, (sxy ** 2) / (sxx * syy)


def trend(means_by_key, keys, rising):
    """Describe whether the means rise or fall steadily across the ordered keys."""
    series = [means_by_key[k] for k in keys if k in means_by_key]
    if len(series) < 2:
        return "not enough levels to judge"
    steps = list(zip(series, series[1:]))
    if rising:
        ok = all(b > a for a, b in steps)
    else:
        ok = all(b < a for a, b in steps)
    return "YES, at every step" if ok else "NOT consistently"


# ------------------------------------------------------------------ report
class Report:
    """Collects lines of text so they can be printed and saved together."""

    def __init__(self):
        self.lines = []

    def add(self, text=""):
        self.lines.append(text)

    def heading(self, text):
        self.add()
        self.add(text)
        self.add("-" * len(text))

    def text(self):
        return "\n".join(self.lines) + "\n"


def condition_table(report, rows, field, label, unit=" s", decimals=3):
    """Mean of `field` for each contrast, size and brightness band."""
    for title, key_func, order in (
            ("Contrast", lambda r: r["contrast"], CONTRAST_ORDER),
            ("Size setting", lambda r: r["size"], SIZE_ORDER),
            ("Brightness", lambda r: brightness_band(r["brightness_pct"])
             if r["brightness_pct"] is not None else None,
             [b[0] for b in BRIGHTNESS_BANDS])):
        groups = group(rows, key_func)
        if not groups:
            continue
        report.add(f"  {label} by {title.lower()}:")
        for key in ordered(groups, order):
            report.add(f"    {key:<10} "
                       f"{summary(values(groups[key], field), unit, decimals)}")


def report_target_hitting(report, rows):
    report.heading("TARGET HITTING (Fitts' Law)")
    rows = [r for r in rows if r["time_sec"] is not None
            and r["distance_px"] and r["target_size_px"]]
    if not rows:
        report.add("No Target Hitting data yet.")
        return None
    report.add(f"{len(rows)} successful trials.")

    by_size = group(rows, lambda r: int(r["target_size_px"]))
    by_dist = group(rows, lambda r: int(r["distance_px"]))
    size_means = {k: mean(values(v, "time_sec")) for k, v in by_size.items()}
    dist_means = {k: mean(values(v, "time_sec")) for k, v in by_dist.items()}

    report.add()
    report.add("Mean time by target size (all distances pooled):")
    for key in sorted(by_size):
        report.add(f"  {key:>4} px   {summary(values(by_size[key], 'time_sec'))}"
                   f"   mean misses {mean(values(by_size[key], 'misses') or [0]):.2f}")
    report.add("Mean time by distance (all sizes pooled):")
    for key in sorted(by_dist):
        report.add(f"  {key:>4} px   {summary(values(by_dist[key], 'time_sec'))}")

    sizes, dists = sorted(by_size), sorted(by_dist)
    report.add()
    report.add("Mean time (s), distance (rows) x target size (columns):")
    report.add("  " + " " * 8 + "".join(f"{s:>9} px" for s in sizes))
    for d in dists:
        cells = []
        for s in sizes:
            cell = [r["time_sec"] for r in rows
                    if int(r["distance_px"]) == d and int(r["target_size_px"]) == s]
            cells.append(f"{mean(cell):>9.3f}   " if cell else f"{'-':>9}   ")
        report.add(f"  {d:>4} px " + "".join(cells))

    report.add()
    report.add("Fitts' Law predictions:")
    report.add("  Larger targets reduce time? "
               + trend(size_means, sizes, rising=False))
    report.add("  Longer distances increase time? "
               + trend(dist_means, dists, rising=True))

    points = [(math.log2(r["distance_px"] / r["target_size_px"] + 1), r["time_sec"])
              for r in rows]
    fit = fit_line([p[0] for p in points], [p[1] for p in points])
    if fit:
        a, b, r2 = fit
        report.add(f"  Straight-line fit  time = {a:.3f} + {b:.3f} x ID   "
                   f"(ID = log2(D/W + 1), R-squared = {r2:.2f}, n = {len(points)})")
        report.add("  A clearly positive slope with a reasonable R-squared "
                   "supports Fitts' Law.")
    else:
        report.add("  Not enough varied trials for a straight-line fit.")

    report.add()
    condition_table(report, rows, "time_sec", "Mean time")
    return points


def report_identification(report, rows):
    report.heading("IDENTIFICATION")
    rows = [r for r in rows if r["response"]]
    if not rows:
        report.add("No Identification data yet.")
        return
    report.add(f"{len(rows)} answers.")

    report.add()
    report.add("What participants reported, by figure and contrast:")
    for figure, fig_rows in sorted(group(rows, lambda r: r["stimulus"]).items()):
        report.add(f"  {figure}")
        by_contrast = group(fig_rows, lambda r: r["contrast"])
        for contrast in ordered(by_contrast, CONTRAST_ORDER):
            counts = defaultdict(int)
            for r in by_contrast[contrast]:
                counts[r["response"]] += 1
            text = "; ".join(f"{resp} x{n}" for resp, n in sorted(counts.items()))
            report.add(f"    {contrast:<8} {text}")

    report.add()
    condition_table(report, rows, "time_sec", "Mean time to answer")
    cant_tell = [r for r in rows if r["response"].strip().lower() == "can't tell"]
    report.add(f"  \"Can't tell\" answers: {len(cant_tell)} of {len(rows)}")


def report_ease(report, rows):
    report.heading("EASE OF USE (1 = very difficult, 5 = very easy)")
    for task in (FITTS, IDENT):
        task_rows = [r for r in rows if r["task_type"] == task
                     and r["ease_1to5"] is not None]
        if not task_rows:
            continue
        report.add(f"{task}:")
        condition_table(report, task_rows, "ease_1to5", "Mean rating",
                        unit="", decimals=2)


def save_charts(rows, points, folder, report):
    """Save PNG charts if matplotlib is available."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        report.add()
        report.add("(Charts skipped: matplotlib is not installed. "
                   "Run  pip install matplotlib  to enable them.)")
        return

    fitts = [r for r in rows if r["task_type"] == FITTS and r["time_sec"] is not None
             and r["distance_px"] and r["target_size_px"]]
    if not fitts:
        return

    # Chart 1: time against target size, one line per distance
    fig, ax = plt.subplots(figsize=(6, 4))
    for d in sorted({int(r["distance_px"]) for r in fitts}):
        xs, ys = [], []
        for s in sorted({int(r["target_size_px"]) for r in fitts}):
            cell = [r["time_sec"] for r in fitts
                    if int(r["distance_px"]) == d and int(r["target_size_px"]) == s]
            if cell:
                xs.append(s)
                ys.append(mean(cell))
        ax.plot(xs, ys, marker="o", label=f"{d} px away")
    ax.set_xlabel("Target size (px)")
    ax.set_ylabel("Mean time to click (s)")
    ax.set_title("Bigger targets are faster to hit")
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(folder, "chart_time_by_size.png"), dpi=150)
    plt.close(fig)

    # Chart 2: time against index of difficulty with the fitted line
    if points:
        xs, ys = [p[0] for p in points], [p[1] for p in points]
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.scatter(xs, ys, alpha=0.5)
        fit = fit_line(xs, ys)
        if fit:
            a, b, r2 = fit
            x_line = [min(xs), max(xs)]
            ax.plot(x_line, [a + b * x for x in x_line], color="red",
                    label=f"fit: R² = {r2:.2f}")
            ax.legend()
        ax.set_xlabel("Index of difficulty, log2(D/W + 1)")
        ax.set_ylabel("Time to click (s)")
        ax.set_title("Fitts' Law check")
        fig.tight_layout()
        fig.savefig(os.path.join(folder, "chart_fitts_fit.png"), dpi=150)
        plt.close(fig)

    # Chart 3: mean time by contrast for both tasks
    fig, ax = plt.subplots(figsize=(6, 4))
    width = 0.38
    for offset, task in ((-width / 2, FITTS), (width / 2, IDENT)):
        task_rows = [r for r in rows if r["task_type"] == task
                     and r["time_sec"] is not None]
        by_contrast = group(task_rows, lambda r: r["contrast"])
        labels = [c for c in CONTRAST_ORDER if c in by_contrast]
        xs = [CONTRAST_ORDER.index(c) + offset for c in labels]
        ax.bar(xs, [mean(values(by_contrast[c], "time_sec")) for c in labels],
               width=width, label=task)
    ax.set_xticks(range(len(CONTRAST_ORDER)))
    ax.set_xticklabels(CONTRAST_ORDER)
    ax.set_xlabel("Contrast level")
    ax.set_ylabel("Mean time (s)")
    ax.set_title("Effect of contrast on time")
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(folder, "chart_time_by_contrast.png"), dpi=150)
    plt.close(fig)

    report.add()
    report.add(f"Charts saved in: {folder}")


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else logger.DEFAULT_CSV
    if not os.path.exists(path):
        print(f"Cannot find {path}. Run app.py and complete some tests first.")
        return 1
    rows = load_rows(path)
    if not rows:
        print("The CSV file is empty.")
        return 1

    folder = os.path.join(os.path.dirname(os.path.abspath(path)), "analysis_output")
    os.makedirs(folder, exist_ok=True)

    report = Report()
    report.heading(f"RESULTS SUMMARY  ({os.path.basename(path)})")
    participants = sorted({r["participant"] for r in rows})
    report.add(f"Participants: {', '.join(participants)}")
    report.add(f"Rows: {len(rows)}   (Target Hitting: "
               f"{sum(r['task_type'] == FITTS for r in rows)}, Identification: "
               f"{sum(r['task_type'] == IDENT for r in rows)})")

    points = report_target_hitting(report, [r for r in rows if r["task_type"] == FITTS])
    report_identification(report, [r for r in rows if r["task_type"] == IDENT])
    report_ease(report, rows)
    save_charts(rows, points, folder, report)

    text = report.text()
    print(text)
    with open(os.path.join(folder, "analysis_summary.txt"), "w", encoding="utf-8") as f:
        f.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
