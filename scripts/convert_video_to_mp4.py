from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

import imageio_ffmpeg


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert a demo WebM recording to MP4.")
    parser.add_argument("--input", default="docs/demo_video_draft_en.webm")
    parser.add_argument("--output", default="docs/demo_video_draft_en.mp4")
    parser.add_argument("--width", type=int, default=1280)
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    if not input_path.exists():
        raise FileNotFoundError(input_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    command = [
        ffmpeg,
        "-y",
        "-i",
        str(input_path),
        "-vf",
        f"scale={args.width}:-2",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(output_path),
    ]
    subprocess.run(command, check=True)
    print(f"MP4 written to {output_path}")


if __name__ == "__main__":
    main()
