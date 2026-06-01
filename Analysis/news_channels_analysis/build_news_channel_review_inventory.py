import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path


NEWS_KEYWORDS = (
    "news",
    "newsroom",
    "newsmakers",
    "breaking",
    "report",
    "reports",
    "journal",
    "post",
    "press",
    "times",
    "today",
    "television",
    "tv",
    "media",
    "bulletin",
    "world",
    "wire",
    "herald",
    "gazette",
)


def load_known_news_channels(review_csv: Path) -> set[str]:
    if not review_csv.exists():
        return set()

    with review_csv.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or "channel_title" not in reader.fieldnames:
            return set()

        if "is_news" not in reader.fieldnames:
            return {
                (row.get("channel_title") or "").strip()
                for row in reader
                if (row.get("channel_title") or "").strip()
            }

        known_news_channels: set[str] = set()
        for row in reader:
            channel_title = (row.get("channel_title") or "").strip()
            is_news = (row.get("is_news") or "").strip().lower()
            if channel_title and is_news in {"yes", "y", "true", "1"}:
                known_news_channels.add(channel_title)
        return known_news_channels


def looks_news_like(channel_title: str) -> bool:
    lowered = channel_title.lower()
    return any(keyword in lowered for keyword in NEWS_KEYWORDS)


def build_inventory_rows(
    csv_path: Path,
    known_news_channels: set[str],
) -> list[dict[str, str | int]]:
    counts: Counter[str] = Counter()
    ids_by_channel: dict[str, set[str]] = defaultdict(set)
    countries_by_channel: dict[str, set[str]] = defaultdict(set)

    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError("CSV appears empty or missing header.")

        for row in reader:
            channel_title = (row.get("channel_title") or "").strip()
            if not channel_title:
                continue

            counts[channel_title] += 1

            channel_id = (row.get("channel_id") or "").strip()
            channel_country = (row.get("channel_country") or "").strip()
            if channel_id:
                ids_by_channel[channel_title].add(channel_id)
            if channel_country:
                countries_by_channel[channel_title].add(channel_country)

    rows: list[dict[str, str | int]] = []
    for channel_title, video_count in counts.items():
        if channel_title in known_news_channels:
            continue

        rows.append(
            {
                "channel_title": channel_title,
                "video_count": video_count,
                "channel_ids": "; ".join(sorted(ids_by_channel[channel_title])),
                "channel_countries": "; ".join(sorted(countries_by_channel[channel_title])),
                "is_news": "",
                "review_status": "needs_review",
                "suggested_news": "yes" if looks_news_like(channel_title) else "",
                "notes": "",
            }
        )

    rows.sort(
        key=lambda row: (
            -int(row["video_count"]),
            str(row["channel_title"]).lower(),
        )
    )
    return rows


def save_inventory(rows: list[dict[str, str | int]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "channel_title",
                "video_count",
                "channel_ids",
                "channel_countries",
                "is_news",
                "review_status",
                "suggested_news",
                "notes",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    default_csv = Path(__file__).resolve().parents[2] / "Datasets" / "gl-cl-w-topics-FINAL.csv"
    default_output = Path(__file__).resolve().parent / "all_channels_review_inventory.csv"
    default_review_csv = Path(__file__).resolve().parent / "identified_news_channels.csv"

    parser = argparse.ArgumentParser(
        description="Build a review inventory of all unique channels in the cleaned Greenland dataset."
    )
    parser.add_argument("--csv", type=Path, default=default_csv, help="Path to the cleaned Greenland CSV.")
    parser.add_argument(
        "--output",
        type=Path,
        default=default_output,
        help="Path where the full review inventory CSV will be written.",
    )
    parser.add_argument(
        "--review-csv",
        type=Path,
        default=default_review_csv,
        help="Existing curated news-channel CSV used to pre-fill confirmed channels.",
    )

    args = parser.parse_args()
    known_news_channels = load_known_news_channels(args.review_csv)
    rows = build_inventory_rows(args.csv, known_news_channels)
    save_inventory(rows, args.output)

    print(f"Source CSV: {args.csv.resolve()}")
    print(f"Unique channels found: {len(rows)}")
    print(f"Pre-filled confirmed news channels: {len(known_news_channels)}")
    print(f"Saved review inventory to: {args.output.resolve()}")


if __name__ == "__main__":
    main()
