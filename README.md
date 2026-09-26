# VidDoblaje

**Traducción y doblaje automático de vídeos al español — 100% local**

## Instalación

1. Descarga `VidDoblajeSetup.exe`
2. Doble clic para instalar (no requiere admin)
3. Abre VidDoblaje desde el menú inicio
4. Pulsa **TRADUCIR Y DOBLAR AL ESPAÑOL**
5. Agrega un vídeo (drag & drop)
6. Espera el procesamiento
7. Obtén el vídeo final

## Características

- **Pipeline completo**: análisis → transcripción → diarización → traducción → TTS → sincronización → subtítulos → mezcla → exportación
- **100% local**: sin APIs en la nube
- **CPU y GPU**: detección automática
- **Diarización sin HF token**: speechbrain (Apache 2.0)
- **Auto-descarga de modelos**: First Run Wizard
- **Checkpoints**: reanuda desde el último punto
- **Temas**: oscuro / claro / auto
- **Formatos**: MP4, MKV entrada; MP4, MKV salida

## Modelos base (auto-descargados)

| Modelo | Función | Licencia |
|--------|---------|----------|
| whisper-base | ASR | MIT |
| opus-mt-en-es | Traducción | CC-BY-4.0 |
| piper-es_ES-davefx-medium | TTS | MIT |
| speechbrain-ecapa | Diarización | Apache-2.0 |

## Build

```bash
./scripts/build.sh
```

## Licencia

MIT — ver [LICENSE.txt](LICENSE.txt)
