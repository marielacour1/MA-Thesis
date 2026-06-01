# MA Thesis — YouTube Greenland Discourse Analysis

A complete pipeline for studying how "Greenland" is framed in YouTube video content. The pipeline goes from raw API scraping through NLP topic modeling, manual frame assignment, and statistical regression analysis.

## Repository layout

```
yt_scraper.py                            # YouTube Data API v3 scraper
refetch_missing_video_rows.py            # Re-fetch specific videos to update stats
config.yaml                              # Scraper search parameters
requirements.txt                         # Python dependencies
Datasets/
├── yt-greenland.csv                     # Raw API output
├── gl-cl.csv                            # After language/spam filtering
├── gl-cl-w-topics.csv                   # After BERTopic topic assignment
├── gl-cl-w-topics-FINAL.csv            # After final filtering + frame assignment
├── deleted.csv / deleted2.csv           # Videos removed in each filtering pass
├── deleted-videos.csv                   # Merged deletion log with reasons
├── duplicate-videos.csv                 # Detected near-duplicate videos
└── greenland-only-title-videos.csv      # Videos with "greenland" only in title
Analysis/
├── removing_irrelevant_videos.py        # Step 1 — language, spam, film/game filtering
├── final_filtering.py                   # Step 3 — topic/term/channel exclusions
├── assign_frames_to_final.py            # Step 4 — map topics → 5 analytical frames
├── analyze_channel_country.py           # Quick channel country distribution check
├── top_channels_by_video_count.py       # Top channels by video count
├── Topic_modeling/
│   ├── Creating_frames/
│   │   ├── title_bertopic_modeling.py           # Step 2 — BERTopic + KMeans clustering
│   │   ├── extract_topic_titles.py              # Print top titles per topic
│   │   ├── frame_distribution_over_time/
│   │   │   └── frame_prevalence_over_time.py    # Frame share per 2-month window
│   │   └── (topic assignment CSVs + JSON/TXT results)
│   ├── topic_prevalence_over_time/
│   │   └── topic_prevalence_over_time.py        # Topic counts by year
│   └── frame_engagement_regression/
│       ├── topic_engagement_regression.R        # OLS regression: frame → engagement
│       └── frame_engagement_subscriber_control.R
├── geopolitical_frame_analysis/
│   ├── assign_geopolitical_subframes.py         # Subdivide geopolitical frame into 5 subframes
│   ├── export_geopolitical_topic_results.py
│   ├── top_geopolitical_channels_by_subscribers.py
│   └── subframe_distribution_over_time/
│       └── subframe_prevalence_over_time.py
├── channel_country_analysis/
│   ├── channel_country_breakdown_by_frame.py    # Country distribution by frame
│   └── predict_missing_channel_country.py       # Infer missing country from channel metadata
├── channel_subscriber_distribution_by_frame/
│   └── channel_subscriber_distribution_by_frame.py
├── video_duration_distribution_by_frame/
│   └── video_duration_distribution_by_frame.py
├── plot_frame_distribution/
│   └── plot_frame_distribution.py               # Pie chart of frame shares
├── Categorical_table/
│   └── categorical_youtube_table.py             # HTML summary table of categorical columns
├── Descriptive_table/
│   └── descriptive_numeric_table.py             # HTML summary table of numeric columns
├── precision_and_recall/
│   ├── make_precision_recall_samples.py         # Draw random samples for manual review
│   └── calculate_precision_recall.py            # Compute precision/recall from annotated samples
├── filtering_flow_charts/
│   └── export_html_png.py                       # Export filtering funnel diagrams
└── news_channels_analysis/
    ├── build_news_channel_review_inventory.py   # Build channel review spreadsheet
    ├── extract_news_channels_dataset.py         # Filter dataset to news channels only
    ├── news_title_bertopic_modeling.py          # BERTopic on news-channel titles
    ├── analyze_official_news_channel_countries.py
    └── calculate_official_news_channel_video_share.py
```

## Setup

```bash
python -m venv .venv

# macOS / Linux
source .venv/bin/activate

# Windows
.venv\Scripts\activate

pip install -r requirements.txt
```

The R scripts (`frame_engagement_regression/`) require R with `ggplot2` installed.

## Pipeline

### Step 0 — Scrape

Requires a YouTube Data API v3 key. Create `.env` in the repo root:

```
YOUTUBE_API_KEY=your_key_here
```

Multiple keys for quota rotation:

```
YOUTUBE_API_KEY=key1
YOUTUBE_API_KEY_2=key2
YOUTUBE_API_KEY_3=key3
```

Configure the date range and other parameters in `config.yaml`, then run:

```bash
python yt_scraper.py
# Output: Datasets/yt-greenland.csv
```

To update view/like counts for already-collected videos, set `refresh_existing: true` in `config.yaml`.  
To re-fetch specific videos by ID: `python refetch_missing_video_rows.py`.

### Step 1 — Clean

Removes non-English content, spam, game/film false positives, duplicates, and bannlisted channels/terms/video IDs:

```bash
python Analysis/removing_irrelevant_videos.py
# Input:  Datasets/yt-greenland.csv
# Output: Datasets/gl-cl.csv
#         Datasets/deleted.csv
#         Datasets/duplicate-videos.csv
#         Datasets/greenland-only-title-videos.csv
```

### Step 2 — Topic modeling

Embeds video titles with sentence-transformers, clusters with KMeans (silhouette-optimised), and extracts topics with BERTopic:

```bash
python Analysis/Topic_modeling/Creating_frames/title_bertopic_modeling.py
# Input:  Datasets/gl-cl.csv
# Output: Analysis/Topic_modeling/Creating_frames/gl-cl-w-topics.csv
#         Analysis/Topic_modeling/Creating_frames/gl-cl-topic-results.json
#         Analysis/Topic_modeling/Creating_frames/gl-cl-topic-results.txt
```

Copy the output CSV to `Datasets/gl-cl-w-topics.csv` before proceeding.

### Step 3 — Final filtering

Excludes specific topics, terms, channels, and video IDs identified during manual review of the topic model output:

```bash
python Analysis/final_filtering.py
# Input:  Datasets/gl-cl-w-topics.csv
# Output: Datasets/gl-cl-w-topics-FINAL.csv
#         Datasets/deleted2.csv
#         Datasets/deleted-videos.csv  (merged with deleted.csv)
```

### Step 4 — Frame assignment

Maps each of the 500 discovered topics to one of five analytical frames:

| Frame | Description |
|-------|-------------|
| Local Cultures and Everyday Life | Daily life, food, culture, travel |
| Knowledge and Education | Documentaries, educational content |
| Geopolitical and Strategic | Political discourse, diplomacy, security |
| Nature and Tourism | Landscapes, climate, outdoor activities |
| Climate Change and Natural Disaster | Environmental and disaster content |

```bash
python Analysis/assign_frames_to_final.py
# Input/Output: Datasets/gl-cl-w-topics-FINAL.csv  (adds "frame" column in place)
```

### Step 5 — Analysis

All analysis scripts read from `Datasets/gl-cl-w-topics-FINAL.csv` unless noted. Run each from the repo root:

```bash
# Geopolitical subframes (subdivides geopolitical frame into 5 sub-categories)
python Analysis/geopolitical_frame_analysis/assign_geopolitical_subframes.py

# Frame distribution over time (2-month windows)
python Analysis/Topic_modeling/Creating_frames/frame_distribution_over_time/frame_prevalence_over_time.py

# Subframe distribution over time
python Analysis/geopolitical_frame_analysis/subframe_distribution_over_time/subframe_prevalence_over_time.py

# Topic/frame prevalence by year
python Analysis/Topic_modeling/topic_prevalence_over_time/topic_prevalence_over_time.py

# Channel country breakdown by frame
python Analysis/channel_country_analysis/channel_country_breakdown_by_frame.py

# Subscriber distribution by frame
python Analysis/channel_subscriber_distribution_by_frame/channel_subscriber_distribution_by_frame.py

# Video duration distribution by frame
python Analysis/video_duration_distribution_by_frame/video_duration_distribution_by_frame.py

# Frame distribution pie chart
python Analysis/plot_frame_distribution/plot_frame_distribution.py

# Descriptive and categorical summary tables (HTML)
python Analysis/Descriptive_table/descriptive_numeric_table.py
python Analysis/Categorical_table/categorical_youtube_table.py

# Regression: frame effects on engagement (run in R)
# Rscript Analysis/Topic_modeling/frame_engagement_regression/topic_engagement_regression.R
# Rscript Analysis/Topic_modeling/frame_engagement_regression/frame_engagement_subscriber_control.R
```

### Step 6 — News channel analysis

```bash
# Build review inventory of all channels
python Analysis/news_channels_analysis/build_news_channel_review_inventory.py

# Extract dataset filtered to news channels only
python Analysis/news_channels_analysis/extract_news_channels_dataset.py

# Topic model on news channel titles
python Analysis/news_channels_analysis/news_title_bertopic_modeling.py

# News channel country distribution
python Analysis/news_channels_analysis/analyze_official_news_channel_countries.py

# Official news channel video share
python Analysis/news_channels_analysis/calculate_official_news_channel_video_share.py
```

### Precision and recall

```bash
# Draw random samples for manual annotation
python Analysis/precision_and_recall/make_precision_recall_samples.py

# After annotating the sample spreadsheets, compute scores
python Analysis/precision_and_recall/calculate_precision_recall.py
```

## Data flow summary

```
yt-greenland.csv  (raw)
    ↓  removing_irrelevant_videos.py
gl-cl.csv  (language/spam filtered)
    ↓  title_bertopic_modeling.py
gl-cl-w-topics.csv  (500 topics assigned)
    ↓  final_filtering.py
gl-cl-w-topics-FINAL.csv  (core analysis dataset, with frame column)
    ├→ assign_geopolitical_subframes.py
    ├→ frame_prevalence_over_time.py
    ├→ channel_country_analysis/
    ├→ frame_engagement_regression/ (R)
    └→ news_channels_analysis/
```
