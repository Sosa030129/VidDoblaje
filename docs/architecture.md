# Arquitectura

VidDoblaje sigue un patrón de pipeline con checkpoints. Cada stage puede fallar y reanudarse independientemente.

## Estructura

```
src/viddoblaje/
├── __main__.py          # Entry point
├── cli.py               # CLI mode
├── config.py            # Settings
├── pipeline.py          # Orquestador
├── core/
│   ├── hardware.py      # Detección HW
│   ├── project.py       # Modelo de datos
│   ├── checkpoint.py    # Checkpoints
│   ├── queue_manager.py # Cola
│   └── model_manager.py # Modelos IA
├── stages/
│   ├── analysis.py
│   ├── audio_extraction.py
│   ├── asr.py           # Whisper
│   ├── diarization.py   # speechbrain
│   ├── translation.py   # MarianMT
│   ├── tts.py           # Piper
│   ├── sync.py
│   ├── subtitles.py
│   ├── mix.py
│   └── export.py
├── ui/
│   ├── app.py
│   ├── main_window.py
│   ├── processor.py
│   ├── first_run.py     # Wizard
│   ├── model_manager_ui.py
│   ├── settings.py
│   └── translation_editor.py
└── utils/
    └── ffmpeg.py
```

## Pipeline

10 stages en orden: analysis → audio_extraction → transcription → diarization → translation → voice_generation → sync → subtitles → mix → export

Cada stage guarda un checkpoint. Si falla, reanuda desde el último válido.

## Diarización

Usa **speechbrain** (Apache 2.0) por defecto, sin requerir HF token.
pyannote 3.1 es opcional (mejor calidad pero requiere licencia HF).
