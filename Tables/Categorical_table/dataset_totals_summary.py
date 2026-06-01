import argparse
import csv
from pathlib import Path


HERE = Path(__file__).resolve().parent
PROJECT_DIR = HERE.parent.parent
DEFAULT_CSV = PROJECT_DIR / "Datasets" / "final_dataset.csv"
DEFAULT_OUTPUT = HERE / "gl-cl-dataset-totals-summary-google-docs.html"


def parse_int(value: str | None) -> int:
    if value is None:
        return 0
    value = value.strip()
    if not value:
        return 0
    try:
        return int(value)
    except ValueError:
        try:
            return int(float(value))
        except ValueError:
            return 0


def seconds_to_hms(seconds: int) -> str:
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours}h {minutes}m {secs}s"


def load_rows(csv_path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as infile:
        reader = csv.DictReader(infile)
        fieldnames = list(reader.fieldnames or [])
        if not fieldnames:
            raise ValueError("CSV appears empty or missing header.")
        return list(reader), fieldnames


def build_summary(rows: list[dict[str, str]]) -> list[tuple[str, str]]:
    total_videos = len(rows)
    total_duration_seconds = 0
    total_views = 0
    total_likes = 0
    total_comments = 0

    channels = set()
    channel_countries = set()

    for row in rows:
        duration = parse_int(row.get("duration"))
        total_duration_seconds += duration

        total_views += parse_int(row.get("view_count"))
        total_likes += parse_int(row.get("video_like_count"))
        total_comments += parse_int(row.get("comment_count"))

        channel_id = (row.get("channel_id") or "").strip()
        if channel_id:
            channels.add(channel_id)

        country = (row.get("channel_country") or "").strip()
        if country:
            channel_countries.add(country)

    summary = [
        ("Total videos", f"{total_videos:,}"),
        (
            "Total content duration",
            f"{seconds_to_hms(total_duration_seconds)} ({total_duration_seconds:,} seconds)",
        ),
        ("Total views", f"{total_views:,}"),
        ("Total likes", f"{total_likes:,}"),
        ("Total comments", f"{total_comments:,}"),
        ("Unique channels", f"{len(channels):,}"),
        ("Unique channel countries", f"{len(channel_countries):,}"),
    ]

    return summary


def build_html_table(summary: list[tuple[str, str]], total_rows: int) -> str:
    html_rows = [
        "      <tr><th>Metric</th><th>Value</th></tr>"
    ]
    for metric, value in summary:
        html_rows.append(
            f"      <tr><td>{metric}</td><td>{value}</td></tr>"
        )

    html = """<!doctype html>
<html>
<head>
  <meta charset=\"utf-8\">
  <style>
    body { font-family: Arial, sans-serif; }
    table { border-collapse: collapse; width: 100%; }
    th, td { border: 1px solid #999; padding: 8px; }
    th { background: #f2f2f2; text-align: left; }
    td { text-align: left; }
  </style>
</head>
<body>
  <h1>Dataset Totals Summary</h1>
  <p>Summary statistics for <strong>{total_rows:,}</strong> videos in the dataset.</p>
  <table>
"""
    html += "\n".join(html_rows)
    html += f"\n  </table>\n  <p>Data source: {DEFAULT_CSV.name}</p>\n</body>\n</html>"
    return html


def write_html(output_path: Path, summary: list[tuple[str, str]], total_rows: int) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(build_html_table(summary, total_rows), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build dataset-level totals for the YouTube dataset." 
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=DEFAULT_CSV,
        help="Path to the dataset CSV file.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Path to write the HTML summary table.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    csv_path = args.csv.resolve()
    output_path = args.output.resolve()

    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    rows, fieldnames = load_rows(csv_path)
    summary = build_summary(rows)
    write_html(output_path, summary, total_rows=len(rows))

    print(f"Dataset: {csv_path}")
    print(f"Rows: {len(rows):,}")
    for metric, value in summary:
        print(f"{metric}: {value}")
    print(f"Saved HTML summary table to: {output_path}")


if __name__ == "__main__":
    main()
