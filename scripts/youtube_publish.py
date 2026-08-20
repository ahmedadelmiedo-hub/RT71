"""Upload a prepared long video and companion Short to YouTube.

This utility performs no upload unless explicitly passed ``--execute``. The
OAuth credential file is intentionally restored from a GitHub secret at runtime
and is never written to the repository.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_package(path: Path) -> dict:
    package = json.loads(path.read_text(encoding="utf-8"))
    if not package.get("publishing", {}).get("enabled"):
        raise ValueError("publishing is disabled in the episode package")
    return package


def build_video_body(metadata: dict, description: str) -> dict:
    return {
        "snippet": {
            "title": metadata["title"],
            "description": description,
            "tags": metadata["tags"],
            "categoryId": metadata["category_id"],
            "defaultLanguage": metadata["default_language"],
        },
        "status": {
            "privacyStatus": metadata["privacy_status"],
            "selfDeclaredMadeForKids": metadata["self_declared_made_for_kids"],
            "containsSyntheticMedia": metadata["contains_synthetic_media"],
        },
    }


def upload_video(service, video_path: Path, body: dict, notify_subscribers: bool) -> str:
    from googleapiclient.http import MediaFileUpload

    request = service.videos().insert(
        part="snippet,status",
        body=body,
        media_body=MediaFileUpload(str(video_path), mimetype="video/mp4", chunksize=8 * 1024 * 1024, resumable=True),
        notifySubscribers=notify_subscribers,
    )
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"Upload progress: {int(status.progress() * 100)}%")
    return response["id"]


def publish(long_video: Path, short_video: Path, package: dict, credentials_path: Path) -> dict:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    credentials = Credentials.from_authorized_user_file(
        str(credentials_path),
        scopes=["https://www.googleapis.com/auth/youtube.upload"],
    )
    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
    if not credentials.valid:
        raise RuntimeError("YouTube OAuth credentials are invalid or cannot be refreshed")

    service = build("youtube", "v3", credentials=credentials, cache_discovery=False)
    long_details = package["long_video"]
    long_id = upload_video(
        service,
        long_video,
        build_video_body(long_details, long_details["description"]),
        notify_subscribers=long_details["notify_subscribers"],
    )
    long_url = f"https://www.youtube.com/watch?v={long_id}"
    short_details = package["short"]
    short_body = build_video_body(
        {
            **short_details,
            "category_id": long_details["category_id"],
            "default_language": long_details["default_language"],
            "self_declared_made_for_kids": long_details["self_declared_made_for_kids"],
            "contains_synthetic_media": long_details["contains_synthetic_media"],
        },
        short_details["description_template"].replace("{long_video_url}", long_url),
    )
    short_id = upload_video(service, short_video, short_body, notify_subscribers=False)
    return {
        "long_video_id": long_id,
        "long_video_url": long_url,
        "short_video_id": short_id,
        "short_video_url": f"https://www.youtube.com/watch?v={short_id}",
        "related_video_link_method": short_details["related_video_link_method"],
        "note": "The long-video URL is included in the Short description. Set YouTube Studio's Related Video field after upload to add the native Shorts-player link.",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Upload a prepared RT71 long video and companion Short to YouTube.")
    parser.add_argument("--long-video", type=Path, required=True)
    parser.add_argument("--short-video", type=Path, required=True)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--credentials", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--execute", action="store_true", help="Actually upload the two public videos.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    package = load_package(args.package)
    if not args.execute:
        print(json.dumps({"ready": True, "episode_id": package["episode_id"], "upload_performed": False}, ensure_ascii=False))
        return 0
    for artifact in (args.long_video, args.short_video, args.credentials):
        if not artifact.is_file():
            raise FileNotFoundError(f"required file not found: {artifact}")
    result = publish(args.long_video, args.short_video, package, args.credentials)
    args.result.parent.mkdir(parents=True, exist_ok=True)
    args.result.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
