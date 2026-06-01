import csv
import importlib.util
from collections import Counter, defaultdict
from pathlib import Path


HERE = Path(__file__).resolve().parent
GEOPOLITICAL_DIR = HERE.parent
ANALYSIS_DIR = GEOPOLITICAL_DIR.parent
PROJECT_DIR = ANALYSIS_DIR.parent
FRAME_TIME_SCRIPT = (
    ANALYSIS_DIR
    / "Topic_modeling"
    / "Creating_frames"
    / "frame_distribution_over_time"
    / "frame_prevalence_over_time.py"
)
SOURCE_CSV = GEOPOLITICAL_DIR / "geopolitical_frame_videos_with_subframes.csv"
DATE_COLUMN = "published_at"
SUBFRAME_COLUMN = "geopolitical_subframe"
UNASSIGNED_SUBFRAME = "Unassigned geopolitical subframe"
CROSS_CUTTING_NON_FRAME = "Cross-cutting non-frame: Greenland through Humor and Platform Satire"
EXCLUDED_SUBFRAMES = {UNASSIGNED_SUBFRAME, CROSS_CUTTING_NON_FRAME}

SUBFRAME_DISPLAY_ORDER = [
    "American Expansionism",
    "Great Power Rivalry",
    "Diplomatic Resistance",
    "Defense Infrastructure",
    "Resource Extraction and Investment",
]

SUBFRAME_DISPLAY_NAMES = {
    "Greenland as an Object of American Strategic Interest": "American Expansionism",
    "Greenland as an Object of American Expansion": "American Expansionism",
    "Greenland as a Site of Arctic Great Power Rivalry": "Great Power Rivalry",
    "Diplomacy and Resistance": "Diplomatic Resistance",
    "Greenland as a Site of Diplomatic Resistance": "Diplomatic Resistance",
    "Greenland as a Sovereign Political Actor": "Diplomatic Resistance",
    "Greenland as an Arctic Military Outpost": "Defense Infrastructure",
    "Greenland as a Strategic Military Outpost": "Defense Infrastructure",
    "Greenland as a Strategic Resource Frontier": "Resource Extraction and Investment",
}

DEUTAN_DISTINCT_PALETTE = [
    (0, 76, 153),      # dark blue
    (230, 159, 0),     # orange
    (204, 0, 121),     # magenta
    (0, 0, 0),         # black
    (240, 228, 66),    # yellow
    (86, 180, 233),    # sky blue
    (117, 112, 179),   # purple
    (213, 94, 0),      # vermillion
    (90, 90, 90),      # gray
    (0, 114, 178),     # blue
]

def display_subframe_name(subframe: str) -> str:
    return SUBFRAME_DISPLAY_NAMES.get(subframe, subframe)


def rename_rows_for_plot(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    renamed_rows = []
    for row in rows:
        renamed_row = row.copy()
        renamed_row["frame"] = display_subframe_name(row["frame"])
        renamed_rows.append(renamed_row)
    return renamed_rows


def subframe_sort_key(subframe: str) -> tuple[int, str]:
    display_name = display_subframe_name(subframe)
    if display_name in SUBFRAME_DISPLAY_ORDER:
        return SUBFRAME_DISPLAY_ORDER.index(display_name), display_name
    return len(SUBFRAME_DISPLAY_ORDER), display_name


def load_frame_time_module():
    spec = importlib.util.spec_from_file_location("frame_prevalence_over_time", FRAME_TIME_SCRIPT)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load plotting helpers from {FRAME_TIME_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_subframe_period_counts(
    csv_path: Path,
    helpers,
) -> tuple[dict[str, Counter[str]], Counter[str], int]:
    counts_by_period: dict[str, Counter[str]] = defaultdict(Counter)
    period_totals: Counter[str] = Counter()
    invalid_rows = 0

    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError("CSV appears empty or missing header.")
        for column in (SUBFRAME_COLUMN, DATE_COLUMN):
            if column not in reader.fieldnames:
                raise ValueError(f"Column '{column}' not found. Available columns: {reader.fieldnames}")

        for row in reader:
            period = helpers.extract_period(row.get(DATE_COLUMN))
            if period is None:
                invalid_rows += 1
                continue

            subframe = (row.get(SUBFRAME_COLUMN) or "").strip() or UNASSIGNED_SUBFRAME
            if subframe in EXCLUDED_SUBFRAMES:
                continue

            counts_by_period[period][subframe] += 1
            period_totals[period] += 1

    if not counts_by_period:
        raise ValueError("No valid subframe/date rows found in the CSV.")

    return counts_by_period, period_totals, invalid_rows


def save_subframe_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["period", "subframe", "count", "total_videos_in_period", "prevalence"],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "period": row["period"],
                    "subframe": row["frame"],
                    "count": row["count"],
                    "total_videos_in_period": row["total_videos_in_period"],
                    "prevalence": row["prevalence"],
                }
            )


def main() -> None:
    helpers = load_frame_time_module()
    if not SOURCE_CSV.exists():
        raise FileNotFoundError(f"CSV not found: {SOURCE_CSV}")

    counts_by_period, period_totals, invalid_rows = load_subframe_period_counts(SOURCE_CSV, helpers)
    source_subframes = helpers.choose_frames(counts_by_period, frames=None, top_n=10)
    source_subframes = sorted(source_subframes, key=subframe_sort_key)
    periods = sorted(counts_by_period)
    rows = helpers.build_rows(counts_by_period, period_totals, source_subframes)
    rows = rename_rows_for_plot(rows)
    subframes = [display_subframe_name(subframe) for subframe in source_subframes]

    csv_out = HERE / "geopolitical_subframe_distribution_over_time_latest.csv"
    plot_out = HERE / "geopolitical_subframe_distribution_over_time_latest.png"
    pdf_out = HERE / "geopolitical_subframe_distribution_over_time_latest.pdf"

    save_subframe_csv(csv_out, rows)
    helpers.save_multiplot(
        plot_out,
        periods=periods,
        frames=subframes,
        rows=rows,
        palette=DEUTAN_DISTINCT_PALETTE,
    )

    print(f"Source CSV: {SOURCE_CSV}")
    print(f"Two-month periods found: {len(periods)}")
    print(f"Rows with missing date: {invalid_rows}")
    print(f"Subframes plotted: {', '.join(subframes)}")
    print(f"Saved two-month CSV to: {csv_out}")
    print(f"Saved multiplot to: {plot_out}")
    print(f"Saved PDF to: {pdf_out}")


if __name__ == "__main__":
    main()
