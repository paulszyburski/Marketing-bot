# Marketing Bot

Generates a slideshow or video and uploads it to TikTok and YouTube Shorts for every app in
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

Set `"uploadPlatforms": ["tiktok", "youtube"]` on each app. Remove a platform
from that list to disable its uploader. When the field is absent, both uploaders
are enabled.

Set `API_PASSWORD` in `.env` before starting the API. Every endpoint, including
the interactive documentation, uses HTTP Basic authentication with username
`admin` and this password.

Store one promotional image per app at
`assets/advertising/<app-id>/advertisement.png`, and set its path in the app's
`advertisingImage` field in `data/apps.json`.

Store real app screenshots used as in-slideshow proof at
`assets/proof/<app-id>/`. Supported formats are JPG, PNG, and WebP. You can
override the directory per app with `proofAssetsPath` in `data/apps.json`.
When screenshots are present, generated slides follow a hook → problem →
solution → screenshot proof → CTA arc. Each post randomly uses one of these
styles: POV, storytelling, before and after, tutorial, comparison, or
curiosity driven.

The uploader automatically adds this image as the final slideshow photo. For
video posts, it creates a sibling `<video-name>_with_ad.mp4`, fades the final
0.5 seconds into the image, and holds the image for another 2 seconds. Video
generation is structured as a 15-second hook/problem/demo/payoff story followed
by this 2-second real-UI branded card, for approximately 17 seconds total.

Runs started from the control website expose their latest output in the
authenticated **Debug log** panel. The panel refreshes every three seconds.
Chromium automatically uses headless mode when the API service has no graphical
`DISPLAY`; set `BROWSER_HEADLESS=false` only when that service has access to a
desktop session and a visible browser is required.

If TikTok blocks or changes its upload interface, the runner records a full-page
screenshot and HTML snapshot under `data/<AppName>/browser_debug/`. Upload
processing dialogs are allowed up to three minutes to finish; safe confirmation
dialogs are then closed before the caption and posting steps continue.

Call `test_video_montage()` in `src/utils.py` to generate a completely new AI
video, create its advertising montage, and save both locally without uploading.
The preview is saved under `data/<AppName>/montage_previews/`.

Run it once from the Pi desktop before scheduling it:

```bash
PYTHONPATH=src .venv/bin/python -m automation.main
```

To choose an app and log in to its TikTok and YouTube accounts manually, call
`login_manually()` from `src/automation/main.py`. For example:

```bash
PYTHONPATH=src .venv/bin/python -c "from automation.main import login_manually; login_manually()"
```

Select the app number, complete each login in Chromium, and then press Enter in
the terminal. Both sessions are retained in that app's `profilePath`. Credentials in
`.env` use the upper-case app `id`, for example `DRIVEPROOF_EMAIL` and
`DRIVEPROOF_PASSWORD`. Add a separate pair for every app.

YouTube Studio classifies the uploaded vertical MP4 as a Short. Video posts use
the generated vertical video; slideshow posts are rendered with 1.5-second
animated slides, slow zoom/pan movement, quick fade transitions, and the configured
advertising card at the end.
Set an optional `backgroundMusic` path on an app to loop that audio under its
slideshow Shorts. It can point to one audio file or a folder containing MP3,
WAV, M4A, AAC, OGG, or FLAC tracks. Folder tracks are selected randomly without
repeating the previous track for that app. Without it, the renderer adds a
generated music bed so the resulting MP4 is never silent. The fallback rotates between
several electronic beat styles with drums, bass, chord changes, and melody;
for production-quality music, provide your own licensed MP3.
The uploader selects **Public**, so it publishes immediately. Complete the first
YouTube login from a headed, interactive run because Google may request 2FA or a
CAPTCHA.

To test the full generation flow without uploading anything,
call `run_test_pipeline()` from `src/automation/utils.py`:

```bash
PYTHONPATH=src .venv/bin/python -c "from automation.utils import run_test_pipeline; run_test_pipeline('data/apps.json')"
```

Choose an app when prompted. The test uses the same 10% video / 90% slideshow
selection as a live run, prints the completed local preview path, and opens
TikTok with that app's saved profile to verify login. It never starts an upload.

## Scheduled runs

The Marketing Bot uses a systemd user timer to run automatically three times
per day: once at a randomized time between **6:00 AM and noon**, once between
**noon and 6:00 PM**, and once between **6:00 PM and midnight**.

The timer:
- Selects three new random execution times every day.
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
exec env PYTHONPATH="$PROJECT_DIR/src" \
    "$PROJECT_DIR/.venv/bin/python" -m automation.main
```

Make it executable:

```bash
chmod +x run.sh
```

### 2. Configure the systemd timer

The repository contains two systemd configuration files:

- `systemd/marketing-bot.service` — starts the Python script.
- `systemd/marketing-bot.timer` — schedules execution twice daily.

Ensure `marketing-bot.timer` contains:

```ini
[Unit]
Description=Run Marketing Bot three times daily at random times

[Timer]
OnCalendar=*-*-* 06:00:00
OnCalendar=*-*-* 12:00:00
OnCalendar=*-*-* 18:00:00
RandomizedDelaySec=5h59m
AccuracySec=1s
Persistent=true
Unit=marketing-bot.service

[Install]
WantedBy=timers.target
```

Every day, systemd schedules one run between 6:00 AM and noon, another between
noon and 6:00 PM, and a third between 6:00 PM and midnight.

`Persistent=true` allows a missed execution to run when the system comes back
online.

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

Scheduled runs default to headless Chromium because systemd does not reliably
inherit the active desktop's `DISPLAY`. Manual runs from a desktop terminal can
still use a visible Chromium window. Set `BROWSER_HEADLESS=false` only when the
service is explicitly configured with access to a valid graphical session.

For reliable operation:

- Keep the Raspberry Pi powered on.
- Ensure the Chromium browser profile belongs to the same Linux user running the service.
- Prevent automatic suspension during scheduled hours.

Enable lingering for the user if scheduled runs must execute while logged out.

**Note:** Each scheduled execution processes every enabled app. If three apps are enabled, the bot will attempt three uploads during that execution.
