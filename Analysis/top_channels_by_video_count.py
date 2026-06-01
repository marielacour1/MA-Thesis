import argparse
import csv
from collections import Counter
from pathlib import Path


DEFAULT_CSV = Path(__file__).resolve().parent.parent / "Datasets" / "gl-cl-w-topics-FINAL.csv"
DEFAULT_CHANNEL_COLUMN = "channel_title"
DEFAULT_TOP_N = 50


def count_videos_by_channel(csv_path: Path, channel_column: str) -> Counter[str]:
    counts: Counter[str] = Counter()

    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None or channel_column not in reader.fieldnames:
            raise ValueError(
                f"Column '{channel_column}' not found in CSV. Available columns: {reader.fieldnames}"
            )

        for row in reader:
            channel_id = (row.get(channel_column) or "").strip()
            if channel_id:
                counts[channel_id] += 1

    if not counts:
        raise ValueError("No non-empty channel IDs found in CSV.")

    return counts


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Print the channels with the most videos in the dataset."
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=DEFAULT_CSV,
        help=f"Path to the CSV dataset. Defaults to: {DEFAULT_CSV}",
    )
    parser.add_argument(
        "--channel-column",
        default=DEFAULT_CHANNEL_COLUMN,
        help=f"Channel name column. Defaults to: {DEFAULT_CHANNEL_COLUMN}",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=DEFAULT_TOP_N,
        help=f"How many channels to print. Defaults to: {DEFAULT_TOP_N}",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    counts = count_videos_by_channel(args.csv, args.channel_column)

    print(f"Top {args.top_n} channels by number of videos")
    print("-" * 60)
    print(f"{'Rank':>4}  {'Videos':>6}  Channel")
    print("-" * 60)

    for rank, (channel_id, video_count) in enumerate(
        counts.most_common(args.top_n), start=1
    ):
        print(f"{rank:>4}  {video_count:>6}  {channel_id}")


if __name__ == "__main__":
    main()
