"""Clientes HTTP de prueba que envían el token CSRF igual que el navegador.

La aplicación inyecta <input type="hidden" name="csrf"> en cada formulario POST de una página con sesión.
Este procesador agrega ese mismo campo a los POST urlencoded de urllib cuando hay sesión y el cuerpo
no trae ya un campo csrf (las pruebas que validan el rechazo envían el suyo propio o usan un cliente sin él).
"""
from http.cookiejar import CookieJar
from urllib.parse import parse_qs
from urllib.request import BaseHandler, HTTPCookieProcessor, build_opener

from src import quality


def session_csrf(jar):
    for cookie in jar:
        if cookie.name == 'finanzas_session' and cookie.value:
            return quality.csrf_token(cookie.value)
    return ''


def opener_csrf(opener):
    """Token CSRF de la sesión guardada en un opener (para cuerpos multipart armados a mano)."""
    for handler in opener.handlers:
        if isinstance(handler, HTTPCookieProcessor):
            return session_csrf(handler.cookiejar)
    return ''


class CsrfProcessor(BaseHandler):
    handler_order = 400  # antes de que urllib calcule Content-Length del cuerpo

    def __init__(self, jar):
        self.jar = jar

    def http_request(self, request):
        body = request.data
        content_type = request.get_header('Content-type') or ''
        if isinstance(body, bytes) and not content_type.lower().startswith('multipart/'):
            token = session_csrf(self.jar)
            if token and 'csrf' not in parse_qs(body.decode('utf-8', 'replace'), keep_blank_values=True):
                request.data = body + (b'&' if body else b'') + b'csrf=' + token.encode()
                request.remove_header('Content-length')
                request.remove_header('Content-Length')
        return request

    https_request = http_request


def csrf_opener(jar=None, *handlers):
    jar = jar if jar is not None else CookieJar()
    return build_opener(HTTPCookieProcessor(jar), CsrfProcessor(jar), *handlers)
