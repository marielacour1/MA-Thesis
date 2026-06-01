import argparse
import csv
import json
import os
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

DEFAULT_MAX_TOPICS_IN_PLOT = 500

try:
    from bertopic import BERTopic
except ImportError as exc:
    raise SystemExit(
        "BERTopic is not installed. Install dependencies first, e.g.\n"
        "  pip install bertopic sentence-transformers umap-learn scikit-learn"
    ) from exc

try:
    from sentence_transformers import SentenceTransformer
except ImportError as exc:
    raise SystemExit(
        "sentence-transformers is not installed. Install it with:\n"
        "  pip install sentence-transformers"
    ) from exc


def load_env_file(env_path: Path) -> None:
    if not env_path.exists():
        return

    with env_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key:
                os.environ[key] = value


DEFAULT_STOPWORDS = {
    "in","podcast","the","of","to","with","and","from","on","at","for","by","is","or","how",
    "a","are","that","this","it","as","was","but","be","not","di","sa",

    #specific channels or names of people
    "tjr", "joerogan", "q's",
    # Core term
    "greenland","greenland's",

    # Years
    "2000","2001","2002","2003","2004","2005","2006","2007","2008","2009","2010","2011","2012","2013","2014","2015","2016","2017","2018","2019","2020","2021","2022","2023","2024","2025","2026",

    # Numbers
    "1","2","3","4","5","6","7","8","9","10","11","12","13","14","15","16","17","18","19","20",
    "21","22","23","24","25","26","27","28","29","30","31","32","33","34","35","36","37","38","39",
    "40","41","42","43","44","45","46","47","48","49","50","51","52","53","54","55","56","57","58",
    "59","60","61","62","63","64","65","66","67","68","69","70","71","72","73","74","75","76","77",
    "78","79","80","81","82","83","84","85","86","87","88","89","90","91","92","93","94","95","96",
    "97","98","99","100",

    # Extra numeric tokens from your topics (NEW)
    "720p","1080p","4k","200","330","800","neo","a330","dash","dash8","v2","khz",
    "09","25",

    "480p",
    "360",
    "2027",
    "52s",
    "660",
    "1919",
    "2523",
    "1932",
    "184",
    "9799930397",
    "479",

    #languages
    "hindi", "tamil", "urdu", "telugu", "malayalam", "bengali", "kannada", "marathi", "gujarati", "punjabi", "odia", "assamese", "sinhala",

    # Time / sequencing noise
    "day","days","part","episode","series","chapter", "ep", "season", "day", "week", "trailer", "preview", "recap", "finale", "stream", "update", "news", "review", "reaction",

    # Generic words
    "hd","vs","why","my","you","we","they","about","all","do","if","me","your","his",

    #movie related content
    "movie","trailer","teaser","review","reaction","film","cinema","director","actor","actress","hollywood","bollywood", "movies", "aftermovie", "bluray", "blu ray", "dvd", "video", "videos", "clip", "clips", "cinematic",
    "documentary", "trailers", "scene", "moviescenes", "bestactor", "movierecap", "scenes",

    # YouTube noise
    "subscribers","tiktok","reels","reel","shorts","short","youtubeshorts","youtubeshort","viral","trending","shortvideo",
    "video","ytshorts","ytshort","viralvideo","shortsfeed","yshorts","shortsyoutube",
    "subscribe","shortsvideo","trendingshorts","shortvideos","shortsvideos","shorts2024","shorts2025","shorts2026",
    "shorts2023","shorts2022","shorts2021","shorts2020","shorts2019", "viralreels","trendingvideo","trendingreels","trendingshorts","trendingshort","viralreel","viralshorts",
    "viralshorts","viralshort","youtube","shortsviral","viralvideos","share", "fypppp", "fypp", "fyppp", "whatsapp", "hotshorts"
}

TOKEN_RE = re.compile(r"[A-Za-z0-9']+")


def parse_view_count(value: str | None) -> int:
    raw = (value or "").strip()
    if not raw:
        return 0

    cleaned = raw.replace(",", "").replace(" ", "")
    try:
        return int(float(cleaned))
    except ValueError:
        return 0


@dataclass
class KResult:
    k: int
    silhouette: float | None
    topic_count: int
    noise_count: int
    topic_sizes: dict[int, int]
    top_words: dict[int, list[str]]
    topic_examples: dict[int, list[str]]
    topic_assignments: list[int]


def read_csv_rows(csv_path: Path, title_column: str) -> tuple[list[dict[str, str]], list[str], list[str]]:
    rows: list[dict[str, str]] = []
    titles: list[str] = []
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None or title_column not in reader.fieldnames:
            raise ValueError(
                f"Column '{title_column}' not found in CSV. Available columns: {reader.fieldnames}"
            )

        for row in reader:
            row_dict = dict(row)
            title = (row_dict.get(title_column) or "").strip()
            if title:
                rows.append(row_dict)
                titles.append(title)

    if not titles:
        raise ValueError("No non-empty titles found in CSV.")

    return rows, titles, list(reader.fieldnames)


def clean_text(text: str, stopwords: set[str], min_word_length: int) -> str:
    tokens = [
        t
        for t in TOKEN_RE.findall(text.lower())
        if len(t) >= min_word_length and t not in stopwords
    ]
    return " ".join(tokens)


def preprocess_titles(titles: Iterable[str], stopwords: set[str], min_word_length: int) -> list[str]:
    cleaned = [clean_text(t, stopwords=stopwords, min_word_length=min_word_length) for t in titles]
    return [c if c else "untitled" for c in cleaned]


def normalize_title_for_grouping(title: str) -> str:
    # Only collapse exact duplicate titles for example selection.
    return " ".join((title or "").casefold().split())


def select_distinct_examples(
    ranked_indices: np.ndarray,
    rows: list[dict[str, str]],
    original_titles: list[str],
    normalized_titles: list[str],
    examples_per_topic: int,
) -> list[str]:
    norm_counts: Counter[str] = Counter()
    best_row_for_norm: dict[str, dict[str, str] | None] = {}
    first_title_for_norm: dict[str, str] = {}
    ranked_norms: list[str] = []

    for idx in ranked_indices:
        title_idx = int(idx)
        norm = normalized_titles[title_idx]
        if not norm:
            continue
        norm_counts[norm] += 1
        row = rows[title_idx]
        if norm not in best_row_for_norm:
            best_row_for_norm[norm] = row
            first_title_for_norm[norm] = original_titles[title_idx]
            ranked_norms.append(norm)
        else:
            current_best = best_row_for_norm[norm]
            if current_best is None:
                best_row_for_norm[norm] = row
            else:
                current_best_views = parse_view_count(current_best.get("view_count"))
                candidate_views = parse_view_count(row.get("view_count"))
                if candidate_views > current_best_views:
                    best_row_for_norm[norm] = row

    selected_examples: list[str] = []
    for norm in ranked_norms:
        best_row = best_row_for_norm.get(norm) or {}
        best_title = (best_row.get("video_title") or "").strip() or first_title_for_norm.get(norm, "")
        best_video_id = (best_row.get("video_id") or "").strip()
        example_prefix = f"{best_video_id}, " if best_video_id else ""
        count = norm_counts[norm]
        if count > 1:
            selected_examples.append(f"{example_prefix}{best_title} ({count} videos)")
        else:
            selected_examples.append(f"{example_prefix}{best_title}")
        if len(selected_examples) >= examples_per_topic:
            break

    return selected_examples


def fit_and_validate(
    docs: list[str],
    rows: list[dict[str, str]],
    original_titles: list[str],
    normalized_titles: list[str],
    embeddings: np.ndarray,
    k: int,
    top_n_words: int,
    examples_per_topic: int,
    random_state: int,
) -> KResult:
    # Use KMeans as BERTopic clustering backend to avoid hdbscan build issues on some Windows/Python combos.
    clustering_model = KMeans(n_clusters=k, random_state=random_state, n_init="auto")

    topic_model = BERTopic(
        nr_topics=None,
        embedding_model=None,
        hdbscan_model=clustering_model,
        top_n_words=top_n_words,
        calculate_probabilities=False,
        verbose=False,
    )

    topics, _ = topic_model.fit_transform(docs, embeddings=embeddings)

    embeddings_array = np.asarray(embeddings)
    labels = np.array(topics)
    valid_mask = labels != -1

    silhouette: float | None = None
    if valid_mask.sum() >= 3:
        unique_labels = np.unique(labels[valid_mask])
        if len(unique_labels) >= 2:
            silhouette = float(silhouette_score(embeddings_array[valid_mask], labels[valid_mask], metric="cosine"))

    topics_info = topic_model.get_topic_info()
    non_noise_topics = topics_info[topics_info["Topic"] != -1]["Topic"].tolist()
    topic_sizes: dict[int, int] = {}
    top_words: dict[int, list[str]] = {}
    topic_examples: dict[int, list[str]] = {}
    for topic_id in non_noise_topics:
        words = [w for w, _ in (topic_model.get_topic(topic_id) or [])[:10]]
        top_words[int(topic_id)] = words

        topic_indices = np.where(labels == topic_id)[0]
        topic_sizes[int(topic_id)] = int(topic_indices.size)
        if topic_indices.size == 0:
            topic_examples[int(topic_id)] = []
            continue

        # "Strongest" examples are those closest to the topic centroid in embedding space.
        topic_emb = embeddings_array[topic_indices]
        centroid = topic_emb.mean(axis=0)
        centroid_norm = np.linalg.norm(centroid)
        if centroid_norm > 0:
            centroid = centroid / centroid_norm
        similarities = topic_emb @ centroid
        ranked_local = topic_indices[np.argsort(-similarities)]
        topic_examples[int(topic_id)] = select_distinct_examples(
            ranked_indices=ranked_local,
            rows=rows,
            original_titles=original_titles,
            normalized_titles=normalized_titles,
            examples_per_topic=examples_per_topic,
        )

    return KResult(
        k=k,
        silhouette=silhouette,
        topic_count=len(non_noise_topics),
        noise_count=int((labels == -1).sum()),
        topic_sizes=topic_sizes,
        top_words=top_words,
        topic_examples=topic_examples,
        topic_assignments=labels.tolist(),
    )


def result_to_payload(result: KResult) -> dict:
    return {
        "k": result.k,
        "silhouette": result.silhouette,
        "topic_count": result.topic_count,
        "noise_count": result.noise_count,
        "topic_sizes": {str(k): v for k, v in result.topic_sizes.items()},
        "top_words": {str(k): v for k, v in result.top_words.items()},
        "topic_examples": {str(k): v for k, v in result.topic_examples.items()},
    }
def save_results_payload(
    output_path: Path,
    *,
    csv_path: Path,
    title_column: str,
    result: KResult,
) -> None:
    payload = {
        "csv": str(csv_path),
        "title_column": title_column,
        "k_values": [result.k],
        "results": [result_to_payload(result)],
        "best_k": result.k,
        "best_result": result_to_payload(result),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def build_results_text(result: KResult) -> str:
    sil = "N/A" if result.silhouette is None else f"{result.silhouette:.4f}"
    lines = []
    lines.append("BERTopic result")
    lines.append("=" * 38)
    lines.append(f"k={result.k}: silhouette={sil}, discovered_topics={result.topic_count}, noise_docs={result.noise_count}")
    lines.append("")
    lines.append("Topics ordered by size:")

    topic_ids = sorted(result.topic_sizes, key=lambda tid: (-result.topic_sizes[tid], tid))
    for topic_id in topic_ids:
        words = ", ".join(result.top_words.get(topic_id, [])) or "(none)"
        size = result.topic_sizes.get(topic_id, 0)
        lines.append(f"Topic {topic_id}")
        lines.append(f"  Videos: {size:,}")
        lines.append(f"  Top words: {words}")

        examples = result.topic_examples.get(topic_id, [])
        if examples:
            lines.append("  Example titles:")
            for index, example in enumerate(examples, start=1):
                lines.append(f"    {index}. {example}")
        else:
            lines.append("  Example titles: (none)")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def save_topic_assignments_csv(
    output_path: Path,
    *,
    original_titles: list[str],
    topic_assignments: list[int],
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["topic", "title"])
        writer.writeheader()
        for topic, title in zip(topic_assignments, original_titles):
            writer.writerow({"topic": int(topic), "title": title})


def save_csv_with_topics(
    output_path: Path,
    *,
    rows: list[dict[str, str]],
    fieldnames: list[str],
    topic_assignments: list[int],
    topic_column: str = "topic",
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_fieldnames = list(fieldnames)
    if topic_column not in output_fieldnames:
        output_fieldnames.append(topic_column)

    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=output_fieldnames)
        writer.writeheader()
        for row, topic in zip(rows, topic_assignments):
            row_with_topic = dict(row)
            row_with_topic[topic_column] = "noise" if int(topic) == -1 else f"topic{int(topic)}"
            writer.writerow(row_with_topic)


def _html_escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def save_topic_plot(best: KResult, output_path: Path, max_topics: int) -> None:
    try:
        from html2image import Html2Image
    except ImportError as exc:
        raise SystemExit(
            "html2image is required. Install it with:\n  pip install html2image"
        ) from exc

    topic_ids = sorted(best.topic_sizes, key=lambda tid: best.topic_sizes[tid], reverse=True)
    topic_ids = topic_ids[: max(max_topics, 1)]
    if not topic_ids:
        raise ValueError("No topics available to plot.")

    rows_html = ""
    for tid in topic_ids:
        size = best.topic_sizes.get(tid, 0)
        words = ", ".join(best.top_words.get(tid, [])[:6]) or "—"
        examples = best.topic_examples.get(tid, [])
        examples_html = "".join(
            f"<li>{_html_escape(ex)}</li>" for ex in examples[:3]
        ) or "<li>—</li>"
        rows_html += f"""
        <tr>
            <td class="topic-cell"><span class="topic-id">Topic {tid}</span><br><span class="count">{size} videos</span></td>
            <td class="words-cell">{_html_escape(words)}</td>
            <td class="examples-cell"><ol>{examples_html}</ol></td>
        </tr>"""

    title_text = f"BERTopic Topic Overview ({best.topic_count} topics)"
    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ background: #fff; padding: 48px; font-family: -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif; color: #1a1a1a; }}
h1 {{ font-size: 28px; font-weight: 700; margin-bottom: 6px; }}
.subtitle {{ font-size: 16px; color: #666; margin-bottom: 32px; }}
table {{ width: 100%; border-collapse: collapse; }}
thead th {{ text-align: left; font-size: 16px; font-weight: 600; color: #444;
    padding: 10px 16px; border-bottom: 2px solid #ccc; border-right: 1px solid #ddd; }}
thead th:last-child {{ border-right: none; }}
tbody tr {{ border-bottom: 1px solid #e5e5e5; }}
tbody tr:nth-child(even) {{ background: #fafafa; }}
td {{ padding: 14px 16px; vertical-align: top; font-size: 16px; line-height: 1.5; border-right: 1px solid #e5e5e5; }}
td:last-child {{ border-right: none; }}
.topic-cell {{ white-space: nowrap; }}
.topic-id {{ font-size: 18px; font-weight: 700; }}
.count {{ font-size: 14px; color: #999; }}
.words-cell {{ color: #333; }}
.examples-cell ol {{ padding-left: 20px; }}
.examples-cell li {{ margin-bottom: 4px; color: #333; }}
.footer {{ margin-top: 24px; font-size: 14px; color: #888; }}
</style></head><body>
<h1>{_html_escape(title_text)}</h1>
<p class="subtitle">Largest topics with representative words and example titles</p>
<table>
<thead><tr><th>Topic</th><th>Top words</th><th>Example titles</th></tr></thead>
<tbody>{rows_html}</tbody>
</table>
<p class="footer">Exact duplicate titles are shown once with occurrence counts.</p>
</body></html>"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    hti = Html2Image(output_path=str(output_path.parent), custom_flags=["--hide-scrollbars"])
    tmp_name = "__tmp_topic_plot.png"
    hti.screenshot(html_str=html, save_as=tmp_name, size=(1200, 200 + len(topic_ids) * 160))

    from PIL import Image
    tmp_path = output_path.parent / tmp_name
    img = Image.open(tmp_path)
    bbox = img.getbbox()
    if bbox:
        cropped = img.crop((0, 0, bbox[2], bbox[3]))
        cropped.save(output_path, dpi=(300, 300))
        cropped.close()
    else:
        img.save(output_path, dpi=(300, 300))
    img.close()
    if tmp_path != output_path:
        tmp_path.unlink(missing_ok=True)


def print_results(result: KResult) -> None:
    print(build_results_text(result), end="")


def main() -> None:
    script_path = Path(__file__).resolve()
    script_dir = script_path.parent
    project_dir = script_path.parents[3]
    load_env_file(project_dir / ".env")

    default_csv = project_dir / "Datasets" / "gl-cl.csv"

    parser = argparse.ArgumentParser(
        description="Run BERTopic on YouTube titles with one fixed k value defined at the top of the script."
    )
    parser.add_argument("--csv", type=Path, default=default_csv, help="Path to input CSV")
    parser.add_argument("--title-column", default="video_title", help="Title column name")
    parser.add_argument(
        "--embedding-model",
        default="all-MiniLM-L6-v2",
        help="SentenceTransformer embedding model",
    )
    parser.add_argument("--top-n-words", type=int, default=10, help="Top words per topic")
    parser.add_argument(
        "--examples-per-topic",
        type=int,
        default=6,
        help="How many strongest example titles to print per topic (default: 6)",
    )
    parser.add_argument("--min-word-length", type=int, default=2, help="Minimum token length")
    parser.add_argument(
        "--output-json",
        type=Path,
        default=None,
        help="Path to save validation results and the best-topic summary JSON. Default: save in this script folder.",
    )
    parser.add_argument(
        "--output-text",
        type=Path,
        default=None,
        help="Path to save a readable text summary. Default: save next to the JSON output.",
    )
    parser.add_argument(
        "--output-csv-w-topics",
        type=Path,
        default=None,
        help="Path to save a copy of the input CSV with an added topic column from the best run. Default: save in this script folder.",
    )
    parser.add_argument(
        "--output-plot",
        type=Path,
        default=None,
        help="Path to save the topic overview plot PNG. Default: save in this script folder.",
    )
    parser.add_argument(
        "--max-topics-in-plot",
        type=int,
        default=DEFAULT_MAX_TOPICS_IN_PLOT,
        help=f"How many of the largest topics to show in the overview plot (default: {DEFAULT_MAX_TOPICS_IN_PLOT}).",
    )
    parser.add_argument("--random-state", type=int, default=42, help="Random seed")

    args = parser.parse_args()
    csv_path = args.csv.resolve()

    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    output_json_path = (
        args.output_json.resolve()
        if args.output_json
        else script_dir / f"{csv_path.stem}-topic-results.json"
    )
    output_text_path = (
        args.output_text.resolve()
        if args.output_text
        else script_dir / f"{csv_path.stem}-topic-results.txt"
    )
    output_assignments_path = script_dir / f"{csv_path.stem}-topic-assignments.csv"
    output_csv_with_topics_path = script_dir / f"{csv_path.stem}-w-topics.csv"

    print(f"Saving JSON output to: {output_json_path}")
    print(f"Saving text output to: {output_text_path}")

    rows, titles, fieldnames = read_csv_rows(csv_path, title_column=args.title_column)
    docs = preprocess_titles(titles, stopwords=DEFAULT_STOPWORDS, min_word_length=args.min_word_length)
    normalized_titles = [normalize_title_for_grouping(title) for title in titles]
    topic_k = DEFAULT_MAX_TOPICS_IN_PLOT

    print(f"Encoding {len(docs)} titles with model '{args.embedding_model}' ...")
    sentence_model = SentenceTransformer(args.embedding_model)
    embeddings = sentence_model.encode(
        docs,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )

    print(f"Fitting BERTopic for k={topic_k} ...")
    result = fit_and_validate(
        docs=docs,
        rows=rows,
        original_titles=titles,
        normalized_titles=normalized_titles,
        embeddings=embeddings,
        k=topic_k,
        top_n_words=args.top_n_words,
        examples_per_topic=args.examples_per_topic,
        random_state=args.random_state,
    )
    results_text = build_results_text(result)
    print(results_text, end="")

    save_results_payload(
        output_path=output_json_path,
        csv_path=csv_path,
        title_column=args.title_column,
        result=result,
    )
    output_text_path.parent.mkdir(parents=True, exist_ok=True)
    output_text_path.write_text(results_text, encoding="utf-8")
    save_topic_assignments_csv(
        output_path=output_assignments_path,
        original_titles=titles,
        topic_assignments=result.topic_assignments,
    )
    save_csv_with_topics(
        output_path=output_csv_with_topics_path,
        rows=rows,
        fieldnames=fieldnames,
        topic_assignments=result.topic_assignments,
    )
    print(f"\nSaved topic results to: {output_json_path}")
    print(f"Saved text summary to: {output_text_path}")
    print(f"Saved topic assignments to: {output_assignments_path}")
    print(f"Saved CSV with topics to: {output_csv_with_topics_path}")


if __name__ == "__main__":
    main()
