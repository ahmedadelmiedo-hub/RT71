"""Finds the channel's best-performing publish hour from YouTube Analytics,
so the teaser can be scheduled exactly `lead_time_minutes_before_main`
minutes before that slot.

Requires a YouTube Data/Analytics OAuth token (see docs/personal-voice-xtts.md
sibling doc for the equivalent YouTube OAuth setup pattern already used in
the MoneyPrinterTurbo project — same client, different scope:
https://www.googleapis.com/auth/yt-analytics.readonly).

Output: prints an ISO-8601 datetime for the *next* teaser publish slot.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

try:
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
except ImportError:  # pragma: no cover - optional dependency at analysis time
    Credentials = None
    build = None


def fetch_views_by_hour(credentials_path: Path, channel_id: str, lookback_days: int = 28) -> dict[int, float]:
    """Returns {hour_of_day (0-23): average relative watch activity}."""
    if Credentials is None:
        raise RuntimeError(
            "google-api-python-client not installed. "
            "pip install -r requirements.txt first."
        )
    creds = Credentials.from_authorized_user_file(str(credentials_path))
    youtube_analytics = build("youtubeAnalytics", "v2", credentials=creds)

    end = dt.date.today()
    start = end - dt.timedelta(days=lookback_days)

    response = youtube_analytics.reports().query(
        ids=f"channel=={channel_id}",
        startDate=start.isoformat(),
        endDate=end.isoformat(),
        metrics="views",
        dimensions="elapsedVideoTimeRatio",  # placeholder-safe metric set
        sort="elapsedVideoTimeRatio",
    ).execute()

    # NOTE: YouTube Analytics does not expose a direct "views by hour of day"
    # dimension for arbitrary channels without the `traffic-source-hourly`
    # experimental report. In practice, most creators approximate this from
    # YouTube Studio's "When your viewers are on YouTube" chart (exported as
    # CSV) rather than the API. See fetch_from_studio_csv() below for that path.
    raise NotImplementedError(
        "Direct hourly-views API dimension is not generally available. "
        "Export the 'When your viewers are on YouTube' chart from YouTube "
        "Studio as CSV and use --studio-csv instead."
    )


def fetch_from_studio_csv(csv_path: Path) -> dict[int, float]:
    """Parses the CSV exported from YouTube Studio > Audience >
    'When your viewers are on YouTube'. Expected columns: Hour, Views (or
    similar localized headers) — adjust column names if YouTube changes them."""
    import csv

    hours: dict[int, float] = {}
    with csv_path.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            hour_key = next((k for k in row if "hour" in k.lower() or "ساعة" in k), None)
            value_key = next((k for k in row if k != hour_key), None)
            if hour_key is None or value_key is None:
                continue
            try:
                hour = int(row[hour_key])
                value = float(row[value_key])
            except ValueError:
                continue
            hours[hour] = value
    if not hours:
        raise ValueError(f"could not parse any hour/value rows from {csv_path}")
    return hours


def next_slot_for_hour(target_hour: int, timezone_offset_hours: int = 2) -> dt.datetime:
    """Returns the next upcoming datetime (UTC) matching target_hour in the
    channel's local timezone (default UTC+2, adjust for the audience)."""
    now_utc = dt.datetime.utcnow()
    now_local = now_utc + dt.timedelta(hours=timezone_offset_hours)
    candidate_local = now_local.replace(hour=target_hour, minute=0, second=0, microsecond=0)
    if candidate_local <= now_local:
        candidate_local += dt.timedelta(days=1)
    return candidate_local - dt.timedelta(hours=timezone_offset_hours)


def compute_teaser_slot(best_hour: int, lead_minutes: int, timezone_offset_hours: int = 2) -> dict:
    main_slot = next_slot_for_hour(best_hour, timezone_offset_hours)
    teaser_slot = main_slot - dt.timedelta(minutes=lead_minutes)
    return {
        "main_episode_publish_utc": main_slot.isoformat(),
        "teaser_publish_utc": teaser_slot.isoformat(),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compute next teaser publish slot from peak-viewing hour.")
    parser.add_argument("--studio-csv", type=Path, help="CSV exported from YouTube Studio audience chart")
    parser.add_argument("--config", type=Path, default=Path("config/channel_profile.json"))
    parser.add_argument("--timezone-offset", type=int, default=2, help="Audience local UTC offset, e.g. 2 for Cairo")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    cfg = json.loads(args.config.read_text(encoding="utf-8"))["teaser"]

    if args.studio_csv:
        hours = fetch_from_studio_csv(args.studio_csv)
        best_hour = max(hours, key=hours.get)
    else:
        raise SystemExit(
            "Provide --studio-csv exported from YouTube Studio "
            "(Audience > When your viewers are on YouTube)."
        )

    result = compute_teaser_slot(best_hour, cfg["lead_time_minutes_before_main"], args.timezone_offset)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
