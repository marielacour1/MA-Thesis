import hashlib
import os
import time
import csv
import datetime
import re
import requests
import yaml

# -------------------------
# 0) INDLÆS .env (simpel parser)
# -------------------------

def load_env_file():
    path = os.path.join(SCRIPT_DIR, ".env")
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key:
                # Overskriv evt. eksisterende env for at sikre .env vinder
                os.environ[key] = value

def debug_env_status():
    if API_KEYS:
        print(f".env OK: {len(API_KEYS)} API nøgle(r) tilgængelige")
    else:
        print(".env ikke læst eller YOUTUBE_API_KEY mangler")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
load_env_file()

# -------------------------
# 1) LOAD CONFIGURATION FROM YAML
# -------------------------

def load_config(path=None):
    if path is None:
        path = os.path.join(SCRIPT_DIR, "config.yaml")
    if not os.path.exists(path):
        raise SystemExit(f"Konfigurationsfil ikke fundet: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

CONFIG = load_config()

def _get_api_keys():
    keys = []
    base_key = os.getenv("YOUTUBE_API_KEY", "")
    if base_key and base_key.strip():
        keys.append(base_key.strip())

    numbered_keys = []
    for env_key, value in os.environ.items():
        match = re.fullmatch(r"YOUTUBE_API_KEY_(\d+)", env_key)
        if match and value and value.strip():
            numbered_keys.append((int(match.group(1)), value.strip()))

    numbered_keys.sort(key=lambda item: item[0])
    keys.extend(value for _, value in numbered_keys)
    return keys

API_KEYS = _get_api_keys()
_current_key_index = 0

SEARCH_KEYWORDS = CONFIG.get("search_keywords", ["greenland"])
MAX_VIDEOS = CONFIG.get("max_videos", 200)
MONTH = CONFIG.get("month")
DATE_FROM = CONFIG.get("date_from")
DATE_TO = CONFIG.get("date_to")
FETCH_COMMENTS = CONFIG.get("fetch_comments", False)
FETCH_DESCRIPTIONS = CONFIG.get("fetch_descriptions", False)
MIN_VIEWS = CONFIG.get("min_views", 0)
REFRESH_EXISTING = CONFIG.get("refresh_existing", False)

# -------------------------
# 2) HJÆLPEFUNKTIONER
# -------------------------

BASE_URL = "https://www.googleapis.com/youtube/v3"
CSV_HEADERS = [
    "video_id", "video_title", "video_description", "published_at",
    "duration", "view_count", "video_like_count", "comment_count", "channel_id", "channel_title",
    "channel_subscriber_count", "channel_video_count", "channel_country",
]


class QuotaExceededError(Exception):
    pass


class ApiKeyRejectedError(Exception):
    pass


def yt_get(endpoint, params):
    global _current_key_index
    if not API_KEYS:
        raise SystemExit("Manglende API key. Sæt YOUTUBE_API_KEY i miljøet.")
    last_quota_error = None
    last_key_error = None
    for i in range(_current_key_index, len(API_KEYS)):
        p = dict(params)
        p["key"] = API_KEYS[i]
        resp = requests.get(f"{BASE_URL}/{endpoint}", params=p, timeout=30)
        if resp.status_code == 403:
            try:
                err = resp.json()
                error_reason = err.get("error", {}).get("errors", [{}])[0].get("reason")
                error_details = err.get("error", {}).get("details", [])
                service_disabled = any(
                    detail.get("@type") == "type.googleapis.com/google.rpc.ErrorInfo"
                    and detail.get("reason") == "SERVICE_DISABLED"
                    for detail in error_details
                )
                if error_reason == "quotaExceeded":
                    last_quota_error = QuotaExceededError("YouTube API quota exceeded")
                    _current_key_index = i + 1
                    continue
                if error_reason == "accessNotConfigured" or service_disabled:
                    last_key_error = ApiKeyRejectedError("YouTube API key rejected because the API is disabled or not configured")
                    _current_key_index = i + 1
                    continue
            except (ValueError, IndexError):
                pass
            raise SystemExit(f"YouTube API fejl 403: {resp.text}")
        if resp.status_code != 200:
            raise SystemExit(f"YouTube API fejl {resp.status_code}: {resp.text}")
        _current_key_index = i
        return resp.json()
    if last_quota_error:
        raise last_quota_error
    if last_key_error:
        raise last_key_error
    raise SystemExit("Ingen gyldige API nøgler.")


def get_date_range():
    from_str = DATE_FROM.strip()[:10] if (DATE_FROM and DATE_FROM.strip()) else None
    to_str = DATE_TO.strip()[:10] if (DATE_TO and DATE_TO.strip()) else None
    if from_str and to_str:
        return (from_str, to_str)
    if MONTH and str(MONTH).strip():
        y, m = str(MONTH).strip()[:7].split("-")
        start = datetime.datetime(int(y), int(m), 1, tzinfo=datetime.UTC)
        if int(m) == 12:
            end = datetime.datetime(int(y) + 1, 1, 1, tzinfo=datetime.UTC) - datetime.timedelta(seconds=1)
        else:
            end = datetime.datetime(int(y), int(m) + 1, 1, tzinfo=datetime.UTC) - datetime.timedelta(seconds=1)
        return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")
    return (from_str or (datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=3650)).strftime("%Y-%m-%d")), (to_str or datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d"))


def get_progress_key_date_to(date_to_str):
    if DATE_TO and str(DATE_TO).strip():
        return date_to_str[:10]
    if MONTH and str(MONTH).strip():
        return str(MONTH).strip()[:7]
    return "today"


def get_progress_path(keywords, date_from_str, date_to_str):
    progress_to = get_progress_key_date_to(date_to_str)
    key = "|".join(sorted(k.strip() for k in keywords)) + f"|{date_from_str[:10]}|{progress_to}"
    h = hashlib.sha256(key.encode()).hexdigest()[:16]
    return os.path.join(SCRIPT_DIR, f"scraper_progress_{h}.txt")


def get_legacy_progress_path(keywords, date_from_str, date_to_str):
    key = "|".join(sorted(k.strip() for k in keywords)) + f"|{date_from_str[:10]}|{date_to_str[:10]}"
    h = hashlib.sha256(key.encode()).hexdigest()[:16]
    return os.path.join(SCRIPT_DIR, f"scraper_progress_{h}.txt")


def get_pending_path(progress_path):
    if not progress_path:
        return None
    return progress_path.replace("scraper_progress_", "pending_")


def read_progress_date(progress_path):
    if not progress_path or not os.path.exists(progress_path):
        return None
    try:
        with open(progress_path, "r", encoding="utf-8") as f:
            line = f.readline().strip()[:10]
            if line and len(line) == 10:
                datetime.datetime.strptime(line, "%Y-%m-%d")
                return line
    except (ValueError, OSError):
        pass
    return None


def write_progress_date(progress_path, date_str):
    if not progress_path:
        return
    try:
        with open(progress_path, "w", encoding="utf-8") as f:
            f.write(date_str[:10] + "\n")
    except OSError:
        pass


def apply_progress_resume(date_from_str, date_to_str, progress_path):
    last = read_progress_date(progress_path)
    if not last:
        return date_from_str, date_to_str
    try:
        last_dt = datetime.datetime.fromisoformat(last + "T00:00:00+00:00")
        resume_from = (last_dt + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        if resume_from > date_to_str:
            return None, date_to_str
        return resume_from, date_to_str
    except (ValueError, TypeError):
        return date_from_str, date_to_str


def date_range_windows(from_str, to_str, days_per_window=1):
    if not from_str or not from_str.strip():
        start = datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=3650)
    else:
        start = datetime.datetime.fromisoformat(from_str.strip()[:10] + "+00:00")
    if not to_str or not to_str.strip():
        end = datetime.datetime.now(datetime.UTC)
    else:
        end = datetime.datetime.fromisoformat(to_str.strip()[:10] + "+00:00")
    if start.tzinfo is None:
        start = start.replace(tzinfo=datetime.UTC)
    if end.tzinfo is None:
        end = end.replace(tzinfo=datetime.UTC)
    start = start.replace(hour=0, minute=0, second=0, microsecond=0)
    end = end.replace(hour=0, minute=0, second=0, microsecond=0)
    windows = []
    current = start
    while current <= end:
        window_end = min(current + datetime.timedelta(days=days_per_window - 1), end)
        windows.append((
            current.strftime("%Y-%m-%dT00:00:00Z"),
            window_end.strftime("%Y-%m-%dT23:59:59Z"),
        ))
        current = window_end + datetime.timedelta(days=1)
    return windows


SEARCH_FILENAME_PREFIX = "yt"


def keyword_to_filename(keyword):
    s = "".join(c if c.isalnum() or c in " -_" else "" for c in keyword.lower()).strip()
    return SEARCH_FILENAME_PREFIX + "-" + s.replace(" ", "-").replace("_", "-") + ".csv"


def keywords_to_filename(keywords):
    parts = []
    for k in keywords:
        s = "".join(c if c.isalnum() or c in " -_" else "" for c in k.lower()).strip()
        if s:
            parts.append(s.replace(" ", "-").replace("_", "-"))
    slug = "-".join(parts) if parts else "search"
    return f"{SEARCH_FILENAME_PREFIX}-{slug}.csv"


def search_videos_in_window(query, published_after, published_before):
    video_ids = []
    page_token = None
    while True:
        params = {
            "part": "id",
            "q": query,
            "type": "video",
            "order": "date",
            "publishedAfter": published_after,
            "publishedBefore": published_before,
            "maxResults": 50,
        }
        if page_token:
            params["pageToken"] = page_token
        data = yt_get("search", params)
        for item in data.get("items", []):
            vid = item.get("id", {}).get("videoId")
            if vid:
                video_ids.append(vid)
        page_token = data.get("nextPageToken")
        if not page_token:
            break
        time.sleep(0.1)
    video_ids.reverse()
    return video_ids


def get_video_details(video_ids):
    videos = []
    for i in range(0, len(video_ids), 50):
        chunk = video_ids[i:i+50]
        try:
            data = yt_get("videos", {
                "part": "snippet,statistics,contentDetails",
                "id": ",".join(chunk),
                "maxResults": 50,
            })
        except QuotaExceededError:
            return (videos, True)
        videos.extend(data.get("items", []))
        time.sleep(0.1)
    return (videos, False)


def get_channel_info(channel_ids):
    result = {}
    for i in range(0, len(channel_ids), 50):
        chunk = channel_ids[i:i+50]
        try:
            data = yt_get("channels", {
                "part": "statistics,snippet",
                "id": ",".join(chunk),
                "maxResults": 50,
            })
        except QuotaExceededError:
            return (result, True)
        for item in data.get("items", []):
            cid = item["id"]
            result[cid] = {
                "subscriber_count": item.get("statistics", {}).get("subscriberCount", ""),
                "video_count": item.get("statistics", {}).get("videoCount", ""),
                "country": item.get("snippet", {}).get("country", "") or "",
            }
        time.sleep(0.1)
    return (result, False)


def title_contains_any_keyword(title, keywords):
    title_lower = title.lower()
    return any(keyword.lower() in title_lower for keyword in keywords)


def duration_to_seconds(value):
    if not value:
        return ""
    match = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", value)
    if not match:
        return ""
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    return str(hours * 3600 + minutes * 60 + seconds)


def _filter_and_build_rows(videos, channel_info):
    filtered = [v for v in videos
        if title_contains_any_keyword(v.get("snippet", {}).get("title", ""), SEARCH_KEYWORDS)
        and int((v.get("statistics", {}).get("viewCount") or 0)) >= MIN_VIEWS]
    filtered.sort(key=lambda v: v.get("snippet", {}).get("publishedAt", ""))
    rows = []
    for v in filtered:
        snippet = v.get("snippet", {})
        stats = v.get("statistics", {})
        channel_id = snippet.get("channelId", "")
        info = channel_info.get(channel_id, {})
        rows.append([
            v.get("id", ""),
            snippet.get("title", ""),
            snippet.get("description", "") if FETCH_DESCRIPTIONS else "",
            snippet.get("publishedAt", ""),
            duration_to_seconds(v.get("contentDetails", {}).get("duration", "")),
            stats.get("viewCount", ""),
            stats.get("likeCount", ""),
            stats.get("commentCount", ""),
            channel_id,
            snippet.get("channelTitle", ""),
            info.get("subscriber_count", ""),
            info.get("video_count", ""),
            info.get("country", ""),
        ])
    return rows


def load_written_ids(output_path):
    out = set()
    if os.path.exists(output_path):
        with open(output_path, "r", encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                out.add(row.get("video_id", ""))
    return out


def write_videos_to_csv(videos, channel_info, output_path, existing_ids=None):
    if existing_ids is None:
        existing_ids = load_written_ids(output_path)
    rows_to_write = _filter_and_build_rows(videos, channel_info)
    rows_to_write = [r for r in rows_to_write if r[0] not in existing_ids]
    for r in rows_to_write:
        existing_ids.add(r[0])
    file_existed = os.path.exists(output_path)
    with open(output_path, "a" if file_existed else "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_existed:
            writer.writerow(CSV_HEADERS)
        writer.writerows(rows_to_write)
    return len(rows_to_write), file_existed, existing_ids


def _extract_row_date(row):
    published_at = (row.get("published_at") or "")[:10]
    if len(published_at) != 10:
        return None
    try:
        datetime.datetime.strptime(published_at, "%Y-%m-%d")
        return published_at
    except ValueError:
        return None


def prune_output_rows_for_refresh(output_path, date_from_str, date_to_str):
    if not os.path.exists(output_path):
        return 0
    kept_rows = []
    removed_count = 0
    with open(output_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row_date = _extract_row_date(row)
            if row_date and date_from_str <= row_date <= date_to_str:
                removed_count += 1
                continue
            kept_rows.append([row.get(header, "") for header in CSV_HEADERS])
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(CSV_HEADERS)
        writer.writerows(kept_rows)
    return removed_count


def save_pending_ids(pending_path, pending_ids):
    if not pending_path or not pending_ids:
        return False
    try:
        with open(pending_path, "w", encoding="utf-8") as f:
            f.write("\n".join(pending_ids))
        return True
    except OSError:
        return False


# -------------------------
# 3) MAIN
# -------------------------

def main():
    debug_env_status()
    if not API_KEYS:
        raise SystemExit("Manglende API key. Sæt YOUTUBE_API_KEY i miljøet.")

    configured_date_from_str, date_to_str = get_date_range()
    progress_path = get_progress_path(SEARCH_KEYWORDS, configured_date_from_str, date_to_str)
    legacy_progress_path = get_legacy_progress_path(SEARCH_KEYWORDS, configured_date_from_str, date_to_str)
    if not os.path.exists(progress_path) and os.path.exists(legacy_progress_path):
        progress_path = legacy_progress_path
    if REFRESH_EXISTING:
        date_from_str = configured_date_from_str
    else:
        date_from_str, date_to_str = apply_progress_resume(configured_date_from_str, date_to_str, progress_path)
    output_dir = (
        os.path.join(SCRIPT_DIR, "Datasets", "comments")
        if FETCH_COMMENTS
        else os.path.join(SCRIPT_DIR, "Datasets")
    )
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, keywords_to_filename(SEARCH_KEYWORDS))
    pending_path = get_pending_path(progress_path)

    if REFRESH_EXISTING:
        removed_count = prune_output_rows_for_refresh(output_path, configured_date_from_str, date_to_str)
        if removed_count:
            print(f"Refresh mode: fjernede {removed_count} eksisterende rækker i perioden {configured_date_from_str} til {date_to_str} før genindhentning.\n")
        if pending_path and os.path.exists(pending_path):
            try:
                os.remove(pending_path)
            except OSError:
                pass

    written_ids = load_written_ids(output_path)
    if not REFRESH_EXISTING and pending_path and os.path.exists(pending_path):
        with open(pending_path, "r", encoding="utf-8") as f:
            pending_ids = [line.strip() for line in f if line.strip()]
        if pending_ids:
            print(f"Processing {len(pending_ids)} video IDs from previous run (pending file found).\n")
            try:
                videos, _ = get_video_details(pending_ids)
            except ApiKeyRejectedError:
                save_pending_ids(pending_path, pending_ids)
                print("Pending IDs kunne ikke hentes, fordi de resterende API keys er deaktiverede eller ikke konfigurerede.\n")
                return
            channel_info = {}
            if videos:
                channel_ids_list = list({v.get("snippet", {}).get("channelId", "") for v in videos if v.get("snippet", {}).get("channelId")})
                if channel_ids_list:
                    channel_info, _ = get_channel_info(channel_ids_list)
                n, file_existed, written_ids = write_videos_to_csv(videos, channel_info, output_path, written_ids)
                print(f"Pending: {'Tilføjet' if file_existed else 'Gemte'} {n} rækker i {output_path}\n")
            try:
                os.remove(pending_path)
            except OSError:
                pass

    if date_from_str is None:
        print(f"Allerede ajour. Intet nyt at hente for perioden {configured_date_from_str} til {date_to_str}.\n")
        return

    print(f"Søgeord: {', '.join(SEARCH_KEYWORDS)}")
    print(f"Tidsrum: {date_from_str} til {date_to_str}" + (f" (month: {MONTH})" if MONTH else ""))
    print(f"Max videoer: {MAX_VIDEOS}")
    print(f"Minimum views: {MIN_VIEWS}")
    print(f"Hent kommentarer: {FETCH_COMMENTS}")
    print(f"Hent beskrivelser: {FETCH_DESCRIPTIONS}\n")

    def flush_batch(to_fetch, written_ids):
        while len(to_fetch) >= 50:
            batch = to_fetch[:50]
            to_fetch[:] = to_fetch[50:]
            videos, quota_hit = get_video_details(batch)
            if videos:
                channel_ids_list = list({v.get("snippet", {}).get("channelId", "") for v in videos if v.get("snippet", {}).get("channelId")})
                channel_info = {}
                if channel_ids_list:
                    channel_info, _ = get_channel_info(channel_ids_list)
                _, _, written_ids = write_videos_to_csv(videos, channel_info, output_path, written_ids)
            if quota_hit:
                fetched_ids = {v.get("id") for v in videos}
                to_fetch[:] = [vid for vid in batch if vid not in fetched_ids] + to_fetch
                return to_fetch, written_ids, True
        return to_fetch, written_ids, False

    seen = set()
    to_fetch = []
    last_completed_before = None
    windows = date_range_windows(date_from_str, date_to_str, days_per_window=1)
    print(f"Looper over {len(windows)} dage (1 dag per vindue) indtil max {MAX_VIDEOS} videoer\n")
    try:
        for keyword in SEARCH_KEYWORDS:
            if len(seen) >= MAX_VIDEOS:
                break
            print(f"Søger efter: {keyword}")
            for i, (after, before) in enumerate(windows):
                if len(seen) >= MAX_VIDEOS:
                    break
                chunk = search_videos_in_window(keyword, after, before)
                added = 0
                for vid in chunk:
                    if vid not in seen and len(seen) < MAX_VIDEOS:
                        seen.add(vid)
                        to_fetch.append(vid)
                        added += 1
                if chunk:
                    total = len(seen)
                    print(f"  Vindue {i+1}/{len(windows)} ({after[:10]}–{before[:10]}): +{len(chunk)} raw, +{added} nye, total {total}")
                to_fetch, written_ids, quota_during_flush = flush_batch(to_fetch, written_ids)
                last_completed_before = before
                write_progress_date(progress_path, before[:10])
                if quota_during_flush:
                    if save_pending_ids(pending_path, to_fetch):
                        print(f"\nQuota exceeded while fetching details. CSV updated so far. {len(to_fetch)} IDs saved to {pending_path}; run again to fetch and append.\n")
                    return
            print()
    except QuotaExceededError:
        print("\nYouTube API quota exceeded (all keys). Saving partial results.")
        if last_completed_before:
            write_progress_date(progress_path, last_completed_before[:10])
            print(f"Progress saved; next run resumes from {last_completed_before[:10]}.")
        if save_pending_ids(pending_path, to_fetch):
            print(f"CSV already has {len(written_ids)} videos. {len(to_fetch)} IDs saved to {pending_path}; run again to fetch and append.\n")
        return
    except ApiKeyRejectedError:
        print("\nAll remaining API keys were rejected because YouTube Data API v3 is disabled or not configured.")
        if last_completed_before:
            write_progress_date(progress_path, last_completed_before[:10])
            print(f"Progress saved; next run resumes from {last_completed_before[:10]}.")
        if save_pending_ids(pending_path, to_fetch):
            print(f"CSV already has {len(written_ids)} videos. {len(to_fetch)} IDs saved to {pending_path}; run again to fetch and append after fixing the API key.\n")
        return

    try:
        while to_fetch:
            batch = to_fetch[:50]
            to_fetch[:] = to_fetch[50:]
            videos, quota_hit = get_video_details(batch)
            if videos:
                channel_ids_list = list({v.get("snippet", {}).get("channelId", "") for v in videos if v.get("snippet", {}).get("channelId")})
                channel_info = {}
                if channel_ids_list:
                    channel_info, _ = get_channel_info(channel_ids_list)
                _, _, written_ids = write_videos_to_csv(videos, channel_info, output_path, written_ids)
            if quota_hit:
                fetched_ids = {v.get("id") for v in videos}
                to_fetch[:] = [vid for vid in batch if vid not in fetched_ids] + to_fetch
                if save_pending_ids(pending_path, to_fetch):
                    print(f"Quota exceeded on final flush. {len(to_fetch)} IDs saved to {pending_path}; run again to fetch and append.\n")
                return
    except ApiKeyRejectedError:
        if save_pending_ids(pending_path, to_fetch):
            print(f"Final flush stopped because the remaining API keys are disabled or not configured. {len(to_fetch)} IDs saved to {pending_path}.\n")
        return

    write_progress_date(progress_path, date_to_str)
    print(f"Færdig. {len(written_ids)} videoer i {output_path}")


if __name__ == "__main__":
    main()
