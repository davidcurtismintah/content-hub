import json
import os
import sys

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.oauth2 import service_account


YOUTUBE_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]


def get_youtube_service():
    credentials = Credentials(
        token=None,
        refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["YOUTUBE_CLIENT_ID"],
        client_secret=os.environ["YOUTUBE_CLIENT_SECRET"],
        scopes=YOUTUBE_SCOPES,
    )

    return build(
        "youtube",
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


def main():
    print("Running Content Hub YouTube health check...")
    print()

    youtube = get_youtube_service()

    channel_result = youtube.channels().list(
        part="snippet,status",
        mine=True,
    ).execute()

    channels = channel_result.get("items", [])

    if not channels:
        raise RuntimeError(
            "YouTube authentication succeeded, "
            "but no channel was returned."
        )

    channel = channels[0]

    channel_id = channel.get("id", "")
    channel_title = (
        channel.get("snippet", {})
        .get("title", "")
    )

    print("YouTube authentication: OK")
    print("Channel:", channel_title)
    print("Channel ID:", channel_id)

    sheets = get_sheets_service()

    spreadsheet_id = os.environ["CONTENT_SPREADSHEET_ID"]

    sheets.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range="SETTINGS!A:B",
    ).execute()

    print("Google Sheets access: OK")
    print()
    print("Content Hub YouTube health check: PASS")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print()
        print("Content Hub YouTube health check: FAILED")
        print(str(error))
        sys.exit(1)
