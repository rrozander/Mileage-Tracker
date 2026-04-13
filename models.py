import sqlite3
import os
from datetime import date, timedelta

STRAVA_APPS = {}


def _load_strava_apps():
    """Discover configured Strava apps from env vars (STRAVA_CLIENT_ID_<NAME>)."""
    global STRAVA_APPS
    STRAVA_APPS.clear()
    for key, val in os.environ.items():
        if key.startswith("STRAVA_CLIENT_ID_"):
            name = key[len("STRAVA_CLIENT_ID_"):]
            STRAVA_APPS[name] = {
                "client_id": val,
                "client_secret": os.getenv(f"STRAVA_CLIENT_SECRET_{name}", ""),
                "verify_token": os.getenv(f"WEBHOOK_VERIFY_TOKEN_{name}", ""),
            }


def get_app_credentials(app_name):
    """Return (client_id, client_secret) for a named Strava app."""
    if not STRAVA_APPS:
        _load_strava_apps()
    app = STRAVA_APPS.get(app_name)
    if not app:
        raise ValueError(f"No Strava app configured for '{app_name}'. "
                         f"Available: {list(STRAVA_APPS.keys())}")
    return app["client_id"], app["client_secret"]


def get_all_verify_tokens():
    """Return a set of all configured webhook verify tokens."""
    if not STRAVA_APPS:
        _load_strava_apps()
    return {app["verify_token"] for app in STRAVA_APPS.values() if app["verify_token"]}


def get_app_names():
    """Return list of configured Strava app names."""
    if not STRAVA_APPS:
        _load_strava_apps()
    return list(STRAVA_APPS.keys())


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
            token_expires_at INTEGER NOT NULL,
            strava_app TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            strava_activity_id INTEGER UNIQUE NOT NULL,
            athlete_id INTEGER NOT NULL,
            distance_km REAL NOT NULL,
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
    _migrate_strava_app_column(conn)
    _migrate_moving_time_column(conn)
    conn.commit()
    conn.close()


def _migrate_strava_app_column(conn):
    """Add strava_app column if upgrading from an older schema."""
    cols = [row[1] for row in conn.execute("PRAGMA table_info(athletes)").fetchall()]
    if "strava_app" not in cols:
        conn.execute("ALTER TABLE athletes ADD COLUMN strava_app TEXT NOT NULL DEFAULT ''")


def _migrate_moving_time_column(conn):
    """Add moving_time_s to activities if upgrading from an older schema."""
    cols = [row[1] for row in conn.execute("PRAGMA table_info(activities)").fetchall()]
    if "moving_time_s" not in cols:
        conn.execute("ALTER TABLE activities ADD COLUMN moving_time_s INTEGER")


def upsert_athlete(strava_id, name, avatar_url, access_token, refresh_token,
                   token_expires_at, strava_app=""):
    conn = get_db()
    conn.execute("""
        INSERT INTO athletes (strava_id, name, avatar_url, access_token, refresh_token,
                              token_expires_at, strava_app)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(strava_id) DO UPDATE SET
            name=excluded.name,
            avatar_url=excluded.avatar_url,
            access_token=excluded.access_token,
            refresh_token=excluded.refresh_token,
            token_expires_at=excluded.token_expires_at,
            strava_app=excluded.strava_app
    """, (strava_id, name, avatar_url, access_token, refresh_token, token_expires_at, strava_app))
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


def upsert_activity(strava_activity_id, athlete_id, distance_km, ride_date, name,
                    moving_time_s=None):
    conn = get_db()
    conn.execute("""
        INSERT INTO activities (strava_activity_id, athlete_id, distance_km, ride_date, name,
                                moving_time_s)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(strava_activity_id) DO UPDATE SET
            distance_km=excluded.distance_km,
            ride_date=excluded.ride_date,
            name=excluded.name,
            moving_time_s=COALESCE(excluded.moving_time_s, activities.moving_time_s)
    """, (strava_activity_id, athlete_id, distance_km, ride_date, name, moving_time_s))
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
            COALESCE(SUM(act.distance_km), 0) AS total_km,
            COUNT(act.id) AS ride_count,
            CASE
                WHEN SUM(CASE WHEN act.moving_time_s IS NOT NULL AND act.moving_time_s > 0
                              THEN act.moving_time_s ELSE 0 END) > 0
                THEN SUM(CASE WHEN act.moving_time_s IS NOT NULL AND act.moving_time_s > 0
                              THEN act.distance_km ELSE 0 END) * 3600.0
                     / SUM(CASE WHEN act.moving_time_s IS NOT NULL AND act.moving_time_s > 0
                                THEN act.moving_time_s ELSE 0 END)
                ELSE NULL
            END AS overall_avg_kmh
        FROM athletes a
        LEFT JOIN activities act
            ON act.athlete_id = a.id
            AND act.ride_date >= ?
            AND act.ride_date < ?
        GROUP BY a.id
        ORDER BY total_km DESC
    """, (season_start, season_end)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def current_week_iso_bounds():
    """Monday–Sunday calendar week containing today; return (start, end) as YYYY-MM-DD."""
    today = date.today()
    start = today - timedelta(days=today.weekday())
    end = start + timedelta(days=6)
    return start.isoformat(), end.isoformat()


def get_week_stats_by_athlete(week_start, week_end):
    """Per-athlete weekly km, ride count, longest ride, and avg speed."""
    conn = get_db()
    rows = conn.execute("""
        SELECT
            athlete_id,
            COALESCE(SUM(distance_km), 0) AS week_km,
            COUNT(*) AS week_ride_count,
            MAX(distance_km) AS week_longest_km,
            CASE
                WHEN SUM(CASE WHEN moving_time_s IS NOT NULL AND moving_time_s > 0
                              THEN moving_time_s ELSE 0 END) > 0
                THEN SUM(CASE WHEN moving_time_s IS NOT NULL AND moving_time_s > 0
                              THEN distance_km ELSE 0 END) * 3600.0
                     / SUM(CASE WHEN moving_time_s IS NOT NULL AND moving_time_s > 0
                                THEN moving_time_s ELSE 0 END)
                ELSE NULL
            END AS week_avg_kmh
        FROM activities
        WHERE ride_date >= ? AND ride_date <= ?
        GROUP BY athlete_id
    """, (week_start, week_end)).fetchall()
    conn.close()
    return {r["athlete_id"]: dict(r) for r in rows}


def get_distance_timeline(year=None):
    """Return all rides within the season sorted by date, for charting."""
    season_start, season_end = get_season_bounds(year)
    conn = get_db()
    rows = conn.execute("""
        SELECT
            a.name AS athlete_name,
            act.ride_date,
            act.distance_km,
            act.name AS ride_name
        FROM activities act
        JOIN athletes a ON a.id = act.athlete_id
        WHERE act.ride_date >= ? AND act.ride_date < ?
        ORDER BY act.ride_date
    """, (season_start, season_end)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_rides_for_week():
    """Return rides from the past 7 days, grouped by athlete name.

    Returns a dict: {athlete_name: [{"ride_name", "distance_km", "ride_date"}, ...]}.
    """
    today = date.today().isoformat()
    week_ago = (date.today() - timedelta(days=7)).isoformat()
    conn = get_db()
    rows = conn.execute("""
        SELECT
            a.name AS athlete_name,
            act.name AS ride_name,
            act.distance_km,
            act.ride_date
        FROM activities act
        JOIN athletes a ON a.id = act.athlete_id
        WHERE act.ride_date >= ? AND act.ride_date < ?
        ORDER BY a.name, act.ride_date
    """, (week_ago, today)).fetchall()
    conn.close()

    grouped = {}
    for r in rows:
        d = dict(r)
        grouped.setdefault(d.pop("athlete_name"), []).append(d)
    return grouped


def get_recent_rides(limit=10, year=None):
    season_start, season_end = get_season_bounds(year)
    conn = get_db()
    rows = conn.execute("""
        SELECT
            act.name AS ride_name,
            act.distance_km,
            act.ride_date,
            a.name AS athlete_name,
            a.avatar_url,
            CASE WHEN act.moving_time_s IS NOT NULL AND act.moving_time_s > 0
                 THEN act.distance_km * 3600.0 / act.moving_time_s
                 ELSE NULL END AS avg_kmh
        FROM activities act
        JOIN athletes a ON a.id = act.athlete_id
        WHERE act.ride_date >= ? AND act.ride_date < ?
        ORDER BY act.ride_date DESC, act.created_at DESC
        LIMIT ?
    """, (season_start, season_end, limit)).fetchall()
    conn.close()
    return [dict(r) for r in rows]
