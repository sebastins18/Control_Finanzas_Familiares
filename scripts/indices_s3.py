"""Compara un índice SQLite usando solo datos y archivos temporales."""

from contextlib import ExitStack, closing
from datetime import date, timedelta
from pathlib import Path
import platform
import sqlite3
import statistics
import tempfile
import time


ROOT = Path(__file__).resolve().parents[1]
EVIDENCIA = ROOT / "docs" / "seguimientos" / "indices_s3.md"
INDICE = "idx_movimientos_categoria_fecha"
REGISTROS = 10000
REPETICIONES = 10
CONSULTA = """SELECT id_movimiento, fecha, monto_centimos, descripcion
FROM movimientos
WHERE id_perfil = ? AND id_categoria = ? AND fecha BETWEEN ? AND ?
ORDER BY fecha, id_movimiento"""
PARAMETROS = (1, 3, "2026-04-01", "2026-06-30")


def validar(conexion):
    if conexion.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
        raise RuntimeError("Claves foráneas desactivadas")
    if conexion.execute("PRAGMA foreign_key_check").fetchall():
        raise RuntimeError("Referencias inválidas")
    if conexion.execute("PRAGMA integrity_check").fetchone() != ("ok",):
        raise RuntimeError("Falló integrity_check")
    if conexion.execute("SELECT COUNT(*) FROM movimientos").fetchone()[0] != REGISTROS:
        raise RuntimeError("Cantidad incorrecta de movimientos")


def preparar(conexion):
    conexion.executescript((ROOT / "src" / "schema.sql").read_text(encoding="utf-8"))
    with conexion:
        conexion.execute("""INSERT INTO usuarios
            (id_usuario, nombre, username, password_salt, password_hash)
            VALUES (1, 'Usuario sintético', 'indices_s3', 'salt_ficticio', 'hash_ficticio')""")
        conexion.execute("""INSERT INTO perfiles_financieros
            (id_perfil, nombre, id_propietario) VALUES (1, 'Perfil sintético', 1)""")
        conexion.execute("INSERT INTO integrantes_perfil VALUES (1, 1)")
        conexion.execute("""INSERT INTO cuentas (id_cuenta, id_perfil, nombre)
            VALUES (1, 1, 'Cuenta sintética')""")
        conexion.executemany("""INSERT INTO categorias
            (id_categoria, id_perfil, nombre, tipo) VALUES (?, 1, ?, 'gasto')""",
            [(i, f"Gasto sintético {i}") for i in range(1, 11)])
        conexion.executemany("""INSERT INTO movimientos
            (id_perfil, id_cuenta, id_categoria, tipo, monto_centimos, fecha, descripcion)
            VALUES (1, 1, ?, 'gasto', ?, ?, ?)""", [
                (i % 10 + 1, 100 + i % 10000,
                 (date(2026, 1, 1) + timedelta(days=(i // 10) % 365)).isoformat(),
                 f"Movimiento sintético {i + 1}")
                for i in range(REGISTROS)
            ])


def ejecutar():
    with tempfile.TemporaryDirectory(prefix="indices_s3_") as temporal, ExitStack() as stack:
        conexiones = {}
        for nombre in ("Con índice", "Sin índice"):
            ruta = Path(temporal) / ("con.sqlite3" if nombre == "Con índice" else "sin.sqlite3")
            conexion = stack.enter_context(closing(sqlite3.connect(ruta, cached_statements=0)))
            conexiones[nombre] = conexion
        preparar(conexiones["Con índice"])
        conexiones["Con índice"].backup(conexiones["Sin índice"])
        conexiones["Sin índice"].execute(f"DROP INDEX {INDICE}")
        conexiones["Sin índice"].commit()

        configuraciones = {}
        planes = {}
        referencia = None
        inventarios = {}
        for nombre, conexion in conexiones.items():
            conexion.execute("PRAGMA foreign_keys = ON")
            conexion.execute("PRAGMA cache_size = -2048")
            conexion.execute("PRAGMA temp_store = MEMORY")
            conexion.execute("PRAGMA automatic_index = OFF")
            validar(conexion)
            inventarios[nombre] = dict(conexion.execute(
                "SELECT name, sql FROM sqlite_master WHERE type='index' AND sql IS NOT NULL"
            ).fetchall())
            configuraciones[nombre] = {
                clave: conexion.execute(f"PRAGMA {clave}").fetchone()[0]
                for clave in ("journal_mode", "synchronous", "cache_size", "temp_store", "automatic_index")
            }
            planes[nombre] = conexion.execute("EXPLAIN QUERY PLAN " + CONSULTA, PARAMETROS).fetchall()
            filas = conexion.execute(CONSULTA, PARAMETROS).fetchall()
            if not filas:
                raise RuntimeError("Consulta sin resultados")
            if referencia is not None and filas != referencia:
                raise RuntimeError("Los escenarios devolvieron resultados distintos")
            referencia = filas
        if configuraciones["Con índice"] != configuraciones["Sin índice"]:
            raise RuntimeError("Configuraciones distintas")
        if INDICE not in inventarios["Con índice"]:
            raise RuntimeError("Índice esperado ausente del esquema")
        esperados = dict(inventarios["Con índice"])
        del esperados[INDICE]
        if esperados != inventarios["Sin índice"]:
            raise RuntimeError("Se modificaron otros índices")

        # Calentamiento idéntico; no forma parte de los tiempos publicados.
        for _ in range(2):
            for conexion in conexiones.values():
                conexion.execute(CONSULTA, PARAMETROS).fetchall()
        tiempos = {nombre: [] for nombre in conexiones}
        for vuelta in range(REPETICIONES):
            orden = list(conexiones)
            if vuelta % 2:
                orden.reverse()
            for nombre in orden:
                inicio = time.perf_counter()
                filas = conexiones[nombre].execute(CONSULTA, PARAMETROS).fetchall()
                transcurrido = (time.perf_counter() - inicio) * 1000
                tiempos[nombre].append(transcurrido)
                if filas != referencia:
                    raise RuntimeError("Resultados cambiantes durante la medición")
        for conexion in conexiones.values():
            validar(conexion)

        medianas = {nombre: statistics.median(valores) for nombre, valores in tiempos.items()}
        con, sin = medianas["Con índice"], medianas["Sin índice"]
        if con < sin:
            conclusion = (f"La mediana con índice fue menor en esta ejecución local "
                          f"({(1 - con / sin) * 100:.2f} % respecto de la mediana sin índice). "
                          "Esto muestra una reducción observada en esta muestra, sin demostrar "
                          "significancia estadística ni una mejora general para otras cargas.")
        else:
            conclusion = ("Los resultados no muestran una mejora de la mediana con índice "
                          "en esta ejecución local; no se afirma una aceleración.")
        lineas = [
            "# Seguimiento 3 — Evaluación local del índice SQLite", "",
            f"- Python: {platform.python_version()}; SQLite: {sqlite3.sqlite_version}.",
            f"- Plataforma: {platform.platform()}.",
            f"- Movimientos: {REGISTROS}; diez categorías de gasto; filas recuperadas: {len(referencia)}.",
            "- Solo SQLite temporal creado con tempfile; no se abre la base real del proyecto.",
            "- Esquema leído de src/schema.sql; datos sintéticos deterministas con claves foráneas válidas.",
            "- Dos copias temporales mediante SQLite backup; solo se elimina el índice evaluado en una copia.",
            "- Los demás índices explícitos se conservan y se comprueba su igualdad.",
            f"- Configuración común verificada: {configuraciones['Con índice']}.",
            "- No se activa WAL ni se ejecuta ANALYZE; se usa el esquema base, no db.init_db().", "",
            "## Consulta idéntica en ambos escenarios", "", "```sql", CONSULTA, "```", "",
            f"Parámetros: `{PARAMETROS!r}`.", "",
            "## EXPLAIN QUERY PLAN", "",
        ]
        for nombre, plan in planes.items():
            lineas.extend([f"### {nombre}", "", "```text"])
            lineas.extend(str(fila) for fila in plan)
            lineas.extend(["```", ""])
        lineas.extend([
            "## Tiempos reales", "",
            "Diez ejecuciones por escenario con time.perf_counter y statistics.median, en milisegundos.",
            "Se mide execute + fetchall, incluida preparación SQL; cached_statements=0 en ambas conexiones.",
            "Preparación, planes y validaciones quedan fuera del intervalo cronometrado.", "",
            "| Repetición | Con índice (ms) | Sin índice (ms) |",
            "| --- | ---: | ---: |",
        ])
        for i in range(REPETICIONES):
            lineas.append(f"| {i + 1} | {tiempos['Con índice'][i]:.6f} | {tiempos['Sin índice'][i]:.6f} |")
        lineas.extend([
            f"| Mediana | {con:.6f} | {sin:.6f} |", "", conclusion, "",
            "## Condiciones, validaciones y limitaciones", "",
            "- Mismos datos por copia de base, consulta, parámetros, configuración y número de lecturas.",
            "- Dos lecturas explícitas de calentamiento por escenario, además de la lectura de validación previa.",
            "- Orden alternado por ronda: con/sin, sin/con; sin escrituras durante las mediciones.",
            "- Cachés de SQLite y del sistema operativo no se vacían. No es una comparación en frío;",
            "  el calentamiento y la alternancia reducen algunos sesgos, pero no los eliminan.",
            "- Diez muestras, una única ejecución local, un tamaño y una distribución sintética no representan",
            "  toda carga real ni permiten asegurar significancia estadística. Influyen equipo, disco y otros procesos.",
            "- La estructura física cambia al eliminar el índice; las dos bases son equivalentes en datos, no en tamaño.",
            "- Los planes reflejan la elección del optimizador; no se fuerza un índice ni se eliminan los demás.",
            "- Se verifican resultados idénticos y no vacíos en cada lectura medida, conteos estables,",
            "  foreign_keys=ON, foreign_key_check sin violaciones e integrity_check=ok antes y después.",
            "- No mide inserciones, coste de mantener índices, respuesta web ni Virtualmin; tampoco compara otros motores.",
            "- No se extrapola el resultado a los otros índices del esquema. Las bases temporales se eliminan al finalizar.",
            "", "## Ejecución desde PowerShell", "", "```powershell",
            "py -3 scripts/indices_s3.py", "```", "",
            "La evidencia se crea exclusivamente si no existe; el script rechaza sobrescribirla.",
        ])
        return "\n".join(lineas) + "\n"


def main():
    if EVIDENCIA.exists():
        raise SystemExit(f"No se sobrescribe la evidencia existente: {EVIDENCIA}")
    reporte = ejecutar()
    EVIDENCIA.parent.mkdir(parents=True, exist_ok=True)
    with EVIDENCIA.open("x", encoding="utf-8") as archivo:
        archivo.write(reporte)
    print(reporte)
    print(f"Evidencia: {EVIDENCIA}")


if __name__ == "__main__":
    main()
