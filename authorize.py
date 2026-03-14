#!/usr/bin/env python3
"""
One-time script to authorize a Strava athlete.

Usage:
    python authorize.py <app_name>

Example:
    python authorize.py RILEY
    python authorize.py JASON

Each app_name maps to STRAVA_CLIENT_ID_<app_name> / STRAVA_CLIENT_SECRET_<app_name>
in .env.  Opens a browser for Strava OAuth. After the user authorizes, the tokens
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

load_dotenv()

CALLBACK_PORT = 8090
REDIRECT_URI = f"http://localhost:{CALLBACK_PORT}/callback"

callback_app = Flask(__name__)

_app_name = None
_client_id = None
_client_secret = None


@callback_app.route("/callback")
def callback():
    code = request.args.get("code")
    if not code:
        return "Authorization failed — no code received.", 400

    resp = requests.post("https://www.strava.com/oauth/token", data={
        "client_id": _client_id,
        "client_secret": _client_secret,
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
        strava_app=_app_name,
    )

    print(f"\nAuthorized: {name} (Strava ID {athlete_data['id']}, app={_app_name})")
    print("Tokens saved to the database. You can close this window.")

    threading.Timer(1.0, _shutdown).start()
    return (
        f"<h2>Authorized: {name}</h2>"
        f"<p>Tokens saved (app: {_app_name}). You can close this tab.</p>"
    )


def _shutdown():
    os._exit(0)


def main():
    global _app_name, _client_id, _client_secret

    available = models.get_app_names()
    if len(sys.argv) < 2:
        print(f"Usage: python authorize.py <app_name>")
        print(f"Available apps: {', '.join(available) if available else '(none — check .env)'}")
        sys.exit(1)

    _app_name = sys.argv[1].upper()
    try:
        _client_id, _client_secret = models.get_app_credentials(_app_name)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    authorize_url = (
        f"https://www.strava.com/oauth/authorize"
        f"?client_id={_client_id}"
        f"&response_type=code"
        f"&redirect_uri={REDIRECT_URI}"
        f"&approval_prompt=auto"
        f"&scope=activity:read_all"
    )

    models.init_db()
    print(f"Authorizing via Strava app '{_app_name}'...")
    print(f"If the browser doesn't open, visit:\n{authorize_url}\n")
    webbrowser.open(authorize_url)

    callback_app.run(host="127.0.0.1", port=CALLBACK_PORT)


if __name__ == "__main__":
    main()
