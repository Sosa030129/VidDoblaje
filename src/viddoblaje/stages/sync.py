"""Stage: sincronización temporal."""
from __future__ import annotations
from pathlib import Path
from viddoblaje.core.project import Project
from viddoblaje.utils import get_logger
from viddoblaje.utils.ffmpeg import run_ffmpeg, probe_video

log = get_logger(__name__)


def _get_wav_duration(path: Path) -> float:
    try:
        info = probe_video(path)
        return float(info.get("format", {}).get("duration", 0))
    except Exception:
        try:
            return path.stat().st_size / 32.0
        except Exception:
            return 0.0


def _time_stretch(input_wav, output_wav, target_duration_sec, current_duration_sec):
    if current_duration_sec <= 0 or target_duration_sec <= 0:
        run_ffmpeg(["-y", "-i", str(input_wav), "-c", "copy", str(output_wav)])
        return
    ratio = current_duration_sec / target_duration_sec
    if abs(ratio - 1.0) < 0.05:
        run_ffmpeg(["-y", "-i", str(input_wav), "-c", "copy", str(output_wav)])
        return
    run_ffmpeg(["-y", "-i", str(input_wav), "-filter:a", f"atempo={ratio:.4f}", "-vn", str(output_wav)])


def _pad_silence(input_wav, output_wav, pad_start_sec, pad_end_sec):
    if pad_start_sec <= 0 and pad_end_sec <= 0:
        run_ffmpeg(["-y", "-i", str(input_wav), "-c", "copy", str(output_wav)])
        return
    parts = []
    if pad_start_sec > 0:
        sil_start = output_wav.parent / "_silence_start.wav"
        run_ffmpeg(["-y", "-f", "lavfi", "-i", f"anullsrc=channel_layout=mono:sample_rate=16000", "-t", f"{pad_start_sec:.3f}", str(sil_start)])
        parts.append(sil_start)
    parts.append(input_wav)
    if pad_end_sec > 0:
        sil_end = output_wav.parent / "_silence_end.wav"
        run_ffmpeg(["-y", "-f", "lavfi", "-i", f"anullsrc=channel_layout=mono:sample_rate=16000", "-t", f"{pad_end_sec:.3f}", str(sil_end)])
        parts.append(sil_end)
    concat_file = output_wav.parent / "_concat.txt"
    with open(concat_file, "w", encoding="utf-8") as f:
        for p in parts:
            f.write(f"file '{p.absolute()}\n'")
    run_ffmpeg(["-y", "-f", "concat", "-safe", "0", "-i", str(concat_file), "-c", "copy", str(output_wav)])
    for p in parts:
        if p != input_wav:
            try: p.unlink()
            except Exception: pass
    try: concat_file.unlink()
    except Exception: pass


def run(project: Project) -> dict:
    log.info("Stage: sincronización temporal")
    synced_dir = project.audio_dir / "synced_voices"
    synced_dir.mkdir(exist_ok=True)
    too_long_count = 0
    for seg in project.meta.segments:
        if not seg.voice_path:
            continue
        in_wav = project.root / seg.voice_path
        if not in_wav.exists():
            continue
        target_dur = seg.end_sec - seg.start_sec
        current_dur = _get_wav_duration(in_wav)
        out_wav = synced_dir / f"seg_{seg.index:04d}.wav"
        if current_dur > target_dur * 1.05:
            if current_dur > target_dur * 1.5:
                too_long_count += 1
            _time_stretch(in_wav, out_wav, target_dur, current_dur)
        elif current_dur < target_dur * 0.95:
            diff = target_dur - current_dur
            _pad_silence(in_wav, out_wav, diff / 2, diff / 2)
        else:
            run_ffmpeg(["-y", "-i", str(in_wav), "-c", "copy", str(out_wav)])
        seg.voice_path = str(out_wav.relative_to(project.root))
        seg.status = "synced"
    if too_long_count > 0:
        log.warning("{} segmentos requirieron time-stretch agresivo", too_long_count)
    project.save()
    return {"num_synced": len(project.meta.segments), "too_long_count": too_long_count}
