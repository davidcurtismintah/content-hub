import json
import os
from datetime import datetime, timedelta, timezone

from google.oauth2 import service_account
from googleapiclient.discovery import build


SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
]


def get_drive_service():
    credentials = service_account.Credentials.from_service_account_info(
        json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]),
        scopes=SCOPES,
    )

    return build(
        "drive",
        "v3",
        credentials=credentials,
        cache_discovery=False,
    )


def get_sheets_service():
    credentials = service_account.Credentials.from_service_account_info(
        json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]),
        scopes=SCOPES,
    )

    return build(
        "sheets",
        "v4",
        credentials=credentials,
        cache_discovery=False,
    )


def get_settings(sheets):
    spreadsheet_id = os.environ["CONTENT_SPREADSHEET_ID"]

    result = sheets.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range="SETTINGS!A:B",
    ).execute()

    settings = {}

    for row in result.get("values", []):
        if len(row) >= 2:
            settings[str(row[0]).strip()] = str(row[1]).strip()

    return settings


def get_publications(sheets):
    spreadsheet_id = os.environ["CONTENT_SPREADSHEET_ID"]

    result = sheets.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range="PUBLICATIONS!A:K",
    ).execute()

    return result.get("values", [])


def get_content(sheets):
    spreadsheet_id = os.environ["CONTENT_SPREADSHEET_ID"]

    result = sheets.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range="CONTENT!A:K",
    ).execute()

    return result.get("values", [])


def delete_drive_file(drive, file_id, description):
    if not file_id:
        return

    try:
        drive.files().delete(fileId=file_id).execute()
        print(f"Deleted {description}: {file_id}")
    except Exception as error:
        print(
            f"Could not delete {description} {file_id}: {error}"
        )


def main():
    drive = get_drive_service()
    sheets = get_sheets_service()

    settings = get_settings(sheets)

    enabled = settings.get(
        "CLEANUP_ENABLED",
        "FALSE"
    ).upper() == "TRUE"

    if not enabled:
        print("Drive cleanup is disabled.")
        return

    try:
        retention_hours = int(
            settings.get(
                "CLEANUP_RETENTION_HOURS",
                "48"
            )
        )
    except ValueError:
        retention_hours = 48

    cutoff = datetime.now(timezone.utc) - timedelta(
        hours=retention_hours
    )

    print(
        "Cleanup retention:",
        retention_hours,
        "hours"
    )

    print(
        "Deleting files published before:",
        cutoff.isoformat()
    )

    publications = get_publications(sheets)
    content_rows = get_content(sheets)

    if len(publications) < 2:
        print("No publication records.")
        return

    if len(content_rows) < 2:
        print("No content records.")
        return

    # Build a map of CONTENT ID → most recent successful publication.
    published_content = {}

    for row in publications[1:]:
        if len(row) < 8:
            continue

        content_id = str(row[0]).strip()
        status = str(row[6]).strip()

        if status != "PUBLISHED":
            continue

        date_value = str(row[2]).strip()
        time_value = str(row[3]).strip()

        if not content_id or not date_value:
            continue

        try:
            if time_value:
                published_at = datetime.strptime(
                    date_value + " " + time_value,
                    "%Y-%m-%d %H:%M"
                ).replace(tzinfo=timezone.utc)
            else:
                published_at = datetime.strptime(
                    date_value,
                    "%Y-%m-%d"
                ).replace(tzinfo=timezone.utc)
        except ValueError:
            print(
                "Could not parse publication date for",
                content_id,
                date_value,
                time_value,
            )
            continue

        if (
            content_id not in published_content
            or published_at > published_content[content_id]
        ):
            published_content[content_id] = published_at

    deleted = 0

    for row in content_rows[1:]:
        if len(row) < 11:
            continue

        content_id = str(row[0]).strip()

        if not content_id:
            continue

        if content_id not in published_content:
            continue

        published_at = published_content[content_id]

        if published_at > cutoff:
            continue

        drive_file_id = str(row[2]).strip()
        video_file = str(row[8]).strip()

        # Do not delete anything unless the publication is safely
        # beyond the retention period.
        if drive_file_id:
            delete_drive_file(
                drive,
                drive_file_id,
                f"source image for {content_id}"
            )
            deleted += 1

        # VIDEO FILE may contain a Drive URL rather than a raw ID.
        # Extract the Drive file ID when possible.
        video_file_id = ""

        if "/file/d/" in video_file:
            try:
                video_file_id = video_file.split("/file/d/")[1].split("/")[0]
            except Exception:
                video_file_id = ""

        if video_file_id:
            delete_drive_file(
                drive,
                video_file_id,
                f"video for {content_id}"
            )
            deleted += 1

    print("Cleanup complete.")
    print("Files deleted:", deleted)


if __name__ == "__main__":
    main()
