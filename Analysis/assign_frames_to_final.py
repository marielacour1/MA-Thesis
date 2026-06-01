import csv
import re
from collections import Counter
from pathlib import Path


CSV_PATH = Path(__file__).resolve().parents[1] / "Datasets" / "final_dataset.csv"
FRAME_COLUMN = "frame"


FRAME_TOPICS = {
    "Indigenous Life": {
        300, 276, 415, 418, 227, 448, 6, 7, 474, 475, 450, 454,
        429, 270, 271, 413, 390, 199, 376, 323, 209, 338, 230, 436,
        439, 341, 342, 173, 174, 171, 164, 159, 155, 151, 138, 142,
        134, 129, 122, 111, 119, 87, 62, 63, 59, 49, 46, 38, 21, 26,
        32, 479, 495, 312,
    },
    "Knowledge/Facts": {
        331, 306, 307, 309, 278, 274, 379, 265, 395, 244, 432, 433,
        442, 370, 373, 302, 294, 219, 336, 215, 236, 237, 257, 260,
        405, 359, 339, 458, 459, 417, 246, 247, 412, 414, 250, 470,
        356, 292, 285, 286, 324, 387, 388, 389, 403, 314, 317, 489,
        345, 346, 347, 365, 366, 423, 425, 426, 427, 407, 408, 211,
        212, 204, 197, 190, 194, 184, 188, 182, 177, 179, 169, 162,
        165, 158, 147, 148, 136, 140, 125, 131, 117, 120, 109, 110,
        102, 96, 97, 93, 86, 88, 83, 80, 81, 78, 71, 64, 65, 66, 54,
        50, 36, 22, 17, 13, 8, 3, 4, 2, 496, 497, 499, 106, 92,
    },
    "Geopolitics": {
        381, 392, 401, 404, 406, 410, 420, 421, 428, 441, 447, 449,
        455, 461, 462, 467, 472, 477, 332, 335, 337, 349, 350, 358,
        360, 361, 369, 372, 375, 303, 313, 318, 322, 279, 280, 282,
        283, 289, 293, 297, 133, 137, 143, 145, 146, 150, 153, 156,
        168, 172, 183, 189, 196, 200, 201, 206, 207, 208, 216, 217,
        222, 224, 225, 232, 234, 245, 249, 252, 253, 254, 264, 266,
        273, 275, 130, 124, 41, 47, 51, 53, 55, 57, 61, 69, 70, 76,
        89, 91, 94, 100, 101, 103, 107, 113, 115, 116, 25,
        43, 44, 27, 29, 0, 5, 11, 15, 16, 18, 19, 488, 490, 491,
        492,
    },
    "Nature/Tourism": {
        380, 330, 304, 277, 393, 411, 431, 296, 238, 226, 468, 471,
        480, 493, 451, 473, 291, 223, 268, 272, 363, 367, 287, 301,
        218, 228, 231, 311, 261, 262, 344, 348, 374, 255, 256, 382,
        383, 385, 465, 466, 434, 435, 298, 299, 210, 214, 316, 319,
        320, 321, 351, 353, 354, 355, 445, 446, 396, 398, 400, 483,
        484, 485, 239, 241, 242, 243, 202, 220, 221, 195, 185, 186,
        187, 181, 178, 176, 170, 167, 161, 154, 144, 132, 127, 128,
        123, 121, 114, 108, 104, 105, 95, 98, 84, 90, 79, 82, 77, 72, 73,
        74, 68, 58, 60, 56, 48, 40, 23, 37, 42, 45, 33, 34, 30, 31,
        20, 12, 9, 10, 1,
    },
    "Climate Change": {
        464, 378, 284, 482, 205, 175, 149, 139, 141, 126, 112, 52,
        24, 14, 500,
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


def build_topic_to_frame() -> dict[int, str]:
    topic_to_frame = {}
    duplicate_topics = {}

    for frame, topics in FRAME_TOPICS.items():
        for topic in topics:
            if topic in topic_to_frame:
                duplicate_topics.setdefault(topic, [topic_to_frame[topic]]).append(frame)
            topic_to_frame[topic] = frame

    if duplicate_topics:
        details = "; ".join(
            f"{topic}: {', '.join(frames)}" for topic, frames in sorted(duplicate_topics.items())
        )
        raise ValueError(f"Topics assigned to multiple frames: {details}")

    return topic_to_frame


def main() -> None:
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"CSV not found: {CSV_PATH}")

    topic_to_frame = build_topic_to_frame()
    tmp_path = CSV_PATH.with_suffix(CSV_PATH.suffix + ".tmp")
    frame_counts = Counter()
    missing_topic_counts = Counter()
    total_rows = 0

    with CSV_PATH.open("r", encoding="utf-8", newline="") as infile, tmp_path.open(
        "w", encoding="utf-8", newline=""
    ) as outfile:
        reader = csv.DictReader(infile)
        if reader.fieldnames is None:
            raise ValueError(f"No header found in {CSV_PATH}")
        if "topic" not in reader.fieldnames:
            raise ValueError("Input CSV must contain a 'topic' column.")

        fieldnames = list(reader.fieldnames)
        if FRAME_COLUMN not in fieldnames:
            fieldnames.append(FRAME_COLUMN)

        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()

        for row in reader:
            total_rows += 1
            topic_number = parse_topic_number(row.get("topic"))
            frame = topic_to_frame.get(topic_number, "")
            row[FRAME_COLUMN] = frame

            if frame:
                frame_counts[frame] += 1
            else:
                missing_topic_counts[row.get("topic", "")] += 1

            writer.writerow(row)

    tmp_path.replace(CSV_PATH)

    print(f"Added/updated '{FRAME_COLUMN}' in: {CSV_PATH}")
    print(f"Rows processed: {total_rows:,}")
    print("Frame counts:")
    for frame, count in frame_counts.most_common():
        print(f"  {frame}: {count:,}")
    if missing_topic_counts:
        print("Rows without a frame:")
        for topic, count in missing_topic_counts.most_common():
            print(f"  {topic or '(blank topic)'}: {count:,}")


if __name__ == "__main__":
    main()
