"""Caché en memoria de páginas de solo lectura, usada únicamente como respaldo si SQLite falla.

No se usa para escrituras ni se sirve mientras la base responde con normalidad.
"""
import threading
import time

MAX_AGE_SECONDS = 600
MAX_ENTRIES = 200
_lock = threading.Lock()
_entries = {}


def store(key, body):
    with _lock:
        if len(_entries) >= MAX_ENTRIES and key not in _entries:
            _entries.pop(min(_entries, key=lambda k: _entries[k][0]))
        _entries[key] = (time.time(), body)


def fetch(key):
    """Devuelve (cuerpo, antigüedad en segundos) o None si no hay copia vigente."""
    with _lock:
        entry = _entries.get(key)
    if not entry:
        return None
    age = time.time() - entry[0]
    return (entry[1], int(age)) if age <= MAX_AGE_SECONDS else None


def clear():
    with _lock:
        _entries.clear()


def stale_banner(age):
    return ('<div class="notice-strip" role="alert">⚠ La base de datos no responde. '
            f'Se muestran datos de hace {age} s; no se guardarán cambios hasta que se restablezca.</div>').encode('utf-8')
