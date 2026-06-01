import argparse
import csv
import json
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Iterable

import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

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


DEFAULT_STOPWORDS = {
    "in",
    "the",
    "of",
    "to",
    "with",
    "and",
    "from",
    "on",
    "at",
    "over",
    "for",
    "by",
    "is",
    "how",
    "a",
    "are",
    "that",
    "this",
    "it",
    "as",
    "was",
    "but",
    "be",
    "not",
    "greenland",
    "greenland's",
    "2014",
    "2015",
    "2016",
    "2017",
    "2018",
    "2019",
    "2020",
    "2021",
    "2022",
    "2023",
    "2024",
    "2025",
    "2026",
    "day",
    "hd",
    "vs",
    "why",
    "10",
    "20",
    "30",
    "100",
    "17",
    "4k",
    "my",
    "you",
    "we",
    "they",
    "about",
    "all",
    "do",
    "if",
    "me",
    "your",
    "his",
    "news",
    "live",
    "breaking",
    "english",
    "post",
    "report",
    "http",
    "https",
    "www",
    "com",
    "ly",
    "bit",
    "youtube",
    "channel",
    "subscribe",
    "follow",
    "facebook",
    "twitter",
    "instagram",
    "telegram",
    "tweet",
    "tweets",
    "tweeted",
    "x",
    "video",
    "videos",
    "shows",
    "latest",
    "watch",
    "via",
    "here",
    "more",
    "our",
    "00",
    "24",
    "ca",
    "brand",
    "nbc",
    "nbcnews",
    "cbc",
    "abc",
    "bbc",
    "ctv",
    "ctvnews",
    "cnn",
    "fox",
    "foxnews",
    "fnc",
    "newsmax",
    "cnbc",
    "forbes",
    "vice",
    "geo",
    "crux",
    "wion",
    "n18g",
    "firstpost",
    "oneindia",
    "oneindianews",
    "oneindiaenglish",
    "guardian",
    "guardiannews",
    "times",
    "world",
    "sky",
    "skynews",
    "f24",
    "france24",
    "france",
    "reuters",
    "ap",
    "abcnews",
    "abcnewsaustralia",
    "australia",
    "business",
    "cable",
    "cbs",
    "cbsnews",
    "cx",
    "cnb",
    "euronews",
    "five",
    "global",
    "gravitas",
    "hannity",
    "ingraham",
    "angle",
    "linkedin",
    "mach",
    "most",
    "n18g",
    "palki",
    "primetime",
    "firstedition",
    "edition",
    "iview",
    "notified",
    "platform",
    "platforms",
    "coverage",
    "updates",
    "welcome",
    "connected",
    "informed",
    "click",
    "deeper",
    "organisation",
    "organization",
    "supporters",
    "contribute",
    "bell",
    "icon",
    "notify",
    "notifications",
    "social",
    "media",
    "theguardian",
    "guardianwiressub",
    "guardiannewssubs",
    "guardianaussubs",
    "gdnfootballsubs",
    "gdnsportsubs",
    "itscomplicatedsubs",
    "stories",
    "tiktok",
    "timesnow",
    "today",
    "top",
    "vantage",
    "whatsapp",
    "wsj",
    "7news",
}

TOKEN_RE = re.compile(r"[A-Za-z0-9']+")
TITLE_GROUP_RE = re.compile(r"[A-Za-z0-9]+")
URL_RE = re.compile(r"https?://\S+|www\.\S+")
HANDLE_RE = re.compile(r"(?<!\w)@\w+")
PROMO_LINE_RE = re.compile(
    r"(?im)^\s*(subscribe|follow|like us|watch more|watch live|welcome to|sign up|go deeper|"
    r"read the latest|browse the news|discover our|catch the latest|stay connected|stay informed|"
    r"the guardian on youtube|youtube:|website|facebook|instagram|twitter|telegram)\b.*$"
)
SEPARATOR_RE = re.compile(r"(?m)^[=\-_]{5,}$")
GROUPING_STOPWORDS = {
    "a",
    "an",
    "and",
    "at",
    "for",
    "from",
    "in",
    "of",
    "on",
    "the",
    "to",
    "video",
}


@dataclass
class KResult:
    k: int
    silhouette: float | None
    topic_count: int
    noise_count: int
    topic_sizes: dict[int, int]
    top_words: dict[int, list[str]]
    topic_examples: dict[int, list[str]]


def load_rows_and_documents(
    csv_path: Path,
    *,
    title_column: str,
    description_column: str,
    text_mode: str,
) -> tuple[list[dict[str, str]], list[str], list[str], list[int]]:
    rows: list[dict[str, str]] = []
    titles: list[str] = []
    documents: list[str] = []
    doc_row_indices: list[int] = []
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None or title_column not in reader.fieldnames:
            raise ValueError(
                f"Column '{title_column}' not found in CSV. Available columns: {reader.fieldnames}"
            )
        if text_mode == "title_description" and description_column not in reader.fieldnames:
            raise ValueError(
                f"Column '{description_column}' not found in CSV. Available columns: {reader.fieldnames}"
            )

        for row_index, row in enumerate(reader):
            rows.append(row)
            title = (row.get(title_column) or "").strip()
            description = (row.get(description_column) or "").strip()

            if text_mode == "title":
                document = title
            else:
                document = "\n\n".join(part for part in (title, description) if part)

            if document:
                titles.append(title if title else "(untitled)")
                documents.append(document)
                doc_row_indices.append(row_index)

    if not documents:
        raise ValueError("No non-empty documents found in CSV.")

    return rows, titles, documents, doc_row_indices


def clean_text(text: str, stopwords: set[str], min_word_length: int) -> str:
    text = URL_RE.sub(" ", text)
    text = HANDLE_RE.sub(" ", text)
    text = PROMO_LINE_RE.sub(" ", text)
    text = SEPARATOR_RE.sub(" ", text)
    tokens = [
        token
        for token in TOKEN_RE.findall(text.lower())
        if len(token) >= min_word_length and token not in stopwords
    ]
    return " ".join(tokens)


def preprocess_titles(titles: Iterable[str], stopwords: set[str], min_word_length: int) -> list[str]:
    cleaned = [clean_text(title, stopwords=stopwords, min_word_length=min_word_length) for title in titles]
    return [text if text else "untitled" for text in cleaned]


def normalize_title_for_grouping(title: str) -> str:
    tokens = []
    for token in TITLE_GROUP_RE.findall((title or "").lower()):
        if re.fullmatch(r"(19|20)\d{2}", token):
            continue
        if token in GROUPING_STOPWORDS:
            continue
        tokens.append(token)
    return " ".join(sorted(set(tokens)))


def titles_are_similar_for_grouping(norm_a: str, norm_b: str) -> bool:
    if not norm_a or not norm_b:
        return False
    if norm_a == norm_b:
        return True

    tokens_a = set(norm_a.split())
    tokens_b = set(norm_b.split())
    if not tokens_a or not tokens_b:
        return False

    overlap = len(tokens_a & tokens_b) / max(min(len(tokens_a), len(tokens_b)), 1)
    if overlap >= 0.8:
        return True

    return SequenceMatcher(None, norm_a, norm_b).ratio() >= 0.84


def select_distinct_examples(
    ranked_indices: np.ndarray,
    original_titles: list[str],
    examples_per_topic: int,
) -> list[str]:
    clusters: list[dict[str, object]] = []
    for idx in ranked_indices:
        title = original_titles[int(idx)]
        norm = normalize_title_for_grouping(title)
        if not norm:
            continue

        matched_cluster = None
        for cluster in clusters:
            if titles_are_similar_for_grouping(norm, str(cluster["norm"])):
                matched_cluster = cluster
                break

        if matched_cluster is None:
            clusters.append({"norm": norm, "title": title, "count": 1})
        else:
            matched_cluster["count"] = int(matched_cluster["count"]) + 1

    selected_examples: list[str] = []
    for cluster in clusters[:examples_per_topic]:
        count = int(cluster["count"])
        label = "video" if count == 1 else "videos"
        selected_examples.append(f"{cluster['title']} ({count} {label})")

    return selected_examples


def fit_and_validate(
    docs: list[str],
    original_titles: list[str],
    embeddings: np.ndarray,
    k: int,
    top_n_words: int,
    examples_per_topic: int,
    random_state: int,
) -> KResult:
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
    labels = np.array(topics)
    valid_mask = labels != -1

    silhouette: float | None = None
    if valid_mask.sum() >= 3:
        unique_labels = np.unique(labels[valid_mask])
        if len(unique_labels) >= 2:
            silhouette = float(
                silhouette_score(np.asarray(embeddings)[valid_mask], labels[valid_mask], metric="cosine")
            )

    topics_info = topic_model.get_topic_info()
    non_noise_topics = topics_info[topics_info["Topic"] != -1]["Topic"].tolist()
    topic_sizes: dict[int, int] = {}
    top_words: dict[int, list[str]] = {}
    topic_examples: dict[int, list[str]] = {}

    for topic_id in non_noise_topics:
        words = [word for word, _ in (topic_model.get_topic(topic_id) or [])[:10]]
        top_words[int(topic_id)] = words

        topic_indices = np.where(labels == topic_id)[0]
        topic_sizes[int(topic_id)] = int(topic_indices.size)
        if topic_indices.size == 0:
            topic_examples[int(topic_id)] = []
            continue

        topic_embeddings = np.asarray(embeddings)[topic_indices]
        centroid = topic_embeddings.mean(axis=0)
        centroid_norm = np.linalg.norm(centroid)
        if centroid_norm > 0:
            centroid = centroid / centroid_norm
        similarities = topic_embeddings @ centroid
        ranked_local = topic_indices[np.argsort(-similarities)]
        topic_examples[int(topic_id)] = select_distinct_examples(
            ranked_indices=ranked_local,
            original_titles=original_titles,
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
    )


def fit_topic_model(
    docs: list[str],
    embeddings: np.ndarray,
    k: int,
    top_n_words: int,
    random_state: int,
) -> tuple[BERTopic, np.ndarray]:
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
    return topic_model, np.array(topics)


def choose_best(results: list[KResult]) -> KResult:
    def rank_key(result: KResult) -> tuple[float, int, int]:
        silhouette = -1.0 if result.silhouette is None else result.silhouette
        return (silhouette, -result.noise_count, -abs(result.topic_count - result.k))

    return sorted(results, key=rank_key, reverse=True)[0]


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
    description_column: str,
    text_mode: str,
    embedding_model: str,
    k_values: list[int],
    results: list[KResult],
    best: KResult,
) -> None:
    payload = {
        "csv": str(csv_path),
        "title_column": title_column,
        "description_column": description_column,
        "text_mode": text_mode,
        "embedding_model": embedding_model,
        "k_values": k_values,
        "results": [result_to_payload(result) for result in results],
        "best_k": best.k,
        "best_result": result_to_payload(best),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def build_results_text(results: list[KResult], best: KResult) -> str:
    lines = []
    lines.append("Validation over candidate k values")
    lines.append("=" * 38)
    for result in results:
        sil = "N/A" if result.silhouette is None else f"{result.silhouette:.4f}"
        lines.append(
            f"k={result.k}: silhouette={sil}, discovered_topics={result.topic_count}, noise_docs={result.noise_count}"
        )

    lines.append("")
    lines.append("Best k based on validation:")
    best_sil = "N/A" if best.silhouette is None else f"{best.silhouette:.4f}"
    lines.append(
        f"k={best.k} (silhouette={best_sil}, discovered_topics={best.topic_count}, noise_docs={best.noise_count})"
    )

    lines.append("")
    lines.append("Top words per topic (best k):")
    for topic_id in sorted(best.top_words):
        words = ", ".join(best.top_words[topic_id])
        size = best.topic_sizes.get(topic_id, 0)
        lines.append(f"- Topic {topic_id} ({size} videos): {words}")
        examples = best.topic_examples.get(topic_id, [])
        if examples:
            lines.append("  Examples:")
            for index, example in enumerate(examples, start=1):
                lines.append(f"    {index}. {example}")

    return "\n".join(lines) + "\n"


def get_topic_column_names(text_mode: str) -> tuple[str, str]:
    prefix = "title" if text_mode == "title" else "title_description"
    return f"{prefix}_topic_id", f"{prefix}_topic"


def format_topic_label(topic_id: int, top_words: dict[int, list[str]]) -> str:
    if topic_id == -1:
        return "Unassigned"

    words = [word for word in top_words.get(topic_id, []) if word][:3]
    if not words:
        return f"Topic {topic_id}"
    return f"Topic {topic_id}: {', '.join(words)}"


def save_topic_assignments_csv(
    output_path: Path,
    *,
    rows: list[dict[str, str]],
    text_mode: str,
    doc_row_indices: list[int],
    labels: np.ndarray,
    top_words: dict[int, list[str]],
) -> None:
    topic_id_column, topic_label_column = get_topic_column_names(text_mode)
    fieldnames = list(rows[0].keys())
    for column in (topic_id_column, topic_label_column):
        if column not in fieldnames:
            fieldnames.append(column)

    annotated_rows = [dict(row) for row in rows]
    for row in annotated_rows:
        row[topic_id_column] = ""
        row[topic_label_column] = ""

    for row_index, topic_id in zip(doc_row_indices, labels, strict=True):
        topic_value = int(topic_id)
        annotated_rows[row_index][topic_id_column] = str(topic_value)
        annotated_rows[row_index][topic_label_column] = format_topic_label(topic_value, top_words)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(annotated_rows)


def main() -> None:
    base_dir = Path(__file__).resolve().parent
    default_csv = base_dir / "gl-cl-news-channels-only.csv"

    parser = argparse.ArgumentParser(
        description="Run BERTopic on news-channel documents and save results in this folder."
    )
    parser.add_argument("--csv", type=Path, default=default_csv, help="Path to input CSV")
    parser.add_argument("--title-column", default="video_title", help="Title column name")
    parser.add_argument(
        "--description-column",
        default="video_description",
        help="Description column name",
    )
    parser.add_argument(
        "--text-mode",
        choices=["title", "title_description"],
        default="title_description",
        help="Whether to model titles only or title+description combined (default: title_description)",
    )
    parser.add_argument(
        "--k-values",
        nargs="+",
        type=int,
        default=[8, 10, 12, 14],
        help="Candidate k values to validate",
    )
    parser.add_argument(
        "--embedding-model",
        default="all-MiniLM-L6-v2",
        help="SentenceTransformer embedding model",
    )
    parser.add_argument("--top-n-words", type=int, default=10, help="Top words per topic")
    parser.add_argument(
        "--examples-per-topic",
        type=int,
        default=5,
        help="How many strongest example titles to include per topic",
    )
    parser.add_argument("--min-word-length", type=int, default=2, help="Minimum token length")
    parser.add_argument(
        "--output-json",
        type=Path,
        default=None,
        help="Path to save JSON results. Default: save in this folder next to the CSV.",
    )
    parser.add_argument(
        "--output-txt",
        type=Path,
        default=None,
        help="Path to save a readable text summary. Default: save in this folder next to the CSV.",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=None,
        help="Path to save the input CSV again with topic columns appended.",
    )
    parser.add_argument("--random-state", type=int, default=42, help="Random seed")

    args = parser.parse_args()
    csv_path = args.csv.resolve()
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    mode_suffix = "topic-results" if args.text_mode == "title" else f"{args.text_mode}-topic-results"
    output_json_path = (
        args.output_json.resolve()
        if args.output_json
        else base_dir / f"{csv_path.stem}-{mode_suffix}.json"
    )
    output_txt_path = (
        args.output_txt.resolve()
        if args.output_txt
        else base_dir / f"{csv_path.stem}-{mode_suffix}.txt"
    )
    output_csv_path = (
        args.output_csv.resolve()
        if args.output_csv
        else base_dir / f"{csv_path.stem}-{mode_suffix}.csv"
    )

    rows, titles, raw_documents, doc_row_indices = load_rows_and_documents(
        csv_path,
        title_column=args.title_column,
        description_column=args.description_column,
        text_mode=args.text_mode,
    )
    docs = preprocess_titles(raw_documents, stopwords=DEFAULT_STOPWORDS, min_word_length=args.min_word_length)

    print(f"Encoding {len(docs)} documents using mode '{args.text_mode}' with model '{args.embedding_model}' ...")
    sentence_model = SentenceTransformer(args.embedding_model)
    embeddings = sentence_model.encode(
        docs,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )

    results: list[KResult] = []
    for k in args.k_values:
        print(f"Fitting BERTopic for k={k} ...")
        result = fit_and_validate(
            docs=docs,
            original_titles=titles,
            embeddings=embeddings,
            k=k,
            top_n_words=args.top_n_words,
            examples_per_topic=args.examples_per_topic,
            random_state=args.random_state,
        )
        results.append(result)

    best = choose_best(results)
    results_text = build_results_text(results, best)
    print(results_text, end="")

    best_topic_model, best_labels = fit_topic_model(
        docs=docs,
        embeddings=embeddings,
        k=best.k,
        top_n_words=args.top_n_words,
        random_state=args.random_state,
    )
    best_topics_info = best_topic_model.get_topic_info()
    best_top_words: dict[int, list[str]] = {}
    for topic_id in best_topics_info[best_topics_info["Topic"] != -1]["Topic"].tolist():
        best_top_words[int(topic_id)] = [
            word for word, _ in (best_topic_model.get_topic(int(topic_id)) or [])[:10]
        ]

    save_results_payload(
        output_path=output_json_path,
        csv_path=csv_path,
        title_column=args.title_column,
        description_column=args.description_column,
        text_mode=args.text_mode,
        embedding_model=args.embedding_model,
        k_values=args.k_values,
        results=results,
        best=best,
    )
    output_txt_path.write_text(results_text, encoding="utf-8")
    save_topic_assignments_csv(
        output_path=output_csv_path,
        rows=rows,
        text_mode=args.text_mode,
        doc_row_indices=doc_row_indices,
        labels=best_labels,
        top_words=best_top_words,
    )

    print(f"Saved topic results to: {output_json_path}")
    print(f"Saved text summary to: {output_txt_path}")
    print(f"Saved topic-annotated CSV to: {output_csv_path}")


if __name__ == "__main__":
    main()
