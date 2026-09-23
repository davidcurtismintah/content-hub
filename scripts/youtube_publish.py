import json
import os
import re
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload


SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]


def get_youtube_service():
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

    return build(
        "youtube",
        "v3",
        credentials=credentials,
    )


def get_google_credentials():
    credentials_json = os.environ[
        "GOOGLE_SERVICE_ACCOUNT_JSON"
    ]

    return service_account.Credentials.from_service_account_info(
        json.loads(credentials_json),
        scopes=[
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/spreadsheets",
        ],
    )


def get_services():
    credentials = get_google_credentials()

    sheets = build(
        "sheets",
        "v4",
        credentials=credentials,
    )

    drive = build(
        "drive",
        "v3",
        credentials=credentials,
    )

    return sheets, drive


def get_spreadsheet_data(sheets):
    spreadsheet_id = os.environ[
        "CONTENT_SPREADSHEET_ID"
    ]

    result = sheets.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range="PUBLICATIONS!A:K",
    ).execute()

    return spreadsheet_id, result.get("values", [])


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

        value = (
            str(row[1]).strip()
            if len(row) > 1
            else ""
        )

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
        row = row + [""] * (
            len(headers) - len(row)
        )

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


def extract_drive_file_id(value):
    value = str(value or "").strip()

    if not value:
        return ""

    match = re.search(
        r"/file/d/([a-zA-Z0-9_-]+)",
        value,
    )

    if match:
        return match.group(1)

    match = re.search(
        r"[?&]id=([a-zA-Z0-9_-]+)",
        value,
    )

    if match:
        return match.group(1)

    if re.fullmatch(
        r"[a-zA-Z0-9_-]{10,}",
        value,
    ):
        return value

    return ""


def download_video_from_drive(
    drive,
    video_reference,
    output_path,
):
    file_id = extract_drive_file_id(
        video_reference
    )

    if not file_id:
        raise RuntimeError(
            "Could not extract Google Drive file ID "
            "from VIDEO FILE: "
            + video_reference
        )

    file_info = drive.files().get(
        fileId=file_id,
        fields="id,name,mimeType,size",
        supportsAllDrives=True,
    ).execute()

    print(
        f"Downloading video from Drive: "
        f"{file_info['name']}"
    )

    request = drive.files().get_media(
        fileId=file_id
    )

    with open(output_path, "wb") as output:
        downloader = MediaIoBaseDownload(
            output,
            request,
        )

        done = False

        while not done:
            status, done = downloader.next_chunk()

            if status:
                progress = int(
                    status.progress() * 100
                )

                print(
                    f"Drive download progress: "
                    f"{progress}%"
                )

    return output_path


def update_publication_row(
    sheets,
    spreadsheet_id,
    row_number,
    status,
    platform_post_id="",
    error="",
    comment_id="",
    comment_status="",
):
    sheets.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=(
            f"PUBLICATIONS!G{row_number}:K"
            f"{row_number}"
        ),
        valueInputOption="RAW",
        body={
            "values": [[
                status,
                platform_post_id,
                error,
                comment_id,
                comment_status,
            ]]
        },
    ).execute()


def upload_video(
    youtube,
    video_path,
    title,
    description,
    category_id,
):
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "categoryId": category_id,
        },

        "status": {
            "privacyStatus": "unlisted",
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
                f"YouTube upload progress: "
                f"{progress}%"
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
    print(
        "Starting YouTube publishing..."
    )

    youtube = get_youtube_service()

    sheets, drive = get_services()

    (
        spreadsheet_id,
        publication_values,
    ) = get_spreadsheet_data(sheets)

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
                f"Missing PUBLICATIONS column: "
                f"{column}"
            )

    category_id = settings.get(
        "YOUTUBE_DEFAULT_CATEGORY_ID",
        "22",
    )

    standard_comment = settings.get(
        "YOUTUBE_STANDARD_COMMENT",
        "",
    )

    max_uploads = int(
        settings.get(
            "YOUTUBE_MAX_UPLOADS_PER_RUN",
            "1",
        )
    )

    if max_uploads <= 0:
        print(
            "YouTube uploads are disabled "
            "for this run."
        )
        return

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
                f"Content not found: "
                f"{content_id}"
            )
            skipped += 1
            continue

        video_reference = content_data[
            content_id
        ]["video_file"]

        if not video_reference:
            print(
                f"No VIDEO FILE for "
                f"{content_id}"
            )
            skipped += 1
            continue

        try:
            video_path = (
                videos_dir
                / f"{content_id}.mp4"
            )

            if not video_path.exists():
                download_video_from_drive(
                    drive,
                    video_reference,
                    video_path,
                )

            print()
            print(
                f"Preparing YouTube upload: "
                f"{content_id}"
            )

            print(f"Title: {title}")

            print(
                "Initial visibility: UNLISTED"
            )

            update_publication_row(
                sheets,
                spreadsheet_id,
                row_number,
                "UPLOADING",
            )

            response = upload_video(
                youtube,
                video_path,
                title,
                caption,
                category_id,
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
                        "Standard comment created."
                    )

                except Exception as comment_error:
                    new_comment_status = "ERROR"

                    print(
                        "Comment creation failed: "
                        + str(comment_error)
                    )

            update_publication_row(
                sheets,
                spreadsheet_id,
                row_number,
                "UPLOADED",
                video_id,
                "",
                new_comment_id,
                new_comment_status,
            )

            processed += 1

            print(
                f"Completed: {content_id}"
            )

            if processed >= max_uploads:
                print(
                    "Reached YouTube upload "
                    f"limit: {max_uploads}"
                )
                break

        except Exception as error:
            error_message = str(error)

            print(
                "YouTube publishing failed "
                f"for {content_id}: "
                f"{error_message}"
            )

            update_publication_row(
                sheets,
                spreadsheet_id,
                row_number,
                "YOUTUBE_ERROR",
                "",
                error_message,
                "",
                "",
            )

            failed += 1

    print()
    print(
        "YouTube publishing complete."
    )

    print(
        f"Processed: {processed}"
    )

    print(
        f"Skipped: {skipped}"
    )

    print(
        f"Failed: {failed}"
    )


if __name__ == "__main__":
    main()
