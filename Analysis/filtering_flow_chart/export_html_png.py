"""Export the filtering-flow HTML figures to PNG."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
EXPORTS = {
    "flow": {
        "html": HERE / "filtering-flow-stacked.html",
        "png": HERE / "filtering-flow-stacked.png",
        "width": 715,
        "height": 710,
    },
    "frames": {
        "html": HERE / "filtering-frames-presentable.html",
        "png": HERE / "filtering-frames-presentable.png",
        "width": 772,
        "height": 190,
    },
}


def find_browser() -> Path:
    candidates = [
        shutil.which("msedge"),
        shutil.which("chrome"),
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return Path(candidate)
    raise RuntimeError("Could not find Microsoft Edge, Google Chrome, or Chromium.")


def make_screenshot_html(html_path: Path, profile_dir: Path) -> Path:
    html = html_path.read_text(encoding="utf-8")
    screenshot_css = """
  <style>
    html, body {
      background: #fff !important;
      margin: 0 !important;
      padding: 0 !important;
    }
    .page {
      width: 100vw !important;
      margin: 0 !important;
      padding: 0 !important;
    }
  </style>
"""
    output_path = profile_dir / f"{html_path.stem}-screenshot.html"
    output_path.write_text(html.replace("</head>", f"{screenshot_css}\n</head>", 1), encoding="utf-8")
    return output_path


def export_png(html_path: Path, png_path: Path, *, width: int, height: int, scale: float) -> None:
    browser = find_browser()
    html_path = html_path.resolve()
    png_path = png_path.resolve()
    png_path.parent.mkdir(parents=True, exist_ok=True)

    if not html_path.exists():
        raise FileNotFoundError(f"HTML input does not exist: {html_path}")

    with tempfile.TemporaryDirectory(prefix="filtering-flow-browser-", dir=png_path.parent) as profile:
        screenshot_html = make_screenshot_html(html_path, Path(profile))
        command = [
            str(browser),
            "--headless",
            "--disable-gpu",
            "--disable-crash-reporter",
            "--disable-crashpad",
            "--disable-dev-shm-usage",
            "--hide-scrollbars",
            f"--force-device-scale-factor={scale}",
            f"--user-data-dir={profile}",
            f"--window-size={width},{height}",
            f"--screenshot={png_path}",
            screenshot_html.as_uri(),
        ]
        result = subprocess.run(command, check=False, capture_output=True, text=True)

    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"PNG export failed with {browser.name}: {message}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export filtering-flow PNG figures.")
    parser.add_argument("--only", choices=sorted(EXPORTS), help="Export one figure instead of both.")
    parser.add_argument("--width", type=int, help="Override the viewport width in CSS pixels.")
    parser.add_argument("--scale", type=float, default=3, help="Pixel density multiplier.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    keys = [args.only] if args.only else EXPORTS
    try:
        for key in keys:
            export = EXPORTS[key]
            export_png(
                export["html"],
                export["png"],
                width=args.width or export["width"],
                height=export["height"],
                scale=args.scale,
            )
            print(f"Wrote {export['png'].resolve()}")
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
