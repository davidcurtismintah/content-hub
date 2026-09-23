import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from google.oauth2 import service_account
from googleapiclient.discovery import build


def get_google_credentials():
    credentials_json = os.environ[
        "GOOGLE_SERVICE_ACCOUNT_JSON"
    ]

    return service_account.Credentials.from_service_account_info(
        json.loads(credentials_json),
        scopes=[
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

    return sheets


def get_youtube_service():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    client_id = os.environ["YOUTUBE_CLIENT_ID"]
    client_secret = os.environ["YOUTUBE_CLIENT_SECRET"]
    refresh_token = os.environ["YOUTUBE_REFRESH_TOKEN"]

    credentials = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=[
            "https://www.googleapis.com/auth/youtube.upload",
            "https://www.googleapis.com/auth/youtube.force-ssl",
        ],
    )

    credentials.refresh(Request())

    return build(
        "youtube",
        "v3",
        credentials=credentials,
    )


def get_publications(sheets, spreadsheet_id):
    result = sheets.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range="PUBLICATIONS!A:K",
    ).execute()

    return result.get("values", [])


def update_status(
    sheets,
    spreadsheet_id,
    row_number,
):
    sheets.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=f"PUBLICATIONS!G{row_number}:I{row_number}",
        valueInputOption="RAW",
        body={
            "values": [[
                "PUBLISHED",
                "",
                "",
            ]]
        },
    ).execute()


def make_public(youtube, video_id):
    response = youtube.videos().update(
        part="status",
        body={
            "id": video_id,
            "status": {
                "privacyStatus": "public",
            },
        },
    ).execute()

    return response


def main():
    print(
        "Checking for YouTube videos "
        "ready to publish..."
    )

    spreadsheet_id = os.environ[
        "CONTENT_SPREADSHEET_ID"
    ]

    sheets = get_services()

    youtube = get_youtube_service()

    publications = get_publications(
        sheets,
        spreadsheet_id,
    )

    if len(publications) < 2:
        print("No publications found.")
        return

    headers = publications[0]

    header_map = {
        header.strip(): index
        for index, header in enumerate(headers)
    }

    timezone_name = "Africa/Accra"

    timezone = ZoneInfo(timezone_name)

    now = datetime.now(timezone)

    published = 0

    for row_number, raw_row in enumerate(
        publications[1:],
        start=2,
    ):
        row = raw_row + [""] * (
            len(headers) - len(raw_row)
        )

        destination_id = str(
            row[header_map["DESTINATION ID"]]
        ).strip()

        status = str(
            row[header_map["STATUS"]]
        ).strip()

        video_id = str(
            row[header_map["PLATFORM POST ID"]]
        ).strip()

        date_string = str(
            row[header_map["DATE"]]
        ).strip()

        time_string = str(
            row[header_map["TIME"]]
        ).strip()

        if destination_id != "YT-01":
            continue

        if status != "UPLOADED":
            continue

        if not video_id:
            continue

        if not date_string or not time_string:
            continue

        try:
            scheduled_time = datetime.strptime(
                f"{date_string} {time_string}",
                "%Y-%m-%d %H:%M",
            ).replace(
                tzinfo=timezone
            )

        except ValueError:
            print(
                f"Invalid date/time on row "
                f"{row_number}"
            )
            continue

        if now < scheduled_time:
            continue

        print()
        print(
            f"Publishing YouTube video: "
            f"{video_id}"
        )

        try:
            make_public(
                youtube,
                video_id,
            )

            sheets.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=(
                    f"PUBLICATIONS!G"
                    f"{row_number}:I"
                    f"{row_number}"
                ),
                valueInputOption="RAW",
                body={
                    "values": [[
                        "PUBLISHED",
                        video_id,
                        "",
                    ]]
                },
            ).execute()

            published += 1

            print(
                f"Published: {video_id}"
            )

        except Exception as error:
            print(
                f"Failed to publish "
                f"{video_id}: {error}"
            )

    print()
    print(
        f"Videos published: {published}"
    )


if __name__ == "__main__":
    main()
