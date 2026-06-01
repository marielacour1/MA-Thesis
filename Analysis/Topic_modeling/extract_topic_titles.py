import csv
from pathlib import Path


def row_matches_topic(row, topic_num):
    topic = (row.get("topic") or "").strip()
    return topic == str(topic_num) or topic == f"topic{topic_num}"


def main():
    topic_num = int(input("Enter the topic number: "))
    script_dir = Path(__file__).parent
    csv_path = script_dir / "gl-cl-w-topics.csv"
    if not csv_path.exists():
        csv_path = script_dir / "gl-cl-topic-assignments.csv"

    txt_output_path = script_dir / f"topic_{topic_num}_titles.txt"
    csv_output_path = script_dir / f"topic_{topic_num}_titles.csv"

    videos = []
    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row_matches_topic(row, topic_num):
                videos.append({
                    "video_id": (row.get("video_id") or "").strip(),
                    "title": (row.get("video_title") or row.get("title") or "").strip(),
                })

    with txt_output_path.open("w", encoding="utf-8") as f:
        for video in videos:
            f.write(f"{video['title']}\n")

    with csv_output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["video_id", "title"])
        writer.writeheader()
        writer.writerows(videos)

    print(f"Extracted {len(videos)} titles for topic {topic_num} to {txt_output_path}")
    print(f"Saved subset CSV to {csv_output_path}")

if __name__ == "__main__":
    main()
