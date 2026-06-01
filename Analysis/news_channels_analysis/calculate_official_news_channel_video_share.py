import argparse
import csv
from collections import Counter
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_FINAL_CSV = (
    Path(__file__).resolve().parents[2]
    / "Datasets"
    / "gl-cl-w-topics-FINAL.csv"
)
DEFAULT_REVIEW_CSV = SCRIPT_DIR / "gl-cl-w-topics-FINAL-official-news-channels-ai-review.csv"


def pct(part: int, whole: int) -> float:
    return (part / whole * 100) if whole else 0.0


def load_channel_ids(review_csv: Path, strict_only: bool = False) -> set[str]:
    channel_ids: set[str] = set()

    with review_csv.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError(f"CSV appears empty or missing header: {review_csv}")

        required_columns = {"channel_id", "ai_news_status"}
        missing_columns = required_columns - set(reader.fieldnames)
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise ValueError(f"Missing column(s) in {review_csv}: {missing}")

        for row in reader:
            channel_id = (row.get("channel_id") or "").strip()
            status = (row.get("ai_news_status") or "").strip()
            if not channel_id:
                continue
            if strict_only and status != "official_news_channel":
                continue
            channel_ids.add(channel_id)

    return channel_ids


def calculate_video_share(
    final_csv: Path,
    news_channel_ids: set[str],
) -> tuple[int, int, Counter[str], Counter[str]]:
    total_videos = 0
    news_videos = 0
    frame_totals: Counter[str] = Counter()
    frame_news_totals: Counter[str] = Counter()

    with final_csv.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError(f"CSV appears empty or missing header: {final_csv}")

        required_columns = {"channel_id", "frame"}
        missing_columns = required_columns - set(reader.fieldnames)
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise ValueError(f"Missing column(s) in {final_csv}: {missing}")

        for row in reader:
            total_videos += 1
            frame = (row.get("frame") or "").strip() or "Unassigned"
            channel_id = (row.get("channel_id") or "").strip()

            frame_totals[frame] += 1
            if channel_id in news_channel_ids:
                news_videos += 1
                frame_news_totals[frame] += 1

    return total_videos, news_videos, frame_totals, frame_news_totals


def print_summary(
    label: str,
    channel_count: int,
    total_videos: int,
    news_videos: int,
    frame_totals: Counter[str],
    frame_news_totals: Counter[str],
) -> None:
    print(label)
    print("=" * len(label))
    print(f"News channels: {channel_count:,}")
    print(
        f"News-channel videos: {news_videos:,} of {total_videos:,} "
        f"({pct(news_videos, total_videos):.2f}%)"
    )
    print()
    print("Frame breakdown")
    print("frame,news_channel_videos,total_videos_in_frame,pct_within_frame")
    for frame, total in frame_totals.most_common():
        news_count = frame_news_totals[frame]
        print(f"{frame},{news_count},{total},{pct(news_count, total):.2f}%")
    print()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Calculate what share of final dataset videos come from official "
            "or likely official news channels, overall and within each frame."
        )
    )
    parser.add_argument("--final-csv", type=Path, default=DEFAULT_FINAL_CSV)
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
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    all_review_channel_ids = load_channel_ids(args.review_csv, strict_only=args.strict_only)
    total_videos, news_videos, frame_totals, frame_news_totals = calculate_video_share(
        args.final_csv,
        all_review_channel_ids,
    )

    label = (
        "Strict official-news-channel share"
        if args.strict_only
        else "Official and likely official news-channel share"
    )
    print_summary(
        label,
        len(all_review_channel_ids),
        total_videos,
        news_videos,
        frame_totals,
        frame_news_totals,
    )

    if args.include_strict_comparison and not args.strict_only:
        strict_channel_ids = load_channel_ids(args.review_csv, strict_only=True)
        total_videos, news_videos, frame_totals, frame_news_totals = calculate_video_share(
            args.final_csv,
            strict_channel_ids,
        )
        print_summary(
            "Strict official-news-channel share",
            len(strict_channel_ids),
            total_videos,
            news_videos,
            frame_totals,
            frame_news_totals,
        )


if __name__ == "__main__":
    main()
