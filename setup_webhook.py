#!/usr/bin/env python3
"""
Register (or view/delete) a Strava webhook subscription.

Usage:
    python setup_webhook.py create <callback_url>
    python setup_webhook.py view
    python setup_webhook.py delete <subscription_id>

Example:
    python setup_webhook.py create https://your-domain.com/webhook
"""

import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("STRAVA_CLIENT_ID")
CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET")
VERIFY_TOKEN = os.getenv("WEBHOOK_VERIFY_TOKEN")
SUBSCRIPTIONS_URL = "https://www.strava.com/api/v3/push_subscriptions"


def create_subscription(callback_url):
    resp = requests.post(SUBSCRIPTIONS_URL, data={
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "callback_url": callback_url,
        "verify_token": VERIFY_TOKEN,
    }, timeout=15)

    if resp.status_code == 201:
        data = resp.json()
        print(f"Subscription created. ID: {data['id']}")
    else:
        print(f"Failed ({resp.status_code}): {resp.text}")
        sys.exit(1)


def view_subscriptions():
    resp = requests.get(SUBSCRIPTIONS_URL, params={
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }, timeout=10)
    resp.raise_for_status()
    subs = resp.json()

    if not subs:
        print("No active subscriptions.")
    else:
        for sub in subs:
            print(f"  ID: {sub['id']}  callback: {sub['callback_url']}")


def delete_subscription(sub_id):
    resp = requests.delete(
        f"{SUBSCRIPTIONS_URL}/{sub_id}",
        params={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        },
        timeout=10,
    )
    if resp.status_code == 204:
        print(f"Subscription {sub_id} deleted.")
    else:
        print(f"Failed ({resp.status_code}): {resp.text}")
        sys.exit(1)


def main():
    if not CLIENT_ID or not CLIENT_SECRET:
        print("Error: Set STRAVA_CLIENT_ID and STRAVA_CLIENT_SECRET in .env")
        sys.exit(1)

    if len(sys.argv) < 2:
        print(__doc__.strip())
        sys.exit(1)

    command = sys.argv[1]

    if command == "create":
        if len(sys.argv) < 3:
            print("Usage: python setup_webhook.py create <callback_url>")
            sys.exit(1)
        create_subscription(sys.argv[2])

    elif command == "view":
        view_subscriptions()

    elif command == "delete":
        if len(sys.argv) < 3:
            print("Usage: python setup_webhook.py delete <subscription_id>")
            sys.exit(1)
        delete_subscription(sys.argv[2])

    else:
        print(f"Unknown command: {command}")
        print(__doc__.strip())
        sys.exit(1)


if __name__ == "__main__":
    main()
