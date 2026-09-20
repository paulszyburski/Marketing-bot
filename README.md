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

Run it once from the Pi desktop before scheduling it:

```bash
.venv/bin/python src/main.py
```

Log in to TikTok in the Chromium window if required. The login is retained in
the app's `profilePath`.

## Scheduled runs

Create `~/.config/systemd/user/marketing-bot.service`:

```ini
[Unit]
Description=Generate and upload Marketing Bot slideshow
After=graphical-session.target network-online.target

[Service]
Type=oneshot
WorkingDirectory=/absolute/path/to/Marketing-bot
Environment=DISPLAY=:0
ExecStart=/absolute/path/to/Marketing-bot/.venv/bin/python src/main.py
```

Create `~/.config/systemd/user/marketing-bot.timer`:

```ini
[Unit]
Description=Run Marketing Bot on schedule

[Timer]
OnCalendar=Mon,Wed,Fri 18:00
Persistent=true

[Install]
WantedBy=timers.target
```

Adjust `OnCalendar` and both absolute paths, then enable the timer:

```bash
systemctl --user daemon-reload
systemctl --user enable --now marketing-bot.timer
systemctl --user list-timers
```

View logs with:

```bash
journalctl --user -u marketing-bot.service
```
