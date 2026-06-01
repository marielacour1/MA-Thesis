import csv
import sys
from collections import defaultdict
from pathlib import Path


HERE = Path(__file__).resolve().parent
INPUT_PATH = HERE / "geopolitical_frame_videos_with_subframes.csv"
CHANNEL_OUTPUT_PATH = HERE / "top_geopolitical_channels_by_subscribers.csv"
VIDEO_OUTPUT_PATH = HERE / "top_geopolitical_videos_by_views.csv"
TOP_N = 20


def parse_int(value: str | None) -> int | None:
    text = (value or "").strip().replace(",", "")
    if not text:
        return None
    try:
        number = int(float(text))
    except ValueError:
        return None
    if number < 0:
        return None
    return number


def format_count(value: int | None) -> str:
    if value is None:
        return "missing"
    return f"{value:,}"


def load_channel_stats() -> list[dict[str, object]]:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"Input CSV not found: {INPUT_PATH}")

    channels: dict[str, dict[str, object]] = defaultdict(
        lambda: {
            "channel_title": "",
            "channel_subscriber_count": None,
            "geopolitical_video_count": 0,
        }
    )

    with INPUT_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {
            "video_id",
            "channel_id",
            "channel_title",
            "channel_subscriber_count",
        }
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")

        for row in reader:
            channel_id = (row.get("channel_id") or "").strip()
            if not channel_id:
                continue

            stats = channels[channel_id]
            stats["channel_id"] = channel_id
            stats["channel_title"] = (row.get("channel_title") or "").strip()
            stats["geopolitical_video_count"] += 1

            subscribers = parse_int(row.get("channel_subscriber_count"))
            current_subscribers = stats["channel_subscriber_count"]
            if subscribers is not None and (
                current_subscribers is None or subscribers > current_subscribers
            ):
                stats["channel_subscriber_count"] = subscribers

    return sorted(
        channels.values(),
        key=lambda item: (
            item["channel_subscriber_count"] is not None,
            item["channel_subscriber_count"] or -1,
            item["geopolitical_video_count"],
        ),
        reverse=True,
    )


def load_video_stats() -> list[dict[str, object]]:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"Input CSV not found: {INPUT_PATH}")

    videos: list[dict[str, object]] = []

    with INPUT_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {
            "video_id",
            "video_title",
            "published_at",
            "view_count",
            "channel_id",
            "channel_title",
        }
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")

        for row in reader:
            views = parse_int(row.get("view_count"))
            if views is None:
                continue

            videos.append(
                {
                    "video_id": (row.get("video_id") or "").strip(),
                    "video_title": (row.get("video_title") or "").strip(),
                    "published_at": (row.get("published_at") or "").strip(),
                    "view_count": views,
                    "channel_title": (row.get("channel_title") or "").strip(),
                    "channel_id": (row.get("channel_id") or "").strip(),
                }
            )

    return sorted(videos, key=lambda item: item["view_count"], reverse=True)


def write_channel_output(rows: list[dict[str, object]]) -> None:
    fieldnames = [
        "rank",
        "channel_title",
        "channel_id",
        "channel_subscriber_count",
        "geopolitical_video_count",
    ]
    with CHANNEL_OUTPUT_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for rank, row in enumerate(rows, start=1):
            writer.writerow(
                {
                    "rank": rank,
                    "channel_title": row["channel_title"],
                    "channel_id": row["channel_id"],
                    "channel_subscriber_count": row["channel_subscriber_count"],
                    "geopolitical_video_count": row["geopolitical_video_count"],
                }
            )


def write_video_output(rows: list[dict[str, object]]) -> None:
    fieldnames = [
        "rank",
        "video_title",
        "view_count",
        "channel_title",
        "channel_id",
        "video_id",
        "published_at",
    ]
    with VIDEO_OUTPUT_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for rank, row in enumerate(rows, start=1):
            writer.writerow(
                {
                    "rank": rank,
                    "video_title": row["video_title"],
                    "view_count": row["view_count"],
                    "channel_title": row["channel_title"],
                    "channel_id": row["channel_id"],
                    "video_id": row["video_id"],
                    "published_at": row["published_at"],
                }
            )


def shorten(text: str, max_length: int) -> str:
    if len(text) <= max_length:
        return text
    return f"{text[: max_length - 3]}..."


def printable(text: str) -> str:
    encoding = sys.stdout.encoding or "utf-8"
    return text.encode(encoding, errors="replace").decode(encoding)


def print_channel_rows(rows: list[dict[str, object]]) -> None:
    print(f"Top {len(rows)} geopolitical-frame channels by subscriber count")
    print(f"Source: {INPUT_PATH}")
    print()

    table_rows = [
        {
            "rank": str(rank),
            "channel_title": printable(str(row["channel_title"])),
            "subscribers": format_count(row["channel_subscriber_count"]),
            "videos": format_count(row["geopolitical_video_count"]),
            "channel_id": str(row["channel_id"]),
        }
        for rank, row in enumerate(rows, start=1)
    ]

    headers = {
        "rank": "#",
        "channel_title": "Channel",
        "subscribers": "Subscribers",
        "videos": "Geo. videos",
        "channel_id": "Channel ID",
    }
    widths = {
        key: max(len(headers[key]), *(len(row[key]) for row in table_rows))
        for key in headers
    }

    header_line = (
        f"{headers['rank']:>{widths['rank']}}  "
        f"{headers['channel_title']:<{widths['channel_title']}}  "
        f"{headers['subscribers']:>{widths['subscribers']}}  "
        f"{headers['videos']:>{widths['videos']}}  "
        f"{headers['channel_id']:<{widths['channel_id']}}"
    )
    separator_line = (
        f"{'-' * widths['rank']}  "
        f"{'-' * widths['channel_title']}  "
        f"{'-' * widths['subscribers']}  "
        f"{'-' * widths['videos']}  "
        f"{'-' * widths['channel_id']}"
    )

    print(header_line)
    print(separator_line)
    for row in table_rows:
        print(
            f"{row['rank']:>{widths['rank']}}  "
            f"{row['channel_title']:<{widths['channel_title']}}  "
            f"{row['subscribers']:>{widths['subscribers']}}  "
            f"{row['videos']:>{widths['videos']}}  "
            f"{row['channel_id']:<{widths['channel_id']}}"
        )

    print()
    print(f"Saved channel CSV to: {CHANNEL_OUTPUT_PATH}")


def print_video_rows(rows: list[dict[str, object]]) -> None:
    print()
    print(f"Top {len(rows)} geopolitical-frame videos by view count")
    print()

    table_rows = [
        {
            "rank": str(rank),
            "video_title": printable(shorten(str(row["video_title"]), 70)),
            "views": format_count(row["view_count"]),
            "channel_title": printable(shorten(str(row["channel_title"]), 36)),
            "video_id": str(row["video_id"]),
        }
        for rank, row in enumerate(rows, start=1)
    ]

    headers = {
        "rank": "#",
        "video_title": "Video",
        "views": "Views",
        "channel_title": "Channel",
        "video_id": "Video ID",
    }
    widths = {
        key: max(len(headers[key]), *(len(row[key]) for row in table_rows))
        for key in headers
    }

    header_line = (
        f"{headers['rank']:>{widths['rank']}}  "
        f"{headers['video_title']:<{widths['video_title']}}  "
        f"{headers['views']:>{widths['views']}}  "
        f"{headers['channel_title']:<{widths['channel_title']}}  "
        f"{headers['video_id']:<{widths['video_id']}}"
    )
    separator_line = (
        f"{'-' * widths['rank']}  "
        f"{'-' * widths['video_title']}  "
        f"{'-' * widths['views']}  "
        f"{'-' * widths['channel_title']}  "
        f"{'-' * widths['video_id']}"
    )

    print(header_line)
    print(separator_line)
    for row in table_rows:
        print(
            f"{row['rank']:>{widths['rank']}}  "
            f"{row['video_title']:<{widths['video_title']}}  "
            f"{row['views']:>{widths['views']}}  "
            f"{row['channel_title']:<{widths['channel_title']}}  "
            f"{row['video_id']:<{widths['video_id']}}"
        )

    print()
    print(f"Saved video CSV to: {VIDEO_OUTPUT_PATH}")


def main() -> None:
    top_channel_rows = load_channel_stats()[:TOP_N]
    top_video_rows = load_video_stats()[:TOP_N]
    write_channel_output(top_channel_rows)
    write_video_output(top_video_rows)
    print_channel_rows(top_channel_rows)
    print_video_rows(top_video_rows)


if __name__ == "__main__":
    main()
