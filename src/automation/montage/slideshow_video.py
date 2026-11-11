import hashlib
import math
import random
import secrets
import subprocess
import wave
from pathlib import Path

import imageio_ffmpeg
from PIL import Image

from automation.montage.branding import add_google_play_badge


SUPPORTED_IMAGES = {".jpg", ".jpeg", ".png", ".webp"}
SUPPORTED_AUDIO = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"}

BEAT_STYLES = (
    (108, ((48, 55, 60), (43, 50, 55), (45, 52, 57), (41, 48, 53))),
    (116, ((45, 52, 57), (48, 55, 60), (52, 59, 64), (50, 57, 62))),
    (124, ((52, 59, 64), (48, 55, 60), (45, 52, 57), (47, 54, 59))),
    (132, ((50, 57, 62), (45, 52, 57), (48, 55, 60), (43, 50, 55))),
    (100, ((43, 50, 55), (46, 53, 58), (41, 48, 53), (48, 55, 60))),
    (120, ((47, 54, 59), (50, 57, 62), (43, 50, 55), (45, 52, 57))),
)


def _frequency(midi_note):
    return 440.0 * (2.0 ** ((midi_note - 69) / 12.0))


def _synthesize_backing_track(path, duration, seed_text, style_index=None):
    """Create a short electronic beat with drums, bass, chords and melody."""
    seed = int(hashlib.sha256(seed_text.encode()).hexdigest()[:16], 16)
    rng = random.Random(seed)
    style_index = seed % len(BEAT_STYLES) if style_index is None else style_index
    bpm, progression = BEAT_STYLES[style_index]
    sample_rate = 22_050
    beat_seconds = 60.0 / bpm
    frame_count = math.ceil(duration * sample_rate)
    melody_pattern = [0, 1, 2, 1, 0, 2, 1, 2]

    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        frames = bytearray()
        for frame in range(frame_count):
            t = frame / sample_rate
            beat = t / beat_seconds
            beat_in_bar = beat % 4
            chord = progression[int(beat // 4) % len(progression)]

            # Punchy kick on every beat, with extra weight on beats one/three.
            kick_t = (beat % 1) * beat_seconds
            kick = math.sin(2 * math.pi * (58 + 45 * math.exp(-25 * kick_t)) * t)
            kick *= math.exp(-18 * kick_t) * (0.42 if int(beat) % 2 == 0 else 0.3)

            # Short noise snare on beats two/four and crisp eighth-note hats.
            snare_t = ((beat_in_bar - 1) % 2) * beat_seconds
            snare = 0.0
            if snare_t < 0.16:
                snare = rng.uniform(-1, 1) * math.exp(-22 * snare_t) * 0.18
            hat_t = (beat % 0.5) * beat_seconds
            hat = rng.uniform(-1, 1) * math.exp(-55 * hat_t) * 0.055

            # Chord stabs, moving bass and a small repeating top melody.
            chord_t = (beat % 2) * beat_seconds
            chord_sound = sum(
                math.sin(2 * math.pi * _frequency(note + 12) * t)
                for note in chord
            ) / 3
            chord_sound *= math.exp(-2.6 * chord_t) * 0.1
            bass_note = chord[0] - 12 + (7 if int(beat) % 4 == 3 else 0)
            bass = math.sin(2 * math.pi * _frequency(bass_note) * t) * 0.13
            step = int(beat * 2)
            melody_t = (beat * 2 % 1) * beat_seconds / 2
            melody_note = chord[melody_pattern[step % len(melody_pattern)]] + 24
            melody = math.sin(2 * math.pi * _frequency(melody_note) * t)
            melody *= math.exp(-8 * melody_t) * 0.075

            sample = max(-0.95, min(0.95, kick + snare + hat + chord_sound + bass + melody))
            value = int(sample * 32767)
            frames.extend(value.to_bytes(2, "little", signed=True))
        output.writeframes(frames)
    print(f"Generated backing beat: {bpm} BPM, style {style_index + 1}")


def _choose_background_music(configured_path, slides_path):
    """Resolve one configured file or choose a non-repeating file from a folder."""
    music_path = Path(configured_path).expanduser().resolve()
    if music_path.is_file():
        return music_path, None
    if not music_path.is_dir():
        raise FileNotFoundError(f"Background music not found: {music_path}")

    tracks = sorted(
        path for path in music_path.iterdir()
        if path.is_file() and path.suffix.casefold() in SUPPORTED_AUDIO
    )
    if not tracks:
        extensions = ", ".join(sorted(SUPPORTED_AUDIO))
        raise ValueError(
            f"No supported audio files in {music_path}. Supported: {extensions}"
        )

    history_path = None
    previous_track = None
    if slides_path.parent.name == "slides":
        history_path = slides_path.parent.parent / "last_youtube_music.txt"
        try:
            previous_track = Path(history_path.read_text(encoding="utf-8").strip())
        except OSError:
            pass

    choices = [track for track in tracks if track != previous_track]
    selected = secrets.choice(choices or tracks)
    print(f"Selected YouTube background track: {selected.name}")
    return selected, history_path


def render_slideshow_video(
    slides_path,
    advertising_image,
    seconds_per_slide=1.5,
    advertising_seconds=2.0,
    background_music=None,
    transition_seconds=0.22,
):
    """Render animated photos and the advertising card as a vertical MP4."""
    slides_path = Path(slides_path).expanduser().resolve()
    advertising_image = Path(advertising_image).expanduser().resolve()
    images = sorted(
        path for path in slides_path.iterdir()
        if path.is_file() and path.suffix.lower() in SUPPORTED_IMAGES
    )
    if not images:
        raise ValueError(f"No slideshow images found in {slides_path}")
    if not advertising_image.is_file():
        raise FileNotFoundError(f"Advertising image not found: {advertising_image}")

    badged_advertising_image = slides_path / ".youtube_ad_with_badge.png"
    with Image.open(advertising_image) as ad_image:
        add_google_play_badge(ad_image).save(badged_advertising_image)
    images.append(badged_advertising_image)
    durations = [float(seconds_per_slide)] * (len(images) - 1) + [float(advertising_seconds)]
    transition_seconds = min(
        float(transition_seconds),
        min(durations) / 3,
    )
    total_duration = sum(durations)
    output_path = slides_path / "youtube_short.mp4"
    temporary_path = slides_path / "youtube_short.tmp.mp4"
    command = [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-hide_banner", "-loglevel", "error"]
    filters = []
    labels = []
    for index, (image, duration) in enumerate(zip(images, durations)):
        command.extend(["-loop", "1", "-framerate", "30", "-t", str(duration), "-i", str(image)])
        label = f"v{index}"
        labels.append(f"[{label}]")
        frame_count = max(1, round(duration * 30))
        zoom_rate = "0.0018" if index % 2 == 0 else "0.0013"
        horizontal_pan = (
            "iw/2-(iw/zoom/2)"
            if index % 3 == 0
            else "(iw-iw/zoom)*on/{frames}"
        ).format(frames=frame_count)
        vertical_pan = (
            "ih/2-(ih/zoom/2)"
            if index % 3 != 2
            else "(ih-ih/zoom)*(1-on/{frames})"
        ).format(frames=frame_count)
        fade_filters = []
        if index > 0:
            fade_filters.append(f"fade=t=in:st=0:d={transition_seconds}")
        if index < len(images) - 1:
            fade_start = max(duration - transition_seconds, 0)
            fade_filters.append(
                f"fade=t=out:st={fade_start}:d={transition_seconds}"
            )
        fades = ",".join(fade_filters)
        if fades:
            fades += ","
        filters.append(
            f"[{index}:v]scale=1080:1920:force_original_aspect_ratio=increase,"
            f"crop=1080:1920,setsar=1,"
            f"zoompan=z='min(zoom+{zoom_rate},1.10)':x='{horizontal_pan}':"
            f"y='{vertical_pan}':d={frame_count}:s=1080x1920:fps=30,"
            f"fps=30,{fades}format=yuv420p,setpts=PTS-STARTPTS[{label}]"
        )
    audio_index = len(images)
    generated_music = None
    beat_history_path = None
    selected_beat_style = None
    selected_music = None
    music_history_path = None
    if background_music:
        selected_music, music_history_path = _choose_background_music(
            background_music,
            slides_path,
        )
        command.extend(["-stream_loop", "-1", "-i", str(selected_music)])
    else:
        generated_music = slides_path / ".youtube_backing_track.wav"
        seed = int(hashlib.sha256(str(slides_path).encode()).hexdigest()[:16], 16)
        selected_beat_style = seed % len(BEAT_STYLES)
        if slides_path.parent.name == "slides":
            beat_history_path = slides_path.parent.parent / "last_youtube_beat.txt"
            try:
                previous_style = int(beat_history_path.read_text().strip())
                if selected_beat_style == previous_style:
                    selected_beat_style = (selected_beat_style + 1) % len(BEAT_STYLES)
            except (OSError, ValueError):
                pass
        _synthesize_backing_track(
            generated_music,
            total_duration,
            str(slides_path),
            selected_beat_style,
        )
        command.extend(["-i", str(generated_music)])
    filters.append(f"{''.join(labels)}concat=n={len(labels)}:v=1:a=0[outv]")
    fade_start = max(total_duration - 1.0, 0)
    filters.append(
        f"[{audio_index}:a]atrim=duration={total_duration},"
        f"asetpts=PTS-STARTPTS,afade=t=out:st={fade_start}:d=1[outa]"
    )
    command.extend([
        "-filter_complex", ";".join(filters),
        "-map", "[outv]", "-map", "[outa]",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(temporary_path),
    ])
    print(f"Rendering YouTube slideshow Short: {output_path}")
    try:
        subprocess.run(command, check=True)
        temporary_path.replace(output_path)
        if beat_history_path is not None and selected_beat_style is not None:
            beat_history_path.write_text(str(selected_beat_style), encoding="utf-8")
        if music_history_path is not None and selected_music is not None:
            music_history_path.write_text(str(selected_music), encoding="utf-8")
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise
    finally:
        if generated_music is not None:
            generated_music.unlink(missing_ok=True)
        badged_advertising_image.unlink(missing_ok=True)
    return str(output_path)
