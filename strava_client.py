import time
import requests
import models

STRAVA_API_BASE = "https://www.strava.com/api/v3"
STRAVA_TOKEN_URL = "https://www.strava.com/oauth/token"

METERS_TO_KM = 0.001


def _get_valid_token(athlete):
    """Return a valid access token, refreshing with the athlete's app credentials if expired."""
    if athlete["token_expires_at"] > time.time():
        return athlete["access_token"]

    client_id, client_secret = models.get_app_credentials(athlete["strava_app"])

    resp = requests.post(STRAVA_TOKEN_URL, data={
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "refresh_token",
        "refresh_token": athlete["refresh_token"],
    }, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    models.update_tokens(
        athlete["strava_id"],
        data["access_token"],
        data["refresh_token"],
        data["expires_at"],
    )
    return data["access_token"]


def get_activity(athlete, activity_id):
    """Fetch a single activity from Strava. Returns the activity dict or None."""
    token = _get_valid_token(athlete)
    resp = requests.get(
        f"{STRAVA_API_BASE}/activities/{activity_id}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.json()


def get_athlete_profile(access_token):
    """Fetch the authenticated athlete's profile."""
    resp = requests.get(
        f"{STRAVA_API_BASE}/athlete",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def activity_distance_km(activity):
    """Extract distance in kilometers from a Strava activity dict."""
    return activity.get("distance", 0) * METERS_TO_KM


def activity_ride_date(activity):
    """Extract the ride date as YYYY-MM-DD from a Strava activity dict."""
    start = activity.get("start_date_local", "")
    return start[:10] if start else ""
