import json
import os
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload


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

    spreadsheet_id = os.environ["CONTENT_SPREADSHEET_ID"]

    # Read CONTENT sheet.
    result = sheets.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range="CONTENT!A:K",
    ).execute()

    values = result.get("values", [])

    if len(values) < 2:
        print("No content found.")
        return

    headers = values[0]

    header_map = {
        header.strip(): index
        for index, header in enumerate(headers)
    }

    required = [
        "CONTENT ID",
        "DRIVE FILE ID",
        "CONTENT TYPE",
        "STATUS",
    ]

    for field in required:
        if field not in header_map:
            raise RuntimeError(
                f"Missing CONTENT column: {field}"
            )

    content_id_col = header_map["CONTENT ID"]
    drive_id_col = header_map["DRIVE FILE ID"]
    type_col = header_map["CONTENT TYPE"]
    status_col = header_map["STATUS"]

    source_dir = Path("work/source")
    source_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    manifest = []

    for row_number, row in enumerate(values[1:], start=2):

        # Make missing cells safe.
        row = row + [""] * (len(headers) - len(row))

        content_id = str(
            row[content_id_col]
        ).strip()

        drive_file_id = str(
            row[drive_id_col]
        ).strip()

        content_type = str(
            row[type_col]
        ).strip()

        status = str(
            row[status_col]
        ).strip()

        # Only process AI-ready images.
        if status != "AI_READY":
            continue

        if content_type != "IMAGE":
            continue

        if not drive_file_id:
            continue

        # Get Drive file metadata.
        file_info = drive.files().get(
            fileId=drive_file_id,
            fields="id,name,mimeType",
            supportsAllDrives=True,
        ).execute()

        file_name = file_info["name"]

        extension = Path(file_name).suffix.lower()

        if extension not in {
            ".jpg",
            ".jpeg",
            ".png",
            ".webp",
            ".gif",
        }:
            print(
                f"Skipping unsupported file: {file_name}"
            )
            continue

        local_name = (
            f"{content_id}{extension}"
        )

        local_path = source_dir / local_name

        request = drive.files().get_media(
            fileId=drive_file_id
        )

        with open(local_path, "wb") as output:

            downloader = MediaIoBaseDownload(
                output,
                request
            )

            done = False

            while not done:
                _, done = downloader.next_chunk()

        print(
            f"Downloaded: {file_name}"
        )

        manifest.append({
            "row_number": row_number,
            "content_id": content_id,
            "drive_file_id": drive_file_id,
            "source_file": str(local_path),
        })

    manifest_path = Path(
        "work/content_manifest.json"
    )

    manifest_path.write_text(
        json.dumps(
            manifest,
            indent=2
        ),
        encoding="utf-8"
    )

    print(
        f"Ready for video creation: "
        f"{len(manifest)}"
    )


if __name__ == "__main__":
    main()