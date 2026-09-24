import json
import os
import sys
from datetime import datetime, timezone

import requests

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
        json.loads(
            os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]
        ),
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


def send_health_alert(subject, message):

    url = os.environ["HEALTH_ALERT_URL"]
    token = os.environ["HEALTH_ALERT_TOKEN"]

    response = requests.post(
        url,
        json={
            "action": "health_alert",
            "token": token,
            "subject": subject,
            "message": message,
        },
        timeout=30,
    )

    if response.status_code != 200:
        raise RuntimeError(
            "Health alert request failed: "
            + response.text
        )

    data = response.json()

    if not data.get("success"):
        raise RuntimeError(
            "Health alert was rejected: "
            + str(data)
        )


def run_health_check():

    print(
        "Running Content Hub YouTube health check..."
    )
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

    channel_id = channel.get(
        "id",
        ""
    )

    channel_title = (
        channel
        .get("snippet", {})
        .get("title", "")
    )

    print(
        "YouTube authentication: OK"
    )

    print(
        "Channel:",
        channel_title
    )

    print(
        "Channel ID:",
        channel_id
    )

    sheets = get_sheets_service()

    spreadsheet_id = os.environ[
        "CONTENT_SPREADSHEET_ID"
    ]

    sheets.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range="SETTINGS!A:B",
    ).execute()

    print(
        "Google Sheets access: OK"
    )

    print()
    print(
        "Content Hub YouTube health check: PASS"
    )


def main():

    try:

        run_health_check()

        return 0

    except Exception as error:

        error_message = str(
            error.message
            if hasattr(error, "message")
            else error
        )

        timestamp = datetime.now(
            timezone.utc
        ).strftime(
            "%Y-%m-%d %H:%M:%S UTC"
        )

        print()
        print(
            "Content Hub YouTube health check: FAILED"
        )

        print(
            error_message
        )

        subject = (
            "🚨 Content Hub YouTube "
            "Health Check FAILED"
        )

        message = (
            "Content Hub YouTube Health Check FAILED\n\n"
            f"Time: {timestamp}\n\n"
            "Problem:\n"
            f"{error_message}\n\n"
            "Check the GitHub Actions log for details."
        )

        try:

            send_health_alert(
                subject,
                message
            )

            print(
                "Health alert email sent."
            )

        except Exception as alert_error:

            print(
                "WARNING: Could not send "
                "health alert email:"
            )

            print(
                str(alert_error)
            )

        return 1


if __name__ == "__main__":
    sys.exit(main())
