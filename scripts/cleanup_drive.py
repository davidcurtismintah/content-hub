import json
import os
import re
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from googleapiclient.discovery import build


GHANA_TZ = ZoneInfo("Africa/Accra")

YOUTUBE_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]


def get_drive_service():
    credentials = service_account.Credentials.from_service_account_info(
        json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]),
        scopes=[
            "https://www.googleapis.com/auth/drive",
        ],
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
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
        ],
    )

    return build(
        "sheets",
        "v4",
        credentials=credentials,
        cache_discovery=False,
    )


def get_youtube_service():
    credentials = Credentials(
        token=None,
        refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["YOUTUBE_CLIENT_ID"],
        client_secret=os.environ["YOUTUBE_CLIENT_SECRET"],
        scopes=YOUTUBE_SCOPES,
    )

    credentials.refresh(Request())

    return build(
        "youtube",
        "v3",
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


def parse_publication_time(date_value, time_value):
    if not date_value:
        return None

    if time_value:
        return datetime.strptime(
            f"{date_value} {time_value}",
            "%Y-%m-%d %H:%M",
        ).replace(tzinfo=GHANA_TZ)

    return datetime.strptime(
        date_value,
        "%Y-%m-%d",
    ).replace(tzinfo=GHANA_TZ)


def extract_drive_file_id(value):
    if not value:
        return ""

    value = str(value).strip()

    match = re.search(
        r"/file/d/([^/]+)",
        value,
    )

    if match:
        return match.group(1)

    match = re.search(
        r"[?&]id=([^&]+)",
        value,
    )

    if match:
        return match.group(1)

    # CONTENT!I stores the Drive file ID directly in the current
    # Apps Script upload flow, not a URL. Accept that form too.
    if re.fullmatch(r"[A-Za-z0-9_-]{10,}", value):
        return value

    return ""


def verify_youtube_public(youtube, video_id):
    result = youtube.videos().list(
        part="status",
        id=video_id,
    ).execute()

    items = result.get("items", [])

    if not items:
        return False

    privacy_status = (
        items[0]
        .get("status", {})
        .get("privacyStatus", "")
    )

    return privacy_status == "public"


def delete_drive_file(drive, file_id, description):
    if not file_id:
        return True

    try:
        drive.files().delete(
            fileId=file_id
        ).execute()

        print(
            f"Deleted {description}: {file_id}"
        )

        return True

    except Exception as error:
        print(
            f"Could not delete {description} "
            f"{file_id}: {error}"
        )

        return False


def mark_content_cleaned(
    sheets,
    row_number
):
    spreadsheet_id = os.environ[
        "CONTENT_SPREADSHEET_ID"
    ]

    sheets.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=f"CONTENT!K{row_number}",
        valueInputOption="RAW",
        body={
            "values": [
                ["CLEANED"]
            ]
        },
    ).execute()


def main():

    print(
        "Starting Content Hub Drive cleanup..."
    )

    sheets = get_sheets_service()
    drive = get_drive_service()
    youtube = get_youtube_service()

    settings = get_settings(sheets)

    cleanup_enabled = (
        settings
        .get("CLEANUP_ENABLED", "FALSE")
        .upper()
        == "TRUE"
    )

    if not cleanup_enabled:
        print(
            "Drive cleanup is disabled."
        )
        return

    try:
        retention_hours = int(
            settings.get(
                "CLEANUP_RETENTION_HOURS",
                "48",
            )
        )
    except ValueError:
        retention_hours = 48

    now = datetime.now(GHANA_TZ)

    cutoff = (
        now -
        timedelta(
            hours=retention_hours
        )
    )

    print(
        "Retention:",
        retention_hours,
        "hours"
    )

    print(
        "Cleanup cutoff:",
        cutoff.isoformat()
    )

    publications = get_publications(
        sheets
    )

    content_rows = get_content(
        sheets
    )

    if len(publications) < 2:
        print(
            "No publication records."
        )
        return

    if len(content_rows) < 2:
        print(
            "No content records."
        )
        return

    eligible = {}

    for row in publications[1:]:

        if len(row) < 9:
            continue

        content_id = str(
            row[0]
        ).strip()

        destination_id = str(
            row[1]
        ).strip()

        date_value = str(
            row[2]
        ).strip()

        time_value = str(
            row[3]
        ).strip()

        status = str(
            row[6]
        ).strip()

        video_id = str(
            row[7]
        ).strip()

        # YouTube only
        if destination_id != "YT-01":
            continue

        # Must have been successfully published
        if status != "PUBLISHED":
            continue

        if not content_id or not video_id:
            continue

        published_at = parse_publication_time(
            date_value,
            time_value
        )

        if not published_at:
            continue

        # Must be at least retention_hours old
        if published_at > cutoff:
            continue

        print()
        print(
            f"Checking YouTube publication "
            f"{video_id} for {content_id}"
        )

        # Final safety check
        if not verify_youtube_public(
            youtube,
            video_id
        ):
            print(
                "SKIP: YouTube video is not "
                "confirmed PUBLIC."
            )
            continue

        eligible[content_id] = True

    deleted_files = 0
    cleaned_items = 0

    for index, row in enumerate(
        content_rows[1:],
        start=2
    ):

        if len(row) < 11:
            continue

        content_id = str(
            row[0]
        ).strip()

        content_status = str(
            row[10]
        ).strip()

        if content_id not in eligible:
            continue

        if content_status == "CLEANED":
            continue

        source_file_id = str(
            row[2]
        ).strip()

        video_file_url = str(
            row[8]
        ).strip()

        video_file_id = extract_drive_file_id(
            video_file_url
        )

        print()
        print(
            f"Cleaning content: {content_id}"
        )

        all_successful = True

        if source_file_id:

            success = delete_drive_file(
                drive,
                source_file_id,
                f"source image for {content_id}"
            )

            if success:
                deleted_files += 1
            else:
                all_successful = False

        if video_file_id:

            success = delete_drive_file(
                drive,
                video_file_id,
                f"video for {content_id}"
            )

            if success:
                deleted_files += 1
            else:
                all_successful = False

        if all_successful:

            mark_content_cleaned(
                sheets,
                index
            )

            cleaned_items += 1

            print(
                f"Marked {content_id} as CLEANED."
            )

        else:

            print(
                f"{content_id} was not marked "
                "CLEANED because one or more "
                "files could not be deleted."
            )

    print()
    print(
        "Drive cleanup complete."
    )

    print(
        "Files deleted:",
        deleted_files
    )

    print(
        "Content items cleaned:",
        cleaned_items
    )


if __name__ == "__main__":

    try:
        main()

    except Exception as error:

        print()
        print(
            "Drive cleanup FAILED:"
        )

        print(
            str(error)
        )

        sys.exit(1)
