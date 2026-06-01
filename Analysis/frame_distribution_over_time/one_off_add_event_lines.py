"""One-off overlay of event markers on the latest monthly frame plot.

This script intentionally leaves frame_prevalence_over_time.py unchanged.
Delete this file and the generated *_with_events.png when the temporary plot
is no longer needed.
"""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


HERE = Path(__file__).resolve().parent
BASE_PNG = HERE / "frame_distribution_over_time_monthly_subframe_palette.png"
PERIOD_CSV = HERE / "frame_distribution_over_time_monthly_subframe_palette.csv"
OUTPUT_PNG = HERE / "frame_distribution_over_time_monthly_subframe_palette_with_numbered_events.png"

EVENTS = [
    ("2019-08-18", "First proposal"),
    ("2024-12-22", "Buying Greenland is absolute necessity"),
    ("2025-01-07", "Donald Trump Jr. visits Nuuk"),
    ("2025-03-04", "SOTU: obtain Greenland"),
    ("2025-12-22", 'Trump says US "has to have" Greenland'),
    ("2026-01-17", "January Greenland statements"),
    ("2026-02-21", "Hospital ship post"),
]
EVENT_MARKER_COLOR = (58, 58, 58, 255)
EVENT_BOX_FILL = (255, 255, 255, 245)
LABEL_X_OFFSETS = {
    2: -16,
    3: 16,
    5: -16,
    7: 16,
}
PALETTE = [
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
TOP_COUNT_AXIS_MAX = 1600.0
SHARE_AXIS_MAX = 0.85

Image.MAX_IMAGE_PIXELS = None


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


def read_periods(path: Path) -> list[str]:
    periods: set[str] = set()
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            period = (row.get("period") or "").strip()
            if period:
                periods.add(period)
    return sorted(periods)


def period_starts_year(period: str) -> bool:
    return period.endswith("-01") or period.endswith("-01/02")


def read_count_values(path: Path) -> tuple[list[str], dict[str, dict[str, float]]]:
    frames: list[str] = []
    values: dict[str, dict[str, float]] = {}
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            frame = (row.get("frame") or "").strip()
            period = (row.get("period") or "").strip()
            if not frame or not period:
                continue
            if frame not in values:
                frames.append(frame)
                values[frame] = {}
            values[frame][period] = float(row.get("count") or 0)
            values[frame][f"count:{period}"] = float(row.get("count") or 0)
            values[frame][f"prevalence:{period}"] = float(row.get("prevalence") or 0)
    return frames, values


def draw_top_frequency_panel(
    *,
    image: Image.Image,
    draw: ImageDraw.ImageDraw,
    periods: list[str],
    frames: list[str],
    values_by_frame: dict[str, dict[str, float]],
    scale: float,
    axis_left: float,
    axis_right: float,
    axis_top: float,
    axis_bottom: float,
) -> None:
    panel_font = load_font(round(255 * scale))
    tick_font = load_font(round(205 * scale))
    erase_top = axis_top - round(330 * scale)
    erase_left = max(0, axis_left - round(590 * scale))
    draw.rectangle(
        (erase_left, erase_top, image.width, axis_bottom + round(70 * scale)),
        fill=(255, 255, 255, 255),
    )

    draw.text((axis_left, axis_top - round(280 * scale)), "A. Frequency", fill="#111111", font=panel_font)
    draw.line([(axis_left, axis_top), (axis_left, axis_bottom)], fill="#333333", width=round(13 * scale))
    draw.line([(axis_left, axis_bottom), (axis_right, axis_bottom)], fill="#333333", width=round(13 * scale))

    for step in range(5):
        frac = step / 4
        y = axis_bottom - frac * (axis_bottom - axis_top)
        if step:
            draw.line([(axis_left, y), (axis_right, y)], fill="#e8e8e8", width=round(8 * scale))
        value = frac * TOP_COUNT_AXIS_MAX
        label = f"{value:.0f}"
        bbox = draw.textbbox((0, 0), label, font=tick_font)
        draw.text(
            (axis_left - round(62 * scale) - (bbox[2] - bbox[0]), y - round(50 * scale)),
            label,
            fill="#444444",
            font=tick_font,
        )

    x_spacing = (axis_right - axis_left) / max(len(periods) - 1, 1)
    for idx, period in enumerate(periods):
        x = axis_left + idx * x_spacing
        draw.line([(x, axis_bottom), (x, axis_bottom + round(24 * scale))], fill="#777777", width=round(8 * scale))
        if period_starts_year(period):
            draw.line([(x, axis_top), (x, axis_bottom + round(36 * scale))], fill="#d0d0d0", width=round(8 * scale))
            draw.line([(x, axis_bottom), (x, axis_bottom + round(42 * scale))], fill="#333333", width=round(8 * scale))

    for frame_idx, frame in enumerate(frames):
        color = PALETTE[frame_idx % len(PALETTE)]
        points: list[tuple[float, float]] = []
        for period_idx, period in enumerate(periods):
            x = axis_left + period_idx * x_spacing
            value = values_by_frame.get(frame, {}).get(period, 0.0)
            y = axis_bottom - (min(value, TOP_COUNT_AXIS_MAX) / TOP_COUNT_AXIS_MAX) * (axis_bottom - axis_top)
            points.append((x, y))
        if len(points) >= 2:
            draw.line(points, fill=color, width=round(40 * scale))


def draw_colored_series(
    *,
    draw: ImageDraw.ImageDraw,
    periods: list[str],
    frames: list[str],
    values_by_frame: dict[str, dict[str, float]],
    value_key: str,
    max_value: float,
    scale: float,
    axis_left: float,
    axis_right: float,
    axis_top: float,
    axis_bottom: float,
) -> None:
    x_spacing = (axis_right - axis_left) / max(len(periods) - 1, 1)
    for frame_idx, frame in enumerate(frames):
        color = PALETTE[frame_idx % len(PALETTE)]
        points: list[tuple[float, float]] = []
        for period_idx, period in enumerate(periods):
            x = axis_left + period_idx * x_spacing
            value = values_by_frame.get(frame, {}).get(f"{value_key}:{period}", 0.0)
            y = axis_bottom - (min(value, max_value) / max_value) * (axis_bottom - axis_top)
            points.append((x, y))
        if len(points) >= 2:
            draw.line(points, fill=color, width=round(40 * scale))


def draw_event_label(
    *,
    draw: ImageDraw.ImageDraw,
    x: float,
    label_text: str,
    label_center_y: float,
    label_offset_x: float,
    axis_left: float,
    axis_right: float,
    scale: float,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> None:
    bbox = draw.textbbox((0, 0), label_text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    box_width = max(text_width + round(22 * scale), round(82 * scale))
    box_height = max(text_height + round(34 * scale), round(118 * scale))
    half_width = box_width / 2
    half_height = box_height / 2
    box_center_x = min(max(x + label_offset_x, axis_left + half_width), axis_right - half_width)

    draw.rectangle(
        (
            box_center_x - half_width,
            label_center_y - half_height,
            box_center_x + half_width,
            label_center_y + half_height,
        ),
        fill=EVENT_BOX_FILL,
        outline=EVENT_MARKER_COLOR,
        width=max(2, round(3 * scale)),
    )
    draw.text(
        (
            box_center_x - (bbox[0] + bbox[2]) / 2,
            label_center_y - (bbox[1] + bbox[3]) / 2,
        ),
        label_text,
        fill=EVENT_MARKER_COLOR,
        font=font,
    )


def main() -> None:
    if not BASE_PNG.exists():
        raise FileNotFoundError(f"Base PNG not found: {BASE_PNG}")
    if not PERIOD_CSV.exists():
        raise FileNotFoundError(f"Period CSV not found: {PERIOD_CSV}")

    periods = read_periods(PERIOD_CSV)
    frames, values_by_frame = read_count_values(PERIOD_CSV)
    period_to_index = {period: idx for idx, period in enumerate(periods)}

    image = Image.open(BASE_PNG).convert("RGB")
    draw = ImageDraw.Draw(image, "RGBA")
    scale = image.width / 8200

    axis_left = 600 * scale
    axis_right = (600 + (8200 - 600 - 180)) * scale
    margin_top = 1850 * scale
    panel_gap = 520 * scale
    margin_bottom = 590 * scale
    panel_height = (image.height - margin_top - margin_bottom - panel_gap) / 2
    top_axis_top = margin_top
    top_axis_bottom = margin_top + panel_height
    bottom_axis_top = top_axis_bottom + panel_gap
    bottom_axis_bottom = bottom_axis_top + panel_height

    draw_top_frequency_panel(
        image=image,
        draw=draw,
        periods=periods,
        frames=frames,
        values_by_frame=values_by_frame,
        scale=scale,
        axis_left=axis_left,
        axis_right=axis_right,
        axis_top=top_axis_top,
        axis_bottom=top_axis_bottom,
    )

    x_spacing = (axis_right - axis_left) / max(len(periods) - 1, 1)
    font = load_font(round(118 * scale))
    line_width = max(4, round(7 * scale))
    label_center_y = top_axis_top + round(108 * scale)

    for event_idx, (date_string, label) in enumerate(EVENTS):
        event_date = datetime.strptime(date_string, "%Y-%m-%d")
        period = f"{event_date.year}-{event_date.month:02d}"
        if period not in period_to_index:
            continue

        x = axis_left + period_to_index[period] * x_spacing
        label_text = str(event_idx + 1)

        draw.line([(x, top_axis_top), (x, top_axis_bottom)], fill=EVENT_MARKER_COLOR, width=line_width)
        draw.line([(x, bottom_axis_top), (x, bottom_axis_bottom)], fill=EVENT_MARKER_COLOR, width=line_width)
        draw_event_label(
            draw=draw,
            x=x,
            label_text=label_text,
            label_center_y=label_center_y,
            label_offset_x=LABEL_X_OFFSETS.get(event_idx + 1, 0) * scale,
            axis_left=axis_left,
            axis_right=axis_right,
            scale=scale,
            font=font,
        )

    draw_colored_series(
        draw=draw,
        periods=periods,
        frames=frames,
        values_by_frame=values_by_frame,
        value_key="count",
        max_value=TOP_COUNT_AXIS_MAX,
        scale=scale,
        axis_left=axis_left,
        axis_right=axis_right,
        axis_top=top_axis_top,
        axis_bottom=top_axis_bottom,
    )
    draw_colored_series(
        draw=draw,
        periods=periods,
        frames=frames,
        values_by_frame=values_by_frame,
        value_key="prevalence",
        max_value=SHARE_AXIS_MAX,
        scale=scale,
        axis_left=axis_left,
        axis_right=axis_right,
        axis_top=bottom_axis_top,
        axis_bottom=bottom_axis_bottom,
    )

    for event_idx, (date_string, label) in enumerate(EVENTS):
        event_date = datetime.strptime(date_string, "%Y-%m-%d")
        period = f"{event_date.year}-{event_date.month:02d}"
        if period not in period_to_index:
            continue

        x = axis_left + period_to_index[period] * x_spacing
        label_text = str(event_idx + 1)
        draw_event_label(
            draw=draw,
            x=x,
            label_text=label_text,
            label_center_y=label_center_y,
            label_offset_x=LABEL_X_OFFSETS.get(event_idx + 1, 0) * scale,
            axis_left=axis_left,
            axis_right=axis_right,
            scale=scale,
            font=font,
        )

    image.save(OUTPUT_PNG, dpi=(1200, 1200))
    print(f"Wrote {OUTPUT_PNG.resolve()}")


if __name__ == "__main__":
    main()
