"""Ejecuta la suite de tests/ y guarda un resumen JSON por archivo de prueba.

Uso: python -m scripts.run_quality_suite [--output ruta.json]

El resumen no incluye trazas ni rutas internas: solo cuantas pruebas hubo por archivo, su
resultado, su duracion y, si algo fallo, la ultima linea del error. Ademas, por cada prueba
("pruebas"): clase y metodo, que significa (su docstring), con que funciones de la aplicacion
se logro (analisis estatico de su codigo: llamadas a src/ y scripts/, y rutas HTTP con la
funcion que las atiende), resultado y duracion. Cada prueba usa su propia
base temporal, asi que no toca data/finanzas.sqlite3. Solo biblioteca estandar.
Codigo de salida: 0 si todo pasa, 1 si hay fallos o errores.
"""
import argparse
import ast
import inspect
import io
import json
import os
import platform
import re
import sqlite3
import sys
import time
import traceback
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MAX_PROBLEMS_PER_FILE = 5
MAX_FUNCTIONS_PER_TEST = 8

# «Con qué se logró»: se analiza el código de cada prueba (AST, sin ejecutarlo de nuevo) para listar
# las funciones de la aplicación que llama directamente y las rutas HTTP que usa, traducidas a la
# función que atiende cada ruta. Así el detalle no depende de una lista mantenida a mano por prueba.
APP_PACKAGES = ('src', 'scripts')
IGNORED_CALLS = {'db.connect', 'db.db_path', 'quality.results_dir', 'quality.csrf_token'}
IGNORED_PREFIXES = ('request_ctx.',)
ROUTE_FUNCTIONS = (
    (r'/(\?.*)?', 'app.dashboard_page()'),
    (r'/movimientos', 'db.save_movement()'),
    (r'/movimientos/[^/]+/actualizar', 'db.save_movement()'),
    (r'/movimientos/[^/]+/eliminar', 'db.remove_movement()'),
    (r'/presupuestos', 'db.save_budget()'),
    (r'/historial\.csv.*', 'reportes.history_csv()'),
    (r'/historial.*', 'reportes.history_page()'),
    (r'/reportes/anual\.csv.*', 'reportes.annual_csv()'),
    (r'/reportes/anual.*', 'reportes.annual_page()'),
    (r'/admin/usuarios/guardar', 'Handler.do_POST → auth.save_users()'),
    (r'/admin/usuarios.*', 'app.users_page()'),
    (r'/admin/cambiar-clave', 'Handler.do_POST → auth.hash_password()'),
    (r'/admin/calidad/ejecutar', 'quality.start()'),
    (r'/admin/calidad.*', 'quality.content()'),
    (r'/admin/[a-z_]+(/[^/]+)?/guardar', 'extension.save()'),
    (r'/admin/[a-z_]+/[^/]+/eliminar', 'extension.delete()'),
    (r'/admin/[a-z_]+.*', 'extension.page()'),
    (r'/login.*', 'Handler.do_POST (inicio de sesión) → auth.hash_password()'),
    (r'/registro.*', 'auth.register()'),
    (r'/logout', 'Handler.do_POST (cierre de sesión)'),
    (r'/perfiles/elegir', 'profiles.selection_page()'),
    (r'/perfiles/seleccionar', 'profiles.access()'),
    (r'/perfiles/crear', 'profiles.create()'),
    (r'/perfiles/[^/]+/guardar', 'profiles.rename()'),
    (r'/perfiles/[^/]+/invitar', 'profiles.invite()'),
    (r'/perfiles/[^/]+/integrantes/[^/]+/eliminar', 'profiles.remove_member()'),
    (r'/perfiles/[^/]+/eliminar', 'profiles.delete()'),
    (r'/perfiles', 'profiles.page()'),
    (r'/comprobantes/subir', 'extension.upload_receipt()'),
    (r'/comprobantes/[^/]+/eliminar', 'extension.delete_receipt()'),
    (r'/comprobantes/[^/]+/archivo', 'Handler.do_GET (archivo de comprobante)'),
    (r'/comprobantes', 'extension.receipts_page()'),
    (r'/recurrentes/generar', 'recurrentes.generate()'),
    (r'/alertas/[^/]+/leida', 'Handler.do_POST (marcar alerta como leída)'),
    (r'/health', 'Handler.do_GET (/health)'),
)


def _route_function(text):
    if text.startswith(('scripts/', 'scripts\\')) and text.endswith('.py'):
        return f'Script {text.replace(chr(92), "/")}'
    if text.startswith(('http://', 'https://')):
        text = '/' + text.split('/', 3)[3] if text.count('/') >= 3 else '/'
    if not text.startswith('/'):
        return None
    path = text[len('/finanzas'):] if text.startswith('/finanzas/') else text
    for pattern, label in ROUTE_FUNCTIONS:
        if re.fullmatch(pattern, path):
            return f'Ruta {path.split("?")[0]} → {label}'
    return None


def _string_value(node):
    """Texto de una constante o f-string; las partes variables se reemplazan por 1."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return ''.join(v.value if isinstance(v, ast.Constant) else '1' for v in node.values)
    return None


class _CodeIndex:
    """Por módulo de prueba: funciones de la app usadas por cada función (y sus ayudantes del mismo módulo)."""

    def __init__(self):
        self._modules = {}

    def _imports(self, tree):
        names = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and node.module.split('.')[0] in APP_PACKAGES:
                parts = node.module.split('.')
                for alias in node.names:
                    local = alias.asname or alias.name
                    if len(parts) == 1:          # from src import db  -> db.*
                        names[local] = ('module', alias.name if parts[0] == 'src' else f'{parts[0]}.{alias.name}')
                    else:                        # from src.app import x -> app.x
                        prefix = parts[-1] if parts[0] == 'src' else '.'.join(parts)
                        names[local] = ('function', f'{prefix}.{alias.name}')
        return names

    def _direct(self, func, imports):
        found, helpers, ignored = [], set(), []
        for default in func.args.defaults + [d for d in func.args.kw_defaults if d is not None]:
            text = _string_value(default)          # p. ej. def post(self, fields, route='/registro')
            route = _route_function(text) if text else None
            if route:
                found.append(route)
        for node in ast.walk(func):
            if isinstance(node, ast.Call):
                target = node.func
                label = None
                if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name):
                    kind = imports.get(target.value.id)
                    if kind and kind[0] == 'module':
                        label = f'{kind[1]}.{target.attr}'
                    elif target.value.id == 'self':
                        helpers.add(target.attr)
                elif isinstance(target, ast.Attribute) and isinstance(target.value, ast.Attribute) \
                        and isinstance(target.value.value, ast.Name) and imports.get(target.value.value.id, ('',))[0] == 'module':
                    label = f'{imports[target.value.value.id][1]}.{target.value.attr}.{target.attr}'
                elif isinstance(target, ast.Name) and imports.get(target.id, ('',))[0] == 'function':
                    label = imports[target.id][1]
                if label and (label in IGNORED_CALLS or label.startswith(IGNORED_PREFIXES)):
                    ignored.append(label + '()')
                elif label:
                    found.append(label + '()')
                # Rutas y scripts: solo cadenas pasadas como argumento (self.get('/x'), Request(self.base + '/x'), …).
                for arg in list(node.args) + [k.value for k in node.keywords]:
                    for candidate in (arg.right if isinstance(arg, ast.BinOp) else arg,
                                      *(arg.elts if isinstance(arg, (ast.List, ast.Tuple)) else ())):
                        text = _string_value(candidate)
                        if text and len(text) < 160:
                            route = _route_function(text)
                            if route:
                                found.append(route)
        # Si la prueba solo usa llamadas de infraestructura (p. ej. db.connect), esas son lo que verifica.
        return (found or ignored), helpers

    def module(self, name):
        if name not in self._modules:
            index = {}
            try:
                source = inspect.getsource(sys.modules[name])
                tree = ast.parse(source)
            except (KeyError, OSError, TypeError, SyntaxError):
                tree = None
            if tree is not None:
                imports = self._imports(tree)
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        index[node.name] = self._direct(node, imports)
            self._modules[name] = index
        return self._modules[name]

    def functions_for(self, module_name, method):
        index = self.module(module_name)
        if method not in index:
            return []
        found, helpers = index[method]
        result = list(found)
        for helper in sorted(helpers):          # un nivel de ayudantes (self.post, self.add, …)
            if helper in index and not helper.startswith('test'):
                result.extend(index[helper][0])
        unique = list(dict.fromkeys(result))
        relevant = [f for f in unique if f[:-2] not in IGNORED_CALLS and not f.startswith(IGNORED_PREFIXES)]
        return (relevant or unique)[:MAX_FUNCTIONS_PER_TEST]


CODE_INDEX = _CodeIndex()


def _module_of(test):
    module = type(test).__module__
    if module == 'unittest.loader':  # modulo que no se pudo importar
        return getattr(test, '_testMethodName', 'importacion')
    return module


class Collector(unittest.TextTestResult):
    """Acumula resultados por modulo de prueba."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.modules = {}
        self._started = 0.0

    def _row(self, test):
        name = _module_of(test)
        return self.modules.setdefault(name, {
            'archivo': name, 'tests': 0, 'ok': 0, 'fallos': 0, 'errores': 0,
            'omitidos': 0, 'segundos': 0.0, 'problemas': [], 'pruebas': []})

    def _entry(self, test):
        """Detalle por prueba: método, qué significa (docstring) y con qué funciones de la app se logró."""
        row = self._row(test)
        method = getattr(test, '_testMethodName', str(test))
        if not row['pruebas'] or row['pruebas'][-1]['_id'] != id(test):
            module = type(test).__module__
            row['pruebas'].append({
                '_id': id(test), 'clase': type(test).__name__, 'prueba': method,
                'significado': (test.shortDescription() or '') if hasattr(test, 'shortDescription') else '',
                'funciones': CODE_INDEX.functions_for(module, method) if module != 'unittest.loader' else [],
                'resultado': 'ok', 'segundos': 0.0, 'detalle': ''})
        return row['pruebas'][-1]

    def startTest(self, test):
        super().startTest(test)
        self._started = time.perf_counter()
        self._row(test)['tests'] += 1
        self._entry(test)

    def stopTest(self, test):
        elapsed = time.perf_counter() - self._started
        self._row(test)['segundos'] += elapsed
        self._entry(test)['segundos'] = round(elapsed, 3)
        super().stopTest(test)

    def addSuccess(self, test):
        super().addSuccess(test)
        self._row(test)['ok'] += 1

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self._row(test)['omitidos'] += 1
        entry = self._entry(test)
        entry['resultado'], entry['detalle'] = 'omitida', str(reason)[:300]

    def _problem(self, test, err, key):
        row = self._row(test)
        row[key] += 1
        text = ''.join(traceback.format_exception_only(err[0], err[1])).strip()
        text = (text.replace(str(ROOT), '<proyecto>').splitlines()[-1:] or [''])[0][:300]
        entry = self._entry(test)
        entry['resultado'], entry['detalle'] = ('fallo' if key == 'fallos' else 'error'), text
        if len(row['problemas']) < MAX_PROBLEMS_PER_FILE:
            row['problemas'].append({'prueba': getattr(test, '_testMethodName', str(test)), 'detalle': text})

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self._problem(test, err, 'fallos')

    def addError(self, test, err):
        super().addError(test, err)
        self._problem(test, err, 'errores')


def _description(module_name):
    doc = (getattr(sys.modules.get(module_name), '__doc__', None) or '').strip()
    return doc.splitlines()[0].strip() if doc else ''


def run(start_dir, output):
    """Descubre y ejecuta las pruebas de start_dir; escribe el JSON de forma atomica."""
    started = time.perf_counter()
    # Cargador nuevo: defaultTestLoader recuerda el primer directorio y falla en usos posteriores.
    suite = unittest.TestLoader().discover(str(start_dir), pattern='test_*.py')
    runner = unittest.TextTestRunner(stream=io.StringIO(), resultclass=Collector, verbosity=0)
    # El servidor HTTP de las pruebas escribe su registro en stderr: se descarta aqui.
    with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
        result = runner.run(suite)
    files = []
    for name in sorted(result.modules):
        row = dict(result.modules[name])
        row['segundos'] = round(row['segundos'], 3)
        row['descripcion'] = _description(name)
        row['pruebas'] = [{k: v for k, v in entry.items() if k != '_id'} for entry in row['pruebas']]
        files.append(row)
    payload = {
        'generado': datetime.now().isoformat(timespec='seconds'),
        'segundos': round(time.perf_counter() - started, 2),
        'entorno': {'python': platform.python_version(), 'sqlite': sqlite3.sqlite_version,
                    'sistema': platform.system()},
        'total': sum(f['tests'] for f in files),
        'exito': result.wasSuccessful(),
        'archivos': files,
    }
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(output.name + '.tmp')
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding='utf-8')
    os.replace(temporary, output)
    return payload


def main():
    from src import quality
    parser = argparse.ArgumentParser(description='Suite de pruebas con resumen JSON')
    parser.add_argument('--output', type=Path, default=quality.results_dir() / quality.JOBS['suite']['file'])
    args = parser.parse_args()
    payload = run(ROOT / 'tests', args.output)
    state = 'OK' if payload['exito'] else 'CON FALLOS'
    print(f"{payload['total']} pruebas en {len(payload['archivos'])} archivos: {state} ({payload['segundos']} s)")
    return 0 if payload['exito'] else 1


if __name__ == '__main__':
    sys.exit(main())
