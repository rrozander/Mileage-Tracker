"""Insert synthetic demo data for two riders spanning several months."""

import random
import sqlite3
import os
from datetime import date, timedelta

random.seed(42)

DB_PATH = os.getenv("DATABASE_PATH", "mileage.db")

RIDERS = [
    {"strava_id": 900001, "name": "Alex Thompson", "avatar_url": None,
     "avg_km": (25, 55), "rides_per_week": (3, 5), "speed_range": (20, 30)},
    {"strava_id": 900002, "name": "Jamie Rivera", "avatar_url": None,
     "avg_km": (20, 50), "rides_per_week": (3, 6), "speed_range": (18, 28)},
]

RIDE_NAMES = [
    "Morning Loop", "Evening Cruise", "River Trail", "Hill Repeats",
    "Coffee Ride", "Recovery Spin", "Long Weekend Ride", "Commute",
    "Gravel Grind", "Sunset Ride", "Lake Loop", "Fast Flat Out",
    "Headwind Sufferfest", "Neighborhood Spin", "Tempo Intervals",
    "Weekend Explorer", "Bridge Circuit", "Forest Path", "Coastal Cruise",
]

SEASON_START = date(date.today().year, 4, 1)
DEMO_END = date.today()


def generate_rides(rider, start, end):
    rides = []
    current = start
    activity_id_base = rider["strava_id"] * 10000

    while current <= end:
        week_rides = random.randint(*rider["rides_per_week"])
        week_days = random.sample(range(7), min(week_rides, 7))

        for dow in sorted(week_days):
            ride_date = current + timedelta(days=dow)
            if ride_date < start or ride_date > end:
                continue

            distance = round(random.uniform(*rider["avg_km"]), 1)
            speed_kmh = random.uniform(*rider["speed_range"])
            moving_time_s = int(distance / speed_kmh * 3600)
            name = random.choice(RIDE_NAMES)

            activity_id_base += 1
            rides.append({
                "strava_activity_id": activity_id_base,
                "distance_km": distance,
                "ride_date": ride_date.isoformat(),
                "name": name,
                "moving_time_s": moving_time_s,
            })

        current += timedelta(days=7)

    return rides


def main():
    if DEMO_END < SEASON_START:
        print("Season hasn't started yet — nothing to seed.")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    demo_strava_ids = [r["strava_id"] for r in RIDERS]
    placeholders = ",".join("?" * len(demo_strava_ids))
    conn.execute(f"""
        DELETE FROM activities WHERE athlete_id IN (
            SELECT id FROM athletes WHERE strava_id IN ({placeholders})
        )
    """, demo_strava_ids)

    for rider in RIDERS:
        conn.execute("""
            INSERT INTO athletes (strava_id, name, avatar_url,
                                  access_token, refresh_token, token_expires_at, strava_app)
            VALUES (?, ?, ?, 'demo', 'demo', 0, 'demo')
            ON CONFLICT(strava_id) DO UPDATE SET name=excluded.name
        """, (rider["strava_id"], rider["name"], rider["avatar_url"]))

        row = conn.execute(
            "SELECT id FROM athletes WHERE strava_id=?", (rider["strava_id"],)
        ).fetchone()
        athlete_id = row[0]

        rides = generate_rides(rider, SEASON_START, DEMO_END)
        for r in rides:
            conn.execute("""
                INSERT INTO activities
                    (strava_activity_id, athlete_id, distance_km, ride_date, name, moving_time_s)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(strava_activity_id) DO UPDATE SET
                    distance_km=excluded.distance_km,
                    ride_date=excluded.ride_date,
                    name=excluded.name,
                    moving_time_s=excluded.moving_time_s
            """, (r["strava_activity_id"], athlete_id,
                  r["distance_km"], r["ride_date"], r["name"], r["moving_time_s"]))

        print(f"  {rider['name']}: {len(rides)} rides inserted")

    conn.commit()
    conn.close()
    print(f"\nDone — database: {DB_PATH}")


if __name__ == "__main__":
    import models
    models.init_db()
    print("Seeding demo data...\n")
    main()
