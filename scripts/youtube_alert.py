import os

import requests


def send_youtube_alert(
    subject,
    message,
):
    url = os.environ.get("HEALTH_ALERT_URL", "").strip()
    token = os.environ.get("HEALTH_ALERT_TOKEN", "").strip()

    if not url:
        raise RuntimeError(
            "HEALTH_ALERT_URL is not configured."
        )

    if not token:
        raise RuntimeError(
            "HEALTH_ALERT_TOKEN is not configured."
        )

    response = requests.post(
        url,
        json={
            "action": "health_alert",
            "alertType": "publication",
            "token": token,
            "subject": subject,
            "message": message,
        },
        timeout=30,
    )

    if response.status_code != 200:
        raise RuntimeError(
            "YouTube alert request failed: "
            + response.text
        )

    data = response.json()

    if not data.get("success"):
        raise RuntimeError(
            "YouTube alert was rejected: "
            + str(data)
        )

    return data
