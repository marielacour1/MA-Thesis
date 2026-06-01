import argparse
import csv
from pathlib import Path

import yt_scraper


def load_video_ids(path: Path) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(f"Missing ID file not found: {path}")

    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or "video_id" not in reader.fieldnames:
            raise ValueError("ID CSV must contain a 'video_id' column.")

        seen = set()
        video_ids = []
        for row in reader:
            video_id = (row.get("video_id") or "").strip()
            if not video_id or video_id in seen:
                continue
            seen.add(video_id)
            video_ids.append(video_id)

    return video_ids


def build_rows_from_videos(videos: list[dict], channel_info: dict[str, dict[str, str]]) -> dict[str, dict[str, str]]:
    rows_by_id: dict[str, dict[str, str]] = {}
    for video in videos:
        snippet = video.get("snippet", {})
        stats = video.get("statistics", {})
        content = video.get("contentDetails", {})
        channel_id = snippet.get("channelId", "")
        info = channel_info.get(channel_id, {})
        video_id = video.get("id", "")
        if not video_id:
            continue

        rows_by_id[video_id] = {
            "video_id": video_id,
            "video_title": snippet.get("title", ""),
            "video_description": snippet.get("description", "") if yt_scraper.FETCH_DESCRIPTIONS else "",
            "published_at": snippet.get("publishedAt", ""),
            "duration": yt_scraper.duration_to_seconds(content.get("duration", "")),
            "view_count": stats.get("viewCount", ""),
            "video_like_count": stats.get("likeCount", ""),
            "comment_count": stats.get("commentCount", ""),
            "channel_id": channel_id,
            "channel_title": snippet.get("channelTitle", ""),
            "channel_subscriber_count": info.get("subscriber_count", ""),
            "channel_video_count": info.get("video_count", ""),
            "channel_country": info.get("country", ""),
        }
    return rows_by_id


def fetch_rows(video_ids: list[str]) -> dict[str, dict[str, str]]:
    refreshed_videos = []
    for start in range(0, len(video_ids), 50):
        batch = video_ids[start : start + 50]
        videos, quota_hit = yt_scraper.get_video_details(batch)
        refreshed_videos.extend(videos)
        if quota_hit:
            raise yt_scraper.QuotaExceededError(
                f"Quota exceeded while refetching IDs starting at batch {start // 50 + 1}."
            )

    channel_ids = sorted(
        {
            video.get("snippet", {}).get("channelId", "")
            for video in refreshed_videos
            if video.get("snippet", {}).get("channelId")
        }
    )
    channel_info = {}
    if channel_ids:
        channel_info, quota_hit = yt_scraper.get_channel_info(channel_ids)
        if quota_hit:
            raise yt_scraper.QuotaExceededError("Quota exceeded while refetching channel details.")

    return build_rows_from_videos(refreshed_videos, channel_info)


def update_existing_csv(
    csv_path: Path,
    refreshed_rows_by_id: dict[str, dict[str, str]],
) -> tuple[int, int, list[str]]:
    if not csv_path.exists():
        raise FileNotFoundError(f"Target CSV not found: {csv_path}")

    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or yt_scraper.CSV_HEADERS)
        rows = list(reader)

    replacements = 0
    found_ids = set()
    updated_rows = []
    for row in rows:
        video_id = (row.get("video_id") or "").strip()
        replacement = refreshed_rows_by_id.get(video_id)
        if replacement is None:
            updated_rows.append({header: row.get(header, "") for header in fieldnames})
            continue

        updated_rows.append({header: replacement.get(header, "") for header in fieldnames})
        replacements += 1
        found_ids.add(video_id)

    missing_from_target = sorted(set(refreshed_rows_by_id) - found_ids)

    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(updated_rows)

    return replacements, len(updated_rows), missing_from_target


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    default_ids_file = script_dir / "Analysis" / "Descriptive_table" / "gl-cl-numeric-quality-issues.csv"
    default_target_csv = script_dir / "Datasets" / "yt-greenland.csv"

    parser = argparse.ArgumentParser(
        description="Re-fetch specific YouTube video rows and overwrite matching rows in yt-greenland.csv."
    )
    parser.add_argument(
        "--ids-csv",
        type=Path,
        default=default_ids_file,
        help="CSV file containing video IDs. Must contain a 'video_id' column.",
    )
    parser.add_argument(
        "--target-csv",
        type=Path,
        default=default_target_csv,
        help="Target CSV to update in place.",
    )
    args = parser.parse_args()

    yt_scraper.debug_env_status()
    if not yt_scraper.API_KEYS:
        raise SystemExit("Manglende API key. Sæt YOUTUBE_API_KEY i miljøet eller .env.")

    ids_csv = args.ids_csv.resolve()
    target_csv = args.target_csv.resolve()

    video_ids = load_video_ids(ids_csv)
    if not video_ids:
        raise SystemExit(f"No video IDs found in: {ids_csv}")

    print(f"Loading {len(video_ids)} unique video IDs from: {ids_csv}")
    refreshed_rows_by_id = fetch_rows(video_ids)
    print(f"Fetched fresh data for {len(refreshed_rows_by_id)} videos from the YouTube API.")

    replacements, total_rows, missing_from_target = update_existing_csv(target_csv, refreshed_rows_by_id)
    print(f"Updated {replacements} matching rows in: {target_csv}")
    print(f"Total rows preserved in target CSV: {total_rows}")

    not_returned = [video_id for video_id in video_ids if video_id not in refreshed_rows_by_id]
    if not_returned:
        print(f"IDs not returned by the API: {len(not_returned)}")
        for video_id in not_returned[:20]:
            print(f"  {video_id}")
        if len(not_returned) > 20:
            print("  ...")

    if missing_from_target:
        print(f"Fetched IDs not found in target CSV: {len(missing_from_target)}")
        for video_id in missing_from_target[:20]:
            print(f"  {video_id}")
        if len(missing_from_target) > 20:
            print("  ...")


if __name__ == "__main__":
    main()
