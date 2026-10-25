import subprocess
from pathlib import Path

import imageio_ffmpeg


DEFAULT_FADE_SECONDS = 0.5
DEFAULT_HOLD_SECONDS = 2.0


def _video_metadata(video_path: Path) -> dict:
    reader = imageio_ffmpeg.read_frames(str(video_path))
    try:
        return next(reader)
    finally:
        reader.close()


def _has_audio(ffmpeg: str, video_path: Path) -> bool:
    probe = subprocess.run(
        [ffmpeg, "-hide_banner", "-i", str(video_path)],
        capture_output=True,
        check=False,
        text=True,
    )
    return "Audio:" in probe.stderr


def append_advertising_image(
    video_path,
    advertising_image,
    fade_seconds=DEFAULT_FADE_SECONDS,
    hold_seconds=DEFAULT_HOLD_SECONDS,
    output_path=None,
):
    """Crossfade a video into an app advertisement and hold the final image."""

    video_path = Path(video_path).expanduser().resolve()
    advertising_image = Path(advertising_image).expanduser().resolve()

    if not video_path.is_file():
        raise FileNotFoundError(f"Video not found: {video_path}")
    if not advertising_image.is_file():
        raise FileNotFoundError(
            f"Advertising image not found: {advertising_image}"
        )

    metadata = _video_metadata(video_path)
    duration = float(metadata["duration"])
    width, height = metadata["size"]
    fps = max(round(float(metadata.get("fps") or 30)), 1)

    if duration <= fade_seconds:
        fade_seconds = max(duration / 2, 0.1)

    fade_start = max(duration - fade_seconds, 0)
    output_duration = duration + hold_seconds
    output_path = (
        Path(output_path).expanduser().resolve()
        if output_path
        else video_path.with_name(f"{video_path.stem}_with_ad.mp4")
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_name(
        f"{output_path.stem}.tmp.mp4"
    )

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    filter_graph = (
        f"[1:v]scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},fps={fps},format=yuv420p,"
        f"setpts=PTS-STARTPTS[ad];"
        f"[0:v]fps={fps},format=rgba,setpts=PTS-STARTPTS,"
        f"fade=t=out:st={fade_start}:d={fade_seconds}:alpha=1[video];"
        f"[ad][video]overlay=eof_action=pass:shortest=0:format=auto,"
        f"format=yuv420p[outv]"
    )

    command = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(video_path),
        "-loop",
        "1",
        "-framerate",
        str(fps),
        "-t",
        str(output_duration),
        "-i",
        str(advertising_image),
        "-filter_complex",
        filter_graph,
        "-map",
        "[outv]",
    ]

    if _has_audio(ffmpeg, video_path):
        command.extend(
            [
                "-map",
                "0:a:0",
                "-af",
                (
                    f"afade=t=out:st={fade_start}:d={fade_seconds},"
                    f"apad=pad_dur={hold_seconds}"
                ),
                "-c:a",
                "aac",
                "-b:a",
                "192k",
            ]
        )

    command.extend(
        [
            "-c:v",
            "libx264",
            "-r",
            str(fps),
            "-preset",
            "medium",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            "-t",
            str(output_duration),
            str(temporary_path),
        ]
    )

    print(f"Creating advertising outro: {output_path}")
    try:
        subprocess.run(command, check=True)
        temporary_path.replace(output_path)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise

    return str(output_path)
