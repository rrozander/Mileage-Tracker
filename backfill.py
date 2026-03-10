#!/usr/bin/env python3
"""
One-time backfill script that pulls existing Ride activities from Strava
for all authorized athletes and stores them in the database.

Usage:
    python backfill.py
"""

import time
import requests
from dotenv import load_dotenv

load_dotenv()

import models
import strava_client

STRAVA_API_BASE = "https://www.strava.com/api/v3"


def fetch_rides(athlete, after_ts, before_ts):
    """Yield all Ride activities for an athlete within the time window."""
    page = 1
    per_page = 100

    while True:
        token = strava_client._get_valid_token(athlete)
        resp = requests.get(
            f"{STRAVA_API_BASE}/athlete/activities",
            headers={"Authorization": f"Bearer {token}"},
            params={
                "after": int(after_ts),
                "before": int(before_ts),
                "page": page,
                "per_page": per_page,
            },
            timeout=15,
        )
        resp.raise_for_status()
        activities = resp.json()

        if not activities:
            break

        for act in activities:
            if act.get("type") == "Ride" or act.get("sport_type") == "Ride":
                yield act

        if len(activities) < per_page:
            break

        page += 1
        time.sleep(0.5)


def backfill_athlete(athlete):
    season_start, season_end = models.get_season_bounds()

    after_ts = time.mktime(time.strptime(season_start, "%Y-%m-%d"))
    before_ts = time.mktime(time.strptime(season_end, "%Y-%m-%d"))

    print(f"  Fetching rides from {season_start} to {season_end}...")
    count = 0

    for act in fetch_rides(athlete, after_ts, before_ts):
        distance = strava_client.activity_distance_km(act)
        ride_date = strava_client.activity_ride_date(act)
        name = act.get("name", "Ride")
        strava_id = act["id"]

        models.upsert_activity(strava_id, athlete["id"], distance, ride_date, name)
        count += 1
        print(f"    {ride_date}  {distance:6.1f} km  {name}")

    return count


def main():
    models.init_db()
    conn = models.get_db()
    athletes = [dict(r) for r in conn.execute("SELECT * FROM athletes").fetchall()]
    conn.close()

    if not athletes:
        print("No athletes in the database. Run authorize.py first.")
        return

    total = 0
    for athlete in athletes:
        print(f"\nBackfilling: {athlete['name']} (Strava ID {athlete['strava_id']})")
        count = backfill_athlete(athlete)
        total += count
        print(f"  -> {count} rides saved")

    print(f"\nDone. {total} total rides backfilled.")


if __name__ == "__main__":
    main()
