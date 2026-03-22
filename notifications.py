import os
import logging
from datetime import date, timedelta

from twilio.rest import Client as TwilioClient

import models

logger = logging.getLogger(__name__)

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER", "")
NOTIFICATION_PHONES = [
    p.strip() for p in os.getenv("NOTIFICATION_PHONES", "").split(",") if p.strip()
]


def _get_twilio_client():
    if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER]):
        logger.warning("Twilio credentials not configured — SMS disabled")
        return None
    if not NOTIFICATION_PHONES:
        logger.warning("NOTIFICATION_PHONES is empty — SMS disabled")
        return None
    return TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


def send_group_sms(body):
    """Send *body* as an SMS to every number in NOTIFICATION_PHONES."""
    client = _get_twilio_client()
    if client is None:
        return

    for phone in NOTIFICATION_PHONES:
        try:
            client.messages.create(
                body=body,
                from_=TWILIO_FROM_NUMBER,
                to=phone,
            )
            logger.info("SMS sent to %s", phone)
        except Exception:
            logger.exception("Failed to send SMS to %s", phone)


def check_and_notify_surpass(athlete_name, distance_km, old_standings, new_standings):
    """Compare leaderboard before/after a ride and notify if a surpass occurred.

    *old_standings* and *new_standings* are lists of dicts from
    ``models.get_leaderboard_stats()`` (ordered by total_km DESC).
    """
    old_rank = {row["name"]: idx for idx, row in enumerate(old_standings)}
    new_rank = {row["name"]: idx for idx, row in enumerate(new_standings)}
    new_totals = {row["name"]: row["total_km"] for row in new_standings}

    rider_old = old_rank.get(athlete_name)
    rider_new = new_rank.get(athlete_name)

    if rider_old is None or rider_new is None:
        return
    if rider_new >= rider_old:
        return  # didn't move up

    passed = [
        name for name, old_pos in old_rank.items()
        if name != athlete_name
        and old_pos < rider_old          # were ahead before
        and new_rank.get(name, 0) > rider_new  # now behind
    ]

    if not passed:
        return

    rider_total = new_totals.get(athlete_name, 0)
    for name in passed:
        their_total = new_totals.get(name, 0)
        msg = (
            f"🚴 {athlete_name} just passed {name} with a {distance_km:.1f} km ride! "
            f"{athlete_name} now leads with {rider_total:.1f} km "
            f"vs {name}'s {their_total:.1f} km."
        )
        send_group_sms(msg)


def send_weekly_recap():
    """Build and send a Monday-morning weekly recap covering the past 7 days."""
    today = date.today()
    week_start = today - timedelta(days=7)
    week_end = today

    rides_by_athlete = models.get_rides_for_week()
    if not rides_by_athlete:
        logger.info("No rides in the past week — skipping recap")
        return

    season_stats = models.get_leaderboard_stats()

    header = (
        f"📊 Weekly Ride Recap "
        f"({week_start.strftime('%b %-d')} – {week_end.strftime('%b %-d')})\n"
    )

    lines = [header]
    for athlete_name, rides in rides_by_athlete.items():
        total = sum(r["distance_km"] for r in rides)
        lines.append(f"{athlete_name}: {len(rides)} ride{'s' if len(rides) != 1 else ''}, {total:.1f} km")
        for r in rides:
            rd = date.fromisoformat(r["ride_date"])
            day_name = rd.strftime("%A")
            lines.append(f"  - {day_name}: {r['ride_name']} ({r['distance_km']:.1f} km)")
        lines.append("")

    season_parts = [f"{s['name']} {s['total_km']:.1f} km" for s in season_stats]
    lines.append("Season totals: " + " | ".join(season_parts))

    send_group_sms("\n".join(lines))
