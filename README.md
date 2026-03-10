# Bike Mileage Leaderboard

A self-hosted leaderboard that tracks bike kilometers between two riders using the Strava API.
The page is publicly accessible (no login required) and updates automatically via Strava webhooks whenever a ride is posted.

**Season window:** April 1 -- September 1 (configurable in `.env`).

## Prerequisites

- Python 3.9+
- A [Strava API application](https://www.strava.com/settings/api)
- A publicly reachable URL for webhooks (e.g. Cloudflare Tunnel on a Raspberry Pi)

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and fill in your Strava Client ID and Client Secret from <https://www.strava.com/settings/api>.  
Pick any random string for `WEBHOOK_VERIFY_TOKEN`.

### 3. Authorize each rider

Run the authorize script once per rider. It opens a browser for Strava OAuth and stores the tokens in the local SQLite database.

```bash
python authorize.py
```

Repeat for the second rider (log into their Strava account first, or have them run it on their machine and copy the resulting `mileage.db`).

### 4. Start the app

```bash
python app.py
```

The leaderboard is now available at `http://localhost:5000`.

### 5. Expose publicly (Raspberry Pi)

Install Cloudflare Tunnel (`cloudflared`) to make the app reachable from the internet without opening ports:

```bash
# Install cloudflared (Debian/Raspberry Pi)
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64.deb -o cloudflared.deb
sudo dpkg -i cloudflared.deb

# Authenticate (one-time)
cloudflared tunnel login

# Create a tunnel
cloudflared tunnel create mileage-tracker

# Route your domain to the tunnel
cloudflared tunnel route dns mileage-tracker leaderboard.yourdomain.com

# Run the tunnel
cloudflared tunnel --url http://localhost:5000 run mileage-tracker
```

### 6. Register the Strava webhook

Once the app is publicly accessible, register the webhook so Strava pushes ride events:

```bash
python setup_webhook.py create https://leaderboard.yourdomain.com/webhook
```

Verify the subscription:

```bash
python setup_webhook.py view
```

## Running in Production

Use `gunicorn` instead of the Flask dev server:

```bash
gunicorn -w 2 -b 0.0.0.0:5000 app:app
```

### systemd service (auto-start on boot)

Create `/etc/systemd/system/mileage-tracker.service`:

```ini
[Unit]
Description=Bike Mileage Leaderboard
After=network.target

[Service]
User=pi
WorkingDirectory=/home/pi/Mileage-Tracker
ExecStart=/home/pi/Mileage-Tracker/.venv/bin/gunicorn -w 2 -b 0.0.0.0:5000 app:app
Restart=always
EnvironmentFile=/home/pi/Mileage-Tracker/.env

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now mileage-tracker
```

## Project Structure

```
.
├── app.py               # Flask app (routes, webhook handler)
├── models.py            # SQLite schema and queries
├── strava_client.py     # Strava API client (token refresh, activity fetch)
├── authorize.py         # One-time OAuth authorization script
├── setup_webhook.py     # Webhook subscription management
├── templates/
│   └── index.html       # Leaderboard page
├── static/
│   └── style.css        # Styles
├── requirements.txt
├── .env.example
└── .gitignore
```

## How It Works

1. Both riders authorize the app via `authorize.py` (one-time OAuth flow).
2. Strava sends a webhook `POST` to `/webhook` whenever a ride is created, updated, or deleted.
3. The app fetches the ride details from Strava, checks that it's a bike ride within the season window, and stores it in SQLite.
4. The public leaderboard at `/` reads from the database and auto-refreshes every 60 seconds.
