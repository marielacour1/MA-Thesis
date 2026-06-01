import argparse
import csv
import math
from collections import Counter
from pathlib import Path


DEFAULT_NUMERIC_COLUMNS = [
    "duration",
    "view_count",
    "video_like_count",
    "comment_count",
    "channel_subscriber_count",
    "channel_video_count",
]

VARIABLE_LABELS = {
    "duration": "Video duration (seconds)",
    "view_count": "Video views",
    "video_like_count": "Video likes",
    "comment_count": "Video comments",
    "channel_subscriber_count": "Channel subscribers",
    "channel_video_count": "Channel video count",
}

MISSING_LABEL = "Missing / not specified"
OTHER_LABEL = "Other"
OTHER_THRESHOLD_PERCENT = 1.0

HERE = Path(__file__).resolve().parent
PROJECT_DIR = HERE.parent.parent
DEFAULT_CSV = PROJECT_DIR / "Datasets" / "final_dataset.csv"
DEFAULT_OUTPUT = HERE / "gl-cl-frame-breakdown-summary.html"


def parse_numeric(value: str | None) -> float | None:
    raw = (value or "").strip()
    if not raw:
        return None
    cleaned = raw.replace(",", "").replace(" ", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


def percentile(sorted_values: list[float], p: float) -> float:
    if not sorted_values:
        raise ValueError("Cannot compute percentile of empty list.")
    if len(sorted_values) == 1:
        return sorted_values[0]
    rank = (len(sorted_values) - 1) * p
    low = math.floor(rank)
    high = math.ceil(rank)
    if low == high:
        return sorted_values[low]
    weight = rank - low
    return sorted_values[low] * (1 - weight) + sorted_values[high] * weight


def sample_sd(values: list[float], mean_value: float) -> float:
    if len(values) < 2:
        return 0.0
    variance = sum((value - mean_value) ** 2 for value in values) / (len(values) - 1)
    return math.sqrt(variance)


def format_number(value: float, decimals: int) -> str:
    if abs(value - round(value)) < 1e-12:
        return f"{int(round(value)):,}"
    return f"{value:,.{decimals}f}"


def variable_label(column: str) -> str:
    return VARIABLE_LABELS.get(column, column.replace("_", " ").title())


def load_rows(csv_path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as infile:
        reader = csv.DictReader(infile)
        fieldnames = list(reader.fieldnames or [])
        if not fieldnames:
            raise ValueError("CSV appears empty or missing header.")
        return list(reader), fieldnames


def build_numeric_summary(rows: list[dict[str, str]], columns: list[str]) -> list[dict[str, float | int | str]]:
    summary_rows: list[dict[str, float | int | str]] = []
    for column in columns:
        values: list[float] = []
        missing_n = 0
        invalid_n = 0
        invalid_examples: list[str] = []

        for row in rows:
            raw = (row.get(column) or "").strip()
            if not raw:
                missing_n += 1
                continue
            parsed = parse_numeric(raw)
            if parsed is None:
                invalid_n += 1
                if raw not in invalid_examples and len(invalid_examples) < 3:
                    invalid_examples.append(raw)
                continue
            values.append(parsed)

        total_n = len(rows)
        valid_n = len(values)
        if values:
            values.sort()
            mean_value = sum(values) / valid_n
            q1 = percentile(values, 0.25)
            median = percentile(values, 0.50)
            q3 = percentile(values, 0.75)
            p5 = percentile(values, 0.05)
            p95 = percentile(values, 0.95)
            summary_rows.append(
                {
                    "variable": column,
                    "n_total": total_n,
                    "n_valid": valid_n,
                    "n_missing": missing_n,
                    "n_invalid": invalid_n,
                    "mean": mean_value,
                    "sd": sample_sd(values, mean_value),
                    "median": median,
                    "q1": q1,
                    "q3": q3,
                    "iqr": q3 - q1,
                    "min": values[0],
                    "max": values[-1],
                    "p5": p5,
                    "p95": p95,
                    "sum": sum(values),
                    "invalid_examples": "; ".join(invalid_examples),
                }
            )
        else:
            summary_rows.append(
                {
                    "variable": column,
                    "n_total": total_n,
                    "n_valid": 0,
                    "n_missing": missing_n,
                    "n_invalid": invalid_n,
                    "mean": float("nan"),
                    "sd": float("nan"),
                    "median": float("nan"),
                    "q1": float("nan"),
                    "q3": float("nan"),
                    "iqr": float("nan"),
                    "min": float("nan"),
                    "max": float("nan"),
                    "p5": float("nan"),
                    "p95": float("nan"),
                    "sum": float("nan"),
                    "invalid_examples": "; ".join(invalid_examples),
                }
            )
    return summary_rows


def format_missing_summary(row: dict[str, float | int | str]) -> str:
    missing_n = int(row["n_missing"])
    total_n = int(row["n_total"])
    pct = (missing_n / total_n * 100) if total_n else 0.0
    pct_text = "<0.1%" if missing_n and pct < 0.1 else f"{pct:.1f}%"
    return f"{missing_n:,} ({pct_text})"


def build_numeric_html(summary_rows: list[dict[str, float | int | str]], decimals: int) -> str:
    headers = [
        "Variable",
        "n",
        "Missing values",
        "Mean",
        "SD",
        "Median",
        "Q1",
        "Q3",
        "Min",
        "Max",
    ]
    rows: list[str] = []
    for row in summary_rows:
        rows.append(
            "      <tr>"
            + "".join(
                f"<td>{value}</td>"
                for value in [
                    variable_label(str(row["variable"])),
                    f"{int(row['n_valid']):,}",
                    format_missing_summary(row),
                    format_number(float(row["mean"]), decimals),
                    format_number(float(row["sd"]), 0),
                    format_number(float(row["median"]), decimals),
                    format_number(float(row["q1"]), decimals),
                    format_number(float(row["q3"]), decimals),
                    format_number(float(row["min"]), decimals),
                    format_number(float(row["max"]), decimals),
                ]
            )
            + "</tr>"
        )
    html = "      <tr>" + "".join(f"<th>{h}</th>" for h in headers) + "</tr>\n"
    html += "\n".join(rows)
    return html


def build_country_summary(
    rows: list[dict[str, str]],
    other_threshold_percent: float,
    global_country_counts: Counter[str],
) -> list[dict[str, str | int | float]]:
    counts: Counter[str] = Counter()
    for row in rows:
        value = (row.get("channel_country") or "").strip()
        if not value:
            value = MISSING_LABEL
        counts[value] += 1

    total_n = len(rows)
    grouped_counts: Counter[str] = Counter()
    other_n = 0
    for value, count in counts.items():
        percent_of_all = (count / total_n * 100) if total_n else 0.0
        if value != MISSING_LABEL and percent_of_all < other_threshold_percent:
            other_n += count
        else:
            grouped_counts[value] += count
    if other_n:
        grouped_counts[OTHER_LABEL] += other_n

    ordered_items = sorted(
        grouped_counts.items(),
        key=lambda item: (item[0] in {MISSING_LABEL, OTHER_LABEL}, -item[1], item[0]),
    )

    summary_rows: list[dict[str, str | int | float]] = []
    for value, count in ordered_items:
        country_total = global_country_counts.get(value, 0)
        summary_rows.append(
            {
                "category": value,
                "count": count,
                "percent_of_all": (count / total_n * 100) if total_n else 0.0,
                "percent_of_country": (count / country_total * 100) if country_total else None,
                "total_n": total_n,
            }
        )
    return summary_rows


def load_country_names() -> dict[str, str]:
    module_path = HERE / "categorical_youtube_table.py"
    if not module_path.exists():
        return {}
    import importlib.util

    spec = importlib.util.spec_from_file_location("categorical_youtube_table", module_path)
    if spec is None or spec.loader is None:
        return {}
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, "COUNTRY_NAMES", {}) or {}


def category_label(value: str) -> str:
    country_names = load_country_names()
    if value == MISSING_LABEL:
        return value
    return country_names.get(value, value)


def build_country_html(summary_rows: list[dict[str, str | int | float]]) -> str:
    rows: list[str] = []
    for row in summary_rows:
        percent_of_country = row.get("percent_of_country")
        percent_of_country_text = (
            f"{float(percent_of_country):.1f}%" if percent_of_country is not None else ""
        )
        rows.append(
            "      <tr>"
            f"<td>{category_label(str(row['category']))}</td>"
            f"<td>{int(row['count']):,}</td>"
            f"<td>{float(row['percent_of_all']):.1f}%</td>"
            f"<td>{percent_of_country_text}</td>"
            "</tr>"
        )
    header = "      <tr><th>Country</th><th>n</th><th>% of videos</th><th>% of country total</th></tr>\n"
    return header + "\n".join(rows)


def build_totals(rows: list[dict[str, str]]) -> list[tuple[str, str]]:
    total_videos = len(rows)
    duration_seconds = 0
    total_views = 0
    total_likes = 0
    total_comments = 0
    channels = set()
    countries = set()

    for row in rows:
        duration_seconds += int(parse_numeric(row.get("duration") or "0") or 0)
        total_views += int(parse_numeric(row.get("view_count") or "0") or 0)
        total_likes += int(parse_numeric(row.get("video_like_count") or "0") or 0)
        total_comments += int(parse_numeric(row.get("comment_count") or "0") or 0)
        channel_id = (row.get("channel_id") or "").strip()
        if channel_id:
            channels.add(channel_id)
        country = (row.get("channel_country") or "").strip()
        if country:
            countries.add(country)

    return [
        ("Total videos", f"{total_videos:,}"),
        (
            "Total content duration",
            f"{duration_seconds // 3600:,}h {(duration_seconds % 3600) // 60}m {duration_seconds % 60}s",
        ),
        ("Total views", f"{total_views:,}"),
        ("Total likes", f"{total_likes:,}"),
        ("Total comments", f"{total_comments:,}"),
        ("Unique channels", f"{len(channels):,}"),
        ("Unique channel countries", f"{len(countries):,}"),
    ]


def build_totals_html(totals: list[tuple[str, str]]) -> str:
    rows = [
        "      <tr>" + "".join(f"<th>{metric}</th>" for metric, _ in totals) + "</tr>"
    ]
    rows.append(
        "      <tr>"
        + "".join(f"<td>{value}</td>" for _, value in totals)
        + "</tr>"
    )
    return "\n".join(rows)


def build_page(
    frames: list[str],
    frame_rows: dict[str, list[dict[str, str]]],
    numeric_columns: list[str],
    decimals: int,
    global_country_counts: Counter[str],
) -> str:
    html = """<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Frame breakdown summary</title>
  <style>
    body { font-family: Arial, sans-serif; line-height: 1.5; margin: 20px; }
    h1, h2, h3 { color: #2a3a52; }
    table { border-collapse: collapse; width: 100%; margin-bottom: 24px; }
    th, td { border: 1px solid #999; padding: 8px; }
    th { background: #f2f2f2; text-align: left; }
    td { text-align: left; }
    .section { margin-bottom: 40px; }
    .note { color: #555; font-size: 0.95em; }
  </style>
</head>
<body>
  <h1>Frame Breakdown Summary</h1>
"""
    for frame in frames:
        rows = frame_rows[frame]
        numeric_summary = build_numeric_summary(rows, numeric_columns)
        country_summary = build_country_summary(rows, OTHER_THRESHOLD_PERCENT, global_country_counts)
        totals = build_totals(rows)

        html += f"  <div class=\"section\">\n    <h2>{frame}</h2>\n"
        html += "    <h3>Descriptive numeric table</h3>\n"
        html += "    <table>\n" + build_numeric_html(numeric_summary, decimals) + "\n    </table>\n"
        html += "    <h3>Country distribution</h3>\n"
        html += "    <table>\n" + build_country_html(country_summary) + "\n    </table>\n"
        html += "    <h3>Totals</h3>\n"
        html += "    <table>\n" + build_totals_html(totals) + "\n    </table>\n"
        html += "  </div>\n"

    html += "</body>\n</html>"
    return html


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a frame-based HTML summary with numeric, country, and total tables."
    )
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV, help="Path to input CSV.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Path to HTML output file.")
    parser.add_argument("--decimals", type=int, default=2, help="Decimal places for numeric summary.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    csv_path = args.csv.resolve()
    output_path = args.output.resolve()

    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    rows, fieldnames = load_rows(csv_path)
    numeric_columns = [c for c in DEFAULT_NUMERIC_COLUMNS if c in fieldnames]
    if not numeric_columns:
        raise ValueError("No numeric columns found in the dataset.")

    frame_rows: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        frame = (row.get("frame") or "").strip()
        if not frame:
            continue
        frame_rows.setdefault(frame, []).append(row)

    global_country_counts: Counter[str] = Counter()
    for row in rows:
        country = (row.get("channel_country") or "").strip()
        if not country:
            country = MISSING_LABEL
        global_country_counts[country] += 1

    frames = sorted(frame_rows.keys(), key=lambda f: -len(frame_rows[f]))
    page = build_page(frames, frame_rows, numeric_columns, args.decimals, global_country_counts)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(page, encoding="utf-8")

    print(f"Dataset: {csv_path}")
    print(f"Frames: {len(frames)}")
    print(f"Saved frame summary to: {output_path}")


if __name__ == "__main__":
    main()
