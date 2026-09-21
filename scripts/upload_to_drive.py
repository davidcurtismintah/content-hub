import json
import os
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
]


def get_credentials():
    credentials_json = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]

    return service_account.Credentials.from_service_account_info(
        json.loads(credentials_json),
        scopes=SCOPES,
    )


def main():

    credentials = get_credentials()

    drive = build(
        "drive",
        "v3",
        credentials=credentials,
    )

    sheets = build(
        "sheets",
        "v4",
        credentials=credentials,
    )

    spreadsheet_id = os.environ[
        "CONTENT_SPREADSHEET_ID"
    ]

    video_folder_id = os.environ[
        "VIDEO_FOLDER_ID"
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

    for item in manifest:

        content_id = item["content_id"]
        row_number = item["row_number"]

        source_file = Path(
            item["source_file"]
        )

        video_file = Path(
            "work/output"
        ) / f"{source_file.stem}.mp4"

        if not video_file.exists():
            raise RuntimeError(
                f"Video not found: {video_file}"
            )

        print(
            f"Uploading video for {content_id}"
        )

        metadata = {
            "name": video_file.name,
            "parents": [video_folder_id],
        }

        media = MediaFileUpload(
            str(video_file),
            mimetype="video/mp4",
            resumable=True,
        )

        uploaded = drive.files().create(
            body=metadata,
            media_body=media,
            fields="id,name,webViewLink",
            supportsAllDrives=True,
        ).execute()

        video_id = uploaded["id"]

        video_url = (
            uploaded.get("webViewLink")
            or f"https://drive.google.com/file/d/{video_id}/view"
        )

        # I = VIDEO FILE
        sheets.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"CONTENT!I{row_number}",
            valueInputOption="RAW",
            body={
                "values": [
                    [video_url]
                ]
            },
        ).execute()

        # K = STATUS
        sheets.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"CONTENT!K{row_number}",
            valueInputOption="RAW",
            body={
                "values": [
                    ["VIDEO_CREATED"]
                ]
            },
        ).execute()

        print(
            f"Completed {content_id}"
        )

    print("Upload and sheet update complete.")


if __name__ == "__main__":
    main()