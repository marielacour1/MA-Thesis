import csv
from collections import Counter, defaultdict
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parents[1]
INPUT_CSV = PROJECT_DIR / "Datasets" / "final_dataset.csv"
OUTPUT_TXT = SCRIPT_DIR / "channel-country-breakdown-by-frame.txt"
FRAME_COLUMN = "frame"
COUNTRY_COLUMN = "channel_country"
MISSING_COUNTRY_LABEL = "(No country)"
OTHER_COUNTRIES_LABEL = "Other countries"
OTHER_THRESHOLD_PERCENT = 1.0


TABLE_COLUMNS = [
    ("Country", "Country", "left"),
    ("Videos", "Videos", "right"),
    ("% frame", "% frame", "right"),
    ("% known", "% known", "right"),
    ("% country", "% country", "right"),
]


def pct(part: int, whole: int) -> float:
    if whole == 0:
        return 0.0
    return part / whole * 100


def normalize_country(value: str | None) -> str:
    country = (value or "").strip().upper()
    return country or MISSING_COUNTRY_LABEL


def align(value: str, width: int, direction: str) -> str:
    if direction == "right":
        return value.rjust(width)
    return value.ljust(width)


def format_table(rows: list[dict[str, str]]) -> list[str]:
    widths = {
        key: max(len(header), *(len(row[key]) for row in rows))
        for key, header, _direction in TABLE_COLUMNS
    }
    separator = "-+-".join("-" * widths[key] for key, _header, _direction in TABLE_COLUMNS)
    header = " | ".join(
        align(header, widths[key], direction)
        for key, header, direction in TABLE_COLUMNS
    )
    body = [
        " | ".join(
            align(row[key], widths[key], direction)
            for key, _header, direction in TABLE_COLUMNS
        )
        for row in rows
    ]
    return [separator, header, separator, *body, separator]


def load_country_counts_by_frame() -> tuple[dict[str, Counter[str]], Counter[str], int]:
    country_counts_by_frame: dict[str, Counter[str]] = defaultdict(Counter)
    country_totals: Counter[str] = Counter()
    missing_frame_rows = 0

    with INPUT_CSV.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        missing = [column for column in (FRAME_COLUMN, COUNTRY_COLUMN) if column not in fieldnames]
        if missing:
            raise ValueError(f"Missing required columns: {', '.join(missing)}")

        for row in reader:
            frame = (row.get(FRAME_COLUMN) or "").strip()
            if not frame:
                missing_frame_rows += 1
                continue

            country = normalize_country(row.get(COUNTRY_COLUMN))
            country_counts_by_frame[frame][country] += 1
            country_totals[country] += 1

    if not country_counts_by_frame:
        raise ValueError("No rows with frame values found.")

    return dict(country_counts_by_frame), country_totals, missing_frame_rows


def build_frame_table(
    frame: str,
    country_counts: Counter[str],
    country_totals: Counter[str],
) -> list[str]:
    total_videos = sum(country_counts.values())
    no_country_count = country_counts[MISSING_COUNTRY_LABEL]
    known_country_total = total_videos - no_country_count
    display_counts: Counter[str] = Counter()
    display_totals: Counter[str] = Counter()

    for country, count in country_counts.items():
        if country == MISSING_COUNTRY_LABEL:
            display_counts[country] += count
            display_totals[country] += country_totals[country]
        elif pct(count, known_country_total) < OTHER_THRESHOLD_PERCENT:
            display_counts[OTHER_COUNTRIES_LABEL] += count
            display_totals[OTHER_COUNTRIES_LABEL] += country_totals[country]
        else:
            display_counts[country] += count
            display_totals[country] += country_totals[country]

    rows = []
    countries = sorted(
        display_counts,
        key=lambda country: (
            country == MISSING_COUNTRY_LABEL,
            country == OTHER_COUNTRIES_LABEL,
            -display_counts[country],
            country,
        ),
    )
    for country in countries:
        count = display_counts[country]
        rows.append(
            {
                "Country": country,
                "Videos": f"{count:,}",
                "% frame": f"{pct(count, total_videos):.2f}%",
                "% known": (
                    "" if country == MISSING_COUNTRY_LABEL else f"{pct(count, known_country_total):.2f}%"
                ),
                "% country": f"{pct(count, display_totals[country]):.2f}%",
            }
        )

    lines = [
        "",
        frame,
        "=" * len(frame),
        (
            f"Total: {total_videos:,} | "
            f"With country: {known_country_total:,} ({pct(known_country_total, total_videos):.2f}%) | "
            f"No country: {no_country_count:,} ({pct(no_country_count, total_videos):.2f}%)"
        ),
    ]
    lines.extend(format_table(rows))
    return lines


def build_report(
    country_counts_by_frame: dict[str, Counter[str]],
    country_totals: Counter[str],
    missing_frame_rows: int,
) -> str:
    total_videos = sum(sum(country_counts.values()) for country_counts in country_counts_by_frame.values())
    frames = sorted(
        country_counts_by_frame,
        key=lambda frame: sum(country_counts_by_frame[frame].values()),
        reverse=True,
    )

    lines = [
        "Channel Country Breakdown by Frame",
        "==================================",
        f"Input CSV: {INPUT_CSV}",
        f"Total videos with a frame: {total_videos:,}",
        f"Rows skipped because frame was missing: {missing_frame_rows:,}",
        "",
        "Notes:",
        f"- Missing or blank channel_country values are shown as {MISSING_COUNTRY_LABEL}.",
        f"- Countries below {OTHER_THRESHOLD_PERCENT:.0f}% of videos with a known country within a frame are grouped as {OTHER_COUNTRIES_LABEL}.",
        "- '% frame' uses all videos in the frame as the denominator.",
        "- '% known' uses only videos with a non-missing country in the frame as the denominator.",
        "- '% country' shows the percentage of all videos from that country that appear in the given frame.",
    ]

    for frame in frames:
        lines.extend(build_frame_table(frame, country_counts_by_frame[frame], country_totals))

    return "\n".join(lines) + "\n"


def main() -> None:
    country_counts_by_frame, country_totals, missing_frame_rows = load_country_counts_by_frame()
    report = build_report(country_counts_by_frame, country_totals, missing_frame_rows)
    OUTPUT_TXT.write_text(report, encoding="utf-8")
    print(report, end="")
    print(f"\nSaved report to: {OUTPUT_TXT}")


if __name__ == "__main__":
    main()
