import argparse
import csv
from collections import Counter
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_REVIEW_CSV = SCRIPT_DIR / "gl-cl-w-topics-FINAL-official-news-channels-ai-review.csv"
MISSING_COUNTRY_LABEL = "Missing country"


def pct(part: int, whole: int) -> float:
    return (part / whole * 100) if whole else 0.0


def parse_int(value: str | None) -> int:
    try:
        return int((value or "").strip())
    except ValueError:
        return 0


def load_country_counts(
    review_csv: Path,
    strict_only: bool = False,
) -> tuple[Counter[str], Counter[str], list[dict[str, str]]]:
    channel_counts: Counter[str] = Counter()
    video_counts: Counter[str] = Counter()
    missing_country_rows: list[dict[str, str]] = []

    with review_csv.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError(f"CSV appears empty or missing header: {review_csv}")

        required_columns = {
            "channel_title",
            "channel_id",
            "video_count_in_final",
            "channel_country",
            "ai_news_status",
        }
        missing_columns = required_columns - set(reader.fieldnames)
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise ValueError(f"Missing column(s) in {review_csv}: {missing}")

        for row in reader:
            status = (row.get("ai_news_status") or "").strip()
            if strict_only and status != "official_news_channel":
                continue

            country = (row.get("channel_country") or "").strip()
            country_label = country or MISSING_COUNTRY_LABEL
            channel_counts[country_label] += 1
            video_counts[country_label] += parse_int(row.get("video_count_in_final"))

            if not country:
                missing_country_rows.append(
                    {
                        "channel_title": (row.get("channel_title") or "").strip(),
                        "channel_id": (row.get("channel_id") or "").strip(),
                        "video_count_in_final": (row.get("video_count_in_final") or "").strip(),
                        "ai_news_status": status,
                    }
                )

    return channel_counts, video_counts, missing_country_rows


def print_country_summary(
    label: str,
    channel_counts: Counter[str],
    video_counts: Counter[str],
    missing_country_rows: list[dict[str, str]],
    show_missing_channels: bool,
) -> None:
    total_channels = sum(channel_counts.values())
    total_videos = sum(video_counts.values())
    missing_channels = channel_counts[MISSING_COUNTRY_LABEL]

    print(label)
    print("=" * len(label))
    print(f"News channels: {total_channels:,}")
    print(
        f"Channels without country: {missing_channels:,} "
        f"({pct(missing_channels, total_channels):.0f}%)"
    )
    print()
    print("Country breakdown")
    print(
        f"{'country':<16}"
        f"{'channels':>10}"
        f"{'% channels':>12}"
        f"{'videos':>12}"
        f"{'% videos':>10}"
    )
    for country, channels in channel_counts.most_common():
        videos = video_counts[country]
        print(
            f"{country:<16}"
            f"{channels:>10}"
            f"{pct(channels, total_channels):>11.0f}%"
            f"{videos:>12}"
            f"{pct(videos, total_videos):>9.0f}%"
        )

    if show_missing_channels and missing_country_rows:
        print()
        print("Channels without country")
        print("channel_title,channel_id,video_count_in_final,ai_news_status")
        for row in missing_country_rows:
            print(
                f"{row['channel_title']},{row['channel_id']},"
                f"{row['video_count_in_final']},{row['ai_news_status']}"
            )
    print()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Summarize which country codes official or likely official news "
            "channels operate from, including missing country values."
        )
    )
    parser.add_argument("--review-csv", type=Path, default=DEFAULT_REVIEW_CSV)
    parser.add_argument(
        "--strict-only",
        action="store_true",
        help="Only count channels marked official_news_channel.",
    )
    parser.add_argument(
        "--include-strict-comparison",
        action="store_true",
        help="Also print a separate strict official_news_channel-only summary.",
    )
    parser.add_argument(
        "--show-missing-channels",
        action="store_true",
        help="Print the channel names and IDs where channel_country is blank.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    channel_counts, video_counts, missing_country_rows = load_country_counts(
        args.review_csv,
        strict_only=args.strict_only,
    )
    label = (
        "Strict official news-channel countries"
        if args.strict_only
        else "Official and likely official news-channel countries"
    )
    print_country_summary(
        label,
        channel_counts,
        video_counts,
        missing_country_rows,
        args.show_missing_channels,
    )

    if args.include_strict_comparison and not args.strict_only:
        channel_counts, video_counts, missing_country_rows = load_country_counts(
            args.review_csv,
            strict_only=True,
        )
        print_country_summary(
            "Strict official news-channel countries",
            channel_counts,
            video_counts,
            missing_country_rows,
            args.show_missing_channels,
        )


if __name__ == "__main__":
    main()
