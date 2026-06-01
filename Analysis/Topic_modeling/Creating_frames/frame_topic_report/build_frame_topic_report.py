import importlib.util
import re
from pathlib import Path


HERE = Path(__file__).resolve().parent
PROJECT_DIR = HERE.parents[3]
ASSIGN_FRAMES_SCRIPT = PROJECT_DIR / "Analysis" / "assign_frames_to_final.py"
FINAL_FILTERING_SCRIPT = PROJECT_DIR / "Analysis" / "final_filtering.py"
TOPIC_RESULTS_TXT = (
    PROJECT_DIR
    / "Analysis"
    / "Topic_modeling"
    / "Creating_frames"
    / "gl-cl-topic-results.txt"
)
OUTPUT_TXT = HERE / "frame_topic_results_reordered.txt"

FRAME_ORDER = [
    "Nature/Tourism",
    "Geopolitics",
    "Knowledge/Facts",
    "Indigenous Life",
    "Climate Change",
]
DELETED_LABEL = "Deleted"
IGNORE_TOPICS = {500}
TOPIC_HEADING_RE = re.compile(r"^Topic (\d+)\s*$", re.MULTILINE)


def load_module(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not import module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_topic_mappings() -> dict[str, list[int]]:
    assign_frames = load_module(ASSIGN_FRAMES_SCRIPT, "assign_frames_to_final")
    final_filtering = load_module(FINAL_FILTERING_SCRIPT, "final_filtering")

    frame_topics = {
        frame: sorted(topic for topic in assign_frames.FRAME_TOPICS.get(frame, set()) if topic not in IGNORE_TOPICS)
        for frame in FRAME_ORDER
    }
    frame_topics[DELETED_LABEL] = sorted(
        topic for topic in final_filtering.TOPICS_TO_EXCLUDE if topic not in IGNORE_TOPICS
    )
    return frame_topics


def parse_topic_blocks(path: Path) -> tuple[str, dict[int, str]]:
    text = path.read_text(encoding="utf-8")
    matches = list(TOPIC_HEADING_RE.finditer(text))
    if not matches:
        raise ValueError(f"No topic blocks found in {path}")

    preamble = text[: matches[0].start()].rstrip()
    blocks: dict[int, str] = {}
    for index, match in enumerate(matches):
        topic = int(match.group(1))
        block_start = match.start()
        block_end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        if topic not in IGNORE_TOPICS:
            blocks[topic] = text[block_start:block_end].rstrip()

    return preamble, blocks


def format_topic_list(topics: list[int]) -> str:
    return ", ".join(str(topic) for topic in topics)


def build_report() -> str:
    frame_topics = load_topic_mappings()
    preamble, topic_blocks = parse_topic_blocks(TOPIC_RESULTS_TXT)

    assigned_topics = {topic for topics in frame_topics.values() for topic in topics}
    available_topics = set(topic_blocks)
    missing_blocks = sorted(assigned_topics - available_topics)
    unassigned_blocks = sorted(available_topics - assigned_topics)

    lines: list[str] = [
        "Frame Topic Assignments",
        "=" * 80,
        f"Source frame assignments: {ASSIGN_FRAMES_SCRIPT}",
        f"Source deleted-topic list: {FINAL_FILTERING_SCRIPT}",
        f"Source topic results: {TOPIC_RESULTS_TXT}",
        "Note: topic 500 is excluded because it is not in the original topic-modeling result output.",
        "",
    ]

    for label in FRAME_ORDER + [DELETED_LABEL]:
        topics = frame_topics[label]
        lines.extend(
            [
                label,
                "-" * len(label),
                f"Topics ({len(topics)}): {format_topic_list(topics)}",
                "",
            ]
        )

    if missing_blocks or unassigned_blocks:
        lines.extend(["Coverage Check", "-" * 14])
        if missing_blocks:
            lines.append(f"Assigned/deleted topics missing from topic-results file: {format_topic_list(missing_blocks)}")
        if unassigned_blocks:
            lines.append(f"Topic-result blocks not assigned to a frame or deleted: {format_topic_list(unassigned_blocks)}")
        lines.append("")

    lines.extend(
        [
            "Topic Results Ordered By Frame",
            "=" * 80,
        ]
    )
    if preamble:
        lines.extend([preamble, ""])

    for label in FRAME_ORDER + [DELETED_LABEL]:
        lines.extend([label, "-" * len(label), ""])
        for topic in frame_topics[label]:
            block = topic_blocks.get(topic)
            if block is not None:
                lines.extend([block, ""])

    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    HERE.mkdir(parents=True, exist_ok=True)
    report = build_report()
    OUTPUT_TXT.write_text(report, encoding="utf-8")
    print(f"Wrote frame topic report to: {OUTPUT_TXT}")


if __name__ == "__main__":
    main()
