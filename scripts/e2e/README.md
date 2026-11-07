# E2E real de MisFinanzas — Windows

Requiere Python 3.12, acceso a internet para descargar dependencias y espacio para Chromium y video. Ejecutar desde la raíz del repositorio. La aplicación sigue usando solo la biblioteca estándar; las dependencias de QA viven en `.venv-e2e/`, ignorada por Git.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/e2e/setup.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/e2e/run.ps1
```

El destino predeterminado es una carpeta nueva `evidencias/s4-AAAAMMDD-HHMMSS`. El recorrido grabado dura aproximadamente 4 minutos, según el equipo, y genera PNG auténticos, WebM, MP4 H.264, CSV descargados, JSON, HTML y Markdown. No requiere FFmpeg del sistema: se usa el binario local de `imageio-ffmpeg`.

Para un diagnóstico rápido sin video:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/e2e/run.ps1 -Quick
```

Comandos directos, dentro del entorno preparado:

```powershell
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path $PWD '.venv-e2e\browsers'
.\.venv-e2e\Scripts\python.exe scripts/e2e/run_e2e.py --record --pace 10 --output evidencias/s4-repeticion
.\.venv-e2e\Scripts\python.exe scripts/e2e/run_support_checks.py --output evidencias/s4-repeticion/reportes
```

Las verificaciones adicionales se ejecutan después del recorrido para evitar competencia de recursos durante la grabación. Incluyen la suite existente, la instalación limpia y una carga idempotente de 1.000 registros en otra base temporal. Sus resultados se contabilizan por separado de las 27 comprobaciones E2E.

La única comprobación pública disponible es optativa y de lectura:

```powershell
.\.venv-e2e\Scripts\python.exe scripts/e2e/check_public_login.py --output evidencias/s4-repeticion/reportes/login_publico.json
```

Ese script fija exactamente la URL del login, ejecuta GET, no sigue redirecciones, no inicia sesión y no guarda el contenido ni cookies. No existe una opción para apuntar las pruebas de escritura a una URL pública.

El runner crea su propia base dentro de `TemporaryDirectory`, fija `DB_PATH` únicamente en su proceso antes de importar la aplicación y escucha en `127.0.0.1` con puerto asignado por el sistema. Usa `APP_BASE_PATH=/finanzas`. Inicializa una cuenta estándar ficticia y su perfil como fixture; los movimientos, categorías y presupuestos se operan desde formularios reales. Las consultas de contraste abren SQLite en modo de solo lectura. Al finalizar cierra servidor, navegador y registros, restaura el entorno del proceso y elimina la base temporal.

No reutiliza credenciales del proyecto ni de CRNube. Genera contraseñas aleatorias en memoria, nunca las imprime ni las incorpora a reportes. No habilita tracing, HAR, exportación de cookies ni estados de sesión. El campo de contraseña aparece enmascarado en el video. Los resultados sintéticos y los CSV no contienen información personal real.

La suite es un recorrido secuencial: si falla un paso, registra el fallo y omite los dependientes; no hace reintentos de escrituras. Los informes se guardan durante la ejecución. Una carpeta de destino con contenido se rechaza para conservar las evidencias anteriores. La grabación usa Chromium completo en modo headless, viewport 1280 × 720 y zona `America/Costa_Rica`.

`playwright.html` es el informe de la suite Python que controla Playwright. El reporter HTML de Playwright Test para Node no forma parte de este proyecto. La página final del video es este informe real de QA, distinguido de la aplicación.

La captura completa de página puede ser más alta que 720 píxeles; el video conserva 1280 × 720. El script omite deliberadamente la validación HTML en E23 para comprobar el rechazo HTTP 400 del backend. No modifica el código de la aplicación.

## ZIP de evidencias

El ZIP final conserva `scripts/e2e/` y `evidencias/s4/`. Se necesita el repositorio de MisFinanzas para repetir la suite; no es una distribución completa de la aplicación. Extraer o copiar `scripts/e2e/` sobre el mismo directorio del checkout identificado en el informe. No ejecutar el runner fuera de esa estructura, porque resuelve la raíz a partir de su ubicación.

Los scripts `run_e2e.py`, `run_support_checks.py` y `check_public_login.py` permiten repetir las verificaciones por separado. El empaquetado final usa `package_evidence.py`; consultar `--help` para las carpetas de entrada. No publica el video, no crea commits ni tags y no envía datos a servicios de generación multimedia.
