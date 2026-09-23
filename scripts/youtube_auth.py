import json
import os
import sys
import webbrowser

from google_auth_oauthlib.flow import InstalledAppFlow


SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]


def main():
    client_file = "youtube_client_secret.json"

    if not os.path.exists(client_file):
        raise RuntimeError(
            "youtube_client_secret.json not found."
        )

    flow = InstalledAppFlow.from_client_secrets_file(
        client_file,
        SCOPES,
    )

    credentials = flow.run_local_server(
        port=8080,
        access_type="offline",
        prompt="consent",
    )

    print("\nAuthorization successful.\n")

    print("REFRESH TOKEN:")
    print(credentials.refresh_token)

    print("\nCLIENT ID:")
    print(credentials.client_id)

    print("\nCLIENT SECRET:")
    print(credentials.client_secret)

    print("\nSave these securely.")
    print("Do NOT commit them to GitHub.")


if __name__ == "__main__":
    main()
