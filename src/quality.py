"""Panel de calidad para administradores: ejecuta la suite y las mediciones y muestra los resultados.

Seguridad y robustez (pensado para un servidor Linux):
- Solo se lanzan DOS trabajos fijos (`JOBS`); el navegador nunca envia comandos ni argumentos.
- Cada trabajo corre en un proceso hijo aparte, con una base de prueba propia (carpeta `sandbox`),
  sin DB_PATH, clave inicial ni APP_BASE_PATH del servidor: no toca la base real.
- Un solo trabajo a la vez, tambien entre procesos (archivo `running.lock` con caducidad).
- Cada trabajo tiene tiempo maximo; al vencer se termina el proceso hijo.
- Los resultados se guardan en `QUALITY_DIR` o, por defecto, en `<carpeta de DB_PATH>/quality`.
- Todo texto leido de archivos se escapa antes de mostrarse. No se muestran rutas ni trazas.
- Las acciones POST exigen un token anti-CSRF ligado a la sesion (ver `csrf_token`).
Solo biblioteca estandar.
"""
import hashlib
import hmac
import json
import os
import re
import secrets
import subprocess
import sys
import threading
import time
from datetime import datetime
from html import escape
from pathlib import Path

from src import db

ROOT = db.ROOT
DOCS = ROOT / 'docs'
SECRET = secrets.token_bytes(32)  # solo en memoria; los tokens caducan al reiniciar el servidor
MAX_BYTES = 300_000
DECISION_IDS = range(6, 11)

JOBS = {
    'suite': {
        'title': 'Suite de pruebas', 'file': 'suite.json', 'timeout': 900,
        'module': 'scripts.run_quality_suite', 'extra': [],
    },
    'bench': {
        'title': 'Mediciones de SQLite', 'file': 'benchmark.md', 'timeout': 1200,
        'module': 'scripts.benchmark_s3', 'extra': ['--count', '100000', '--runs', '5'],
    },
}
LOCK_TTL = max(job['timeout'] for job in JOBS.values()) + 120
STATE_LABELS = {'ok': 'Correcto', 'fallos': 'Terminó con fallos', 'error': 'Error al ejecutar',
                'timeout': 'Tiempo agotado'}

OPERATION_HELP = (
    ('Movimientos por rango de fecha', 'lista los movimientos de un mes; muestra el efecto del índice por fecha.'),
    ('Total de gasto por categoría', 'suma gastos agrupados por categoría en un mes.'),
    ('Actualización de un gasto por id', 'modifica una fila por clave primaria; sirve de control (no depende de índices).'),
)


def results_dir() -> Path:
    configured = os.environ.get('QUALITY_DIR', '').strip()
    return Path(configured).expanduser() if configured else db.db_path().parent / 'quality'


def csrf_token(session_token: str) -> str:
    return hmac.new(SECRET, b'quality:' + session_token.encode(), hashlib.sha256).hexdigest()


def csrf_valid(session_token: str, supplied: str) -> bool:
    return bool(session_token) and hmac.compare_digest(csrf_token(session_token), str(supplied))


def _lock_path() -> Path:
    return results_dir() / 'running.lock'


def running_job():
    """(nombre, inicio) del trabajo en curso o None. Un bloqueo caducado se considera abandonado."""
    lock = _lock_path()
    try:
        if time.time() - lock.stat().st_mtime > LOCK_TTL:
            lock.unlink(missing_ok=True)
            return None
        name, _, started = lock.read_text(encoding='utf-8').partition('|')
        return (name, float(started or lock.stat().st_mtime)) if name in JOBS else None
    except (OSError, ValueError):
        return None


def _acquire(job: str) -> bool:
    results_dir().mkdir(parents=True, exist_ok=True)
    for _ in range(2):
        try:
            fd = os.open(_lock_path(), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            running_job()  # retira el bloqueo si caduco
            if not _lock_path().exists():
                continue
            return False
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            handle.write(f'{job}|{time.time()}')
        return True
    return False


def _status_path() -> Path:
    return results_dir() / 'status.json'


def read_status() -> dict:
    try:
        data = json.loads(_status_path().read_text(encoding='utf-8'))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _write_status(job: str, entry: dict) -> None:
    data = read_status()
    data[job] = entry
    target = _status_path()
    temporary = target.with_name(target.name + '.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
    os.replace(temporary, target)


def _child_env() -> dict:
    """Entorno aislado: nada del servidor real (base, clave inicial, prefijo) llega al proceso hijo."""
    blocked = {'DB_PATH', 'FINANZAS_INITIAL_ADMIN_PASSWORD', 'APP_BASE_PATH'}
    env = {key: value for key, value in os.environ.items() if key not in blocked}
    sandbox = results_dir() / 'sandbox'
    sandbox.mkdir(parents=True, exist_ok=True)
    env['DB_PATH'] = str(sandbox / 'sandbox.sqlite3')
    return env


def _command(job: str, output: Path) -> list:
    spec = JOBS[job]
    return [sys.executable, '-m', spec['module'], '--output', str(output), *spec['extra']]


def start(job: str) -> str:
    """Lanza un trabajo conocido. Devuelve 'started', 'busy', 'unknown' o 'error'."""
    if job not in JOBS:
        return 'unknown'
    if not _acquire(job):
        return 'busy'
    try:
        output = results_dir() / (JOBS[job]['file'] + '.new')
        process = subprocess.Popen(_command(job, output), cwd=str(ROOT), env=_child_env(),
                                   stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL)
    except OSError:
        _release()
        return 'error'
    threading.Thread(target=_watch, args=(job, process, output, time.time()), daemon=True).start()
    return 'started'


def _watch(job: str, process, output: Path, started: float) -> None:
    final = results_dir() / JOBS[job]['file']
    state = 'error'
    try:
        try:
            code = process.wait(timeout=JOBS[job]['timeout'])
            state = 'ok' if code == 0 else ('fallos' if job == 'suite' and code == 1 else 'error')
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            state = 'timeout'
        if state in ('ok', 'fallos') and output.exists():
            os.replace(output, final)
        else:
            output.unlink(missing_ok=True)
            if state in ('ok', 'fallos'):
                state = 'error'  # termino sin producir resultados
        _write_status(job, {'estado': state, 'inicio': started, 'fin': time.time()})
    except OSError:
        pass
    finally:
        _release()


def _release() -> None:
    """Retira el bloqueo. Reintenta porque en Windows no se puede borrar un archivo que otro
    hilo esta leyendo en ese instante; si fallara, el bloqueo quedaria hasta caducar."""
    for _ in range(40):
        try:
            _lock_path().unlink(missing_ok=True)
            return
        except OSError:
            time.sleep(0.05)


def _read_text(path: Path):
    try:
        if path.stat().st_size > MAX_BYTES:
            return None
        return path.read_text(encoding='utf-8')
    except OSError:
        return None


def _stamp(value) -> str:
    try:
        return datetime.fromtimestamp(float(value)).strftime('%d/%m/%Y %H:%M:%S')
    except (TypeError, ValueError, OSError, OverflowError):
        return 'desconocida'


def load_suite():
    text = _read_text(results_dir() / JOBS['suite']['file'])
    try:
        data = json.loads(text) if text else None
    except ValueError:
        return None
    return data if isinstance(data, dict) and isinstance(data.get('archivos'), list) else None


def parse_benchmark(text: str) -> list:
    """Filas (operacion, escenario, ejecuciones, mediana) de la tabla de medianas."""
    rows = []
    for line in text.splitlines():
        if line.startswith('|') and ('con indices' in line or 'sin indices' in line):
            cells = [c.strip() for c in line.strip().strip('|').split('|')]
            if len(cells) >= 4:
                rows.append(tuple(cells[:4]))
    return rows


def parse_decisions(text: str) -> list:
    blocks = []
    for part in re.split(r'(?m)^## ', text):
        match = re.match(r'D-(\d{3}) \S+ (.+)', part)
        if match and int(match.group(1)) in DECISION_IDS:
            lines = [l.strip()[1:].strip() for l in part.splitlines()[1:] if l.strip().startswith('-')]
            blocks.append((f'D-{match.group(1)} \u2014 {match.group(2).strip()}', lines))
    return blocks


def _h(value) -> str:
    return escape(str(value), quote=True)


def _inline(text: str) -> str:
    safe = _h(text)
    safe = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', safe)
    return re.sub(r'`(.+?)`', r'<code>\1</code>', safe)


def _table(headers, rows) -> str:
    head = ''.join(f'<th>{_h(h)}</th>' for h in headers)
    body = ''.join('<tr>' + ''.join(f'<td>{_h(c)}</td>' for c in row) + '</tr>' for row in rows)
    return f'<div class="table-scroll"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def _run_form(job: str, csrf: str, busy: bool) -> str:
    return ('<form method="post" action="/admin/calidad/ejecutar" style="display:inline" class="quality-form">'
            f'<input type="hidden" name="job" value="{_h(job)}"><input type="hidden" name="csrf" value="{_h(csrf)}">'
            f'<button class="primary" type="submit"{" disabled" if busy else ""}>Ejecutar: {_h(JOBS[job]["title"])}</button></form>')


def _loading_panel(current) -> str:
    """Indicador visible mientras un trabajo corre (se oculta solo al terminar: la página se recarga)."""
    if not current:
        return ''
    title = _h(JOBS[current[0]]['title'])
    return ('<div class="quality-loading" role="status" aria-live="polite">'
            '<span class="spinner" aria-hidden="true"></span>'
            f'<div><strong>Ejecutando: {title}</strong>'
            f'<p class="help">Iniciado {_h(_stamp(current[1]))}. Puede tardar varios minutos; '
            'la página se actualiza sola al terminar.</p></div></div>')


def _status_line(job: str, status: dict, current) -> str:
    title = _h(JOBS[job]['title'])
    if current and current[0] == job:
        return f'<span class="pill neutral">{title}: en ejecución desde {_h(_stamp(current[1]))}</span>'
    entry = status.get(job)
    if not isinstance(entry, dict):
        return f'<span class="pill neutral">{title}: sin ejecuciones desde este servidor</span>'
    label = STATE_LABELS.get(entry.get('estado'), 'Desconocido')
    return f'<span class="pill neutral">{title}: {_h(label)} · {_h(_stamp(entry.get("fin")))}</span>'


def _suite_section(data) -> str:
    if not data:
        return ('<section class="panel"><h3>Resultados de las pruebas</h3><p class="help">Aún no hay resultados. '
                'Pulsa «Ejecutar: Suite de pruebas».</p></section>')
    rows, failing = [], []
    for item in data['archivos']:
        if not isinstance(item, dict):
            continue
        bad = int(item.get('fallos', 0)) + int(item.get('errores', 0))
        if bad:
            failing.append(str(item.get('archivo', '')))
        detail = '; '.join(f"{p.get('prueba', '')}: {p.get('detalle', '')}" for p in item.get('problemas', [])
                           if isinstance(p, dict))
        rows.append((item.get('archivo', ''), item.get('descripcion', ''), item.get('tests', 0),
                     'FALLA' if bad else 'OK', item.get('segundos', 0), detail))
    env = data.get('entorno', {}) if isinstance(data.get('entorno'), dict) else {}
    summary = 'Sin fallos' if not failing else 'Con fallos en: ' + ', '.join(failing)
    return ('<section class="panel table-panel"><h3>Resultados de las pruebas</h3>'
            f'<p><strong>{_h(data.get("total", 0))}</strong> pruebas en <strong>{len(rows)}</strong> archivos · {_h(summary)}.<br>'
            f'Generado: {_h(data.get("generado", ""))} · Duración total: {_h(data.get("segundos", ""))} s · '
            f'Python {_h(env.get("python", "?"))}, SQLite {_h(env.get("sqlite", "?"))}, {_h(env.get("sistema", "?"))}.</p>'
            + _table(['Archivo', 'Qué comprueba', 'Tests', 'Resultado', 'Segundos', 'Detalle de problemas'], rows)
            + '</section>')


def _bench_section() -> str:
    live = _read_text(results_dir() / JOBS['bench']['file'])
    rows = parse_benchmark(live) if live else []
    source = 'ejecución de este servidor'
    if not rows:
        fallback = _read_text(DOCS / 'seguimientos' / 'S3_mediciones.md')
        rows = parse_benchmark(fallback) if fallback else []
        source = 'informe del repositorio (medido en otro equipo)'
    if not rows:
        return ('<section class="panel"><h3>Mediciones de SQLite</h3><p class="help">Aún no hay mediciones. '
                'Pulsa «Ejecutar: Mediciones de SQLite».</p></section>')
    help_items = ''.join(f'<li><strong>{_h(n)}</strong>: {_h(t)}</li>' for n, t in OPERATION_HELP)
    return ('<section class="panel table-panel"><h3>Mediciones de SQLite (mediana en ms)</h3>'
            f'<p>Fuente: {_h(source)}. Cada operación se repite varias veces y se reporta la mediana. '
            'Los tiempos dependen del equipo: compara escenarios, no máquinas.</p>'
            f'<ul>{help_items}</ul>'
            + _table(['Operación', 'Escenario', 'Ejecuciones (ms)', 'Mediana (ms)'], rows) + '</section>')


def _decisions_section() -> str:
    text = _read_text(DOCS / 'decisiones.md')
    blocks = parse_decisions(text) if text else []
    if not blocks:
        return ''
    items = ''.join(f'<details class="subform"><summary><strong>{_h(title)}</strong></summary><ul>'
                    + ''.join(f'<li>{_inline(line)}</li>' for line in lines) + '</ul></details>'
                    for title, lines in blocks)
    return f'<section class="panel"><h3>Decisiones técnicas (D-006 a D-010)</h3>{items}</section>'


def content(csrf: str, notice: str = '') -> str:
    """Contenido HTML de /admin/calidad (el llamador lo envuelve con layout)."""
    current = running_job()
    status = read_status()
    busy = current is not None
    note = f'<p class="help" role="status">{_h(notice)}</p>' if notice else ''
    refresh = '<script>setTimeout(function(){location.reload()},4000)</script>' if busy else ''
    # Al pulsar, el botón se bloquea y aparece el indicador antes de que responda el servidor.
    refresh += ('<script>document.querySelectorAll(".quality-form").forEach(function(f){'
                'f.addEventListener("submit",function(){'
                'var b=f.querySelector("button");if(b){b.disabled=true;b.textContent="Iniciando…";}'
                'var p=document.createElement("div");p.className="quality-loading";p.setAttribute("role","status");'
                'p.innerHTML=\'<span class="spinner" aria-hidden="true"></span><div><strong>Iniciando trabajo…</strong>'
                '<p class="help">Espere mientras el servidor lo prepara.</p></div>\';'
                'f.parentNode.insertBefore(p,f);});});</script>')
    intro = ('<section class="panel"><p class="eyebrow">CALIDAD · SOLO ADMINISTRADORES</p>'
             '<h2>Pruebas, mediciones y decisiones</h2>'
             '<p>Las pruebas y mediciones se ejecutan en un proceso aparte con una base temporal: '
             '<strong>no modifican los datos reales</strong>. Solo corre un trabajo a la vez y cada uno tiene tiempo máximo. '
             'Mientras corren consumen CPU del servidor; evita lanzarlas en horas de uso intenso.</p>'
             f'{note}<p>{_run_form("suite", csrf, busy)} {_run_form("bench", csrf, busy)}</p>'
             f'{_loading_panel(current)}'
             f'<p>{_status_line("suite", status, current)} {_status_line("bench", status, current)}</p></section>')
    return intro + _suite_section(load_suite()) + _bench_section() + _decisions_section() + refresh

