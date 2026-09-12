#!/usr/bin/env python3
"""Record the foreground macOS screen, then edit real footage into a short MP4.

This does not control Chrome, call AI, fill a mock shop, or publish a product.
Keep the intended Chrome window visible during capture. Review crops/redactions
before sharing. Raw recordings belong in ignored work/ or artifacts/ directories.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile


def ffmpeg():
    try:
        import imageio_ffmpeg
    except ImportError:
        raise ValueError("Install requirements-video.txt before exporting.") from None
    return imageio_ffmpeg.get_ffmpeg_exe()


def metadata(path):
    result = subprocess.run([ffmpeg(), "-hide_banner", "-i", str(path)],
                            capture_output=True, text=True)
    duration = re.search(r"Duration: (\d+):(\d+):(\d+(?:\.\d+)?)", result.stderr)
    if not duration:
        raise ValueError("Cannot read the input video duration.")
    hours, minutes, seconds = map(float, duration.groups())
    return hours * 3600 + minutes * 60 + seconds


def rectangle(value):
    parts = [int(x) for x in value.split(",")] if isinstance(value, str) else list(value)
    if len(parts) != 4 or any(isinstance(x, bool) or not isinstance(x, int) for x in parts):
        raise ValueError("Rectangle must contain x,y,width,height integers.")
    if parts[0] < 0 or parts[1] < 0 or parts[2] <= 0 or parts[3] <= 0:
        raise ValueError("Rectangle requires nonnegative position and positive size.")
    return parts


def filter_path(path):
    # Paths are ffmpeg filter values, never shell commands.
    return str(path.resolve()).replace("\\", "\\\\").replace(":", "\\:").replace("'", "'\\''")


def capture(args):
    if sys.platform != "darwin":
        raise ValueError("Capture uses macOS screencapture; export also works elsewhere.")
    # The native recording service may not inherit this process's working directory.
    args.output = args.output.expanduser().resolve()
    if not 1 <= args.seconds <= 1800 or args.display < 1:
        raise ValueError("Use 1–1800 capture seconds and a positive display number.")
    if args.output.exists():
        raise ValueError("Choose a new raw output path; recordings are not overwritten.")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    command = ["/usr/sbin/screencapture", "-v", "-V", str(args.seconds), "-D", str(args.display)]
    if args.rect:
        command += ["-R", ",".join(map(str, rectangle(args.rect)))]
    if args.clicks:
        command += ["-k"]
    command.append(str(args.output))
    print("Recording the visible display; keep Chrome in the foreground. No audio is captured.", flush=True)
    print("Wait for the requested duration and the saved-file confirmation; interrupting may discard the recording.", flush=True)
    subprocess.run(command, check=True)
    if not args.output.is_file() or args.output.stat().st_size == 0:
        raise ValueError("No recording was created; check macOS Screen Recording access.")
    print(json.dumps({"recording": str(args.output), "bytes": args.output.stat().st_size}))


def export(args):
    if args.output.exists() and not args.overwrite:
        raise ValueError("Output already exists; choose another name or use --overwrite.")
    source_duration = metadata(args.input)
    if args.segments:
        segments = json.loads(args.segments.read_text(encoding="utf-8"))
    else:
        segments = [{"start": args.start, "end": source_duration if args.end is None else args.end,
                     "seconds": args.seconds, "caption": args.caption}]
    if not isinstance(segments, list) or not segments:
        raise ValueError("Segments must be a nonempty JSON array.")
    total = 0.0
    for segment in segments:
        if not isinstance(segment, dict):
            raise ValueError("Each segment must be an object.")
        start, end, seconds = (float(segment[key]) for key in ("start", "end", "seconds"))
        if not (0 <= start < end <= source_duration + 0.1 and 0 < seconds <= 40):
            raise ValueError("Segment time ranges must fit the real source recording.")
        segment.update(start=start, end=end, seconds=seconds)
        total += seconds
    if not 30 <= total <= 40:
        raise ValueError("The edited video must total 30–40 seconds.")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    font = args.font
    if any(s.get("caption") for s in segments) and not font.is_file():
        raise ValueError("Provide --font with a font supporting the caption language.")
    with tempfile.TemporaryDirectory(prefix="visible-edit-") as temp:
        filters = []
        for index, segment in enumerate(segments):
            parts = [f"trim=start={segment['start']}:end={segment['end']}",
                     f"setpts={segment['seconds'] / (segment['end'] - segment['start'])}*(PTS-STARTPTS)"]
            crop = segment.get("crop", args.crop)
            if crop:
                x, y, width, height = rectangle(crop)
                segment["crop"] = [x, y, width, height]
                parts.append(f"crop={width}:{height}:{x}:{y}")
            # Redactions use pixels after crop and before scale.
            for box in segment.get("redactions", []):
                x, y, width, height = rectangle(box)
                parts.append(f"drawbox=x={x}:y={y}:w={width}:h={height}:color=black:t=fill")
            parts += ["scale=1600:900:force_original_aspect_ratio=decrease",
                      "pad=1600:900:(ow-iw)/2:(oh-ih)/2:color=0x102d2c", "setsar=1", "fps=30",
                      f"tpad=stop_mode=clone:stop_duration={segment['seconds']}",
                      f"trim=duration={segment['seconds']}", "setpts=PTS-STARTPTS"]
            if segment.get("caption"):
                text_path = Path(temp) / f"caption-{index}.txt"
                text_path.write_text(str(segment["caption"]), encoding="utf-8")
                parts += ["drawbox=x=0:y=812:w=1600:h=88:color=0x102d2c@0.96:t=fill",
                          f"drawtext=fontfile='{filter_path(font)}':textfile='{filter_path(text_path)}':expansion=none:fontcolor=white:fontsize=27:x=34:y=840"]
            filters.append(f"[0:v]{','.join(parts)}[s{index}]")
        filters.append("".join(f"[s{i}]" for i in range(len(segments))) +
                       f"concat=n={len(segments)}:v=1:a=0,format=yuv420p[out]")
        command = [ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", "-i", str(args.input),
                   "-filter_complex", ";".join(filters), "-map", "[out]", "-an", "-map_metadata", "-1",
                   "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-movflags", "+faststart", str(args.output)]
        subprocess.run(command, check=True)
    import imageio_ffmpeg
    frames, seconds = imageio_ffmpeg.count_frames_and_secs(str(args.output))
    if not 30 <= seconds <= 40:
        raise ValueError("Encoded duration is outside 30–40 seconds.")
    manifest = {"source_kind": "visible_screen_recording", "source_file": args.input.name,
                "source_duration_seconds": source_duration, "duration_seconds": seconds,
                "frames": frames, "resolution": [1600, 900], "audio": "none",
                "publication_status": "not_verified_by_recorder", "segments": segments,
                "note": "Real footage edited to the requested duration; publication requires separate page evidence."}
    args.output.with_suffix(".json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "duration_seconds": seconds, "frames": frames}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    record = commands.add_parser("capture", help="Record the visible macOS display without audio")
    record.add_argument("--output", required=True, type=Path)
    record.add_argument("--seconds", type=int, default=120)
    record.add_argument("--display", type=int, default=1)
    record.add_argument("--rect", help="Optional logical screen coordinates x,y,width,height")
    record.add_argument("--clicks", action="store_true")
    edit = commands.add_parser("export", help="Trim/edit real footage into a 30–40 second MP4")
    edit.add_argument("--input", required=True, type=Path)
    edit.add_argument("--output", required=True, type=Path)
    edit.add_argument("--segments", type=Path, help="JSON array with start/end/seconds/caption and optional crop/redactions")
    edit.add_argument("--start", type=float, default=0)
    edit.add_argument("--end", type=float)
    edit.add_argument("--seconds", type=float, default=36)
    edit.add_argument("--crop", help="Source pixel coordinates x,y,width,height")
    edit.add_argument("--caption", default="AutoPersona · 真實 Chrome 操作 · 商品狀態以蝦皮頁面為準")
    edit.add_argument("--font", type=Path, default=Path("/System/Library/Fonts/STHeiti Medium.ttc"))
    edit.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    try:
        capture(args) if args.command == "capture" else export(args)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
