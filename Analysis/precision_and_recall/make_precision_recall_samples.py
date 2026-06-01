import argparse
import csv
import random
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape


SAMPLE_SIZE = 150
RANDOM_SEED = 20260514
YOUTUBE_WATCH_URL = "https://www.youtube.com/watch?v={video_id}"


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def video_row(row: dict[str, str]) -> dict[str, str]:
    return {
        "video_id": (row.get("video_id") or "").strip(),
        "video_title": (row.get("video_title") or "").strip(),
    }


def unique_video_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[str] = set()
    unique_rows = []
    for row in rows:
        video_id = row["video_id"]
        if not video_id or video_id in seen:
            continue
        seen.add(video_id)
        unique_rows.append(row)
    return unique_rows


def sample_rows(rows: list[dict[str, str]], sample_size: int, seed: int) -> list[dict[str, str]]:
    if len(rows) < sample_size:
        raise ValueError(f"Cannot sample {sample_size} rows from only {len(rows)} available rows.")
    rng = random.Random(seed)
    return rng.sample(rows, sample_size)


def deleted_review_pool(
    deleted_1_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    """Filter deleted videos to only include those NOT deleted for duplicate or greenland-only reasons."""
    rows = []
    for row in deleted_1_rows:
        category = (row.get("deletion_reason_category") or "").strip()
        # Exclude duplicates and greenland-only titles, keep all other deletion reasons
        if category in {"duplicate", "greenland_only_title"}:
            continue
        video_id = (row.get("video_id") or "").strip()
        if not video_id:
            continue
        rows.append(video_row(row))
    return unique_video_rows(rows)


def column_letter(index: int) -> str:
    letters = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


def inline_cell(row_index: int, column_index: int, value: str) -> str:
    cell_ref = f"{column_letter(column_index)}{row_index}"
    return (
        f'<c r="{cell_ref}" t="inlineStr">'
        f"<is><t>{escape(value)}</t></is>"
        "</c>"
    )


def worksheet_xml(rows: list[dict[str, str]]) -> tuple[str, list[tuple[str, str]]]:
    sheet_rows = [
        '<row r="1">'
        + inline_cell(1, 1, "Video ID")
        + inline_cell(1, 2, "Video title")
        + "</row>"
    ]
    hyperlinks = []

    for row_number, row in enumerate(rows, start=2):
        video_id = row["video_id"]
        video_title = row["video_title"]
        cell_ref = f"A{row_number}"
        hyperlinks.append((cell_ref, YOUTUBE_WATCH_URL.format(video_id=video_id)))
        sheet_rows.append(
            f'<row r="{row_number}">'
            + inline_cell(row_number, 1, video_id)
            + inline_cell(row_number, 2, video_title)
            + "</row>"
        )

    hyperlink_xml = ""
    if hyperlinks:
        hyperlink_xml = "<hyperlinks>" + "".join(
            f'<hyperlink ref="{cell_ref}" r:id="rId{index}"/>'
            for index, (cell_ref, _) in enumerate(hyperlinks, start=1)
        ) + "</hyperlinks>"

    xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <cols>
    <col min="1" max="1" width="16" customWidth="1"/>
    <col min="2" max="2" width="80" customWidth="1"/>
  </cols>
  <sheetData>
    {"".join(sheet_rows)}
  </sheetData>
  {hyperlink_xml}
</worksheet>
"""
    return xml, hyperlinks


def write_xlsx(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet_xml, hyperlinks = worksheet_xml(rows)
    hyperlink_rels = "\n".join(
        f'<Relationship Id="rId{index}" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink" '
        f'Target="{escape(url)}" TargetMode="External"/>'
        for index, (_, url) in enumerate(hyperlinks, start=1)
    )

    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as xlsx:
        xlsx.writestr(
            "[Content_Types].xml",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>
""",
        )
        xlsx.writestr(
            "_rels/.rels",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>
""",
        )
        xlsx.writestr(
            "xl/workbook.xml",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="Sample" sheetId="1" r:id="rId1"/>
  </sheets>
</workbook>
""",
        )
        xlsx.writestr(
            "xl/_rels/workbook.xml.rels",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>
""",
        )
        xlsx.writestr("xl/worksheets/sheet1.xml", sheet_xml)
        xlsx.writestr(
            "xl/worksheets/_rels/sheet1.xml.rels",
            f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
{hyperlink_rels}
</Relationships>
""",
        )


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    dataset_dir = script_dir.parents[1] / "Datasets"
    parser = argparse.ArgumentParser(
        description="Create precision and recall review samples with clickable YouTube links."
    )
    parser.add_argument("--sample-size", type=int, default=SAMPLE_SIZE)
    parser.add_argument("--seed", type=int, default=RANDOM_SEED)
    parser.add_argument("--final-csv", type=Path, default=dataset_dir / "final_dataset.csv")
    parser.add_argument("--deleted-1-csv", type=Path, default=dataset_dir / "deleted_1.csv")
    parser.add_argument("--output-dir", type=Path, default=script_dir)
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    final_rows = unique_video_rows([video_row(row) for row in read_csv_rows(args.final_csv)])
    deleted_1_rows = read_csv_rows(args.deleted_1_csv)
    deleted_pool = deleted_review_pool(deleted_1_rows)

    precision_sample = sample_rows(final_rows, args.sample_size, args.seed)
    recall_sample = sample_rows(deleted_pool, args.sample_size, args.seed + 1)

    precision_path = args.output_dir / "precision_sample_final_videos.xlsx"
    recall_path = args.output_dir / "recall_sample_deleted_videos.xlsx"
    write_xlsx(precision_path, precision_sample)
    write_xlsx(recall_path, recall_sample)

    print(f"Final dataset pool: {len(final_rows):,} videos")
    print(f"Deleted review pool: {len(deleted_pool):,} videos")
    print(f"Sample size: {args.sample_size:,}")
    print(f"Random seed: {args.seed}")
    print(f"Wrote precision sample: {precision_path.resolve()}")
    print(f"Wrote recall sample: {recall_path.resolve()}")


if __name__ == "__main__":
    main()
