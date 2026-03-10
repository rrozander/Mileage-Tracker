import sqlite3
import os
from datetime import date


def get_db():
    db_path = os.getenv("DATABASE_PATH", "mileage.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS athletes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            strava_id INTEGER UNIQUE NOT NULL,
            name TEXT NOT NULL,
            avatar_url TEXT,
            access_token TEXT NOT NULL,
            refresh_token TEXT NOT NULL,
            token_expires_at INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            strava_activity_id INTEGER UNIQUE NOT NULL,
            athlete_id INTEGER NOT NULL,
            distance_miles REAL NOT NULL,
            ride_date TEXT NOT NULL,
            name TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (athlete_id) REFERENCES athletes(id)
        );

        CREATE INDEX IF NOT EXISTS idx_activities_athlete
            ON activities(athlete_id);
        CREATE INDEX IF NOT EXISTS idx_activities_ride_date
            ON activities(ride_date);
    """)
    conn.commit()
    conn.close()


def upsert_athlete(strava_id, name, avatar_url, access_token, refresh_token, token_expires_at):
    conn = get_db()
    conn.execute("""
        INSERT INTO athletes (strava_id, name, avatar_url, access_token, refresh_token, token_expires_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(strava_id) DO UPDATE SET
            name=excluded.name,
            avatar_url=excluded.avatar_url,
            access_token=excluded.access_token,
            refresh_token=excluded.refresh_token,
            token_expires_at=excluded.token_expires_at
    """, (strava_id, name, avatar_url, access_token, refresh_token, token_expires_at))
    conn.commit()
    conn.close()


def update_tokens(strava_id, access_token, refresh_token, token_expires_at):
    conn = get_db()
    conn.execute("""
        UPDATE athletes
        SET access_token=?, refresh_token=?, token_expires_at=?
        WHERE strava_id=?
    """, (access_token, refresh_token, token_expires_at, strava_id))
    conn.commit()
    conn.close()


def get_athlete_by_strava_id(strava_id):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM athletes WHERE strava_id=?", (strava_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def upsert_activity(strava_activity_id, athlete_id, distance_miles, ride_date, name):
    conn = get_db()
    conn.execute("""
        INSERT INTO activities (strava_activity_id, athlete_id, distance_miles, ride_date, name)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(strava_activity_id) DO UPDATE SET
            distance_miles=excluded.distance_miles,
            ride_date=excluded.ride_date,
            name=excluded.name
    """, (strava_activity_id, athlete_id, distance_miles, ride_date, name))
    conn.commit()
    conn.close()


def delete_activity(strava_activity_id):
    conn = get_db()
    conn.execute(
        "DELETE FROM activities WHERE strava_activity_id=?", (strava_activity_id,)
    )
    conn.commit()
    conn.close()


def get_season_bounds(year=None):
    if year is None:
        year = date.today().year
    start_str = os.getenv("SEASON_START", "04-01")
    end_str = os.getenv("SEASON_END", "09-01")
    season_start = f"{year}-{start_str}"
    season_end = f"{year}-{end_str}"
    return season_start, season_end


def get_leaderboard_stats(year=None):
    season_start, season_end = get_season_bounds(year)
    conn = get_db()
    rows = conn.execute("""
        SELECT
            a.id AS athlete_id,
            a.strava_id,
            a.name,
            a.avatar_url,
            COALESCE(SUM(act.distance_miles), 0) AS total_miles,
            COUNT(act.id) AS ride_count
        FROM athletes a
        LEFT JOIN activities act
            ON act.athlete_id = a.id
            AND act.ride_date >= ?
            AND act.ride_date < ?
        GROUP BY a.id
        ORDER BY total_miles DESC
    """, (season_start, season_end)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_recent_rides(limit=10, year=None):
    season_start, season_end = get_season_bounds(year)
    conn = get_db()
    rows = conn.execute("""
        SELECT
            act.name AS ride_name,
            act.distance_miles,
            act.ride_date,
            a.name AS athlete_name,
            a.avatar_url
        FROM activities act
        JOIN athletes a ON a.id = act.athlete_id
        WHERE act.ride_date >= ? AND act.ride_date < ?
        ORDER BY act.ride_date DESC, act.created_at DESC
        LIMIT ?
    """, (season_start, season_end, limit)).fetchall()
    conn.close()
    return [dict(r) for r in rows]
