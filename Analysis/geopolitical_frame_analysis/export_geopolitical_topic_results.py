import re
from pathlib import Path

from assign_geopolitical_subframes import SUBFRAME_TOPICS


HERE = Path(__file__).resolve().parent
SOURCE_TOPIC_RESULTS = (
    HERE.parent / "Topic_modeling" / "Creating_frames" / "gl-cl-topic-results.txt"
)
FLAT_OUTPUT = HERE / "geopolitical_topic_results.txt"
SUBFRAME_OUTPUT = HERE / "geopolitical_topic_results_by_subframe.txt"


TOPIC_BLOCK_RE = re.compile(
    r"(?ms)^Topic (?P<topic>\d+)\n(?P<body>.*?)(?=^Topic \d+\n|\Z)"
)


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


def parse_topic_blocks(text: str) -> dict[int, str]:
    blocks = {}

    for match in TOPIC_BLOCK_RE.finditer(text):
        topic = int(match.group("topic"))
        blocks[topic] = match.group(0).rstrip()

    return blocks


def format_missing_topics(missing_topics: set[int]) -> str:
    if not missing_topics:
        return "None"
    return ", ".join(str(topic) for topic in sorted(missing_topics))


def write_flat_output(topic_blocks: dict[int, str], topics: set[int], missing_topics: set[int]) -> None:
    lines = [
        "Geopolitics Frame Topic Results",
        "==============================================",
        "",
        "Source file:",
        str(SOURCE_TOPIC_RESULTS),
        "",
        "Note: Topic result blocks are copied unchanged from the source topic-results file.",
        "",
        "Geopolitical topics missing from source topic-results file:",
        format_missing_topics(missing_topics),
        "",
        "Topics",
        "------",
        "",
    ]

    for topic in sorted(topics):
        if topic in topic_blocks:
            lines.extend([topic_blocks[topic], ""])
    FLAT_OUTPUT.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def write_subframe_output(
    topic_blocks: dict[int, str],
    topic_to_subframe: dict[int, str],
    missing_topics: set[int],
) -> None:
    lines = [
        "Geopolitics Frame Topic Results by Subframe",
        "=========================================================",
        "",
        "Source file:",
        str(SOURCE_TOPIC_RESULTS),
        "",
        "Note: Topic result blocks are copied unchanged from the source topic-results file.",
        "",
        "Geopolitical topics missing from source topic-results file:",
        format_missing_topics(missing_topics),
        "",
    ]

    for subframe, topics in SUBFRAME_TOPICS.items():
        present_topics = [topic for topic in sorted(topics) if topic in topic_blocks]
        lines.extend(
            [
                subframe,
                "-" * len(subframe),
                f"Topics: {', '.join(str(topic) for topic in present_topics)}",
                "",
            ]
        )
        for topic in present_topics:
            lines.extend([topic_blocks[topic], ""])
        lines.append("")

    SUBFRAME_OUTPUT.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> None:
    if not SOURCE_TOPIC_RESULTS.exists():
        raise FileNotFoundError(f"Topic-results source not found: {SOURCE_TOPIC_RESULTS}")

    text = SOURCE_TOPIC_RESULTS.read_text(encoding="utf-8")
    topic_blocks = parse_topic_blocks(text)
    topic_to_subframe = build_topic_to_subframe()
    geopolitical_topics = set(topic_to_subframe)
    missing_topics = geopolitical_topics - set(topic_blocks)

    write_flat_output(topic_blocks, geopolitical_topics, missing_topics)
    write_subframe_output(topic_blocks, topic_to_subframe, missing_topics)

    print(f"Wrote flat geopolitical topic results: {FLAT_OUTPUT}")
    print(f"Wrote subframe topic results: {SUBFRAME_OUTPUT}")
    print(f"Geopolitical topics requested: {len(geopolitical_topics):,}")
    print(f"Geopolitical topics found in source: {len(geopolitical_topics - missing_topics):,}")
    print(f"Geopolitical topics missing from source: {format_missing_topics(missing_topics)}")


if __name__ == "__main__":
    main()
