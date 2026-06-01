import argparse
import math
import random
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from make_precision_recall_samples import (
    deleted_review_pool,
    read_csv_rows,
    unique_video_rows,
    video_row,
)


NS = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
}
RANDOM_SEED = 20260514
BOOTSTRAP_DRAWS = 20000


def column_index(cell_ref: str) -> int:
    letters = "".join(ch for ch in cell_ref if ch.isalpha())
    index = 0
    for letter in letters:
        index = index * 26 + (ord(letter.upper()) - ord("A") + 1)
    return index


def load_shared_strings(xlsx: zipfile.ZipFile) -> list[str]:
    try:
        xml = xlsx.read("xl/sharedStrings.xml")
    except KeyError:
        return []

    root = ET.fromstring(xml)
    strings = []
    for item in root.findall("main:si", NS):
        text_parts = [node.text or "" for node in item.findall(".//main:t", NS)]
        strings.append("".join(text_parts))
    return strings


def cell_value(cell: ET.Element, shared_strings: list[str]) -> str:
    cell_type = cell.attrib.get("t")
    value = cell.find("main:v", NS)

    if cell_type == "inlineStr":
        text_parts = [node.text or "" for node in cell.findall(".//main:t", NS)]
        return "".join(text_parts).strip()

    if value is None or value.text is None:
        return ""

    raw = value.text.strip()
    if cell_type == "s":
        return shared_strings[int(raw)].strip()
    return raw


def read_xlsx_rows(path: Path) -> list[dict[str, str]]:
    with zipfile.ZipFile(path) as xlsx:
        shared_strings = load_shared_strings(xlsx)
        sheet_xml = xlsx.read("xl/worksheets/sheet1.xml")

    root = ET.fromstring(sheet_xml)
    rows = []
    for row in root.findall(".//main:row", NS):
        values: dict[int, str] = {}
        for cell in row.findall("main:c", NS):
            ref = cell.attrib.get("r", "")
            if not ref:
                continue
            values[column_index(ref)] = cell_value(cell, shared_strings)
        rows.append(values)

    if not rows:
        return []

    headers = {column: value for column, value in rows[0].items() if value}
    parsed_rows = []
    for row in rows[1:]:
        parsed_rows.append(
            {
                header: row.get(column, "")
                for column, header in headers.items()
            }
        )
    return parsed_rows


def parse_correct(value: str) -> int:
    normalized = str(value).strip()
    if normalized in {"1", "1.0"}:
        return 1
    if normalized in {"0", "0.0"}:
        return 0
    raise ValueError(f"Correct values must be 0 or 1. Found: {value!r}")


def correct_counts(rows: list[dict[str, str]], label: str) -> tuple[int, int, int]:
    rows = [
        row for row in rows
        if (row.get("Video ID") or "").strip() or (row.get("Video title") or "").strip()
    ]
    if not rows:
        raise ValueError(f"{label} has no data rows.")
    if "Correct" not in rows[0]:
        raise ValueError(f"{label} is missing a 'Correct' column.")

    values = [parse_correct(row.get("Correct", "")) for row in rows]
    correct = sum(values)
    total = len(values)
    incorrect = total - correct
    return correct, incorrect, total


def proportion(part: int | float, whole: int | float) -> float:
    return (part / whole) if whole else 0.0


def wilson_interval(successes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    if total == 0:
        return 0.0, 0.0

    p = successes / total
    denominator = 1 + z**2 / total
    center = (p + z**2 / (2 * total)) / denominator
    margin = (
        z
        * math.sqrt((p * (1 - p) / total) + (z**2 / (4 * total**2)))
        / denominator
    )
    return max(0.0, center - margin), min(1.0, center + margin)


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    rank = (len(sorted_values) - 1) * p
    low = math.floor(rank)
    high = math.ceil(rank)
    if low == high:
        return sorted_values[low]
    weight = rank - low
    return sorted_values[low] * (1 - weight) + sorted_values[high] * weight


def bootstrap_recall_interval(
    precision_correct: int,
    precision_total: int,
    deleted_incorrect: int,
    deleted_total: int,
    final_pool_n: int,
    deleted_pool_n: int,
    draws: int,
    seed: int,
) -> tuple[float, float]:
    rng = random.Random(seed)
    recalls = []
    for _ in range(draws):
        precision_draw = rng.betavariate(
            precision_correct + 0.5,
            precision_total - precision_correct + 0.5,
        )
        false_negative_rate_draw = rng.betavariate(
            deleted_incorrect + 0.5,
            deleted_total - deleted_incorrect + 0.5,
        )
        true_positives = precision_draw * final_pool_n
        false_negatives = false_negative_rate_draw * deleted_pool_n
        recalls.append(proportion(true_positives, true_positives + false_negatives))

    return percentile(recalls, 0.025), percentile(recalls, 0.975)


def fmt_pct(value: float) -> str:
    return f"{value:.3f} ({value * 100:.1f}%)"


def fmt_ci(low: float, high: float) -> str:
    return f"[{low:.3f}, {high:.3f}] / [{low * 100:.1f}%, {high * 100:.1f}%]"


def format_results(
    precision_correct: int,
    precision_incorrect: int,
    precision_total: int,
    deleted_correct: int,
    deleted_incorrect: int,
    deleted_total: int,
    final_pool_n: int,
    deleted_pool_n: int,
    bootstrap_draws: int,
    seed: int,
) -> str:
    precision = proportion(precision_correct, precision_total)
    precision_ci = wilson_interval(precision_correct, precision_total)

    deletion_accuracy = proportion(deleted_correct, deleted_total)
    deletion_accuracy_ci = wilson_interval(deleted_correct, deleted_total)

    false_negative_rate = proportion(deleted_incorrect, deleted_total)
    false_negative_rate_ci = wilson_interval(deleted_incorrect, deleted_total)

    estimated_true_positives = precision * final_pool_n
    estimated_false_positives = (1 - precision) * final_pool_n
    estimated_false_negatives = false_negative_rate * deleted_pool_n
    estimated_true_negatives = deletion_accuracy * deleted_pool_n
    estimated_recall = proportion(
        estimated_true_positives,
        estimated_true_positives + estimated_false_negatives,
    )
    recall_ci = bootstrap_recall_interval(
        precision_correct=precision_correct,
        precision_total=precision_total,
        deleted_incorrect=deleted_incorrect,
        deleted_total=deleted_total,
        final_pool_n=final_pool_n,
        deleted_pool_n=deleted_pool_n,
        draws=bootstrap_draws,
        seed=seed,
    )

    lines = [
        "Precision and recall review",
        "=" * 31,
        "",
        "Sample results",
        "-" * 14,
        f"Precision sample: {precision_correct}/{precision_total} correctly kept",
        f"Deleted sample: {deleted_correct}/{deleted_total} correctly deleted",
        "",
        "Estimated confusion matrix",
        "-" * 26,
        f"True positives  (kept and relevant):     {estimated_true_positives:,.1f}",
        f"False positives (kept but irrelevant):    {estimated_false_positives:,.1f}",
        f"False negatives (deleted but relevant):   {estimated_false_negatives:,.1f}",
        f"True negatives  (deleted and irrelevant): {estimated_true_negatives:,.1f}",
        "",
        "Scores",
        "-" * 6,
        f"Precision: {fmt_pct(precision)}",
        f"Precision 95% CI: {fmt_ci(*precision_ci)}",
        f"Recall: {fmt_pct(estimated_recall)}",
        f"Recall 95% uncertainty interval: {fmt_ci(*recall_ci)}",
        "",
        "Deletion sample diagnostics",
        "-" * 27,
        f"Deleted-sample accuracy: {fmt_pct(deletion_accuracy)}",
        f"Deleted-sample accuracy 95% CI: {fmt_ci(*deletion_accuracy_ci)}",
        f"Deleted-sample false-negative rate: {fmt_pct(false_negative_rate)}",
        f"False-negative rate 95% CI: {fmt_ci(*false_negative_rate_ci)}",
        "",
        "Pools",
        "-" * 5,
        f"Final dataset pool: {final_pool_n:,} videos",
        f"Deleted review pool: {deleted_pool_n:,} videos",
        "",
        "Notes",
        "-" * 5,
        "Precision is estimated from the reviewed final-dataset sample.",
        "Recall is estimated as TP / (TP + FN), where TP is inferred from the final-dataset sample and FN from deleted videos marked as incorrectly deleted.",
        f"The recall interval uses a beta-binomial simulation with {bootstrap_draws:,} draws; precision and deletion diagnostics use Wilson binomial intervals.",
    ]
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    dataset_dir = script_dir.parents[1] / "Datasets"

    parser = argparse.ArgumentParser(
        description="Calculate precision and recall from reviewed sample workbooks."
    )
    parser.add_argument(
        "--precision-xlsx",
        type=Path,
        default=script_dir / "precision_sample_final_videos.xlsx",
    )
    parser.add_argument(
        "--recall-xlsx",
        type=Path,
        default=script_dir / "recall_sample_deleted_videos.xlsx",
    )
    parser.add_argument("--final-csv", type=Path, default=dataset_dir / "final_dataset.csv")
    parser.add_argument("--deleted-csv", type=Path, default=dataset_dir / "deleted.csv")
    parser.add_argument("--deleted2-csv", type=Path, default=dataset_dir / "deleted2.csv")
    parser.add_argument("--greenland-only-csv", type=Path, default=dataset_dir / "greenland-only-title-videos.csv")
    parser.add_argument("--duplicate-csv", type=Path, default=dataset_dir / "duplicate-videos.csv")
    parser.add_argument(
        "--output",
        type=Path,
        default=script_dir / "precision_recall_results.txt",
        help="Path to save the precision/recall results text file.",
    )
    parser.add_argument("--bootstrap-draws", type=int, default=BOOTSTRAP_DRAWS)
    parser.add_argument("--seed", type=int, default=RANDOM_SEED)
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    precision_rows = read_xlsx_rows(args.precision_xlsx)
    recall_rows = read_xlsx_rows(args.recall_xlsx)

    precision_correct, precision_incorrect, precision_total = correct_counts(
        precision_rows,
        "Precision sample",
    )
    deleted_correct, deleted_incorrect, deleted_total = correct_counts(
        recall_rows,
        "Deleted sample",
    )

    final_pool = unique_video_rows([video_row(row) for row in read_csv_rows(args.final_csv)])
    deleted_pool = deleted_review_pool(
        deleted_rows=read_csv_rows(args.deleted_csv),
        deleted2_rows=read_csv_rows(args.deleted2_csv),
        greenland_only_rows=read_csv_rows(args.greenland_only_csv),
        duplicate_rows=read_csv_rows(args.duplicate_csv),
    )

    results = format_results(
        precision_correct=precision_correct,
        precision_incorrect=precision_incorrect,
        precision_total=precision_total,
        deleted_correct=deleted_correct,
        deleted_incorrect=deleted_incorrect,
        deleted_total=deleted_total,
        final_pool_n=len(final_pool),
        deleted_pool_n=len(deleted_pool),
        bootstrap_draws=max(args.bootstrap_draws, 1000),
        seed=args.seed,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(results, encoding="utf-8")
    print(results, end="")
    print(f"Saved results to: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)
