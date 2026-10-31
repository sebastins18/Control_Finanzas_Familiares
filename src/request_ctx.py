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


def set_quality_admin(value: bool) -> None:
    _ctx.quality_admin = bool(value)


def is_quality_admin() -> bool:
    """True si la solicitud pertenece a un administrador activo (panel de calidad)."""
    return bool(getattr(_ctx, 'quality_admin', False))


def set_user_id(value):
    _ctx.user_id = int(value)
    _ctx.profile = None


def user_id():
    return getattr(_ctx, 'user_id', 1)


def set_identity(name='', role=''):
    _ctx.identity = (str(name), str(role))


def identity():
    return getattr(_ctx, 'identity', ('', ''))


def set_profile(profile):
    _ctx.profile = dict(profile) if profile else None


def profile_id():
    profile=getattr(_ctx,'profile',None)
    return profile['id_perfil'] if profile else user_id()


def profile():
    return getattr(_ctx,'profile',None)


def is_owner():
    selected=profile()
    return bool(selected and selected['es_propietario'])
