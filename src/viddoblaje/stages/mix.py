"""Stage: mezcla de audio."""
from __future__ import annotations
from pathlib import Path
from viddoblaje.core.project import Project
from viddoblaje.utils import get_logger
from viddoblaje.utils.ffmpeg import run_ffmpeg, get_video_duration

log = get_logger(__name__)


def _build_concat_list(segments, project):
    concat_file = project.audio_dir / "_voices_concat.txt"
    segments_dir = project.audio_dir / "synced_voices"
    silence_dir = project.cache_dir / "silences"
    silence_dir.mkdir(parents=True, exist_ok=True)
    entries = []
    last_end = 0.0
    for seg in segments:
        if not seg.voice_path:
            continue
        voice = project.root / seg.voice_path
        gap = seg.start_sec - last_end
        if gap > 0.05:
            sil_path = silence_dir / f"sil_{int(last_end*1000):08d}.wav"
            if not sil_path.exists():
                run_ffmpeg(["-y", "-f", "lavfi", "-i", f"anullsrc=channel_layout=mono:sample_rate=16000", "-t", f"{gap:.3f}", str(sil_path)])
            entries.append(sil_path)
        entries.append(voice)
        last_end = seg.end_sec
    with open(concat_file, "w", encoding="utf-8") as f:
        for p in entries:
            f.write(f"file '{p.absolute()}\n'")
    return concat_file


def run(project, mix_original_audio=True, voice_gain_db=0.0, original_gain_db=-6.0, normalize=True):
    log.info("Stage: mezcla de audio")
    segments = [s for s in project.meta.segments if s.voice_path]
    if not segments:
        raise RuntimeError("No hay segmentos con voz generada para mezclar")
    concat_file = _build_concat_list(segments, project)
    voices_track = project.audio_dir / "voices_full.wav"
    run_ffmpeg(["-y", "-f", "concat", "-safe", "0", "-i", str(concat_file), "-c", "copy", str(voices_track)])
    voices_48k = project.audio_dir / "voices_48k.wav"
    run_ffmpeg(["-y", "-i", str(voices_track), "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", str(voices_48k)])
    final_mix = project.audio_dir / "final_mix.wav"
    audio_48k = project.audio_dir / "audio_48k_stereo.wav"
    if mix_original_audio and audio_48k.exists():
        inputs = ["-i", str(voices_48k), "-i", str(audio_48k)]
        filter_complex = f"[0:a]volume={voice_gain_db}dB[v];[1:a]volume={original_gain_db}dB[o];[v][o]amix=inputs=2:duration=longest:dropout_transition=0[a]"
        run_ffmpeg(["-y", *inputs, "-filter_complex", filter_complex, "-map", "[a]", "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", str(final_mix)])
    else:
        run_ffmpeg(["-y", "-i", str(voices_48k), "-c", "copy", str(final_mix)])
    if normalize:
        normalized = project.audio_dir / "final_mix_norm.wav"
        run_ffmpeg(["-y", "-i", str(final_mix), "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", str(normalized)])
        final_mix.unlink()
        normalized.rename(final_mix)
    for tmp in [voices_track, voices_48k, concat_file]:
        try: tmp.unlink()
        except Exception: pass
    import shutil
    silence_dir = project.cache_dir / "silences"
    if silence_dir.exists():
        shutil.rmtree(silence_dir, ignore_errors=True)
    return {"output": str(final_mix.relative_to(project.root)), "duration_sec": get_video_duration(final_mix)}
