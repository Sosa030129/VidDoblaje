"""Genera vídeos sintéticos para tests."""
from __future__ import annotations
import argparse
from pathlib import Path
from viddoblaje.utils.ffmpeg import run_ffmpeg


def make_sine_video(out_path, duration_sec=5.0, freq=440.0, color="blue"):
    run_ffmpeg(["-y", "-f", "lavfi", "-i", f"color=c={color}:s=640x360:d={duration_sec}:r=25",
                "-f", "lavfi", "-i", f"sine=frequency={freq}:duration={duration_sec}:sample_rate=16000",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "ultrafast",
                "-c:a", "aac", "-b:a", "128k", "-shortest", str(out_path)])


def make_speech_like_video(out_path, duration_sec=8.0):
    import subprocess
    audio = out_path.parent / "_speech_audio.wav"
    filter_complex = f"sine=frequency=200:duration={duration_sec}:sample_rate=16000,volume='0.5+0.5*sin(2*PI*3*t)':eval=frame"
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", filter_complex, "-t", str(duration_sec), str(audio)],
                   check=True, capture_output=True)
    run_ffmpeg(["-y", "-f", "lavfi", "-i", f"color=c=red:s=640x360:d={duration_sec}:r=25",
                "-i", str(audio), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "ultrafast",
                "-c:a", "aac", "-b:a", "128k", "-shortest", str(out_path)])
    audio.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description="Genera vídeos de prueba")
    parser.add_argument("--out-dir", default="tests/fixtures")
    parser.add_argument("--speech", action="store_true")
    args = parser.parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if args.speech:
        p = out_dir / "test_speech.mp4"
        make_speech_like_video(p, duration_sec=6.0)
        print(f"OK: {p}")
    else:
        p = out_dir / "test_short.mp4"
        make_sine_video(p, duration_sec=5.0)
        print(f"OK: {p}")


if __name__ == "__main__":
    main()
