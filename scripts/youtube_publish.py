import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]

YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"


def get_credentials():
    client_id = os.environ["YOUTUBE_CLIENT_ID"]
    client_secret = os.environ["YOUTUBE_CLIENT_SECRET"]
    refresh_token = os.environ["YOUTUBE_REFRESH_TOKEN"]

    credentials = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=SCOPES,
    )

    credentials.refresh(Request())

    return credentials


def get_youtube_service():
    credentials = get_credentials()

    return build(
        YOUTUBE_API_SERVICE_NAME,
        YOUTUBE_API_VERSION,
        credentials=credentials,
    )


def get_spreadsheet_data():
    from google.oauth2 import service_account

    credentials_json = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]

    credentials = (
        service_account.Credentials.from_service_account_info(
            json.loads(credentials_json),
            scopes=[
                "https://www.googleapis.com/auth/drive",
                "https://www.googleapis.com/auth/spreadsheets",
            ],
        )
    )

    sheets = build(
        "sheets",
        "v4",
        credentials=credentials,
    )

    spreadsheet_id = os.environ["CONTENT_SPREADSHEET_ID"]

    result = sheets.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range="PUBLICATIONS!A:K",
    ).execute()

    return sheets, spreadsheet_id, result.get("values", [])


def get_settings(sheets, spreadsheet_id):
    result = sheets.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range="SETTINGS!A:B",
    ).execute()

    values = result.get("values", [])

    settings = {}

    for row in values[1:]:
        if not row:
            continue

        key = str(row[0]).strip()

        if not key:
            continue

        value = str(row[1]).strip() if len(row) > 1 else ""

        settings[key] = value

    return settings


def get_content_data(sheets, spreadsheet_id):
    result = sheets.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range="CONTENT!A:K",
    ).execute()

    values = result.get("values", [])

    if not values:
        return {}

    headers = values[0]

    header_map = {
        header.strip(): index
        for index, header in enumerate(headers)
    }

    content = {}

    for row in values[1:]:
        row = row + [""] * (len(headers) - len(row))

        content_id = str(
            row[header_map["CONTENT ID"]]
        ).strip()

        if not content_id:
            continue

        content[content_id] = {
            "video_file": str(
                row[header_map["VIDEO FILE"]]
            ).strip(),
            "status": str(
                row[header_map["STATUS"]]
            ).strip(),
        }

    return content


def update_publication_row(
    sheets,
    spreadsheet_id,
    row_number,
    values,
):
    sheets.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=f"PUBLICATIONS!G{row_number}:K{row_number}",
        valueInputOption="RAW",
        body={
            "values": [values]
        },
    ).execute()


def build_publish_datetime(
    date_string,
    time_string,
    timezone_name,
):
    timezone = ZoneInfo(timezone_name)

    local_datetime = datetime.strptime(
        f"{date_string} {time_string}",
        "%Y-%m-%d %H:%M",
    )

    local_datetime = local_datetime.replace(
        tzinfo=timezone
    )

    return local_datetime.isoformat()


def upload_video(
    youtube,
    video_path,
    title,
    description,
    category_id,
    publish_at,
):
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "categoryId": category_id,
        },
        "status": {
            "privacyStatus": "private",
            "publishAt": publish_at,
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(
        str(video_path),
        mimetype="video/mp4",
        resumable=True,
    )

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    response = None

    while response is None:
        status, response = request.next_chunk()

        if status:
            progress = int(
                status.progress() * 100
            )
            print(
                f"Upload progress: {progress}%"
            )

    return response


def create_comment(
    youtube,
    video_id,
    comment_text,
):
    body = {
        "snippet": {
            "videoId": video_id,
            "topLevelComment": {
                "snippet": {
                    "textOriginal": comment_text
                }
            },
        }
    }

    response = youtube.commentThreads().insert(
        part="snippet",
        body=body,
    ).execute()

    return response["id"]


def main():
    youtube = get_youtube_service()

    sheets, spreadsheet_id, publication_values = (
        get_spreadsheet_data()
    )

    settings = get_settings(
        sheets,
        spreadsheet_id,
    )

    content_data = get_content_data(
        sheets,
        spreadsheet_id,
    )

    if len(publication_values) < 2:
        print("No publications found.")
        return

    headers = publication_values[0]

    header_map = {
        header.strip(): index
        for index, header in enumerate(headers)
    }

    required_columns = [
        "CONTENT ID",
        "DESTINATION ID",
        "DATE",
        "TIME",
        "TITLE",
        "CAPTION",
        "STATUS",
        "PLATFORM POST ID",
        "ERROR",
        "COMMENT ID",
        "COMMENT STATUS",
    ]

    for column in required_columns:
        if column not in header_map:
            raise RuntimeError(
                f"Missing PUBLICATIONS column: {column}"
            )

    category_id = settings.get(
        "YOUTUBE_DEFAULT_CATEGORY_ID",
        "22",
    )

    standard_comment = settings.get(
        "YOUTUBE_STANDARD_COMMENT",
        "",
    )

    timezone_name = settings.get(
        "PUBLISH_TIMEZONE",
        "Africa/Accra",
    )

    videos_dir = Path("work/youtube")

    videos_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    processed = 0
    skipped = 0
    failed = 0

    for row_number, raw_row in enumerate(
        publication_values[1:],
        start=2,
    ):
        row = raw_row + [""] * (
            len(headers) - len(raw_row)
        )

        content_id = str(
            row[header_map["CONTENT ID"]]
        ).strip()

        destination_id = str(
            row[header_map["DESTINATION ID"]]
        ).strip()

        date_string = str(
            row[header_map["DATE"]]
        ).strip()

        time_string = str(
            row[header_map["TIME"]]
        ).strip()

        title = str(
            row[header_map["TITLE"]]
        ).strip()

        caption = str(
            row[header_map["CAPTION"]]
        ).strip()

        status = str(
            row[header_map["STATUS"]]
        ).strip()

        platform_post_id = str(
            row[header_map["PLATFORM POST ID"]]
        ).strip()

        comment_id = str(
            row[header_map["COMMENT ID"]]
        ).strip()

        comment_status = str(
            row[header_map["COMMENT STATUS"]]
        ).strip()

        if destination_id != "YT-01":
            skipped += 1
            continue

        if status != "READY":
            skipped += 1
            continue

        if platform_post_id:
            skipped += 1
            continue

        if not content_id:
            skipped += 1
            continue

        if content_id not in content_data:
            print(
                f"Content not found: {content_id}"
            )
            skipped += 1
            continue

        video_file = content_data[content_id][
            "video_file"
        ]

        if not video_file:
            print(
                f"No video file for {content_id}"
            )
            skipped += 1
            continue

        video_name = Path(video_file).name

        possible_paths = [
            Path("work/output") / video_name,
            Path("work/videos") / video_name,
            Path(video_file),
        ]

        video_path = None

        for path in possible_paths:
            if path.exists():
                video_path = path
                break

        if video_path is None:
            print(
                f"Video not found for {content_id}: "
                f"{video_name}"
            )
            skipped += 1
            continue

        try:
            publish_at = build_publish_datetime(
                date_string,
                time_string,
                timezone_name,
            )

            print()
            print(
                f"Uploading {content_id}"
            )
            print(
                f"Title: {title}"
            )
            print(
                f"Publish at: {publish_at}"
            )

            update_publication_row(
                sheets,
                spreadsheet_id,
                row_number,
                [
                    "UPLOADING",
                    "",
                    "",
                    "",
                    "",
                ],
            )

            response = upload_video(
                youtube,
                video_path,
                title,
                caption,
                category_id,
                publish_at,
            )

            video_id = response["id"]

            print(
                f"YouTube video created: "
                f"{video_id}"
            )

            new_comment_id = ""
            new_comment_status = ""

            if standard_comment:
                try:
                    new_comment_id = create_comment(
                        youtube,
                        video_id,
                        standard_comment,
                    )

                    new_comment_status = "CREATED"

                    print(
                        f"Standard comment created: "
                        f"{new_comment_id}"
                    )

                except Exception as comment_error:
                    new_comment_status = "ERROR"

                    print(
                        "Comment creation failed: "
                        f"{comment_error}"
                    )

            update_publication_row(
                sheets,
                spreadsheet_id,
                row_number,
                [
                    "UPLOADED",
                    video_id,
                    "",
                    new_comment_id,
                    new_comment_status,
                ],
            )

            processed += 1

        except Exception as error:
            error_message = str(error)

            print(
                f"Publishing failed for "
                f"{content_id}: "
                f"{error_message}"
            )

            update_publication_row(
                sheets,
                spreadsheet_id,
                row_number,
                [
                    "YOUTUBE_ERROR",
                    "",
                    error_message,
                    comment_id,
                    comment_status,
                ],
            )

            failed += 1

    print()
    print("YouTube publishing complete.")
    print(f"Processed: {processed}")
    print(f"Skipped: {skipped}")
    print(f"Failed: {failed}")


if __name__ == "__main__":
    main()