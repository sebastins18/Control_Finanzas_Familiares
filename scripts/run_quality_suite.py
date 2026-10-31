"""Ejecuta la suite de tests/ y guarda un resumen JSON por archivo de prueba.

Uso: python -m scripts.run_quality_suite [--output ruta.json]

El resumen no incluye trazas ni rutas internas: solo cuantas pruebas hubo por archivo, su
resultado, su duracion y, si algo fallo, la ultima linea del error. Cada prueba usa su propia
base temporal, asi que no toca data/finanzas.sqlite3. Solo biblioteca estandar.
Codigo de salida: 0 si todo pasa, 1 si hay fallos o errores.
"""
import argparse
import io
import json
import os
import platform
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
            'omitidos': 0, 'segundos': 0.0, 'problemas': []})

    def startTest(self, test):
        super().startTest(test)
        self._started = time.perf_counter()
        self._row(test)['tests'] += 1

    def stopTest(self, test):
        self._row(test)['segundos'] += time.perf_counter() - self._started
        super().stopTest(test)

    def addSuccess(self, test):
        super().addSuccess(test)
        self._row(test)['ok'] += 1

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self._row(test)['omitidos'] += 1

    def _problem(self, test, err, key):
        row = self._row(test)
        row[key] += 1
        if len(row['problemas']) < MAX_PROBLEMS_PER_FILE:
            text = ''.join(traceback.format_exception_only(err[0], err[1])).strip()
            text = text.replace(str(ROOT), '<proyecto>').splitlines()[-1:] or ['']
            row['problemas'].append({'prueba': getattr(test, '_testMethodName', str(test)),
                                     'detalle': text[0][:300]})

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
