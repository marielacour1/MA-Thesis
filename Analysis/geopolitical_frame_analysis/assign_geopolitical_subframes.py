import csv
import re
from collections import Counter
from pathlib import Path


HERE = Path(__file__).resolve().parent
ANALYSIS_DIR = HERE.parent
PROJECT_DIR = ANALYSIS_DIR.parent
DATASET_PATH = PROJECT_DIR / "Datasets" / "final_dataset.csv"

GEOPOLITICAL_FRAME = "Geopolitics"
TOPIC_COLUMN = "topic"
FRAME_COLUMN = "frame"
SUBFRAME_COLUMN = "geopolitical_subframe"

SUBSET_PATH = HERE / "geopolitical_frame_videos_with_subframes.csv"
BREAKDOWN_PATH = HERE / "geopolitical_subframe_breakdown.csv"
TOPIC_BREAKDOWN_PATH = HERE / "geopolitical_topic_subframe_breakdown.csv"
REPORT_PATH = HERE / "geopolitical_subframe_validation_report.txt"


SUBFRAME_TOPICS = {
    "American Expansionism": {
        0, 11, 16, 27, 43, 47, 53, 55, 57, 69, 94, 101, 107, 115,
        116, 130, 133, 137, 143, 145, 153, 172, 189, 200, 206, 208,
        224, 232, 245, 253, 273, 283, 293, 297, 332, 335, 337, 349,
        358, 360, 372, 381, 392, 420, 421, 428, 441, 455, 461, 472, 488,
    },
    "Great Power Rivalry": {
        5, 15, 19, 44, 51, 89, 103, 216, 217, 234, 249, 254, 264,
        266, 303, 313, 322, 369, 375, 401, 410, 477, 490,
    },
    "Diplomatic Resistance": {
        18, 29, 41, 70, 76, 91, 124, 168, 222, 225, 252, 279,
        280, 289, 318, 350, 467, 491,
    },
    "Defense Infrastructure": {
        61, 100, 113, 150, 156, 196, 207, 275, 406, 447, 492,
    },
    "Resource Extraction and Investment": {
        25, 146, 183, 201, 282, 361, 404, 462,
    },
}


def parse_topic_number(topic_value: str | None) -> int | None:
    value = (topic_value or "").strip()
    if not value:
        return None

    match = re.fullmatch(r"(?:topic)?(\d+)", value, flags=re.IGNORECASE)
    if match is None:
        return None

    return int(match.group(1))


def build_topic_to_subframe() -> dict[int, str]:
    topic_to_subframe = {}
    duplicate_topics = {}

    for subframe, topics in SUBFRAME_TOPICS.items():
        for topic in topics:
            if topic in topic_to_subframe:
                duplicate_topics.setdefault(topic, [topic_to_subframe[topic]]).append(subframe)
            topic_to_subframe[topic] = subframe

    if duplicate_topics:
        details = "; ".join(
            f"{topic}: {', '.join(subframes)}"
            for topic, subframes in sorted(duplicate_topics.items())
        )
        raise ValueError(f"Topics assigned to multiple geopolitical subframes: {details}")

    return topic_to_subframe


def pct(part: int, whole: int) -> str:
    if whole == 0:
        return "0.0"
    return f"{part / whole * 100:.1f}"


def write_breakdown(total_rows: int, subframe_counts: Counter[str]) -> None:
    with BREAKDOWN_PATH.open("w", encoding="utf-8", newline="") as outfile:
        writer = csv.DictWriter(
            outfile,
            fieldnames=["subframe", "video_count", "percent_of_geopolitical_frame"],
        )
        writer.writeheader()
        for subframe, count in subframe_counts.most_common():
            writer.writerow(
                {
                    "subframe": subframe,
                    "video_count": count,
                    "percent_of_geopolitical_frame": pct(count, total_rows),
                }
            )


def write_topic_breakdown(topic_counts: Counter[int], topic_to_subframe: dict[int, str]) -> None:
    with TOPIC_BREAKDOWN_PATH.open("w", encoding="utf-8", newline="") as outfile:
        writer = csv.DictWriter(
            outfile,
            fieldnames=["topic", "subframe", "video_count"],
        )
        writer.writeheader()
        for topic, count in sorted(topic_counts.items()):
            writer.writerow(
                {
                    "topic": topic,
                    "subframe": topic_to_subframe.get(topic, ""),
                    "video_count": count,
                }
            )


def format_topic_list(topics: set[int] | list[int]) -> str:
    return ", ".join(str(topic) for topic in sorted(topics)) or "None"


def write_report(
    total_rows: int,
    subframe_counts: Counter[str],
    topic_counts: Counter[int],
    instruction_topics_missing_from_dataset: set[int],
    geopolitical_topics_without_subframe: set[int],
) -> None:
    lines = [
        "Geopolitical Subframe Validation Report",
        "======================================",
        "",
        f"Input dataset: {DATASET_PATH}",
        f"Geopolitical frame rows: {total_rows:,}",
        f"Distinct geopolitical topics in dataset: {len(topic_counts):,}",
        "",
        "Subframe breakdown",
        "------------------",
    ]

    for subframe, count in subframe_counts.most_common():
        lines.append(f"{subframe}: {count:,} videos ({pct(count, total_rows)}%)")

    lines.extend(
        [
            "",
            "Instruction topics not found among geopolitical-frame rows",
            "---------------------------------------------------------",
            format_topic_list(instruction_topics_missing_from_dataset),
            "",
            "Geopolitical-frame topics not assigned to a subframe",
            "---------------------------------------------------",
            format_topic_list(geopolitical_topics_without_subframe),
            "",
            "Outputs",
            "-------",
            f"Subset with subframes: {SUBSET_PATH}",
            f"Subframe breakdown: {BREAKDOWN_PATH}",
            f"Topic breakdown: {TOPIC_BREAKDOWN_PATH}",
        ]
    )

    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    if not DATASET_PATH.exists():
        raise FileNotFoundError(f"Dataset not found: {DATASET_PATH}")

    topic_to_subframe = build_topic_to_subframe()
    instruction_topics = set(topic_to_subframe)
    subframe_counts = Counter()
    topic_counts = Counter()
    total_rows = 0

    with DATASET_PATH.open("r", encoding="utf-8", newline="") as infile, SUBSET_PATH.open(
        "w", encoding="utf-8", newline=""
    ) as outfile:
        reader = csv.DictReader(infile)
        if reader.fieldnames is None:
            raise ValueError(f"No header found in {DATASET_PATH}")
        if TOPIC_COLUMN not in reader.fieldnames:
            raise ValueError(f"Input CSV must contain a '{TOPIC_COLUMN}' column.")
        if FRAME_COLUMN not in reader.fieldnames:
            raise ValueError(f"Input CSV must contain a '{FRAME_COLUMN}' column.")

        fieldnames = list(reader.fieldnames)
        if SUBFRAME_COLUMN not in fieldnames:
            fieldnames.append(SUBFRAME_COLUMN)

        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()

        for row in reader:
            if row.get(FRAME_COLUMN) != GEOPOLITICAL_FRAME:
                continue

            total_rows += 1
            topic_number = parse_topic_number(row.get(TOPIC_COLUMN))
            if topic_number is not None:
                topic_counts[topic_number] += 1

            subframe = topic_to_subframe.get(topic_number, "")
            row[SUBFRAME_COLUMN] = subframe
            if subframe:
                subframe_counts[subframe] += 1
            else:
                subframe_counts["Unassigned geopolitical subframe"] += 1

            writer.writerow(row)

    dataset_topics = set(topic_counts)
    instruction_topics_missing_from_dataset = instruction_topics - dataset_topics
    geopolitical_topics_without_subframe = dataset_topics - instruction_topics

    write_breakdown(total_rows, subframe_counts)
    write_topic_breakdown(topic_counts, topic_to_subframe)
    write_report(
        total_rows,
        subframe_counts,
        topic_counts,
        instruction_topics_missing_from_dataset,
        geopolitical_topics_without_subframe,
    )

    print(f"Wrote subset: {SUBSET_PATH}")
    print(f"Wrote subframe breakdown: {BREAKDOWN_PATH}")
    print(f"Wrote topic breakdown: {TOPIC_BREAKDOWN_PATH}")
    print(f"Wrote validation report: {REPORT_PATH}")
    print(f"Geopolitical frame rows: {total_rows:,}")
    print("Subframe counts:")
    for subframe, count in subframe_counts.most_common():
        print(f"  {subframe}: {count:,} ({pct(count, total_rows)}%)")
    print(
        "Instruction topics not found among geopolitical-frame rows: "
        f"{format_topic_list(instruction_topics_missing_from_dataset)}"
    )
    print(
        "Geopolitical-frame topics not assigned to a subframe: "
        f"{format_topic_list(geopolitical_topics_without_subframe)}"
    )


if __name__ == "__main__":
    main()
