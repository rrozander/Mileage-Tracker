import os
import threading
import logging
from datetime import date

from dotenv import load_dotenv
load_dotenv()

from flask import Flask, request, jsonify, render_template

import models
import strava_client

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    season_start, season_end = models.get_season_bounds()
    return jsonify({
        "leaderboard": stats,
        "recent_rides": recent,
        "season_start": season_start,
        "season_end": season_end,
    })


# ---------------------------------------------------------------------------
# Strava webhook
# ---------------------------------------------------------------------------

@app.route("/webhook", methods=["GET"])
def webhook_verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == os.getenv("WEBHOOK_VERIFY_TOKEN"):
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

    distance = strava_client.activity_distance_miles(activity)
    name = activity.get("name", "Ride")

    models.upsert_activity(activity_id, athlete["id"], distance, ride_date, name)
    logger.info("Saved ride %s: %.1f mi by %s", activity_id, distance, athlete["name"])


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    models.init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
