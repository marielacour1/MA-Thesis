import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path


# Curated from the cleaned dataset by reviewing channel names and keeping
# channels that appear to be news organizations, news brands, wire services,
# broadcasters, or newsroom sub-brands.
KNOWN_NEWS_CHANNELS = {
    "7NEWS Australia",
    "ABC News",
    "ABC News (Australia)",
    "AFP News Agency",
    "Al Jazeera English",
    "ANI News",
    "AP Archive",
    "APTN News",
    "ABS-CBN News",
    "Associated Press",
    "BBC News",
    "BBC Politics",
    "BBC World Service",
    "BFBS Forces News",
    "Bloomberg News",
    "CBC News",
    "CBC News North",
    "CBS Evening News",
    "CBS Mornings",
    "CBS News",
    "CBS Sunday Morning",
    "CGTN",
    "CGTN America",
    "CGTN Europe",
    "Channel 4 News",
    "CityNews",
    "CNN",
    "CNN-News18",
    "CNBC Television",
    "CNBC-TV18",
    "CRUX",
    "CTV News",
    "DawnNews English",
    "Daily Freeman",
    "euronews",
    "Express News",
    "Firstpost",
    "Forbes Breaking News",
    "Fox Business",
    "Fox News",
    "FOX 10 Phoenix",
    "FOX 13 Seattle",
    "FRANCE 24 English",
    "GBNews",
    "Geo News",
    "Global News",
    "Guardian News",
    "Hindustan Times",
    "India Today",
    "ITV News",
    "Kalaallit Nunaata Radioa | KNR TV",
    "KGW News",
    "KNR Nutaarsiassat / KNR News",
    "LiveNOW from FOX",
    "NBC News",
    "Newsmax",
    "NewsNation",
    "New York Post",
    "Oneindia News",
    "PBS NewsHour",
    "Reuters",
    "SABC News",
    "SBS News",
    "Scripps News",
    "Sky News",
    "Sky News Australia",
    "South China Morning Post",
    "Straight Arrow News",
    "The Canadian Press",
    "The New York Times",
    "The Wall Street Journal",
    "Times Now",
    "Times Now World",
    "Times Of India",
    "TODAY",
    "UNTV News and Rescue",
    "USA TODAY",
    "VICE News",
    "Washington Post",
    "WION",
    "WSJ News",
}


def load_rows(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError("CSV appears empty or missing header.")
        return list(reader)


def load_curated_news_channels(review_csv: Path) -> set[str]:
    if not review_csv.exists():
        return set(KNOWN_NEWS_CHANNELS)

    with review_csv.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or "channel_title" not in reader.fieldnames:
            raise ValueError(
                f"Curated review CSV must contain a 'channel_title' column. Found: {reader.fieldnames}"
            )

        if "is_news" not in reader.fieldnames:
            curated_news_channels = {
                (row.get("channel_title") or "").strip()
                for row in reader
                if (row.get("channel_title") or "").strip()
            }
            return set(KNOWN_NEWS_CHANNELS) | curated_news_channels

        curated_news_channels: set[str] = set(KNOWN_NEWS_CHANNELS)
        for row in reader:
            channel_title = (row.get("channel_title") or "").strip()
            is_news = (row.get("is_news") or "").strip().lower()
            if channel_title and is_news in {"yes", "y", "true", "1"}:
                curated_news_channels.add(channel_title)

    return curated_news_channels


def filter_news_rows(
    rows: list[dict[str, str]],
    curated_news_channels: set[str],
) -> tuple[list[dict[str, str]], dict[str, dict[str, str | int]]]:
    filtered_rows: list[dict[str, str]] = []
    channel_summary: dict[str, dict[str, str | int]] = {}
    ids_by_channel: dict[str, set[str]] = defaultdict(set)
    countries_by_channel: dict[str, set[str]] = defaultdict(set)
    counts: Counter[str] = Counter()

    for row in rows:
        channel_title = (row.get("channel_title") or "").strip()
        if channel_title not in curated_news_channels:
            continue

        filtered_rows.append(row)
        counts[channel_title] += 1

        channel_id = (row.get("channel_id") or "").strip()
        channel_country = (row.get("channel_country") or "").strip()
        if channel_id:
            ids_by_channel[channel_title].add(channel_id)
        if channel_country:
            countries_by_channel[channel_title].add(channel_country)

    for channel_title in sorted(counts):
        channel_summary[channel_title] = {
            "channel_title": channel_title,
            "video_count": counts[channel_title],
            "channel_ids": "; ".join(sorted(ids_by_channel[channel_title])),
            "channel_countries": "; ".join(sorted(countries_by_channel[channel_title])),
            "selection_method": "curated_name_match",
        }

    return filtered_rows, channel_summary


def save_csv(rows: list[dict[str, str]], output_path: Path, fieldnames: list[str]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def save_channel_summary(channel_summary: dict[str, dict[str, str | int]], output_path: Path) -> None:
    rows = [channel_summary[name] for name in sorted(channel_summary, key=lambda n: (-int(channel_summary[n]["video_count"]), n))]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["channel_title", "video_count", "channel_ids", "channel_countries", "selection_method"],
        )
        writer.writeheader()
        writer.writerows(rows)


def save_summary_text(
    output_path: Path,
    *,
    source_csv: Path,
    total_rows: int,
    filtered_rows: int,
    channel_count: int,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        "\n".join(
            [
                f"Source CSV: {source_csv}",
                f"Total videos in source dataset: {total_rows}",
                f"Videos kept from identified news channels: {filtered_rows}",
                f"Identified news channels: {channel_count}",
                "Selection basis: curated review of channel names in the cleaned dataset.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> None:
    default_csv = Path(__file__).resolve().parents[2] / "Datasets" / "gl-cl.csv"
    default_output_dir = Path(__file__).resolve().parent
    default_review_csv = default_output_dir / "identified_news_channels.csv"

    parser = argparse.ArgumentParser(
        description="Identify likely news channels in the cleaned dataset and save a filtered news-only dataset."
    )
    parser.add_argument("--csv", type=Path, default=default_csv, help="Path to the cleaned input CSV.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=default_output_dir,
        help="Folder where the filtered dataset and channel summary will be saved.",
    )
    parser.add_argument(
        "--review-csv",
        type=Path,
        default=default_review_csv,
        help="Curated channel review CSV. Rows marked is_news=yes will be kept.",
    )

    args = parser.parse_args()
    csv_path = args.csv.resolve()
    output_dir = args.output_dir.resolve()
    review_csv = args.review_csv.resolve()

    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    rows = load_rows(csv_path)
    curated_news_channels = load_curated_news_channels(review_csv)
    filtered_rows, channel_summary = filter_news_rows(rows, curated_news_channels)
    if not rows:
        raise ValueError("Input CSV contains no rows.")

    fieldnames = list(rows[0].keys())
    filtered_csv = output_dir / f"{csv_path.stem}-news-channels-only.csv"
    channels_csv = output_dir / "identified_news_channels.csv"
    summary_txt = output_dir / "summary.txt"

    save_csv(filtered_rows, filtered_csv, fieldnames)
    save_channel_summary(channel_summary, channels_csv)
    save_summary_text(
        summary_txt,
        source_csv=csv_path,
        total_rows=len(rows),
        filtered_rows=len(filtered_rows),
        channel_count=len(channel_summary),
    )

    print(f"Source CSV: {csv_path}")
    print(f"Total videos in source dataset: {len(rows)}")
    print(f"Identified news channels: {len(channel_summary)}")
    print(f"Videos kept from news channels: {len(filtered_rows)}")
    print("")
    print(f"Curated review CSV: {review_csv}")
    print(f"Saved filtered dataset to: {filtered_csv}")
    print(f"Saved identified channels to: {channels_csv}")
    print(f"Saved summary to: {summary_txt}")


if __name__ == "__main__":
    main()
