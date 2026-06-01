import argparse
import csv
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


DATE_RE = re.compile(r"^\s*(\d{4})-(\d{2})-(\d{2})")
PERIOD_LABELS = {
    "01/02": "Jan-Feb",
    "03/04": "Mar-Apr",
    "05/06": "May-Jun",
    "07/08": "Jul-Aug",
    "09/10": "Sep-Oct",
    "11/12": "Nov-Dec",
}

SUBFRAME_PALETTE = [
    (0, 76, 153),
    (230, 159, 0),
    (204, 0, 121),
    (0, 0, 0),
    (240, 228, 66),
    (86, 180, 233),
    (117, 112, 179),
    (213, 94, 0),
    (90, 90, 90),
    (0, 114, 178),
]

FRAME_COLORS = {
    "Nature/Tourism": (0, 114, 178),
    "Geopolitics": (178, 24, 43),
    "Knowledge/Facts": (0, 158, 115),
    "Indigenous Life": (204, 121, 167),
    "Climate Change": (230, 159, 0),
    "Nature and Tourism": (0, 114, 178),
    "Geopolitical and Strategic": (178, 24, 43),
    "Knowledge and Education": (0, 158, 115),
    "Local Cultures and Everyday life": (204, 121, 167),
    "Climate Change and Natural Disaster": (230, 159, 0),
    "Climate change and Natural Disaster": (230, 159, 0),
    "Climate change and natural disaster": (230, 159, 0),
}

FRAME_LABELS = {
    "Climate Change and Natural Disaster": "Climate Change",
    "Climate change and Natural Disaster": "Climate Change",
    "Climate change and natural disaster": "Climate Change",
    "Geopolitical and Strategic": "Geopolitics",
    "Knowledge and Education": "Knowledge/Facts",
    "Local Cultures and Everyday life": "Indigenous Life",
    "Nature and Tourism": "Nature/Tourism",
}


def extract_period(value: str | None, interval_months: int = 2) -> str | None:
    text = (value or "").strip()
    try:
        parsed = datetime.strptime(text[:10], "%Y-%m-%d")
    except ValueError:
        match = DATE_RE.match(text)
        if not match:
            return None
        year, month, day = match.groups()
        try:
            parsed = datetime(int(year), int(month), int(day))
        except ValueError:
            return None

    if interval_months == 1:
        return f"{parsed.year}-{parsed.month:02d}"
    if interval_months != 2:
        raise ValueError("Only 1- and 2-month intervals are supported.")

    period_start_month = ((parsed.month - 1) // interval_months) * interval_months + 1
    period_end_month = period_start_month + interval_months - 1
    return f"{parsed.year}-{period_start_month:02d}/{period_end_month:02d}"


def format_period_label(period: str) -> str:
    year, month_range = period.split("-", maxsplit=1)
    if "/" not in month_range:
        return f"{year}-{month_range}"
    return f"{year} {PERIOD_LABELS.get(month_range, month_range)}"


def period_starts_year(period: str) -> bool:
    return period.endswith("-01") or period.endswith("-01/02")


def frame_label(frame: str) -> str:
    return FRAME_LABELS.get(frame, frame)


def load_frame_period_counts(
    csv_path: Path,
    *,
    frame_column: str,
    date_column: str,
    interval_months: int = 2,
) -> tuple[dict[str, Counter[str]], Counter[str], int]:
    counts_by_period: dict[str, Counter[str]] = defaultdict(Counter)
    period_totals: Counter[str] = Counter()
    invalid_rows = 0

    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError("CSV appears empty or missing header.")
        for column in (frame_column, date_column):
            if column not in reader.fieldnames:
                raise ValueError(f"Column '{column}' not found. Available columns: {reader.fieldnames}")

        for row in reader:
            frame = frame_label((row.get(frame_column) or "").strip())
            period = extract_period(row.get(date_column), interval_months=interval_months)
            if not frame or period is None:
                invalid_rows += 1
                continue
            counts_by_period[period][frame] += 1
            period_totals[period] += 1

    if not counts_by_period:
        raise ValueError("No valid frame/date rows found in the CSV.")

    return counts_by_period, period_totals, invalid_rows


def choose_frames(
    counts_by_period: dict[str, Counter[str]],
    *,
    frames: list[str] | None,
    top_n: int,
) -> list[str]:
    if frames:
        return frames

    total_counts: Counter[str] = Counter()
    for period_counts in counts_by_period.values():
        total_counts.update(period_counts)
    return [frame for frame, _ in total_counts.most_common(max(top_n, 1))]


def build_rows(
    counts_by_period: dict[str, Counter[str]],
    period_totals: Counter[str],
    frames: list[str],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for period in sorted(counts_by_period):
        total_period = period_totals[period]
        for frame in frames:
            count = counts_by_period[period].get(frame, 0)
            prevalence = (count / total_period) if total_period else 0.0
            rows.append(
                {
                    "period": period,
                    "frame": frame,
                    "count": str(count),
                    "total_videos_in_period": str(total_period),
                    "prevalence": f"{prevalence:.6f}",
                }
            )
    return rows


def save_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["period", "frame", "count", "total_videos_in_period", "prevalence"],
        )
        writer.writeheader()
        writer.writerows(rows)


def save_multiplot(
    output_path: Path,
    *,
    periods: list[str],
    frames: list[str],
    rows: list[dict[str, str]],
    title: str = "",
    legend_title: str = "",
    count_panel_label: str = "A. Frequency",
    share_panel_label: str = "B. Share",
    palette: list[tuple[int, int, int]] | None = None,
) -> None:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as exc:
        raise SystemExit("Pillow is required. Install it with:\n  pip install Pillow") from exc

    def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        for font_name in (
            r"C:\Windows\Fonts\times.ttf",
            "times.ttf",
            "Times New Roman.ttf",
            "DejaVuSerif.ttf",
        ):
            try:
                return ImageFont.truetype(font_name, size=size)
            except OSError:
                continue
        return ImageFont.load_default()

    def text_width(text: str, font: ImageFont.FreeTypeFont | ImageFont.ImageFont) -> int:
        bbox = draw.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0]

    def wrap_text(
        text: str,
        font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        max_width: int,
    ) -> list[str]:
        words = text.split()
        lines: list[str] = []
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if current and text_width(candidate, font) > max_width:
                lines.append(current)
                current = word
            else:
                current = candidate
        if current:
            lines.append(current)
        return lines

    def nice_axis_max(max_value: float, metric: str) -> float:
        if metric == "prevalence":
            return max(0.05, min(1.0, ((max_value * 20).__ceil__()) / 20))
        if max_value <= 10:
            return 10.0
        magnitude = 10 ** (len(str(int(max_value))) - 1)
        step = magnitude / 2
        return ((max_value / step).__ceil__()) * step

    # Narrower portrait canvas for thesis placement, with heavier text and
    # strokes so the figure remains readable after scaling.
    width = 8200
    height = 10848
    margin_left = 600
    margin_right = 180
    margin_top = 1850
    margin_bottom = 590
    panel_gap = 520
    plot_width = width - margin_left - margin_right
    panel_height = (height - margin_top - margin_bottom - panel_gap) // 2
    top_panel_height = panel_height
    bottom_panel_height = panel_height

    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    title_font = load_font(350)
    panel_font = load_font(255)
    tick_font = load_font(205)
    axis_font = load_font(230)
    legend_font = load_font(205)
    legend_title_font = load_font(230)

    default_palette = [
        (0, 114, 178),
        (213, 94, 0),
        (0, 158, 115),
        (204, 121, 167),
        (230, 159, 0),
        (86, 180, 233),
        (120, 120, 120),
        (0, 0, 0),
        (160, 160, 160),
        (80, 80, 80),
    ]
    if palette is None:
        palette = [FRAME_COLORS.get(frame, default_palette[idx % len(default_palette)]) for idx, frame in enumerate(frames)]

    values_by_frame: dict[str, dict[str, dict[str, float]]] = defaultdict(lambda: defaultdict(dict))
    for row in rows:
        frame = row["frame"]
        period = row["period"]
        values_by_frame[frame][period]["count"] = float(row["count"])
        values_by_frame[frame][period]["prevalence"] = float(row["prevalence"])

    if title:
        draw.text((margin_left, 42), title, fill="black", font=title_font)

    def draw_y_axis(
        *,
        axis_left: float,
        axis_top: float,
        axis_right: float,
        axis_bottom: float,
        max_value: float,
        metric: str,
    ) -> None:
        draw.line([(axis_left, axis_top), (axis_left, axis_bottom)], fill="#333333", width=13)
        draw.line([(axis_left, axis_bottom), (axis_right, axis_bottom)], fill="#333333", width=13)
        for step in range(6):
            frac = step / 5
            y = axis_bottom - frac * (axis_bottom - axis_top)
            if step:
                draw.line([(axis_left, y), (axis_right, y)], fill="#e8e8e8", width=8)
            value = frac * max_value
            label = f"{value:.0%}" if metric == "prevalence" else f"{value:.0f}"
            bbox = draw.textbbox((0, 0), label, font=tick_font)
            draw.text((axis_left - 62 - (bbox[2] - bbox[0]), y - 50), label, fill="#444444", font=tick_font)

    def draw_x_axis(
        *,
        axis_left: float,
        axis_top: float,
        axis_right: float,
        axis_bottom: float,
        show_labels: bool,
    ) -> None:
        total_points = len(periods)
        x_spacing = (axis_right - axis_left) / max(total_points - 1, 1)

        for idx, period in enumerate(periods):
            x = axis_left + idx * x_spacing
            draw.line([(x, axis_bottom), (x, axis_bottom + 24)], fill="#777777", width=8)

            if not period_starts_year(period):
                continue

            year = period.split("-", maxsplit=1)[0]
            draw.line([(x, axis_top), (x, axis_bottom + 36)], fill="#d0d0d0", width=8)
            if show_labels:
                bbox = draw.textbbox((0, 0), year, font=tick_font)
                draw.text((x - (bbox[2] - bbox[0]) / 2, axis_bottom + 70), year, fill="#333333", font=tick_font)

        for idx, period in enumerate(periods):
            period = periods[idx]
            x = axis_left + idx * x_spacing
            if period_starts_year(period):
                draw.line([(x, axis_bottom), (x, axis_bottom + 42)], fill="#333333", width=8)

    def draw_panel(
        *,
        panel_index: int,
        metric: str,
        label: str,
    ) -> None:
        axis_left = margin_left
        axis_top = margin_top if panel_index == 0 else margin_top + top_panel_height + panel_gap
        axis_right = margin_left + plot_width
        panel_height = top_panel_height if panel_index == 0 else bottom_panel_height
        axis_bottom = axis_top + panel_height
        max_value = max(
            (values_by_frame[frame].get(period, {}).get(metric, 0.0) for frame in frames for period in periods),
            default=0.0,
        )
        max_value = nice_axis_max(max_value, metric)

        draw.text((axis_left, axis_top - 280), label, fill="#111111", font=panel_font)
        draw_y_axis(
            axis_left=axis_left,
            axis_top=axis_top,
            axis_right=axis_right,
            axis_bottom=axis_bottom,
            max_value=max_value,
            metric=metric,
        )
        draw_x_axis(
            axis_left=axis_left,
            axis_top=axis_top,
            axis_right=axis_right,
            axis_bottom=axis_bottom,
            show_labels=panel_index == 1,
        )
        x_spacing = (axis_right - axis_left) / max(len(periods) - 1, 1)
        for frame_idx, frame in enumerate(frames):
            color = palette[frame_idx % len(palette)]
            points: list[tuple[float, float]] = []
            for period_idx, period in enumerate(periods):
                x = axis_left + period_idx * x_spacing
                value = values_by_frame[frame].get(period, {}).get(metric, 0.0)
                y = axis_bottom - (min(value, max_value) / max_value) * (axis_bottom - axis_top)
                points.append((x, y))

            if len(points) >= 2:
                draw.line(points, fill=color, width=40)
            elif points:
                x, y = points[0]
                draw.ellipse((x - 30, y - 30, x + 30, y + 30), fill=color, outline=color)

        if panel_index == 1:
            axis_label = "Publication year"
            bbox = draw.textbbox((0, 0), axis_label, font=axis_font)
            draw.text(
                (axis_left + (axis_right - axis_left - (bbox[2] - bbox[0])) / 2, axis_bottom + 295),
                axis_label,
                fill="#333333",
                font=axis_font,
            )

    legend_x = margin_left
    legend_y = 220 if not title else 420
    if legend_title:
        draw.text((legend_x, legend_y), legend_title, fill="#111111", font=legend_title_font)
    item_top = legend_y + (260 if legend_title else 0)
    column_width = (width - margin_left - margin_right) // 2
    row_height = 460
    for idx, frame in enumerate(frames):
        color = palette[idx % len(palette)]
        column = idx % 2
        row = idx // 2
        x = legend_x + column * column_width
        y = item_top + row * row_height
        draw.line([(x, y + 78), (x + 300, y + 78)], fill=color, width=46)
        for line_idx, line in enumerate(wrap_text(frame_label(frame), legend_font, column_width - 460)):
            draw.text((x + 390, y + line_idx * 205), line, fill="#222222", font=legend_font)

    draw_panel(panel_index=0, metric="count", label=count_panel_label)
    draw_panel(panel_index=1, metric="prevalence", label=share_panel_label)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    high_res_image = image.resize((width * 2, height * 2), Image.Resampling.LANCZOS)
    high_res_image.save(output_path, dpi=(1200, 1200))
    image.save(output_path.with_name(f"{output_path.stem}_600dpi.tif"), dpi=(600, 600), compression="tiff_lzw")
    high_res_image.save(
        output_path.with_name(f"{output_path.stem}_1200dpi.tif"),
        dpi=(1200, 1200),
        compression="tiff_lzw",
    )
    image.save(output_path.with_suffix(".pdf"), "PDF", resolution=600.0)


def write_outputs(
    *,
    output_dir: Path,
    periods: list[str],
    frames: list[str],
    rows: list[dict[str, str]],
    output_prefix: str,
    palette: list[tuple[int, int, int]] | None = None,
) -> tuple[Path, Path, Path]:
    csv_out = output_dir / f"{output_prefix}.csv"
    plot_out = output_dir / f"{output_prefix}.png"
    pdf_out = output_dir / f"{output_prefix}.pdf"

    save_csv(csv_out, rows)
    save_multiplot(
        plot_out,
        periods=periods,
        frames=frames,
        rows=rows,
        palette=palette,
    )
    return csv_out, plot_out, pdf_out


def main() -> None:
    script_path = Path(__file__).resolve()
    script_dir = script_path.parent
    default_csv = script_path.parents[4] / "Datasets" / "gl-cl-w-topics-FINAL.csv"
    default_output_dir = script_dir

    parser = argparse.ArgumentParser(
        description="Plot frame frequency and distribution over time."
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
    parser.add_argument("--top-n", type=int, default=10, help="How many top frames to plot when --frames is not set.")
    parser.add_argument("--output-dir", type=Path, default=default_output_dir, help="Where to save outputs.")
    parser.add_argument(
        "--interval-months",
        type=int,
        choices=[1, 2],
        default=2,
        help="Number of months per period. Default: 2.",
    )
    parser.add_argument(
        "--palette",
        choices=["frame", "subframe"],
        default="frame",
        help="Color palette to use. Default: frame.",
    )
    parser.add_argument(
        "--output-prefix",
        default=None,
        help="Output filename prefix without extension. Default: standard filename for normal settings, descriptive filename otherwise.",
    )
    args = parser.parse_args()
    csv_path = args.csv.resolve()
    output_dir = args.output_dir.resolve()

    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    counts_by_period, period_totals, invalid_rows = load_frame_period_counts(
        csv_path,
        frame_column=args.frame_column,
        date_column=args.date_column,
        interval_months=args.interval_months,
    )
    frames = choose_frames(counts_by_period, frames=args.frames, top_n=args.top_n)
    rows = build_rows(counts_by_period, period_totals, frames)
    periods = sorted(counts_by_period)
    output_prefix = args.output_prefix
    if output_prefix is None:
        output_prefix = "frame_distribution_over_time_latest"
        if args.interval_months != 2 or args.palette != "frame":
            interval_label = "monthly" if args.interval_months == 1 else "two_month"
            output_prefix = f"frame_distribution_over_time_{interval_label}_{args.palette}_palette"
    palette = SUBFRAME_PALETTE if args.palette == "subframe" else None

    csv_out, plot_out, pdf_out = write_outputs(
        output_dir=output_dir,
        periods=periods,
        frames=frames,
        rows=rows,
        output_prefix=output_prefix,
        palette=palette,
    )

    print(f"Source CSV: {csv_path}")
    print(f"{args.interval_months}-month periods found: {len(periods)}")
    print(f"Rows with missing frame/date: {invalid_rows}")
    print(f"Frames plotted: {', '.join(frames)}")
    print(f"Palette: {args.palette}")
    print(f"Saved period CSV to: {csv_out}")
    print(f"Saved multiplot to: {plot_out}")
    print(f"Saved PDF to: {pdf_out}")


if __name__ == "__main__":
    main()
