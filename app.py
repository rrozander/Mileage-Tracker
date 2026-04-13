import os
import threading
import logging
from datetime import date, datetime

from dotenv import load_dotenv
load_dotenv()

from flask import Flask, request, jsonify, render_template
from apscheduler.schedulers.background import BackgroundScheduler

import models
import strava_client
import notifications

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.template_filter("prettydate")
def prettydate_filter(value):
    """Turn 'YYYY-MM-DD' into 'Mon DD, YYYY' (e.g. 'Apr 01, 2026')."""
    try:
        return datetime.strptime(value, "%Y-%m-%d").strftime("%b %d, %Y")
    except (ValueError, TypeError):
        return value

DAY_MAP = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}

_db_initialized = False


@app.before_request
def ensure_db():
    global _db_initialized
    if not _db_initialized:
        models.init_db()
        _db_initialized = True


# ---------------------------------------------------------------------------
# Public leaderboard
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    season_start, season_end = models.get_season_bounds()
    year = date.today().year
    today = date.today().isoformat()

    if today < season_start:
        season_status = "pre"
    elif today >= season_end:
        season_status = "post"
    else:
        season_status = "active"

    return render_template(
        "index.html",
        season_status=season_status,
        season_year=year,
        season_start=season_start,
        season_end=season_end,
    )


@app.route("/api/leaderboard")
def api_leaderboard():
    stats = models.get_leaderboard_stats()
    recent = models.get_recent_rides(limit=10)
    timeline = models.get_distance_timeline()
    season_start, season_end = models.get_season_bounds()
    week_start, week_end = models.current_week_iso_bounds()
    week_map = models.get_week_stats_by_athlete(week_start, week_end)

    if stats:
        leader_km = stats[0]["total_km"]
        for row in stats:
            row["behind_leader_km"] = round(leader_km - row["total_km"], 1)
            ws = week_map.get(row["athlete_id"], {})
            row["week_km"] = round(ws.get("week_km", 0), 1)
            wv = ws.get("week_avg_kmh")
            row["week_avg_kmh"] = round(wv, 1) if wv is not None else None
            rc = row["ride_count"]
            row["avg_ride_km"] = round(row["total_km"] / rc, 1) if rc else None
            v = row.get("overall_avg_kmh")
            if v is not None:
                row["overall_avg_kmh"] = round(v, 1)

    for ride in recent:
        v = ride.get("avg_kmh")
        if v is not None:
            ride["avg_kmh"] = round(v, 1)

    return jsonify({
        "leaderboard": stats,
        "recent_rides": recent,
        "distance_timeline": timeline,
        "season_start": season_start,
        "season_end": season_end,
        "week_start": week_start,
        "week_end": week_end,
    })


# ---------------------------------------------------------------------------
# Strava webhook
# ---------------------------------------------------------------------------

@app.route("/webhook", methods=["GET"])
def webhook_verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token in models.get_all_verify_tokens():
        logger.info("Webhook subscription verified")
        return jsonify({"hub.challenge": challenge})

    logger.warning("Webhook verification failed")
    return "", 403


@app.route("/webhook", methods=["POST"])
def webhook_event():
    data = request.json
    logger.info("Webhook event received: %s", data)

    if data.get("object_type") == "activity":
        # Handle in a background thread so we respond within 2 seconds
        thread = threading.Thread(
            target=_handle_activity_event, args=(data,), daemon=True
        )
        thread.start()

    return "", 200


def _handle_activity_event(data):
    aspect = data.get("aspect_type")
    activity_id = data.get("object_id")
    owner_id = data.get("owner_id")

    if aspect == "delete":
        models.delete_activity(activity_id)
        logger.info("Deleted activity %s", activity_id)
        return

    if aspect not in ("create", "update"):
        return

    athlete = models.get_athlete_by_strava_id(owner_id)
    if athlete is None:
        logger.info("Ignoring event from unknown athlete %s", owner_id)
        return

    try:
        activity = strava_client.get_activity(athlete, activity_id)
    except Exception:
        logger.exception("Failed to fetch activity %s", activity_id)
        return

    if activity is None:
        return

    if activity.get("type") != "Ride" and activity.get("sport_type") != "Ride":
        logger.info("Ignoring non-ride activity %s (type=%s)", activity_id, activity.get("type"))
        return

    ride_date = strava_client.activity_ride_date(activity)
    season_start, season_end = models.get_season_bounds()

    if not (season_start <= ride_date < season_end):
        logger.info("Ignoring out-of-season ride %s (date=%s)", activity_id, ride_date)
        return

    distance = strava_client.activity_distance_km(activity)
    name = activity.get("name", "Ride")
    mt = strava_client.activity_moving_time_s(activity)
    moving_time_s = mt if mt > 0 else None

    old_standings = models.get_leaderboard_stats()
    models.upsert_activity(
        activity_id, athlete["id"], distance, ride_date, name,
        moving_time_s=moving_time_s,
    )
    new_standings = models.get_leaderboard_stats()
    logger.info("Saved ride %s: %.1f km by %s", activity_id, distance, athlete["name"])

    try:
        notifications.check_and_notify_surpass(
            athlete["name"], distance, old_standings, new_standings,
        )
    except Exception:
        logger.exception("Failed to send surpass notification")


# ---------------------------------------------------------------------------
# Scheduled jobs
# ---------------------------------------------------------------------------

def _start_scheduler():
    recap_day = os.getenv("WEEKLY_RECAP_DAY", "mon").lower()
    recap_hour = int(os.getenv("WEEKLY_RECAP_HOUR", "8"))
    day_of_week = DAY_MAP.get(recap_day, 0)

    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(
        notifications.send_weekly_recap,
        trigger="cron",
        day_of_week=day_of_week,
        hour=recap_hour,
        minute=0,
        id="weekly_recap",
    )
    scheduler.start()
    logger.info(
        "Weekly recap scheduled for %s at %02d:00",
        recap_day.capitalize(), recap_hour,
    )


_start_scheduler()


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    models.init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
