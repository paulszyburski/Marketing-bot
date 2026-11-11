# Automation package

This package generates marketing posts and publishes them through TikTok's web
interface. It supports image slideshows and AI-generated vertical videos. Each
enabled app has its own content history, output folders, advertising asset, and
persistent Chromium profile.

Repository setup and systemd scheduling live in the [project README](../../README.md).
This document describes the automation code itself.

## How a run works

`automation.main` loads `data/apps.json`, skips disabled apps, and processes the
remaining apps in file order. The default pipeline selection is random:

- **90% slideshow**
- **10% video**

For every selected app, the run generates the post first and then opens Chromium
with that app's saved profile. Playwright connects to Chromium over its debugging
port and operates TikTok Studio. A failure in one app stops the current process,
so later apps are not attempted in that run.

### Slideshow pipeline

1. Select one of six content styles: POV, storytelling, before and after,
   tutorial, comparison, or curiosity driven.
2. Ask OpenAI for a distinct idea, using recent idea history to reduce repeats.
3. Generate and validate the hook, problem, solution, proof, and CTA copy.
4. Retrieve portrait stock images from Pexels and optionally include one real app
   screenshot from the proof-assets directory.
5. Render the copy over each image and save the slideshow with its metadata.
6. Add the app's advertising image as the final photo.
7. Upload the photos, choose the generated music suggestion, enter the caption
   and hashtags, and post.

### Video pipeline

1. Ask OpenAI for a distinct 15-second concept and a timed generation prompt.
2. Generate a 9:16 video with the configured fal.ai model.
3. Render short hook and benefit overlays from the generated metadata.
4. Fade into the app's advertising image and hold it for two seconds.
5. Upload the resulting video, enter its caption and hashtags, and post.

## Package map

| Path | Responsibility |
| --- | --- |
| `main.py` | CLI entry point, app filtering, and pipeline selection |
| `pipelines/` | High-level slideshow and video orchestration |
| `AI/chatgpt.py` | Ideas, scripts, slide copy, metadata, and response validation |
| `AI/slideshowgeneration.py` | Proof-image selection, stock-image lookup, and slideshow output |
| `AI/videogeneration.py` | fal.ai submission, download, and video metadata output |
| `AI/idea_history.py` | Per-app idea history used to discourage repeated concepts |
| `AI/audio_history.py` | Per-app music history used to avoid repeated songs |
| `browser/browser.py` | Chromium process and debugging-port lifecycle |
| `browser/tiktok.py` | Login checks, TikTok Studio uploads, captions, music, and posting |
| `browser/pinterest.py` | Pexels portrait-image search; the filename is historical |
| `montage/slides.py` | Text rendering for slideshow images |
| `montage/video.py` | FFmpeg overlays, advertising-card fade, and audio extension |
| `utils.py` | Shared browser wrapper, manual login, and local test helpers |

## Running it

Run commands from the repository root so relative `data/` and `assets/` paths
resolve correctly.

```bash
# Normal random run for every enabled app
PYTHONPATH=src .venv/bin/python -m automation.main

# Run one app by its case-insensitive id
PYTHONPATH=src .venv/bin/python -m automation.main --app driveproof

# Force a pipeline
PYTHONPATH=src .venv/bin/python -m automation.main \
  --app driveproof --pipeline slideshow
PYTHONPATH=src .venv/bin/python -m automation.main \
  --app driveproof --pipeline video
```

These commands perform real uploads. For a generation test that does not upload,
use:

```bash
PYTHONPATH=src .venv/bin/python -c \
  "from automation.utils import run_test_pipeline; run_test_pipeline('data/apps.json')"
```

The test prompts for an app, generates a local preview, and opens TikTok only to
verify the saved login. The video-only montage helper also avoids uploading:

```bash
PYTHONPATH=src .venv/bin/python -c \
  "from automation.utils import test_video_montage; test_video_montage()"
```

## App configuration

Apps are read from `data/apps.json`. See `apps.example.json` for a complete
example.

| Field | Required | Use |
| --- | --- | --- |
| `id` | Yes | Stable CLI id, asset folder name, and credential prefix |
| `appName` | Yes | Display name and `data/<appName>/` output folder |
| `appDescription` | Yes | Product context supplied to content generation |
| `appLink` | Recommended | Link supplied to generation prompts |
| `advertisingImage` | Yes | Final slideshow photo and video outro card |
| `profilePath` | Yes | Persistent Chromium profile containing the TikTok session |
| `proofAssetsPath` | No | Override for real app screenshots used in slideshows |
| `enabled` | No | Defaults to `true`; disabled apps are skipped by normal runs |

Without `proofAssetsPath`, screenshots are read from
`assets/proof/<id>/`. Supported formats are JPG, PNG, and WebP. Advertising and
proof paths may be relative to the repository root.

## Environment variables

The package loads `.env` from the repository. Required keys depend on the chosen
pipeline.

| Variable | Purpose |
| --- | --- |
| `CHATGPT_API_KEY` | OpenAI content and metadata generation |
| `PEXELS_API_KEY` | Portrait stock images for slideshows |
| `FAL_KEY` | AI video generation; only required by the video pipeline |
| `BROWSER_EXECUTABLE` | Optional Chrome/Chromium executable or command name |
| `BROWSER_HEADLESS` | `auto` by default; accepts `true` or `false` |
| `TIKTOK_TIMEOUT_SECONDS` | Browser action timeout; defaults to 90 seconds |
| `TIKTOK_SETTLE_SECONDS` | Delay for TikTok UI updates; defaults to 5 seconds |
| `<APP_ID>_EMAIL` | Optional account hint shown during manual login |
| `<APP_ID>_PASSWORD` | Reserved per-app credential value |

The credential prefix is the upper-case app `id`, with non-alphanumeric
characters replaced by underscores. For `drive-proof`, the keys are
`DRIVE_PROOF_EMAIL` and `DRIVE_PROOF_PASSWORD`.

`BROWSER_HEADLESS=auto` uses a visible window when `DISPLAY` is available and
headless Chromium otherwise. Manual login requires a visible browser and an
interactive terminal.

## TikTok login profiles

Each app needs a separate saved TikTok session. Create or refresh one with:

```bash
PYTHONPATH=src .venv/bin/python -c \
  "from automation.main import login_manually; login_manually()"
```

Choose the app, finish logging in inside Chromium, and then press Enter in the
terminal. The session is stored under that app's `profilePath`. Do not run two
processes against the same profile simultaneously.

Scheduled runs cannot pause for login. If a saved session has expired, the run
fails and must be repaired with the interactive login command.

## Generated files

All runtime output is kept below `data/<appName>/`:

```text
data/<appName>/
├── audio_history.json
├── idea_history.json
├── browser_debug/
│   ├── failure_<timestamp>.html
│   └── failure_<timestamp>.png
├── chrome_profile/
├── montage_previews/
├── slides/<YYYY.MM.DD_HH:MM>/
│   ├── data.json
│   └── image_<n>.jpg
└── videos/<YYYY-MM-DD>/
    ├── video_<n>.json
    ├── video_<n>.mp4
    └── video_<n>_with_ad.mp4
```

Idea history retains the latest 50 entries and supplies the latest 20 to new
prompts. Audio history retains 100 unique songs and supplies the latest 50 when
choosing music.

## Failure diagnosis

Start with the exception and the final log lines. For scheduled runs:

```bash
journalctl --user -u marketing-bot.service -n 100 --no-pager
```

Common failure points:

- **Chromium exits immediately:** verify `BROWSER_EXECUTABLE`, profile ownership,
  and the `DISPLAY`/`BROWSER_HEADLESS` combination.
- **TikTok requests login:** refresh the affected app's profile interactively.
- **A TikTok selector or dialog changed:** inspect the screenshot and HTML saved
  under `browser_debug/`.
- **No slideshow image is found:** verify `PEXELS_API_KEY` and the generated
  image query.
- **Content generation fails validation:** inspect the rejected-attempt messages;
  structured responses are retried up to three times.
- **Video generation fails:** verify `FAL_KEY` and inspect the fal.ai event log.
- **Advertising asset is missing:** verify `advertisingImage` before running;
  both pipelines require it.

TikTok changes its upload interface periodically. Keep selectors in
`browser/tiktok.py` scoped to stable roles and attributes, and preserve debug
artifact capture when changing the upload flow.
