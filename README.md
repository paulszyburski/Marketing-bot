# Marketing Bot

Generates a slideshow and uploads it to TikTok for every app in
`data/apps.json`.

## Raspberry Pi setup

The TikTok uploader controls a real Chromium window. Use Raspberry Pi OS with
the desktop environment, and run the job as the same Linux user that owns the
browser profile.

```bash
git clone https://github.com/paulszyburski/Marketing-bot.git
cd Marketing-bot
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
mkdir -p data
cp apps.example.json data/apps.json
```

Fill in `.env` and `data/apps.json`. Both files are intentionally excluded from
Git because they contain secrets or machine-specific configuration.

Store one promotional image per app at
`assets/advertising/<app-id>/advertisement.png`, and set its path in the app's
`advertisingImage` field in `data/apps.json`.

The uploader automatically adds this image as the final slideshow photo. For
video posts, it creates a sibling `<video-name>_with_ad.mp4`, fades the final
0.5 seconds into the image, and holds the image for another 2 seconds.

Call `test_video_montage()` in `src/main.py` to generate a completely new AI
video, create its advertising montage, and save both locally without uploading.
The preview is saved under `data/<AppName>/montage_previews/`.

Run it once from the Pi desktop before scheduling it:

```bash
.venv/bin/python src/main.py
```

Log in to TikTok in the Chromium window if required. The login is retained in
the app's `profilePath`.

## Scheduled runs

The Marketing Bot uses a systemd user timer to run automatically once per day at a randomized time between **10:00 AM and 10:00 PM**.

The timer:
- Selects a new random execution time every day.
- Runs automatically without requiring an open terminal.
- Starts automatically after reboot when the user's systemd manager is running.
- Runs the pipeline for every enabled app in `data/apps.json`.
- Prevents overlapping executions of the same systemd service.

### 1. Configure the launcher

Ensure `run.sh` contains:

```bash
#!/bin/bash
set -euo pipefail

readonly PROJECT_DIR="/home/paul/Projects/Marketing-bot"

cd "$PROJECT_DIR"
exec "$PROJECT_DIR/.venv/bin/python" src/main.py
```

Make it executable:

```bash
chmod +x run.sh
```

### 2. Configure the systemd timer

The repository contains two systemd configuration files:

- `systemd/marketing-bot.service` — starts the Python script.
- `systemd/marketing-bot.timer` — schedules daily execution.

Ensure `marketing-bot.timer` contains:

```ini
[Unit]
Description=Run Marketing Bot Once Daily at a Random Time

[Timer]
OnCalendar=*-*-* 10:00:00
RandomizedDelaySec=12h
AccuracySec=1min
Persistent=false
Unit=marketing-bot.service

[Install]
WantedBy=timers.target
```

Every day at 10:00 AM, systemd selects a random delay of up to 12 hours.

`Persistent=false` prevents the timer from immediately catching up on missed executions after the system was offline.

### 3. Install and enable the timer

```bash
mkdir -p ~/.config/systemd/user

cp systemd/marketing-bot.service systemd/marketing-bot.timer ~/.config/systemd/user/

systemctl --user daemon-reload

systemctl --user enable --now marketing-bot.timer
```

**Important:** This is a user service. Do not use `sudo` with these commands.

### 4. Verify scheduling

Check the next scheduled execution:

```bash
systemctl --user list-timers marketing-bot.timer
```

Check timer status:

```bash
systemctl --user status marketing-bot.timer
```

### 5. View logs

```bash
journalctl --user -u marketing-bot.service -n 50
```

Follow logs in real time:

```bash
journalctl --user -u marketing-bot.service -f
```

### 6. Run manually

To execute the bot immediately:

```bash
systemctl --user start marketing-bot.service
```

This does not disable the next scheduled execution.

### 7. Stop or restart scheduling

Disable automatic execution:

```bash
systemctl --user disable --now marketing-bot.timer
```

Enable automatic execution again:

```bash
systemctl --user enable --now marketing-bot.timer
```

### Raspberry Pi considerations

Because TikTok uploading uses a real Chromium window, the bot requires an accessible graphical desktop session.

For reliable operation:

- Keep the Raspberry Pi powered on.
- Ensure the Chromium browser profile belongs to the same Linux user running the service.
- Configure the desktop session so the browser can launch when the timer triggers.
- Prevent automatic suspension during scheduled hours.
- Verify that the systemd service has access to the graphical session.

A systemd user timer does not automatically guarantee access to the desktop or execution while the user is logged out.

**Note:** Each scheduled execution processes every enabled app. If three apps are enabled, the bot will attempt three uploads during that execution.