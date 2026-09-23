from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


SCOPES = [
    "https://www.googleapis.com/auth/youtube.force-ssl",
]


VIDEO_ID = "wVVhz3MFBrM"


def main():
    print("Starting YouTube comment diagnostic...")

    flow = InstalledAppFlow.from_client_secrets_file(
        "youtube_client_secret.json",
        SCOPES,
    )

    credentials = flow.run_local_server(
        port=8081,
        access_type="offline",
        prompt="consent",
    )

    youtube = build(
        "youtube",
        "v3",
        credentials=credentials,
    )

    print()
    print("Checking authorized channel...")

    channel_response = youtube.channels().list(
        part="id,snippet",
        mine=True,
    ).execute()

    channels = channel_response.get("items", [])

    if not channels:
        raise RuntimeError(
            "No YouTube channel was found."
        )

    for channel in channels:
        print(
            "Channel ID:",
            channel["id"],
        )
        print(
            "Channel title:",
            channel["snippet"]["title"],
        )

    print()
    print("Attempting test comment...")

    body = {
        "snippet": {
            "channelId": channels[0]["id"],
            "videoId": VIDEO_ID,
            "topLevelComment": {
                "snippet": {
                    "textOriginal":
                        "API authorization test comment"
                }
            },
        }
    }

    try:
        response = youtube.commentThreads().insert(
            part="snippet",
            body=body,
        ).execute()

        print()
        print("SUCCESS")
        print(
            "Comment ID:",
            response["id"],
        )

    except Exception as error:
        print()
        print("COMMENT FAILED")
        print(error)


if __name__ == "__main__":
    main()
