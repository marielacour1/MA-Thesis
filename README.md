# MA Thesis - Greenland Video Frame Analysis

This repository contains the data and analysis pipeline for a thesis project on how Greenland is framed in video metadata and engagement patterns. It includes scraping, filtering, topic modeling, frame-level analysis, regression outputs, figure generation, and thesis-ready tables.

Most scripts assume they are run from the repository root:

```powershell
cd "C:\Users\marie\Desktop\MA-Thesis - Copy"
```

## Repository Layout

```text
.
|-- yt_scraper.py
|-- config.yaml
|-- requirements.txt
|-- Datasets/
|   |-- yt-greenland.csv
|   |-- gl-cl.csv
|   |-- final_dataset.csv
|   |-- deleted_1.csv
|   |-- deleted_2.csv
|   `-- deleted_total.csv
|-- Analysis/
|   |-- initial_filtering.py
|   |-- final_filtering_and_frame_assignment.py
|   |-- Topic_modeling/
|   |   |-- title_bertopic_modeling.py
|   |   |-- gl-cl-w-topics.csv
|   |   |-- gl-cl-topic-assignments.csv
|   |   |-- gl-cl-topic-results.txt
|   |   |-- frame_topic_report/
|   |   `-- Topic_validation_help/
|   |-- frame_distribution_over_time/
|   |   |-- frame_prevalence_over_time.py
|   |   `-- frame_distribution_over_time_monthly.png
|   |-- frame_engagement_regression/
|   |   |-- topic_engagement_regression.R
|   |   |-- frame-engagement-regression-coefficients.csv
|   |   |-- frame-engagement-regression-presentable-a4.png
|   |   |-- frame-engagement-regression-coefficients-presentable-a4.png
|   |   `-- all_model_results/
|   |-- geopolitical_frame_analysis/
|   |   |-- assign_geopolitical_subframes.py
|   |   |-- export_geopolitical_topic_results.py
|   |   |-- top_geopolitical_channels_by_subscribers.py
|   |   `-- subframe_distribution_over_time/
|   `-- precision_and_recall/
|       |-- make_precision_recall_samples.py
|       |-- calculate_precision_recall.py
|       `-- precision_recall_results.txt
|-- Tables/
|   |-- categorical_tables/
|   |-- Descriptive_table/
|   |-- channel_country_tables/
|   |-- channel_subscriber_distribution_by_frame/
|   |-- frame_engagement_summary/
|   `-- video_duration_distribution_by_frame/
`-- Flowchart_filtering_process/
    |-- export_html_png.py
    |-- filtering-flow-stacked.html
    `-- filtering-flow-stacked.png
```

## Setup

Create and activate a Python environment:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

The topic modeling step uses BERTopic and sentence-transformers, so the first run can take a while and may download model files.

The regression scripts require R plus `ggplot2`. If `Rscript` is not on PATH on Windows, use the full executable path, for example:

```powershell
& "C:\Program Files\R\R-4.4.3\bin\Rscript.exe" .\Analysis\frame_engagement_regression\topic_engagement_regression.R
```

## Data Files

The main data files currently used by the project are:

```text
Datasets/yt-greenland.csv      Raw scraped data
Datasets/gl-cl.csv             Cleaned data used as topic-modeling input
Analysis/Topic_modeling/gl-cl-w-topics.csv
                               Topic-modeling output with topic labels
Datasets/final_dataset.csv     Main analysis dataset with topic and frame columns
Datasets/deleted_1.csv         First-stage deletion log
Datasets/deleted_2.csv         Final-filtering deletion log
Datasets/deleted_total.csv     Combined deletion log
```

`Datasets/final_dataset.csv` is the main input for most analysis and table scripts.

## Scraping

Create a `.env` file in the repository root with one or more API keys:

```text
YOUTUBE_API_KEY=your_key_here
YOUTUBE_API_KEY_2=optional_second_key
YOUTUBE_API_KEY_3=optional_third_key
```

Configure date ranges, search terms, quotas, and refresh behavior in `config.yaml`, then run:

```powershell
python yt_scraper.py
```

The scraper writes CSV output under `Datasets/`, using the configured search keywords to build the filename.

## Main Pipeline

### 1. Initial Filtering

The current repository contains `Datasets/gl-cl.csv` as the cleaned input to topic modeling. The helper script below writes the first deletion log:

```powershell
python Analysis/initial_filtering.py --input-csv Datasets/yt-greenland.csv
```

Output:

```text
Datasets/deleted_1.csv
```

### 2. Topic Modeling

Run BERTopic over the cleaned title data:

```powershell
python Analysis/Topic_modeling/title_bertopic_modeling.py
```

Default input:

```text
Datasets/gl-cl.csv
```

Default outputs:

```text
Analysis/Topic_modeling/gl-cl-w-topics.csv
Analysis/Topic_modeling/gl-cl-topic-assignments.csv
Analysis/Topic_modeling/gl-cl-topic-results.txt
```

### 3. Final Filtering

Apply topic, term, channel, and video-ID exclusions:

```powershell
python Analysis/final_filtering_and_frame_assignment.py
```

Default input:

```text
Analysis/Topic_modeling/gl-cl-w-topics.csv
```

Default outputs:

```text
Datasets/final_dataset.csv
Datasets/deleted_2.csv
Datasets/deleted_total.csv
```

Note: the script will call `Analysis/assign_frames_to_final.py` if that file is present. In the current working tree, `final_dataset.csv` already contains the `frame` column used by downstream analyses.

## Analysis Scripts

Run these from the repository root.

### Frame Distribution Over Time

```powershell
python Analysis/frame_distribution_over_time/frame_prevalence_over_time.py
```

Output:

```text
Analysis/frame_distribution_over_time/frame_distribution_over_time_monthly.png
```

### Geopolitical Subframe Analysis

```powershell
python Analysis/geopolitical_frame_analysis/assign_geopolitical_subframes.py
python Analysis/geopolitical_frame_analysis/export_geopolitical_topic_results.py
python Analysis/geopolitical_frame_analysis/top_geopolitical_channels_by_subscribers.py
python Analysis/geopolitical_frame_analysis/subframe_distribution_over_time/subframe_prevalence_over_time.py
```

Key outputs include:

```text
Analysis/geopolitical_frame_analysis/geopolitical_frame_videos_with_subframes.csv
Analysis/geopolitical_frame_analysis/geopolitical_subframe_breakdown.csv
Analysis/geopolitical_frame_analysis/geopolitical_topic_results_by_subframe.txt
Analysis/geopolitical_frame_analysis/top_geopolitical_channels_by_subscribers.csv
Analysis/geopolitical_frame_analysis/subframe_distribution_over_time/geopolitical_subframe_distribution_over_time_latest.png
```

### Regression Analysis

```powershell
& "C:\Program Files\R\R-4.4.3\bin\Rscript.exe" .\Analysis\frame_engagement_regression\topic_engagement_regression.R
```

Outputs:

```text
Analysis/frame_engagement_regression/frame-engagement-regression-coefficients.csv
Analysis/frame_engagement_regression/frame-engagement-regression-presentable-a4.png
Analysis/frame_engagement_regression/frame-engagement-regression-coefficients-presentable-a4.png
```

To print the full model results:

```powershell
& "C:\Program Files\R\R-4.4.3\bin\Rscript.exe" .\Analysis\frame_engagement_regression\all_model_results\print_all_model_results.R
```

### Precision And Recall

```powershell
python Analysis/precision_and_recall/make_precision_recall_samples.py
python Analysis/precision_and_recall/calculate_precision_recall.py
```

Outputs:

```text
Analysis/precision_and_recall/precision_sample_final_videos.xlsx
Analysis/precision_and_recall/recall_sample_deleted_videos.xlsx
Analysis/precision_and_recall/precision_recall_results.txt
```

## Table Generation

All table scripts read `Datasets/final_dataset.csv` by default.

```powershell
python Tables/categorical_tables/dataset_totals_table.py
python Tables/categorical_tables/channel_country_summary_table.py
python Tables/categorical_tables/frame_breakdown_tables.py
python Tables/Descriptive_table/numeric_metadata_summary_table.py
python Tables/channel_country_tables/channel_country_by_frame_table.py
python Tables/channel_subscriber_distribution_by_frame/channel_subscribers_by_frame_distribution.py
python Tables/video_duration_distribution_by_frame/video_duration_by_frame_distribution.py
python Tables/frame_engagement_summary/frame_engagement_summary_table.py
```

Representative outputs:

```text
Tables/categorical_tables/gl-cl-dataset-totals-summary-google-docs.html
Tables/categorical_tables/gl-cl-channel-country-summary-google-docs.html
Tables/categorical_tables/gl-cl-frame-breakdown-summary.html
Tables/Descriptive_table/gl-cl-numeric-metadata-summary-google-docs.html
Tables/channel_country_tables/channel-country-by-frame-table.txt
Tables/channel_subscriber_distribution_by_frame/gl-cl-channel-subscribers-by-frame-distribution.png
Tables/video_duration_distribution_by_frame/gl-cl-video-duration-by-frame-distribution.png
Tables/frame_engagement_summary/frame-engagement-summary-table.html
```

## Filtering Flowchart

```powershell
python Flowchart_filtering_process/export_html_png.py
```

Outputs:

```text
Flowchart_filtering_process/filtering-flow-stacked.html
Flowchart_filtering_process/filtering-flow-stacked.png
```

## Data Flow Summary

```text
yt-greenland.csv
  -> initial filtering / stored cleaned file
gl-cl.csv
  -> title_bertopic_modeling.py
Analysis/Topic_modeling/gl-cl-w-topics.csv
  -> final_filtering_and_frame_assignment.py
final_dataset.csv
  -> frame distribution, geopolitical subframes, regressions, precision/recall, tables
```

## Notes

- Run scripts from the repository root unless a script explicitly says otherwise.
- Do not paste long R scripts into the R console line by line; run them as files with `Rscript` or source the complete file.
- Several generated outputs are kept in the repository because they are thesis figures, tables, or validation artifacts.
- The current `final_dataset.csv` is the canonical dataset for downstream analysis.
