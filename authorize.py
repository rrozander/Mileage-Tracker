#!/usr/bin/env python3
"""
One-time script to authorize a Strava athlete.

Usage:
    python authorize.py

Opens a browser for Strava OAuth. After the user authorizes, the tokens
are stored in the database so the main app can fetch activities on their behalf.
"""

import os
import sys
import threading
import webbrowser

import requests
from flask import Flask, request
from dotenv import load_dotenv

import models
import strava_client

load_dotenv()

CLIENT_ID = os.getenv("STRAVA_CLIENT_ID")
CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET")
CALLBACK_PORT = 8090
REDIRECT_URI = f"http://localhost:{CALLBACK_PORT}/callback"

AUTHORIZE_URL = (
    f"https://www.strava.com/oauth/authorize"
    f"?client_id={CLIENT_ID}"
    f"&response_type=code"
    f"&redirect_uri={REDIRECT_URI}"
    f"&approval_prompt=auto"
    f"&scope=activity:read_all"
)

callback_app = Flask(__name__)
server_thread = None


@callback_app.route("/callback")
def callback():
    code = request.args.get("code")
    if not code:
        return "Authorization failed — no code received.", 400

    resp = requests.post("https://www.strava.com/oauth/token", data={
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
    }, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    athlete_data = data["athlete"]
    name = f"{athlete_data['firstname']} {athlete_data['lastname']}"
    avatar = athlete_data.get("profile") or athlete_data.get("profile_medium", "")

    models.init_db()
    models.upsert_athlete(
        strava_id=athlete_data["id"],
        name=name,
        avatar_url=avatar,
        access_token=data["access_token"],
        refresh_token=data["refresh_token"],
        token_expires_at=data["expires_at"],
    )

    print(f"\nAuthorized: {name} (Strava ID {athlete_data['id']})")
    print("Tokens saved to the database. You can close this window.")

    threading.Timer(1.0, _shutdown).start()
    return (
        f"<h2>Authorized: {name}</h2>"
        f"<p>Tokens saved. You can close this tab.</p>"
    )


def _shutdown():
    os._exit(0)


def main():
    if not CLIENT_ID or not CLIENT_SECRET:
        print("Error: Set STRAVA_CLIENT_ID and STRAVA_CLIENT_SECRET in .env")
        sys.exit(1)

    models.init_db()
    print(f"Opening browser for Strava authorization...")
    print(f"If it doesn't open, visit:\n{AUTHORIZE_URL}\n")
    webbrowser.open(AUTHORIZE_URL)

    callback_app.run(host="127.0.0.1", port=CALLBACK_PORT)


if __name__ == "__main__":
    main()
