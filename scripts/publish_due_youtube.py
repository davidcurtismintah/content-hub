import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.oauth2 import service_account

from youtube_alert import send_youtube_alert


SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]

GHANA_TZ = ZoneInfo("Africa/Accra")


def get_youtube_service():
    credentials = Credentials(
        token=None,
        refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["YOUTUBE_CLIENT_ID"],
        client_secret=os.environ["YOUTUBE_CLIENT_SECRET"],
        scopes=SCOPES,
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


def get_publications(sheets):
    spreadsheet_id = os.environ["CONTENT_SPREADSHEET_ID"]

    result = sheets.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range="PUBLICATIONS!A:K",
    ).execute()

    return result.get("values", [])


def update_publication(
    sheets,
    row_number,
    status,
    video_id,
    error="",
):
    spreadsheet_id = os.environ["CONTENT_SPREADSHEET_ID"]

    sheets.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=f"PUBLICATIONS!G{row_number}:I{row_number}",
        valueInputOption="RAW",
        body={
            "values": [[
                status,
                video_id,
                error,
            ]]
        },
    ).execute()


def parse_due_datetime(date_value, time_value):
    if not date_value:
        return None

    if time_value:
        value = f"{date_value} {time_value}"
        return datetime.strptime(
            value,
            "%Y-%m-%d %H:%M",
        ).replace(tzinfo=GHANA_TZ)

    return datetime.strptime(
        date_value,
        "%Y-%m-%d",
    ).replace(tzinfo=GHANA_TZ)


def verify_public(youtube, video_id):
    result = youtube.videos().list(
        part="status",
        id=video_id,
    ).execute()

    items = result.get("items", [])

    if not items:
        return False, "YouTube video was not found."

    privacy_status = (
        items[0]
        .get("status", {})
        .get("privacyStatus", "")
    )

    if privacy_status != "public":
        return (
            False,
            f"YouTube privacy status is '{privacy_status}', not 'public'."
        )

    return True, ""


def main():
    print("Checking for YouTube videos ready to publish...")

    youtube = get_youtube_service()
    sheets = get_sheets_service()

    publications = get_publications(sheets)

    if len(publications) < 2:
        print("No publication records.")
        return

    now = datetime.now(GHANA_TZ)

    published = 0

    for index, row in enumerate(publications[1:], start=2):

        if len(row) < 9:
            continue

        content_id = str(row[0]).strip()
        destination_id = str(row[1]).strip()
        date_value = str(row[2]).strip()
        time_value = str(row[3]).strip()
        status = str(row[6]).strip()
        video_id = str(row[7]).strip()

        if destination_id != "YT-01":
            continue

        if status != "UPLOADED":
            continue

        if not video_id:
            continue

        due_time = parse_due_datetime(
            date_value,
            time_value,
        )

        if not due_time:
            continue

        if due_time > now:
            continue

        print(
            f"Publishing YouTube video: "
            f"{video_id} "
            f"for {content_id}"
        )

        try:
            youtube.videos().update(
                part="status",
                body={
                    "id": video_id,
                    "status": {
                        "privacyStatus": "public",
                    },
                },
            ).execute()

            verified, verification_error = verify_public(
                youtube,
                video_id,
            )

            if not verified:
                print(
                    "Publication verification failed: "
                    + verification_error
                )
            
                previous_error = str(
                    row[8] or ""
                ).strip()
            
                update_publication(
                    sheets,
                    index,
                    "UPLOADED",
                    video_id,
                    verification_error,
                )
            
                if verification_error != previous_error:
            
                    subject = (
                        "🚨 Content Hub YouTube Verification Failed"
                    )
            
                    message = (
                        "A scheduled YouTube publication "
                        "failed verification.\n\n"
                        f"Content ID: {content_id}\n"
                        f"Destination: {destination_id}\n"
                        f"Scheduled time: {date_value} {time_value}\n\n"
                        "Error:\n"
                        f"{verification_error}\n\n"
                        "The video remains in UPLOADED status "
                        "and will be checked again on the next "
                        "scheduler run.\n\n"
                        "Check GitHub Actions and the PUBLICATIONS "
                        "sheet for details."
                    )
            
                    try:
                        send_youtube_alert(
                            subject,
                            message,
                        )
            
                        print(
                            "YouTube verification alert sent."
                        )
            
                    except Exception as alert_error:
            
                        print(
                            "WARNING: Could not send "
                            "YouTube verification alert:"
                        )
            
                        print(
                            str(alert_error)
                        )
            
                else:
            
                    print(
                        "Same verification error already reported. "
                        "Duplicate alert suppressed."
                    )
            
                continue

            update_publication(
                sheets,
                index,
                "PUBLISHED",
                video_id,
                "",
            )

            print(
                f"Published and verified: {video_id}"
            )

            published += 1

        except Exception as error:
            error_message = str(
                error.message
                if hasattr(error, "message")
                else error
            ).strip()
            
            print(
                f"Failed to publish {video_id}: "
                f"{error_message}"
            )

            previous_error = str(
                row[8] or ""
            ).strip()            
            
            update_publication(
                sheets,
                index,
                "UPLOADED",
                video_id,
                error_message,
            )

            if error_message != previous_error:
            
                scheduled_time = (
                    f"{date_value} {time_value}"
                )
            
                subject = (
                    "🚨 Content Hub YouTube Publication Failed"
                )
            
                message = (
                    "A scheduled YouTube publication failed.\n\n"
                    f"Content ID: {content_id}\n"
                    f"Destination: {destination_id}\n"
                    f"Scheduled time: {scheduled_time}\n\n"
                    "Error:\n"
                    f"{error_message}\n\n"
                    "Content Hub will retry the publication "
                    "on the next scheduler run.\n\n"
                    "Check GitHub Actions and the PUBLICATIONS "
                    "sheet for details."
                )
            
                try:
                    send_youtube_alert(
                        subject,
                        message,
                    )
            
                    print(
                        "YouTube failure alert sent."
                    )
            
                except Exception as alert_error:
            
                    print(
                        "WARNING: Could not send "
                        "YouTube failure alert:"
                    )
            
                    print(
                        str(alert_error)
                    )
            
            else:
            
                print(
                    "Same YouTube error already reported. "
                    "Duplicate alert suppressed."
                )


    print(
        f"Videos published and verified: {published}"
    )


if __name__ == "__main__":
    main()
