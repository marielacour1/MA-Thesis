import argparse
import csv
from collections import Counter
from pathlib import Path


DEFAULT_CATEGORICAL_COLUMNS = [
    "channel_country",
]

VARIABLE_LABELS = {
    "channel_country": "Channel country",
}

COUNTRY_NAMES = {
    "AE": "United Arab Emirates",
    "AF": "Afghanistan",
    "AM": "Armenia",
    "AQ": "Antarctica",
    "AR": "Argentina",
    "AT": "Austria",
    "AU": "Australia",
    "AZ": "Azerbaijan",
    "BA": "Bosnia and Herzegovina",
    "BD": "Bangladesh",
    "BE": "Belgium",
    "BG": "Bulgaria",
    "BH": "Bahrain",
    "BO": "Bolivia",
    "BR": "Brazil",
    "BY": "Belarus",
    "CA": "Canada",
    "CH": "Switzerland",
    "CL": "Chile",
    "CM": "Cameroon",
    "CN": "China",
    "CO": "Colombia",
    "CR": "Costa Rica",
    "CY": "Cyprus",
    "CZ": "Czechia",
    "DE": "Germany",
    "DK": "Denmark",
    "DO": "Dominican Republic",
    "DZ": "Algeria",
    "EC": "Ecuador",
    "EE": "Estonia",
    "EG": "Egypt",
    "ES": "Spain",
    "FI": "Finland",
    "FO": "Faroe Islands",
    "FR": "France",
    "GB": "United Kingdom",
    "GE": "Georgia",
    "GH": "Ghana",
    "GL": "Greenland",
    "GR": "Greece",
    "GT": "Guatemala",
    "GU": "Guam",
    "HK": "Hong Kong",
    "HR": "Croatia",
    "HU": "Hungary",
    "ID": "Indonesia",
    "IE": "Ireland",
    "IL": "Israel",
    "IN": "India",
    "IS": "Iceland",
    "IT": "Italy",
    "JM": "Jamaica",
    "JO": "Jordan",
    "JP": "Japan",
    "KE": "Kenya",
    "KH": "Cambodia",
    "KR": "South Korea",
    "KW": "Kuwait",
    "KZ": "Kazakhstan",
    "LB": "Lebanon",
    "LI": "Liechtenstein",
    "LK": "Sri Lanka",
    "LT": "Lithuania",
    "LU": "Luxembourg",
    "LV": "Latvia",
    "MA": "Morocco",
    "MD": "Moldova",
    "ME": "Montenegro",
    "MK": "North Macedonia",
    "MT": "Malta",
    "MX": "Mexico",
    "MY": "Malaysia",
    "NG": "Nigeria",
    "NI": "Nicaragua",
    "NL": "Netherlands",
    "NO": "Norway",
    "NP": "Nepal",
    "NZ": "New Zealand",
    "OM": "Oman",
    "PE": "Peru",
    "PH": "Philippines",
    "PK": "Pakistan",
    "PL": "Poland",
    "PT": "Portugal",
    "PY": "Paraguay",
    "QA": "Qatar",
    "RO": "Romania",
    "RS": "Serbia",
    "RU": "Russia",
    "RW": "Rwanda",
    "SA": "Saudi Arabia",
    "SE": "Sweden",
    "SG": "Singapore",
    "SI": "Slovenia",
    "SK": "Slovakia",
    "SN": "Senegal",
    "TH": "Thailand",
    "TN": "Tunisia",
    "TR": "Turkey",
    "TW": "Taiwan",
    "TZ": "Tanzania",
    "UA": "Ukraine",
    "UG": "Uganda",
    "US": "United States",
    "VG": "British Virgin Islands",
    "VN": "Vietnam",
    "ZA": "South Africa",
    "ZW": "Zimbabwe",
}

MISSING_LABEL = "Missing / not specified"
OTHER_LABEL = "Other"
OTHER_THRESHOLD_PERCENT = 1.0


def variable_label(column: str) -> str:
    return VARIABLE_LABELS.get(column, column.replace("_", " ").title())


def category_label(column: str, value: str) -> str:
    if column == "channel_country":
        return COUNTRY_NAMES.get(value, value)
    return value


def load_rows(csv_path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        if not fieldnames:
            raise ValueError("CSV appears empty or missing header.")
        return list(reader), fieldnames


def summarize_column(
    rows: list[dict[str, str]],
    column: str,
    other_threshold_percent: float,
) -> list[dict[str, str | int | float]]:
    counts: Counter[str] = Counter()
    for row in rows:
        value = (row.get(column) or "").strip()
        counts[value if value else MISSING_LABEL] += 1

    total_n = len(rows)
    missing_n = counts.get(MISSING_LABEL, 0)
    valid_n = total_n - missing_n
    other_n = 0
    grouped_counts: Counter[str] = Counter()

    for value, count in counts.items():
        percent_of_all = (count / total_n * 100) if total_n else 0.0
        if value != MISSING_LABEL and percent_of_all < other_threshold_percent:
            other_n += count
        else:
            grouped_counts[value] += count

    if other_n:
        grouped_counts[OTHER_LABEL] += other_n

    ordered_items = sorted(
        grouped_counts.items(),
        key=lambda item: (item[0] in {MISSING_LABEL, OTHER_LABEL}, -item[1], item[0]),
    )

    summary_rows = []
    for value, count in ordered_items:
        summary_rows.append(
            {
                "variable": column,
                "variable_label": variable_label(column),
                "category": category_label(column, value),
                "n": count,
                "percent_of_all": (count / total_n * 100) if total_n else 0.0,
                "percent_of_valid": (
                    (count / valid_n * 100)
                    if valid_n and value != MISSING_LABEL
                    else None
                ),
                "total_n": total_n,
                "valid_n": valid_n,
                "missing_n": missing_n,
            }
        )
    return summary_rows


def build_html_table(summary_rows: list[dict[str, str | int | float | None]], total_rows: int) -> str:
    html_rows = [
        "      <tr>"
        "<th>Variable</th>"
        "<th>Category</th>"
        "<th>n</th>"
        "<th>% of all videos</th>"
        "<th>% of valid values</th>"
        "</tr>"
    ]

    previous_variable = None
    for row in summary_rows:
        variable = str(row["variable_label"])
        category = str(row["category"])
        percent_valid = row["percent_of_valid"]
        percent_valid_text = "" if percent_valid is None else f"{float(percent_valid):.1f}%"
        html_rows.append(
            "      <tr>"
            f"<td>{variable if variable != previous_variable else ''}</td>"
            f"<td>{category}</td>"
            f"<td>{int(row['n']):,}</td>"
            f"<td>{float(row['percent_of_all']):.1f}%</td>"
            f"<td>{percent_valid_text}</td>"
            "</tr>"
        )
        previous_variable = variable

    html = """<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body { font-family: Arial, sans-serif; }
    table { border-collapse: collapse; }
    th, td { border: 1px solid #999; padding: 6px 9px; text-align: right; }
    th:first-child, td:first-child, th:nth-child(2), td:nth-child(2) { text-align: left; }
    th { background: #f2f2f2; }
    .note { margin-top: 12px; color: #555; }
  </style>
</head>
<body>
  <table>
"""
    html += "\n".join(html_rows)
    html += f"""
  </table>
  <p class="note">Notes: The table includes categorical variables collected directly from YouTube metadata and present in the final dataset. Total dataset size is {total_rows:,} videos. Blank country fields are counted as missing / not specified and excluded from % of valid values. Other groups non-missing categories that each account for less than 1.0% of all videos.</p>
</body>
</html>
"""
    return html


def write_google_docs_html(
    output_path: Path,
    summary_rows: list[dict[str, str | int | float | None]],
    total_rows: int,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(build_html_table(summary_rows, total_rows), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    default_csv = script_dir.parents[1] / "Datasets" / "gl-cl-w-topics-FINAL.csv"
    default_output = script_dir / "gl-cl-youtube-categorical-table-google-docs.html"

    parser = argparse.ArgumentParser(
        description="Save a Google Docs-ready table of YouTube-collected categorical variables."
    )
    parser.add_argument("--csv", type=Path, default=default_csv, help="Path to input CSV.")
    parser.add_argument(
        "--output",
        type=Path,
        default=default_output,
        help="Path to output HTML table.",
    )
    parser.add_argument(
        "--columns",
        nargs="+",
        default=None,
        help="Optional categorical columns to summarize. Default: channel_country.",
    )
    parser.add_argument(
        "--other-threshold-percent",
        type=float,
        default=OTHER_THRESHOLD_PERCENT,
        help="Group non-missing categories below this percent of all videos into Other. Default: 1.0.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    csv_path = args.csv.resolve()
    output_path = args.output.resolve()

    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    rows, fieldnames = load_rows(csv_path)
    columns = args.columns or DEFAULT_CATEGORICAL_COLUMNS
    missing_columns = [column for column in columns if column not in fieldnames]
    if missing_columns:
        raise ValueError("Missing selected categorical columns: " + ", ".join(missing_columns))

    summary_rows = []
    for column in columns:
        summary_rows.extend(
            summarize_column(
                rows,
                column,
                other_threshold_percent=max(args.other_threshold_percent, 0),
            )
        )

    write_google_docs_html(output_path, summary_rows, total_rows=len(rows))

    print(f"Dataset: {csv_path}")
    print(f"Rows: {len(rows):,}")
    print(f"Categorical columns summarized: {', '.join(columns)}")
    print(f"Saved Google Docs HTML table to: {output_path}")


if __name__ == "__main__":
    main()
