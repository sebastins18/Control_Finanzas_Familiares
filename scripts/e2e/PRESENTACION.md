# Demostración S4 guiada por la voz existente

La grabación de presentación está separada de `run_e2e.py`. La voz aceptada es la de `evidencias/MisFinanzas_S4_Voz_Natural.mp4` (Juan Neural); se copia su AAC y se conservan los paquetes sin cambiar tono, velocidad ni calidad. No se ejecuta el generador TTS anterior ni se envían audio, video o datos a servicios externos.

## Preparación

Usar el checkout de MisFinanzas correspondiente al commit indicado en los reportes. Ejecutar desde la raíz en PowerShell con Python 3.12:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/e2e/setup.ps1
.\.venv-e2e\Scripts\python.exe -m pip install -r scripts/e2e/requirements-video.txt
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path $PWD '.venv-e2e\browsers'
```

Se necesitan FFmpeg y FFprobe locales. Esta ejecución usó el paquete essentials de Gyan dentro de `.venv-e2e/tools/ffmpeg/`; `media_common.py` también admite FFprobe en PATH y FFmpeg de imageio. No se distribuyen esos binarios en Git. El modelo local `Systran/faster-whisper-base` se descarga una vez, sin transmitir contenidos:

```powershell
$env:HF_HUB_DISABLE_XET = '1'
.\.venv-e2e\Scripts\python.exe -c "from faster_whisper import WhisperModel; WhisperModel('base', device='cpu', compute_type='int8', download_root='.venv-e2e/modelos')"
```

Mantener como entradas locales el MP4 con voz, `MisFinanzas_S4_Informe_Narracion_Natural.json`, el guion original y los 19 MP3/WAV en `evidencias/audio_generado/`. Los audios y videos grandes están excluidos de Git; deben obtenerse del paquete o del medio privado que acuerde el equipo. El ZIP final no es una distribución completa de la aplicación ni contiene modelos, entornos o bases.

## Ejecución reproducible

Los comandos usan `evidencias/s4_final` y directorios de trabajo nuevos. Para repetir sin sobrescribir evidencia anterior, usar otro `--output` y un `--work` nuevo; pasar el mismo destino a todos los scripts. Las funciones de resumen aceptan la carpeta de salida por API; el comando de este ejemplo corresponde a la entrega final predeterminada.

```powershell
.\.venv-e2e\Scripts\python.exe scripts/e2e/run_e2e.py --pace 0 --output evidencias/s4_final/reportes/e2e
.\.venv-e2e\Scripts\python.exe scripts/e2e/run_support_checks.py --output evidencias/s4_final/reportes/complementarias
.\.venv-e2e\Scripts\python.exe scripts/e2e/build_presentation_summary.py
.\.venv-e2e\Scripts\python.exe scripts/e2e/prepare_narration.py
.\.venv-e2e\Scripts\python.exe scripts/e2e/record_presentation.py --work .venv-e2e/presentacion/toma-final
```

Para una repetición completa sin sobrescribir la entrega actual:

```powershell
$destinoDemo = 'evidencias/s4-repeticion-' + (Get-Date -Format 'yyyyMMdd-HHmmss')
$tomaDemo = '.venv-e2e/presentacion/repeticion-' + (Get-Date -Format 'yyyyMMdd-HHmmss')
.\.venv-e2e\Scripts\python.exe scripts/e2e/run_e2e.py --pace 0 --output "$destinoDemo/reportes/e2e"
.\.venv-e2e\Scripts\python.exe scripts/e2e/run_support_checks.py --output "$destinoDemo/reportes/complementarias"
.\.venv-e2e\Scripts\python.exe scripts/e2e/build_presentation_summary.py --output $destinoDemo
.\.venv-e2e\Scripts\python.exe scripts/e2e/prepare_narration.py --output $destinoDemo
.\.venv-e2e\Scripts\python.exe scripts/e2e/record_presentation.py --coverage 2 --work $tomaDemo --output $destinoDemo
.\.venv-e2e\Scripts\python.exe scripts/e2e/merge_presentation_takes.py --base $tomaDemo --corrections $tomaDemo --output $destinoDemo
.\.venv-e2e\Scripts\python.exe scripts/e2e/record_csv_evidence.py --output $destinoDemo --work "$tomaDemo/csv"
.\.venv-e2e\Scripts\python.exe scripts/e2e/render_presentation.py --work $tomaDemo --output $destinoDemo --csv-coverage "$tomaDemo/csv/cobertura.json"
.\.venv-e2e\Scripts\python.exe scripts/e2e/review_presentation.py --output $destinoDemo
```

El servidor de presentación escucha exclusivamente en `127.0.0.1`, puerto libre asignado por Windows. Crea otra SQLite temporal antes de importar la aplicación, con credenciales aleatorias y datos ficticios. Todas las operaciones de negocio de la demostración pasan por formularios reales; el contraste SQL usa lectura. La base se elimina al terminar. No admite URL pública ni DB externa como destino de escritura.

La cámara usa Chromium completo, viewport y grabación nativa **1920 × 1080**, zoom de presentación 108 %, cursor gráfico que sigue los eventos reales y margen inferior para los subtítulos. No se escala un video 720p. Las páginas de la aplicación conservan su lógica y datos; únicamente se ajusta la presentación del navegador. Los desplazamientos usan visibilidad, condiciones de encuadre y pausas de lectura.

Cada escena incorpora una marca técnica en el preroll. Si el screencast no captura su breve aparición, el renderer usa la duración medida y la cola del clip como anclaje, lo declara en el EDL y exige comprobar visualmente la escena. El montaje excluye el preroll y las marcas. Las pausas de cobertura son grabaciones reales del navegador, sin congelados, bucles ni cambios de velocidad. Si el navegador tarda más de lo previsto, conservar la demora y generar cobertura adicional; nunca repetir automáticamente una escritura.

Una corrección selectiva adicional se puede generar así; la selección debe pasar a `merge_presentation_takes.py` mediante `--corrections`:

```powershell
.\.venv-e2e\Scripts\python.exe scripts/e2e/record_presentation.py --scenes 4,5,9,13,15 --handles 18 --coverage 2 --work .venv-e2e/presentacion/correcciones-01
.\.venv-e2e\Scripts\python.exe scripts/e2e/merge_presentation_takes.py
.\.venv-e2e\Scripts\python.exe scripts/e2e/render_presentation.py
.\.venv-e2e\Scripts\python.exe scripts/e2e/review_presentation.py
```

`merge_presentation_takes.py` guarda una selección explícita y cortes cronológicos de fuente a secuencia. FFmpeg recorta por fotogramas y conserva los segmentos a 1×; nunca usa `atempo`, ratios de duración ni fotogramas sintetizados. Revisar la selección si cambian el guion o las tomas. El registro de montaje y los fotogramas permiten auditar esos cortes.

`prepare_narration.py` contrasta los 19 segmentos con reconocimiento local. Los subtítulos usan límites de palabras reconocidas y grupos de frase, sin estimar tiempos por cantidad de palabras. Los errores ortográficos y las alucinaciones de cola se documentan; no alteran la pista de voz. La versión subtitulada lleva texto incrustado: desactivar el SRT externo al reproducirla para evitar duplicados.

## Revisión y publicación

Revisar las muestras de cada escena y las transiciones con el guion. Documentar la revisión en `reportes/revision_visual_19.json`; la validación declara expresamente si no hubo escucha humana. FFprobe comprueba pistas, códecs y duración; FFmpeg decodifica ambos MP4 y compara uno a uno los paquetes AAC con el master. La detección de silencio identifica las pausas originales sin añadir otras.

Los resultados 27/27, 109/109, 1.000 registros, instalación y respaldo proceden de archivos ejecutados, no de pantallas inventadas. El visor CSV está rotulado como evidencia local y muestra el archivo descargado; el resumen final es un informe de QA separado de la aplicación. La portada lateral está rotulada como editorial.

Publicar los dos MP4 y el ZIP por el medio acordado con el equipo, comprobar permisos del profesor y después incorporar las URL en README y `portal.yml`. Esta tarea no hace esa publicación, push, merge, tags ni cambios en CRNube. La instalación independiente, la revisión del grupo y la evaluación docente permanecen diferenciadas de las pruebas automáticas.
