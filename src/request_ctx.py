"""Estado por solicitud compartido por toda la aplicación.

Vive en su propio módulo a propósito: al ejecutar `python -m src.app`, `src/app.py` se carga como
`__main__` y `src/extension.py` vuelve a importarlo como `src.app` (otra copia del módulo). Si el
rol se guardara en `app.py`, cada copia tendría su propio estado y las páginas generadas desde
`extension.py` mostrarían un menú distinto. Este módulo se importa una sola vez, así que el valor
es único para ambas copias.
"""
import threading

_ctx = threading.local()


def set_admin(value: bool) -> None:
    _ctx.admin = bool(value)


def is_admin() -> bool:
    """True solo si la solicitud en curso pertenece a un administrador activo."""
    return bool(getattr(_ctx, 'admin', False))
