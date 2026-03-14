#!/usr/bin/env python3
"""
Register (or view/delete) a Strava webhook subscription.

Each Strava app needs its own webhook subscription, so you must specify
the app name that corresponds to your .env credentials.

Usage:
    python setup_webhook.py <app_name> create <callback_url>
    python setup_webhook.py <app_name> view
    python setup_webhook.py <app_name> delete <subscription_id>

Example:
    python setup_webhook.py RILEY create https://your-domain.com/webhook
    python setup_webhook.py JASON create https://your-domain.com/webhook
    python setup_webhook.py RILEY view
"""

import os
import sys

import requests
from dotenv import load_dotenv

import models

load_dotenv()

SUBSCRIPTIONS_URL = "https://www.strava.com/api/v3/push_subscriptions"


def create_subscription(client_id, client_secret, verify_token, callback_url):
    resp = requests.post(SUBSCRIPTIONS_URL, data={
        "client_id": client_id,
        "client_secret": client_secret,
        "callback_url": callback_url,
        "verify_token": verify_token,
    }, timeout=15)

    if resp.status_code == 201:
        data = resp.json()
        print(f"Subscription created. ID: {data['id']}")
    else:
        print(f"Failed ({resp.status_code}): {resp.text}")
        sys.exit(1)


def view_subscriptions(client_id, client_secret):
    resp = requests.get(SUBSCRIPTIONS_URL, params={
        "client_id": client_id,
        "client_secret": client_secret,
    }, timeout=10)
    resp.raise_for_status()
    subs = resp.json()

    if not subs:
        print("No active subscriptions.")
    else:
        for sub in subs:
            print(f"  ID: {sub['id']}  callback: {sub['callback_url']}")


def delete_subscription(client_id, client_secret, sub_id):
    resp = requests.delete(
        f"{SUBSCRIPTIONS_URL}/{sub_id}",
        params={
            "client_id": client_id,
            "client_secret": client_secret,
        },
        timeout=10,
    )
    if resp.status_code == 204:
        print(f"Subscription {sub_id} deleted.")
    else:
        print(f"Failed ({resp.status_code}): {resp.text}")
        sys.exit(1)


def main():
    available = models.get_app_names()

    if len(sys.argv) < 3:
        print(__doc__.strip())
        print(f"\nAvailable apps: {', '.join(available) if available else '(none — check .env)'}")
        sys.exit(1)

    app_name = sys.argv[1].upper()
    command = sys.argv[2]

    try:
        client_id, client_secret = models.get_app_credentials(app_name)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    verify_token = os.getenv(f"WEBHOOK_VERIFY_TOKEN_{app_name}", "")

    print(f"Using Strava app: {app_name}")

    if command == "create":
        if len(sys.argv) < 4:
            print("Usage: python setup_webhook.py <app_name> create <callback_url>")
            sys.exit(1)
        if not verify_token:
            print(f"Error: WEBHOOK_VERIFY_TOKEN_{app_name} not set in .env")
            sys.exit(1)
        create_subscription(client_id, client_secret, verify_token, sys.argv[3])

    elif command == "view":
        view_subscriptions(client_id, client_secret)

    elif command == "delete":
        if len(sys.argv) < 4:
            print("Usage: python setup_webhook.py <app_name> delete <subscription_id>")
            sys.exit(1)
        delete_subscription(client_id, client_secret, sys.argv[3])

    else:
        print(f"Unknown command: {command}")
        print(__doc__.strip())
        sys.exit(1)


if __name__ == "__main__":
    main()
