import argparse
import csv
import re
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path

DATE_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})")

EVENTS = [
    ("2019-08-18", "First proposal"),
    ("2024-12-22", "Greenland is national security"),
    ("2025-03-04", "SOTU: obtain Greenland"),
    ("2026-01-03", "Miller posts 'SOON' Greenland"),
    ("2026-01-17", "Tariffs linked to Greenland"),
    ("2026-01-21", "Davos: negotiations, no force"),
    ("2026-02-21", "Hospital ship post"),
]

MIN_DATE = date(2019, 1, 1)


def load_font(size: int):
    try:
        from PIL import ImageFont
    except ImportError:
        return None

    for font_name in ("arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(font_name, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def parse_iso_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d").date()
    except ValueError:
        match = DATE_RE.match(value)
        if match:
            year, month, day = match.groups()
            try:
                return date(int(year), int(month), int(day))
            except ValueError:
                return None
        return None


def format_event_label(event_date_string: str, event_label: str) -> str:
    try:
        event_date = datetime.strptime(event_date_string, "%Y-%m-%d").date()
        return f"{event_date.strftime('%y-%m-%d')} {event_label}"
    except ValueError:
        return event_label


def load_frame_monthly_counts(
    csv_path: Path,
    *,
    frame_column: str,
    date_column: str,
    min_date: date,
) -> tuple[dict[date, Counter[str]], Counter[date], int]:
    counts_by_month: dict[date, Counter[str]] = defaultdict(Counter)
    totals_by_month: Counter[date] = Counter()
    invalid_rows = 0

    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError("CSV appears empty or missing header.")
        for column in (frame_column, date_column):
            if column not in reader.fieldnames:
                raise ValueError(f"Column '{column}' not found. Available columns: {reader.fieldnames}")

        for row in reader:
            frame = (row.get(frame_column) or "").strip()
            published_date = parse_iso_date(row.get(date_column))
            if not frame or published_date is None or published_date < min_date:
                invalid_rows += 1
                continue
            month_key = date(published_date.year, published_date.month, 1)
            counts_by_month[month_key][frame] += 1
            totals_by_month[month_key] += 1

    if not counts_by_month:
        raise ValueError("No valid frame/date rows found in the CSV.")

    return counts_by_month, totals_by_month, invalid_rows


def choose_frames(
    counts_by_date: dict[date, Counter[str]],
    *,
    frames: list[str] | None,
    top_n: int,
) -> list[str]:
    if frames:
        return frames
    total_counts: Counter[str] = Counter()
    for date_counts in counts_by_date.values():
        total_counts.update(date_counts)
    return [frame for frame, _ in total_counts.most_common(max(top_n, 1))]


def build_rows(
    counts_by_date: dict[date, Counter[str]],
    totals_by_date: Counter[date],
    frames: list[str],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for published_date in sorted(counts_by_date):
        total_for_date = totals_by_date[published_date]
        for frame in frames:
            count = counts_by_date[published_date].get(frame, 0)
            prevalence = (count / total_for_date) if total_for_date else 0.0
            rows.append(
                {
                    "date": published_date.isoformat(),
                    "frame": frame,
                    "count": str(count),
                    "total_videos_in_date": str(total_for_date),
                    "prevalence": f"{prevalence:.6f}",
                }
            )
    return rows


def save_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["date", "frame", "count", "total_videos_in_date", "prevalence"],
        )
        writer.writeheader()
        writer.writerows(rows)


def save_total_plot(
    output_path: Path,
    *,
    dates: list[date],
    totals: Counter[date],
    title: str,
    events: list[tuple[str, str]],
) -> None:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as exc:
        raise SystemExit("Pillow is required. Install it with:\n  pip install Pillow") from exc

    width = 1700
    height = 1150
    margin_left = 110
    margin_right = 180
    margin_top = 130
    margin_bottom = 110
    plot_width = width - margin_left - margin_right
    plot_height = height - margin_top - margin_bottom

    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    title_font = load_font(34)
    label_font = load_font(24)
    tick_font = load_font(20)
    event_font = load_font(18)

    max_value = max(totals.values(), default=0)
    max_value = max(max_value, 1)

    axis_left = margin_left
    axis_top = margin_top
    axis_right = margin_left + plot_width
    axis_bottom = margin_top + plot_height

    draw.text((margin_left, 26), title, fill="black", font=title_font)
    subtitle = "Total number of videos published each month."
    draw.text((margin_left, 72), subtitle, fill="#444444", font=tick_font)

    draw.line([(axis_left, axis_top), (axis_left, axis_bottom)], fill="#444444", width=2)
    draw.line([(axis_left, axis_bottom), (axis_right, axis_bottom)], fill="#444444", width=2)

    steps = 6
    for step in range(steps):
        frac = step / (steps - 1)
        y = axis_bottom - frac * plot_height
        draw.line([(axis_left, y), (axis_right, y)], fill="#e5e5e5", width=1)
        value = frac * max_value
        label = f"{value:.0f}"
        bbox = draw.textbbox((0, 0), label, font=tick_font)
        draw.text((axis_left - 14 - (bbox[2] - bbox[0]), y - 10), label, fill="#666666", font=tick_font)

    total_points = len(dates)
    x_spacing = plot_width / max(total_points - 1, 1)
    max_ticks = 12
    for tick_index in range(max_ticks):
        if total_points <= 1:
            break
        idx = round(tick_index * (total_points - 1) / (max_ticks - 1))
        tick_date = dates[idx]
        x = axis_left + idx * x_spacing
        draw.line([(x, axis_bottom), (x, axis_bottom + 6)], fill="#444444", width=1)
        label = tick_date.strftime("%Y-%m")
        bbox = draw.textbbox((0, 0), label, font=tick_font)
        draw.text((x - (bbox[2] - bbox[0]) / 2, axis_bottom + 18), label, fill="#444444", font=tick_font)

    def wrap_text(text: str, max_chars: int = 24) -> list[str]:
        parts = text.split()
        lines: list[str] = []
        current: list[str] = []
        current_len = 0
        for part in parts:
            part_len = len(part) + (1 if current else 0)
            if current and current_len + part_len > max_chars:
                lines.append(" ".join(current))
                current = [part]
                current_len = len(part)
            else:
                current.append(part)
                current_len += part_len
        if current:
            lines.append(" ".join(current))
        return lines[:3]

    for event_date_string, event_label in events:
        try:
            event_date = datetime.strptime(event_date_string, "%Y-%m-%d").date()
        except ValueError:
            continue
        month_key = date(event_date.year, event_date.month, 1)
        if month_key not in dates:
            continue
        x = axis_left + dates.index(month_key) * x_spacing
        draw.line([(x, axis_top), (x, axis_bottom)], fill="#999999", width=2)
        lines = wrap_text(event_label, max_chars=18)
        line_boxes = [draw.textbbox((0, 0), line, font=event_font) for line in lines]
        max_width = max((box[2] - box[0] for box in line_boxes), default=0)
        total_height = sum((box[3] - box[1] for box in line_boxes)) + 4 * max(0, len(lines) - 1)
        text_x = x - max_width / 2
        if text_x < axis_left:
            text_x = axis_left + 4
        elif text_x + max_width > axis_right:
            text_x = axis_right - max_width - 4
        text_y = axis_top - total_height - 14
        draw.rectangle(
            [
                (text_x - 4, text_y - 4),
                (text_x + max_width + 4, text_y + total_height + 4),
            ],
            fill="white",
        )
        for line_box, line in zip(line_boxes, lines):
            draw.text((text_x, text_y), line, fill="#333333", font=event_font)
            text_y += line_box[3] - line_box[1] + 4

    points: list[tuple[float, float]] = []
    for date_idx, published_date in enumerate(dates):
        x = axis_left + date_idx * x_spacing
        value = totals[published_date]
        y = axis_bottom - (value / max_value) * plot_height
        points.append((x, y))
    if len(points) >= 2:
        draw.line(points, fill="#1f77b4", width=7)
    for x, y in points:
        draw.ellipse((x - 6, y - 6, x + 6, y + 6), fill="#1f77b4", outline="#1f77b4")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path, dpi=(300, 300))


def save_line_plot(
    output_path: Path,
    *,
    dates: list[date],
    frames: list[str],
    rows: list[dict[str, str]],
    metric: str,
    title: str,
    events: list[tuple[str, str]],
) -> None:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as exc:
        raise SystemExit("Pillow is required. Install it with:\n  pip install Pillow") from exc

    width = 1700
    height = 2350
    margin_left = 115
    margin_right = 300
    margin_top = 170
    margin_bottom = 95
    panel_gap = 150
    panel_height = (height - margin_top - margin_bottom - panel_gap) / 2
    plot_width = width - margin_left - margin_right

    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    title_font = load_font(38)
    label_font = load_font(26)
    tick_font = load_font(20)
    legend_font = load_font(22)
    event_font = load_font(18)

    palette = [
        (31, 119, 180),
        (255, 127, 14),
        (44, 160, 44),
        (214, 39, 40),
        (148, 103, 189),
        (140, 86, 75),
        (227, 119, 194),
        (127, 127, 127),
        (188, 189, 34),
        (23, 190, 207),
    ]

    values_by_frame: dict[str, dict[date, float]] = defaultdict(dict)
    for row in rows:
        values_by_frame[row["frame"]][date.fromisoformat(row["date"])] = float(row[metric])

    max_value = max(
        (values_by_frame[frame].get(published_date, 0.0) for frame in frames for published_date in dates),
        default=0.0,
    )
    max_value = max(max_value, 1.0 if metric == "count" else 0.01)

    half = len(dates) // 2
    panels = [dates[:half], dates[half:]]
    draw.text((margin_left, 22), title, fill="black", font=title_font)
    subtitle = (
        "Each line shows monthly frame count for the selected frames."
        if metric == "count"
        else "Each line shows monthly frame prevalence (frame count / all videos that month)."
    )
    draw.text((margin_left, 74), subtitle, fill="#444444", font=label_font)

    def wrap_text(text: str, max_chars: int = 24) -> list[str]:
        parts = text.split()
        lines: list[str] = []
        current: list[str] = []
        current_len = 0
        for part in parts:
            part_len = len(part) + (1 if current else 0)
            if current and current_len + part_len > max_chars:
                lines.append(" ".join(current))
                current = [part]
                current_len = len(part)
            else:
                current.append(part)
                current_len += part_len
        if current:
            lines.append(" ".join(current))
        return lines[:3]

    def draw_panel(panel_index: int, panel_dates: list[date]) -> None:
        panel_top = margin_top + panel_index * (panel_height + panel_gap)
        panel_bottom = panel_top + panel_height
        axis_left = margin_left
        axis_right = margin_left + plot_width
        axis_top = panel_top
        axis_bottom = panel_bottom

        draw.line([(axis_left, axis_top), (axis_left, axis_bottom)], fill="#444444", width=2)
        draw.line([(axis_left, axis_bottom), (axis_right, axis_bottom)], fill="#444444", width=2)

        steps = 6
        for step in range(steps):
            frac = step / (steps - 1)
            y = axis_bottom - frac * panel_height
            draw.line([(axis_left, y), (axis_right, y)], fill="#e5e5e5", width=1)
            value = frac * max_value
            label_value = f"{value:.0%}" if metric == "prevalence" else f"{value:.0f}"
            bbox = draw.textbbox((0, 0), label_value, font=tick_font)
            draw.text((axis_left - 14 - (bbox[2] - bbox[0]), y - 10), label_value, fill="#666666", font=tick_font)

        total_points = len(panel_dates)
        x_spacing = plot_width / max(total_points - 1, 1)
        if panel_index == len(panels) - 1:
            max_ticks = 9
            for tick_index in range(max_ticks):
                if total_points <= 1:
                    break
                idx = round(tick_index * (total_points - 1) / (max_ticks - 1))
                tick_date = panel_dates[idx]
                x = axis_left + idx * x_spacing
                draw.line([(x, axis_bottom), (x, axis_bottom + 6)], fill="#444444", width=1)
                label_date = tick_date.strftime("%Y-%m")
                bbox = draw.textbbox((0, 0), label_date, font=tick_font)
                draw.text((x - (bbox[2] - bbox[0]) / 2, axis_bottom + 18), label_date, fill="#444444", font=tick_font)

        event_level = 0
        level_cycle = 3
        inside_event_cutoff = max(1, (len(events) * 3) // 4)
        pending_event_labels: list[tuple[float, float, float, float, list[tuple[tuple[int, int, int, int], str]]]] = []
        for event_index, (event_date_string, event_label) in enumerate(events):
            try:
                event_date = datetime.strptime(event_date_string, "%Y-%m-%d").date()
            except ValueError:
                continue
            month_key = date(event_date.year, event_date.month, 1)
            if month_key not in panel_dates:
                continue
            x = axis_left + panel_dates.index(month_key) * x_spacing
            draw.line([(x, axis_top), (x, axis_bottom)], fill="#999999", width=2)
            display_label = format_event_label(event_date_string, event_label)
            lines = wrap_text(display_label, max_chars=18)
            line_boxes = [draw.textbbox((0, 0), line, font=event_font) for line in lines]
            max_width = max((box[2] - box[0] for box in line_boxes), default=0)
            total_height = sum((box[3] - box[1] for box in line_boxes)) + 4 * max(0, len(lines) - 1)
            text_x = x - max_width / 2
            if text_x < axis_left:
                text_x = axis_left + 4
            elif text_x + max_width > axis_right:
                text_x = axis_right - max_width - 4

            level_offset = event_level * (total_height + 16)
            if event_index < inside_event_cutoff:
                text_y = axis_top + 14 + level_offset
            else:
                text_y = axis_top - total_height - 16 - level_offset
            text_lines: list[tuple[tuple[int, int, int, int], str]] = []
            current_text_y = text_y
            for line_box, line in zip(line_boxes, lines):
                text_lines.append((line_box, line))
                current_text_y += line_box[3] - line_box[1] + 4
            pending_event_labels.append(
                (text_x - 4, text_y - 4, text_x + max_width + 4, text_y + total_height + 4, text_lines)
            )
            event_level = (event_level + 1) % level_cycle

        for frame_idx, frame in enumerate(frames):
            color = palette[frame_idx % len(palette)]
            points: list[tuple[float, float]] = []
            for date_idx, published_date in enumerate(panel_dates):
                x = axis_left + date_idx * x_spacing
                value = values_by_frame[frame].get(published_date, 0.0)
                y = axis_bottom - (value / max_value) * panel_height
                points.append((x, y))
            if len(points) >= 2:
                draw.line(points, fill=color, width=6)
            for x, y in points:
                draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill=color, outline=color)

        for rect_left, rect_top, rect_right, rect_bottom, text_lines in pending_event_labels:
            draw.rectangle(
                [
                    (rect_left, rect_top),
                    (rect_right, rect_bottom),
                ],
                fill="white",
            )
            text_y = rect_top + 4
            text_x = rect_left + 4
            for line_box, line in text_lines:
                draw.text((text_x, text_y), line, fill="#333333", font=event_font)
                text_y += line_box[3] - line_box[1] + 4

    for panel_index, panel_dates in enumerate(panels):
        if panel_dates:
            draw_panel(panel_index, panel_dates)

    legend_x = margin_left + plot_width + 32
    legend_y = margin_top + 10
    draw.text((legend_x, legend_y - 34), "Frames", fill="black", font=label_font)
    for idx, frame in enumerate(frames):
        color = palette[idx % len(palette)]
        y = legend_y + idx * 42
        draw.line([(legend_x, y + 10), (legend_x + 32, y + 10)], fill=color, width=6)
        draw.text((legend_x + 36, y), frame, fill="#333333", font=legend_font)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path, dpi=(300, 300))


def write_outputs(
    *,
    csv_path: Path,
    output_dir: Path,
    frame_suffix: str,
    dates: list[date],
    frames: list[str],
    rows: list[dict[str, str]],
    totals: Counter[date],
    metric: str,
) -> tuple[Path, Path, Path]:
    csv_out = output_dir / f"{csv_path.stem}-frame-{metric}-by-month-{frame_suffix}.csv"
    plot_out = output_dir / f"{csv_path.stem}-frame-{metric}-by-month-{frame_suffix}.png"
    total_plot_out = output_dir / f"{csv_path.stem}-total-videos-by-month.png"

    save_csv(csv_out, rows)
    save_line_plot(
        plot_out,
        dates=dates,
        frames=frames,
        rows=rows,
        metric=metric,
        title=f"Frame {metric.title()} Over Time (Monthly, 2019+)",
        events=EVENTS,
    )
    save_total_plot(
        total_plot_out,
        dates=dates,
        totals=totals,
        title="Total Videos Over Time (Monthly, 2019+)",
        events=EVENTS,
    )
    return csv_out, plot_out, total_plot_out


def main() -> None:
    script_path = Path(__file__).resolve()
    script_dir = script_path.parent
    default_csv = script_path.parents[2] / "Creating_frames" / "gl-cl-w-topics-and-frames.csv"
    default_output_dir = script_dir

    parser = argparse.ArgumentParser(
        description="Plot monthly frame counts for 2019-present with annotated event markers."
    )
    parser.add_argument("--csv", type=Path, default=default_csv, help="Path to frame-annotated CSV.")
    parser.add_argument("--frame-column", default="frame", help="Frame column name.")
    parser.add_argument("--date-column", default="published_at", help="Publication date column name.")
    parser.add_argument(
        "--frames",
        nargs="+",
        default=None,
        help="Optional list of specific frame labels to plot. Default: use the top frames by overall size.",
    )
    parser.add_argument("--top-n", type=int, default=8, help="How many top frames to plot when --frames is not set.")
    parser.add_argument(
        "--metric",
        choices=["prevalence", "count"],
        default="count",
        help="Plot monthly prevalence share or raw counts.",
    )
    parser.add_argument("--output-dir", type=Path, default=default_output_dir, help="Where to save outputs.")

    args = parser.parse_args()
    csv_path = args.csv.resolve()
    output_dir = args.output_dir.resolve()

    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    counts_by_date, totals_by_date, invalid_rows = load_frame_monthly_counts(
        csv_path,
        frame_column=args.frame_column,
        date_column=args.date_column,
        min_date=MIN_DATE,
    )
    dates = sorted(counts_by_date)
    frames = choose_frames(counts_by_date, frames=args.frames, top_n=args.top_n)
    rows = build_rows(counts_by_date, totals_by_date, frames)

    frame_suffix = "selected" if args.frames else f"top{max(args.top_n, 1)}"
    csv_out, plot_out, total_plot_out = write_outputs(
        csv_path=csv_path,
        output_dir=output_dir,
        frame_suffix=frame_suffix,
        dates=dates,
        frames=frames,
        rows=rows,
        totals=totals_by_date,
        metric=args.metric,
    )

    print(f"Source CSV: {csv_path}")
    print(f"Dates included: {dates[0].isoformat()} through {dates[-1].isoformat()}")
    print(f"Rows with missing frame/date or before {MIN_DATE.isoformat()}: {invalid_rows}")
    print(f"Frames plotted: {', '.join(frames)}")
    print(f"Saved CSV to: {csv_out}")
    print(f"Saved frame plot to: {plot_out}")
    print(f"Saved total videos plot to: {total_plot_out}")


if __name__ == "__main__":
    main()
