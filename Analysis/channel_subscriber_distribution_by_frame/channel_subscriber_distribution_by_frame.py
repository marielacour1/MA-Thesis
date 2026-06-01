import csv
import math
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = Path(__file__).resolve().parents[2]
INPUT_CSV = PROJECT_DIR / "Datasets" / "gl-cl-w-topics-FINAL.csv"
OUTPUT_PNG = SCRIPT_DIR / "gl-cl-channel-subscriber-distribution-by-frame.png"
OUTPUT_STATS_TXT = SCRIPT_DIR / "gl-cl-channel-subscriber-descriptive-statistics-by-frame.txt"
FRAME_COLUMN = "frame"
CHANNEL_ID_COLUMN = "channel_id"
SUBSCRIBER_COLUMN = "channel_subscriber_count"

COLORS = {
    "Geopolitics": "#4C78A8",
    "Nature/Tourism": "#F58518",
    "Knowledge/Facts": "#54A24B",
    "Indigenous Life": "#B279A2",
    "Climate Change": "#E45756",
    "Geopolitical and Strategic": "#4C78A8",
    "Nature and Tourism": "#F58518",
    "Knowledge and Education": "#54A24B",
    "Local Cultures and Everyday life": "#B279A2",
    "Climate change and Natural Disaster": "#E45756",
}


def parse_subscribers(value: str | None) -> float | None:
    raw = (value or "").strip().replace(",", "").replace(" ", "")
    if not raw:
        return None
    try:
        subscribers = float(raw)
    except ValueError:
        return None
    if not math.isfinite(subscribers) or subscribers < 0:
        return None
    return subscribers


def percentile(values: list[float], p: float) -> float:
    if not values:
        raise ValueError("Cannot compute percentile of an empty list.")
    sorted_values = sorted(values)
    rank = (len(sorted_values) - 1) * p
    low = math.floor(rank)
    high = math.ceil(rank)
    if low == high:
        return sorted_values[low]
    weight = rank - low
    return sorted_values[low] * (1 - weight) + sorted_values[high] * weight


def mean(values: list[float]) -> float:
    if not values:
        raise ValueError("Cannot compute mean of an empty list.")
    return sum(values) / len(values)


def standard_deviation(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    avg = mean(values)
    variance = sum((value - avg) ** 2 for value in values) / (len(values) - 1)
    return math.sqrt(variance)


def middle_50_mean(values: list[float]) -> float:
    q1 = percentile(values, 0.25)
    q3 = percentile(values, 0.75)
    middle_values = [value for value in values if q1 <= value <= q3]
    if not middle_values:
        return mean(values)
    return mean(middle_values)


def descriptive_stats(values: list[float]) -> dict[str, float]:
    return {
        "n": float(len(values)),
        "mean": mean(values),
        "middle_50_mean": middle_50_mean(values),
        "sd": standard_deviation(values),
        "min": min(values),
        "q1": percentile(values, 0.25),
        "median": percentile(values, 0.50),
        "q3": percentile(values, 0.75),
        "p95": percentile(values, 0.95),
        "max": max(values),
    }


def load_subscribers_by_frame() -> dict[str, list[float]]:
    subscribers_by_channel_frame: dict[tuple[str, str], float] = {}

    with INPUT_CSV.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        required = (FRAME_COLUMN, CHANNEL_ID_COLUMN, SUBSCRIBER_COLUMN)
        missing = [column for column in required if column not in fieldnames]
        if missing:
            raise ValueError(f"Missing required columns: {', '.join(missing)}")

        for row in reader:
            frame = (row.get(FRAME_COLUMN) or "").strip()
            channel_id = (row.get(CHANNEL_ID_COLUMN) or "").strip()
            subscribers = parse_subscribers(row.get(SUBSCRIBER_COLUMN))
            if not frame or not channel_id or subscribers is None:
                continue
            subscribers_by_channel_frame[(frame, channel_id)] = subscribers

    subscribers_by_frame: dict[str, list[float]] = defaultdict(list)
    for (frame, _), subscribers in subscribers_by_channel_frame.items():
        subscribers_by_frame[frame].append(subscribers)

    if not subscribers_by_frame:
        raise ValueError("No valid frame/channel subscriber rows found.")
    return dict(subscribers_by_frame)


def make_log_bins(values: list[float], bin_count: int = 45) -> list[float]:
    shifted_values = [value + 1 for value in values]
    min_value = max(min(shifted_values), 1)
    max_value = max(shifted_values)
    if min_value == max_value:
        return [min_value * 0.9, max_value * 1.1]

    log_min = math.log10(min_value)
    log_max = math.log10(max_value)
    return [10 ** (log_min + (log_max - log_min) * i / bin_count) for i in range(bin_count + 1)]


def frame_order(subscribers_by_frame: dict[str, list[float]]) -> list[str]:
    counts = Counter({frame: len(subscribers) for frame, subscribers in subscribers_by_frame.items()})
    return [frame for frame, _ in counts.most_common()]


def load_fonts():
    font_specs = [
        ("arial.ttf", 44),
        ("arial.ttf", 26),
        ("arial.ttf", 22),
        ("arial.ttf", 18),
        ("arialbd.ttf", 22),
    ]
    fonts = []
    for family, size in font_specs:
        try:
            fonts.append(ImageFont.truetype(family, size))
        except OSError:
            fonts.append(ImageFont.load_default())
    return tuple(fonts)


def histogram_counts(values: list[float], bins: list[float]) -> list[int]:
    counts = [0] * (len(bins) - 1)
    shifted_values = [value + 1 for value in values]
    for value in shifted_values:
        for idx in range(len(bins) - 1):
            if bins[idx] <= value < bins[idx + 1]:
                counts[idx] += 1
                break
        else:
            if value == bins[-1]:
                counts[-1] += 1
    return counts


def histogram_percentages(values: list[float], bins: list[float]) -> list[float]:
    counts = histogram_counts(values, bins)
    total = len(values)
    if total == 0:
        return [0.0 for _ in counts]
    return [count / total * 100 for count in counts]


def format_count(value: float) -> str:
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M".replace(".0M", "M")
    if value >= 1_000:
        return f"{value / 1_000:.1f}k".replace(".0k", "k")
    return f"{value:.0f}"


def draw_dashed_line(
    draw: ImageDraw.ImageDraw,
    xy: tuple[float, float, float, float],
    *,
    fill: str,
    width: int,
    dash: int = 8,
    gap: int = 6,
) -> None:
    x0, y0, x1, y1 = xy
    if x0 != x1:
        raise ValueError("draw_dashed_line only supports vertical lines here.")

    y = y0
    while y < y1:
        y_end = min(y + dash, y1)
        draw.line((x0, y, x1, y_end), fill=fill, width=width)
        y = y_end + gap


def draw_panel(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    frame: str,
    subscribers: list[float],
    bins: list[float],
    max_percentage: float,
    fonts: tuple[ImageFont.ImageFont, ...],
) -> None:
    _, _, _, note_font, bold_font = fonts
    left, top, right, bottom = box
    plot_left = left + 66
    plot_top = top + 58
    plot_right = right - 22
    plot_bottom = bottom - 48
    plot_width = plot_right - plot_left
    plot_height = plot_bottom - plot_top

    color = COLORS.get(frame, "#6B7280")
    percentages = histogram_percentages(subscribers, bins)
    stats = descriptive_stats(subscribers)
    avg = stats["mean"]
    median = stats["median"]
    p95 = stats["p95"]
    shifted_mean = avg + 1
    shifted_median = median + 1
    log_min = math.log10(bins[0])
    log_max = math.log10(bins[-1])

    draw.text((left, top), frame, fill="#1f1f1f", font=bold_font)
    draw.text(
        (right - 230, top + 2),
        f"channels = {len(subscribers):,}\nmean = {format_count(avg)}\nmiddle 50 mean = {format_count(stats['middle_50_mean'])}\nmedian = {format_count(median)}\np95 = {format_count(p95)}",
        fill="#333333",
        font=note_font,
        spacing=3,
    )

    for frac in (0.25, 0.5, 0.75, 1.0):
        y = plot_bottom - plot_height * frac
        draw.line((plot_left, y, plot_right, y), fill="#E0E0E0", width=1)

    for idx, percentage in enumerate(percentages):
        x0 = plot_left + (math.log10(bins[idx]) - log_min) / (log_max - log_min) * plot_width
        x1 = plot_left + (math.log10(bins[idx + 1]) - log_min) / (log_max - log_min) * plot_width
        height = 0 if max_percentage == 0 else percentage / max_percentage * plot_height
        draw.rectangle(
            (x0, plot_bottom - height, max(x0 + 1, x1 - 1), plot_bottom),
            fill=color,
            outline="white",
        )

    median_x = plot_left + (math.log10(shifted_median) - log_min) / (log_max - log_min) * plot_width
    mean_x = plot_left + (math.log10(shifted_mean) - log_min) / (log_max - log_min) * plot_width
    draw_dashed_line(draw, (mean_x, plot_top, mean_x, plot_bottom), fill="#111111", width=2)
    draw.line((median_x, plot_top, median_x, plot_bottom), fill="#1f1f1f", width=2)

    draw.line((plot_left, plot_bottom, plot_right, plot_bottom), fill="#333333", width=1)
    draw.line((plot_left, plot_top, plot_left, plot_bottom), fill="#333333", width=1)

    y_labels = [(0, "0%"), (0.5, f"{max_percentage / 2:.0f}%"), (1, f"{max_percentage:.0f}%")]
    for frac, label in y_labels:
        y = plot_bottom - plot_height * frac
        draw.text((left + 4, y - 8), label, fill="#555555", font=note_font)

    tick_values = [0, 10, 100, 1_000, 10_000, 100_000, 1_000_000, 10_000_000]
    for tick in tick_values:
        shifted_tick = tick + 1
        if shifted_tick < bins[0] or shifted_tick > bins[-1]:
            continue
        x = plot_left + (math.log10(shifted_tick) - log_min) / (log_max - log_min) * plot_width
        draw.line((x, plot_bottom, x, plot_bottom + 5), fill="#333333", width=1)
        label = format_count(tick)
        bbox = draw.textbbox((0, 0), label, font=note_font)
        draw.text((x - (bbox[2] - bbox[0]) / 2, plot_bottom + 9), label, fill="#555555", font=note_font)

    legend_y = plot_top + 6
    draw_dashed_line(draw, (plot_right - 78, legend_y, plot_right - 78, legend_y + 20), fill="#111111", width=2)
    draw.text((plot_right - 66, legend_y - 4), "mean", fill="#333333", font=note_font)
    draw.line((plot_right - 78, legend_y + 31, plot_right - 78, legend_y + 51), fill="#1f1f1f", width=2)
    draw.text((plot_right - 66, legend_y + 21), "median", fill="#333333", font=note_font)


def save_subscriber_multiplot(subscribers_by_frame: dict[str, list[float]]) -> None:
    frames = frame_order(subscribers_by_frame)
    all_subscribers = [
        subscriber
        for subscribers in subscribers_by_frame.values()
        for subscriber in subscribers
    ]
    bins = make_log_bins(all_subscribers)
    max_percentage = max(
        max(histogram_percentages(subscribers, bins))
        for subscribers in subscribers_by_frame.values()
    )

    width, height = 1800, 1500
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    title_font, subtitle_font, small_font, _, _ = load_fonts()
    fonts = load_fonts()

    draw.text((70, 42), "Distribution of Channel Subscribers Across Frames", fill="#1f1f1f", font=title_font)
    draw.text(
        (70, 98),
        "Each channel is counted once per frame; subscriber counts use a log scale and y-values are percentages within each frame.",
        fill="#555555",
        font=small_font,
    )

    panel_width = 790
    panel_height = 380
    x_positions = [70, 930]
    y_positions = [175, 595, 1015]

    for idx, frame in enumerate(frames):
        row = idx // 2
        col = idx % 2
        box = (
            x_positions[col],
            y_positions[row],
            x_positions[col] + panel_width,
            y_positions[row] + panel_height,
        )
        draw_panel(draw, box, frame, subscribers_by_frame[frame], bins, max_percentage, fonts)

    draw.text((760, 1440), "Channel subscribers (log scale)", fill="#333333", font=subtitle_font)
    draw.text((18, 710), "Percent", fill="#333333", font=subtitle_font)

    OUTPUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    image.save(OUTPUT_PNG, dpi=(300, 300))


def build_descriptive_table(subscribers_by_frame: dict[str, list[float]]) -> str:
    rows = []
    for frame in frame_order(subscribers_by_frame):
        stats = descriptive_stats(subscribers_by_frame[frame])
        rows.append(
            {
                "Frame": frame,
                "Channels": f"{int(stats['n']):,}",
                "Mean": f"{stats['mean']:.2f}",
                "Middle 50 mean": f"{stats['middle_50_mean']:.2f}",
                "SD": f"{stats['sd']:.2f}",
                "Min": f"{stats['min']:.2f}",
                "Q1": f"{stats['q1']:.2f}",
                "Median": f"{stats['median']:.2f}",
                "Q3": f"{stats['q3']:.2f}",
                "P95": f"{stats['p95']:.2f}",
                "Max": f"{stats['max']:.2f}",
            }
        )

    columns = ["Frame", "Channels", "Mean", "Middle 50 mean", "SD", "Min", "Q1", "Median", "Q3", "P95", "Max"]
    widths = {
        column: max(len(column), *(len(row[column]) for row in rows))
        for column in columns
    }
    separator = "-" * (sum(widths.values()) + 3 * (len(columns) - 1))
    lines = [
        "Channel subscriber descriptive statistics by frame",
        "Middle 50 mean = mean after keeping only values from Q1 through Q3.",
        "Each channel is counted once per frame.",
        f"Input CSV: {INPUT_CSV}",
        "",
        separator,
        " | ".join(column.ljust(widths[column]) for column in columns),
        separator,
    ]
    for row in rows:
        lines.append(" | ".join(row[column].ljust(widths[column]) for column in columns))
    lines.append(separator)
    return "\n".join(lines) + "\n"


def save_descriptive_table(subscribers_by_frame: dict[str, list[float]]) -> str:
    table = build_descriptive_table(subscribers_by_frame)
    OUTPUT_STATS_TXT.write_text(table, encoding="utf-8")
    return table


def main() -> None:
    subscribers_by_frame = load_subscribers_by_frame()
    save_subscriber_multiplot(subscribers_by_frame)
    table = save_descriptive_table(subscribers_by_frame)

    print(f"Input CSV: {INPUT_CSV}")
    print(f"Saved subscriber multiplot to: {OUTPUT_PNG}")
    print(f"Saved descriptive statistics to: {OUTPUT_STATS_TXT}")
    print()
    print(table, end="")


if __name__ == "__main__":
    main()
