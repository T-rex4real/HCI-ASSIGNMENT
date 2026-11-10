"""CSV data logging for the Human Perception & Performance Tester.

Every finished test block is appended to results.csv (next to this file).
The header row is written automatically the first time.
"""

import csv
import os

CSV_FIELDS = [
    "timestamp",
    "participant",
    "task_type",          # "Identification" or "Target Hitting"
    "trial",
    "visual_condition",   # e.g. "Low contrast | Small size | 100% brightness"
    "contrast",           # High / Medium / Low
    "size",               # Small / Medium / Large
    "brightness_pct",
    "contrast_ratio",     # effective text-vs-background ratio after dimming
    "stimulus",           # figure name (Identification only)
    "distance_px",        # start point -> target centre (Target Hitting only)
    "target_size_px",     # target diameter (Target Hitting only)
    "time_sec",           # time to click the target / to answer
    "misses",             # clicks that missed the target (Target Hitting only)
    "response",           # what the participant said they saw / "hit"
    "ease_1to5",          # 1 = very difficult ... 5 = very easy
]

DEFAULT_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results.csv")


def log_rows(rows, path=DEFAULT_CSV):
    """Append a list of row dictionaries to the CSV file.

    Keys not present in a row are written as empty cells. A key that is not in
    CSV_FIELDS raises ValueError, which catches typos early.
    """
    write_header = not os.path.exists(path) or os.path.getsize(path) == 0
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, restval="")
        if write_header:
            writer.writeheader()
        for row in rows:
            writer.writerow(row)
