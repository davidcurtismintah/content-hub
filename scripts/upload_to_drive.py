import base64
import json
import os
from pathlib import Path

import requests


def main():

    upload_url = os.environ[
        "VIDEO_UPLOAD_URL"
    ]

    upload_token = os.environ[
        "VIDEO_UPLOAD_TOKEN"
    ]

    manifest_path = Path(
        "work/content_manifest.json"
    )

    if not manifest_path.exists():
        raise RuntimeError(
            "content_manifest.json not found."
        )

    manifest = json.loads(
        manifest_path.read_text(
            encoding="utf-8"
        )
    )

    if not manifest:
        print(
            "No videos to upload."
        )
        return

    for item in manifest:

        content_id = item["content_id"]

        source_file = Path(
            item["source_file"]
        )

        video_file = (
            Path("work/output") /
            f"{source_file.stem}.mp4"
        )

        if not video_file.exists():
            raise RuntimeError(
                f"Video not found: {video_file}"
            )

        print(
            f"Uploading {video_file.name}"
        )

        file_bytes = video_file.read_bytes()

        encoded_file = base64.b64encode(
            file_bytes
        ).decode("ascii")

        payload = {
            "token": upload_token,
            "contentId": content_id,
            "fileName": video_file.name,
            "folderId": os.environ[
                "VIDEO_FOLDER_ID"
            ],
            "fileData": encoded_file,
        }

        response = requests.post(
            upload_url,
            json=payload,
            timeout=300
        )

        print(
            "Apps Script response:",
            response.text
        )

        if response.status_code != 200:
            raise RuntimeError(
                f"Upload failed with HTTP "
                f"{response.status_code}"
            )

        result = response.json()

        if not result.get("success"):
            raise RuntimeError(
                result.get(
                    "error",
                    "Unknown upload error"
                )
            )

        print(
            f"Uploaded {content_id}: "
            f"{result['fileUrl']}"
        )


if __name__ == "__main__":
    main()
