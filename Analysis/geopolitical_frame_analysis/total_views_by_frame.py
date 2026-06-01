import argparse
import csv
from collections import defaultdict
from pathlib import Path


HERE = Path(__file__).resolve().parent
PROJECT_DIR = HERE.parent.parent
DATASET_PATH = PROJECT_DIR / "Datasets" / "gl-cl-w-topics-FINAL.csv"


def parse_view_count(value: str | None) -> int:
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


def compute_total_views_by_frame(dataset_path: Path) -> dict[str, int]:
    frame_totals: dict[str, int] = defaultdict(int)
    with dataset_path.open("r", encoding="utf-8", newline="") as infile:
        reader = csv.DictReader(infile)
        if reader.fieldnames is None:
            raise ValueError(f"No header found in {dataset_path}")
        if "frame" not in reader.fieldnames:
            raise ValueError("Input CSV must contain a 'frame' column.")
        if "view_count" not in reader.fieldnames:
            raise ValueError("Input CSV must contain a 'view_count' column.")

        for row in reader:
            frame = (row.get("frame") or "").strip() or "(missing frame)"
            views = parse_view_count(row.get("view_count"))
            frame_totals[frame] += views

    return dict(frame_totals)


def print_frame_totals(frame_totals: dict[str, int]) -> None:
    if not frame_totals:
        print("No frame data found.")
        return

    sorted_frames = sorted(frame_totals.items(), key=lambda item: item[1], reverse=True)
    print("Total views by frame:")
    for frame, total_views in sorted_frames:
        print(f"{frame}: {total_views:,}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compute total views for each frame in the dataset."
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=DATASET_PATH,
        help="Path to the dataset CSV file.",
    )
    args = parser.parse_args()

    if not args.dataset.exists():
        raise FileNotFoundError(f"Dataset not found: {args.dataset}")

    frame_totals = compute_total_views_by_frame(args.dataset)
    print_frame_totals(frame_totals)


if __name__ == "__main__":
    main()
