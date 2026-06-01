import argparse
import csv
import math
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
    "channel_video_count": "Channel videos",
}

DISPLAY_WHOLE_NUMBER_DECIMALS = 0


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


def shorten(text: str, max_width: int) -> str:
    if len(text) <= max_width:
        return text
    if max_width <= 1:
        return text[:max_width]
    return text[: max_width - 3] + "..."


def variable_label(column: str) -> str:
    return VARIABLE_LABELS.get(column, column.replace("_", " ").title())


def missing_or_invalid_n(row: dict[str, float | int | str]) -> int:
    return int(row["n_missing"]) + int(row["n_invalid"])


def format_missing_summary(row: dict[str, float | int | str]) -> str:
    missing_n = int(row["n_missing"])
    total_n = int(row["n_total"])
    pct = (missing_n / total_n * 100) if total_n else 0.0
    pct_text = "<0.1%" if missing_n and pct < 0.1 else f"{pct:.1f}%"
    return f"{missing_n:,} ({pct_text})"


def infer_numeric_columns(fieldnames: list[str], rows: list[dict[str, str]]) -> list[str]:
    candidates: list[str] = []
    for column in fieldnames:
        nonempty = 0
        numeric = 0
        for row in rows:
            raw = (row.get(column) or "").strip()
            if not raw:
                continue
            nonempty += 1
            if parse_numeric(raw) is not None:
                numeric += 1

        if nonempty == 0:
            continue
        if numeric / nonempty >= 0.95:
            candidates.append(column)

    return candidates


def summarize_column(rows: list[dict[str, str]], column: str) -> dict[str, float | int | str]:
    values: list[float] = []
    invalid_examples: list[str] = []
    missing_n = 0
    invalid_n = 0

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

    if not values:
        return {
            "variable": column,
            "n_total": total_n,
            "n_valid": 0,
            "n_missing": missing_n,
            "n_invalid": invalid_n,
            "mean": math.nan,
            "sd": math.nan,
            "median": math.nan,
            "q1": math.nan,
            "q3": math.nan,
            "iqr": math.nan,
            "min": math.nan,
            "max": math.nan,
            "p5": math.nan,
            "p95": math.nan,
            "sum": math.nan,
            "invalid_examples": "; ".join(invalid_examples),
        }

    values.sort()
    mean_value = sum(values) / valid_n
    q1 = percentile(values, 0.25)
    median = percentile(values, 0.50)
    q3 = percentile(values, 0.75)
    p5 = percentile(values, 0.05)
    p95 = percentile(values, 0.95)

    return {
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


def collect_quality_issues(
    rows: list[dict[str, str]], columns: list[str]
) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    for row in rows:
        video_id = (row.get("video_id") or "").strip()
        title = (row.get("video_title") or "").strip()
        for column in columns:
            raw = (row.get(column) or "").strip()
            if not raw:
                issues.append(
                    {
                        "video_id": video_id,
                        "video_title": title,
                        "column": column,
                        "issue_type": "missing",
                        "raw_value": "",
                    }
                )
                continue

            if parse_numeric(raw) is None:
                issues.append(
                    {
                        "video_id": video_id,
                        "video_title": title,
                        "column": column,
                        "issue_type": "invalid",
                        "raw_value": raw,
                    }
                )
    return issues


def print_markdown_table(summary_rows: list[dict[str, float | int | str]], decimals: int) -> None:
    headers = [
        "Variable",
        "Total n",
        "Valid n",
        "Missing values",
        "Mean",
        "SD",
        "Median",
        "Q1",
        "Q3",
        "IQR",
        "Min",
        "Max",
        "P5",
        "P95",
    ]
    print("| " + " | ".join(headers) + " |")
    print("|" + "|".join(["---"] * len(headers)) + "|")

    for row in summary_rows:
        print(
            "| "
            + " | ".join(
                [
                    shorten(str(row["variable"]), 32),
                    f"{row['n_total']:,}",
                    f"{row['n_valid']:,}",
                    f"{row['n_missing']:,}",
                    format_number(float(row["mean"]), DISPLAY_WHOLE_NUMBER_DECIMALS),
                    format_number(float(row["sd"]), DISPLAY_WHOLE_NUMBER_DECIMALS),
                    format_number(float(row["median"]), decimals),
                    format_number(float(row["q1"]), decimals),
                    format_number(float(row["q3"]), decimals),
                    format_number(float(row["iqr"]), decimals),
                    format_number(float(row["min"]), decimals),
                    format_number(float(row["max"]), decimals),
                    format_number(float(row["p5"]), decimals),
                    format_number(float(row["p95"]), decimals),
                ]
            )
            + " |"
        )


def build_aligned_table(summary_rows: list[dict[str, float | int | str]], decimals: int) -> str:
    headers = [
        "Variable",
        "Total n",
        "Valid n",
        "Missing values",
        "Mean",
        "SD",
        "Median",
        "Q1",
        "Q3",
        "IQR",
        "Min",
        "Max",
        "P5",
        "P95",
    ]

    rows = []
    for row in summary_rows:
        rows.append(
            [
                str(row["variable"]),
                f"{row['n_total']:,}",
                f"{row['n_valid']:,}",
                f"{row['n_missing']:,}",
                format_number(float(row["mean"]), DISPLAY_WHOLE_NUMBER_DECIMALS),
                format_number(float(row["sd"]), DISPLAY_WHOLE_NUMBER_DECIMALS),
                format_number(float(row["median"]), decimals),
                format_number(float(row["q1"]), decimals),
                format_number(float(row["q3"]), decimals),
                format_number(float(row["iqr"]), decimals),
                format_number(float(row["min"]), decimals),
                format_number(float(row["max"]), decimals),
                format_number(float(row["p5"]), decimals),
                format_number(float(row["p95"]), decimals),
            ]
        )

    widths = [len(header) for header in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    left_align = {0}

    def format_row(cells: list[str]) -> str:
        formatted = []
        for i, cell in enumerate(cells):
            if i in left_align:
                formatted.append(cell.ljust(widths[i]))
            else:
                formatted.append(cell.rjust(widths[i]))
        return "  ".join(formatted)

    divider = "  ".join("-" * width for width in widths)
    lines = [format_row(headers), divider]
    lines.extend(format_row(row) for row in rows)
    return "\n".join(lines)


def write_csv(output_path: Path, summary_rows: list[dict[str, float | int | str]], decimals: int) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as f:
        fieldnames = [
            "variable",
            "n_total",
            "n_valid",
            "n_missing",
            "n_invalid",
            "mean",
            "sd",
            "median",
            "q1",
            "q3",
            "iqr",
            "min",
            "max",
            "p5",
            "p95",
            "sum",
            "invalid_examples",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in summary_rows:
            writer.writerow(
                {
                    "variable": row["variable"],
                    "n_total": row["n_total"],
                    "n_valid": row["n_valid"],
                    "n_missing": row["n_missing"],
                    "n_invalid": row["n_invalid"],
                    "mean": f"{float(row['mean']):.{decimals}f}",
                    "sd": f"{float(row['sd']):.{DISPLAY_WHOLE_NUMBER_DECIMALS}f}",
                    "median": f"{float(row['median']):.{decimals}f}",
                    "q1": f"{float(row['q1']):.{decimals}f}",
                    "q3": f"{float(row['q3']):.{decimals}f}",
                    "iqr": f"{float(row['iqr']):.{decimals}f}",
                    "min": f"{float(row['min']):.{decimals}f}",
                    "max": f"{float(row['max']):.{decimals}f}",
                    "p5": f"{float(row['p5']):.{decimals}f}",
                    "p95": f"{float(row['p95']):.{decimals}f}",
                    "sum": f"{float(row['sum']):.{decimals}f}",
                    "invalid_examples": row["invalid_examples"],
                }
            )


def write_text_table(output_path: Path, summary_rows: list[dict[str, float | int | str]], decimals: int) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    table = build_aligned_table(summary_rows, decimals)
    notes = (
        "Notes: Mean and SD values are rounded to whole numbers for readability. "
        "SD is the sample standard deviation. "
        "Q1/Q3 are the 25th/75th percentiles. "
        "P5/P95 are the 5th/95th percentiles."
    )
    output_path.write_text(table + "\n\n" + notes + "\n", encoding="utf-8")


def write_quality_issues_csv(output_path: Path, issues: list[dict[str, str]]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    seen = set()
    unique_video_ids = []
    for issue in issues:
        video_id = issue["video_id"]
        if not video_id or video_id in seen:
            continue
        seen.add(video_id)
        unique_video_ids.append(video_id)

    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["video_id"])
        for video_id in unique_video_ids:
            writer.writerow([video_id])


def write_quality_issues_txt(output_path: Path, issues: list[dict[str, str]], columns: list[str]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    seen = set()
    unique_video_ids = []
    for issue in issues:
        video_id = issue["video_id"]
        if not video_id or video_id in seen:
            continue
        seen.add(video_id)
        unique_video_ids.append(video_id)

    output_path.write_text("\n".join(unique_video_ids) + "\n", encoding="utf-8")


def build_table_rows(summary_rows: list[dict[str, float | int | str]], decimals: int) -> list[list[str]]:
    rows = []
    for row in summary_rows:
        rows.append(
            [
                variable_label(str(row["variable"])),
                f"{row['n_valid']:,}",
                format_missing_summary(row),
                format_number(float(row["mean"]), DISPLAY_WHOLE_NUMBER_DECIMALS),
                format_number(float(row["sd"]), DISPLAY_WHOLE_NUMBER_DECIMALS),
                format_number(float(row["median"]), decimals),
                format_number(float(row["q1"]), decimals),
                format_number(float(row["q3"]), decimals),
                format_number(float(row["min"]), decimals),
                format_number(float(row["max"]), decimals),
            ]
        )
    return rows


def build_aligned_table(summary_rows: list[dict[str, float | int | str]], decimals: int) -> str:
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
    rows = build_table_rows(summary_rows, decimals)

    widths = [len(header) for header in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    left_align = {0, 2}

    def format_row(cells: list[str]) -> str:
        formatted = []
        for i, cell in enumerate(cells):
            if i in left_align:
                formatted.append(cell.ljust(widths[i]))
            else:
                formatted.append(cell.rjust(widths[i]))
        return "  ".join(formatted)

    divider = "  ".join("-" * width for width in widths)
    lines = [format_row(headers), divider]
    lines.extend(format_row(row) for row in rows)
    return "\n".join(lines)


def write_csv(output_path: Path, summary_rows: list[dict[str, float | int | str]], decimals: int) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as f:
        fieldnames = [
            "variable",
            "variable_label",
            "n",
            "videos_in_dataset",
            "missing_n",
            "missing_pct",
            "mean",
            "sd",
            "median",
            "q1",
            "q3",
            "min",
            "max",
            "sum",
            "invalid_examples",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in summary_rows:
            total_n = int(row["n_total"])
            missing_n = int(row["n_missing"])
            writer.writerow(
                {
                    "variable": row["variable"],
                    "variable_label": variable_label(str(row["variable"])),
                    "n": row["n_valid"],
                    "videos_in_dataset": total_n,
                    "missing_n": missing_n,
                    "missing_pct": (
                        f"{(missing_n / total_n * 100):.{decimals}f}" if total_n else "0"
                    ),
                    "mean": f"{float(row['mean']):.{decimals}f}",
                    "sd": f"{float(row['sd']):.{DISPLAY_WHOLE_NUMBER_DECIMALS}f}",
                    "median": f"{float(row['median']):.{decimals}f}",
                    "q1": f"{float(row['q1']):.{decimals}f}",
                    "q3": f"{float(row['q3']):.{decimals}f}",
                    "min": f"{float(row['min']):.{decimals}f}",
                    "max": f"{float(row['max']):.{decimals}f}",
                    "sum": f"{float(row['sum']):.{decimals}f}",
                    "invalid_examples": row["invalid_examples"],
                }
            )


def write_tsv(output_path: Path, summary_rows: list[dict[str, float | int | str]], decimals: int) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
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
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(headers)
        writer.writerows(build_table_rows(summary_rows, decimals))


def write_report_ready_tsv(
    output_path: Path,
    summary_rows: list[dict[str, float | int | str]],
    decimals: int,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    headers = [
        "Variable",
        "n",
        "Missing values",
        "Mean (SD)",
        "Median [Q1, Q3]",
        "Range",
    ]
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(headers)
        for row in summary_rows:
            writer.writerow(
                [
                    variable_label(str(row["variable"])),
                    f"{row['n_valid']:,}",
                    format_missing_summary(row),
                    (
                        f"{format_number(float(row['mean']), DISPLAY_WHOLE_NUMBER_DECIMALS)} "
                        f"({format_number(float(row['sd']), DISPLAY_WHOLE_NUMBER_DECIMALS)})"
                    ),
                    (
                        f"{format_number(float(row['median']), decimals)} "
                        f"[{format_number(float(row['q1']), decimals)}, "
                        f"{format_number(float(row['q3']), decimals)}]"
                    ),
                    f"{format_number(float(row['min']), decimals)}-{format_number(float(row['max']), decimals)}",
                ]
            )


def write_google_docs_html(
    output_path: Path,
    summary_rows: list[dict[str, float | int | str]],
    decimals: int,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
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
    rows = build_table_rows(summary_rows, decimals)
    html_rows = [
        "      <tr>" + "".join(f"<th>{header}</th>" for header in headers) + "</tr>"
    ]
    for row in rows:
        html_rows.append(
            "      <tr>"
            + "".join(f"<td>{cell}</td>" for cell in row)
            + "</tr>"
        )

    html = """<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body { font-family: Arial, sans-serif; }
    table { border-collapse: collapse; }
    th, td { border: 1px solid #999; padding: 6px 9px; text-align: right; }
    th:first-child, td:first-child, th:nth-child(3), td:nth-child(3) { text-align: left; }
    th { background: #f2f2f2; }
    .note { margin-top: 12px; color: #555; }
  </style>
</head>
<body>
  <table>
"""
    html += "\n".join(html_rows)
    html += """
  </table>
  <p class="note">Notes: n is the number of usable numeric values for each variable; rows with blank fields are counted as missing values and excluded from n. Mean and SD values are rounded to whole numbers for readability. SD is the sample standard deviation. Q1/Q3 are the 25th/75th percentiles.</p>
</body>
</html>
"""
    output_path.write_text(html, encoding="utf-8")


def write_text_table(output_path: Path, summary_rows: list[dict[str, float | int | str]], decimals: int) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    table = build_aligned_table(summary_rows, decimals)
    notes = (
        "Notes: n is the number of usable numeric values for each variable; "
        "rows with blank fields are counted as missing values and excluded from n. "
        "Mean and SD values are rounded to whole numbers for readability. "
        "SD is the sample standard deviation. "
        "Q1/Q3 are the 25th/75th percentiles."
    )
    output_path.write_text(table + "\n\n" + notes + "\n", encoding="utf-8")


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    default_csv = script_dir.parents[1] / "Datasets" / "final_dataset.csv"
    default_google_docs_output = script_dir / "gl-cl-descriptive-numeric-table-google-docs.html"

    parser = argparse.ArgumentParser(
        description="Save a Google Docs-ready HTML descriptive statistics table for numeric variables."
    )
    parser.add_argument("--csv", type=Path, default=default_csv, help="Path to input CSV.")
    parser.add_argument(
        "--google-docs-output",
        type=Path,
        default=default_google_docs_output,
        help="Path to HTML table that can be copied into Google Docs.",
    )
    parser.add_argument(
        "--columns",
        nargs="+",
        default=None,
        help="Optional list of numeric columns to summarize. Default: standard YouTube numeric columns if present.",
    )
    parser.add_argument(
        "--infer-columns",
        action="store_true",
        help="Infer numeric columns from the dataset instead of using the default list.",
    )
    parser.add_argument("--decimals", type=int, default=2, help="Number of decimals in output (default: 2).")
    args = parser.parse_args()

    csv_path = args.csv.resolve()
    google_docs_output_path = args.google_docs_output.resolve()

    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        if not fieldnames:
            raise ValueError("CSV appears empty or missing header.")
        rows = list(reader)

    if args.columns:
        columns = [column for column in args.columns if column in fieldnames]
    elif args.infer_columns:
        columns = infer_numeric_columns(fieldnames, rows)
    else:
        columns = [column for column in DEFAULT_NUMERIC_COLUMNS if column in fieldnames]

    if not columns:
        raise ValueError("No numeric columns selected. Use --columns or --infer-columns.")

    summary_rows = [summarize_column(rows, column) for column in columns]
    write_google_docs_html(google_docs_output_path, summary_rows, decimals=max(args.decimals, 0))


if __name__ == "__main__":
    main()
