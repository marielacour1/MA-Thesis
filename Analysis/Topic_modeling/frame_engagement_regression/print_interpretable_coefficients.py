import csv
import math
from pathlib import Path


HERE = Path(__file__).resolve().parent
COEFFICIENTS_CSV = HERE / "frame-engagement-regression-coefficients.csv"
REFERENCE_FRAME = "Nature/Tourism"
OUTCOME_LABELS = {
    "log_views": "Views",
    "log_comments": "Comments",
    "log_likes": "Likes",
}


def parse_float(value: str) -> float | None:
    value = (value or "").strip()
    if not value or value.upper() == "NA":
        return None
    return float(value)


def pct_from_log_coef(value: float) -> float:
    return (math.exp(value) - 1) * 100


def fmt_pct(value: float | None, digits: int = 1) -> str:
    if value is None:
        return "NA"
    return f"{value:+.{digits}f}%"


def converted_effect(row: dict[str, str]) -> tuple[str, str]:
    estimate = parse_float(row["estimate"])
    ci_low = parse_float(row["ci_low"])
    ci_high = parse_float(row["ci_high"])
    if estimate is None or ci_low is None or ci_high is None:
        return "NA", "NA"

    if row["outcome"] in {"log_views", "log_comments", "log_likes"}:
        converted = pct_from_log_coef(estimate)
        converted_low = pct_from_log_coef(ci_low)
        converted_high = pct_from_log_coef(ci_high)
        return fmt_pct(converted), f"{fmt_pct(converted_low)} to {fmt_pct(converted_high)}"

    return "NA", "NA"


def main() -> None:
    if not COEFFICIENTS_CSV.exists():
        raise FileNotFoundError(f"Could not find coefficients CSV: {COEFFICIENTS_CSV}")

    with COEFFICIENTS_CSV.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    print("Interpretable Frame Differences in Engagement")
    print("=" * 52)
    print(f"Reference frame: {REFERENCE_FRAME}")
    print("")
    print("Conversion:")
    print("  log outcomes: (exp(coefficient) - 1) * 100 = percent difference")
    print("")

    for outcome, label in OUTCOME_LABELS.items():
        outcome_rows = [
            row
            for row in rows
            if row["outcome"] == outcome and row.get("is_reference", "").upper() == "FALSE"
        ]
        if not outcome_rows:
            continue

        print(label)
        print("-" * len(label))
        print(f"{'Frame':<18} {'Effect':>12}  {'95% CI':>26}")
        for row in outcome_rows:
            effect, ci = converted_effect(row)
            print(f"{row['frame']:<18} {effect:>12}  {ci:>26}")
        print("")


if __name__ == "__main__":
    main()
