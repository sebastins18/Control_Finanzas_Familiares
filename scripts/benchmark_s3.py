"""Benchmark local del Seguimiento 3, exclusivamente en SQLite temporal."""

from datetime import date, timedelta
from pathlib import Path
import platform
import sqlite3
import statistics
import tempfile
import time


ROOT = Path(__file__).resolve().parents[1]
EVIDENCIA = ROOT / "docs" / "seguimientos" / "mediciones_s3.md"
REPETICIONES = 5
REGISTROS = 1000
INSERTAR = """
    INSERT INTO movimientos
        (id_perfil, id_cuenta, id_categoria, tipo, monto_centimos, fecha, descripcion)
    VALUES (1, 1, 1, 'gasto', ?, ?, ?)
"""
POR_CATEGORIA = """
    SELECT id_movimiento, fecha, monto_centimos, descripcion
    FROM movimientos
    WHERE id_perfil = ? AND id_categoria = ? AND fecha BETWEEN ? AND ?
    ORDER BY fecha, id_movimiento
"""
TOTAL_GASTOS = """
    SELECT SUM(monto_centimos) FROM movimientos
    WHERE id_perfil = ? AND tipo = 'gasto' AND fecha BETWEEN ? AND ?
"""
PERIODO = (1, "2026-01-01", "2026-12-31")


def comprobar_integridad(conexion):
    if conexion.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
        raise RuntimeError("Las claves foráneas no están activadas.")
    if conexion.execute("PRAGMA foreign_key_check").fetchall():
        raise RuntimeError("Se encontraron violaciones de claves foráneas.")
    if conexion.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
        raise RuntimeError("Falló la comprobación de integridad SQLite.")


def medir(operacion):
    tiempos = []
    for _ in range(REPETICIONES):
        inicio = time.perf_counter()
        resultado = operacion()
        tiempos.append((time.perf_counter() - inicio) * 1000)
        if resultado is None or resultado == []:
            raise RuntimeError("La operación no devolvió resultados.")
    return tiempos


def ejecutar():
    # No se abre ninguna base del proyecto; el esquema se lee sin modificarlo.
    with tempfile.TemporaryDirectory(prefix="finanzas_s3_") as temporal:
        conexion = sqlite3.connect(Path(temporal) / "benchmark.sqlite3")
        try:
            conexion.execute("PRAGMA foreign_keys = ON")
            conexion.executescript((ROOT / "src" / "schema.sql").read_text(encoding="utf-8"))
            with conexion:
                conexion.execute("""
                    INSERT INTO usuarios
                        (id_usuario, nombre, username, password_salt, password_hash)
                    VALUES (1, 'Usuario sintético', 'benchmark_s3',
                            'salt_sintetico', 'hash_sintetico')
                """)
                conexion.execute("""
                    INSERT INTO perfiles_financieros (id_perfil, nombre, id_propietario)
                    VALUES (1, 'Perfil sintético', 1)
                """)
                conexion.execute("INSERT INTO integrantes_perfil VALUES (1, 1)")
                conexion.execute("""
                    INSERT INTO cuentas (id_cuenta, id_perfil, nombre)
                    VALUES (1, 1, 'Cuenta sintética')
                """)
                conexion.execute("""
                    INSERT INTO categorias (id_categoria, id_perfil, nombre, tipo)
                    VALUES (1, 1, 'Gastos sintéticos', 'gasto')
                """)
                conexion.executemany(INSERTAR, [
                    (100 + i % 10000,
                     (date(2026, 1, 1) + timedelta(days=i % 365)).isoformat(),
                     f"Movimiento sintético {i + 1}")
                    for i in range(REGISTROS)
                ])
            comprobar_integridad(conexion)
            iniciales = conexion.execute("SELECT COUNT(*) FROM movimientos").fetchone()[0]
            if iniciales < 1000:
                raise RuntimeError("Se requieren al menos 1000 movimientos antes de medir.")

            def insertar():
                with conexion:
                    conexion.execute(INSERTAR, (1250, "2026-06-15", "Inserción medida"))
                return True  # El contexto ya confirmó la transacción.

            def consultar():
                return conexion.execute(POR_CATEGORIA, (1, 1, *PERIODO[1:])).fetchall()

            def sumar():
                return conexion.execute(TOTAL_GASTOS, PERIODO).fetchone()[0]

            resultados = [
                ("Insertar gasto y confirmar transacción", medir(insertar)),
                ("Consultar por categoría y rango de fechas (fetchall)", medir(consultar)),
                ("SUM(monto_centimos) de gastos del período", medir(sumar)),
            ]
            comprobar_integridad(conexion)
            finales = conexion.execute("SELECT COUNT(*) FROM movimientos").fetchone()[0]
            filas = consultar()
            total = sumar()
            if finales != iniciales + REPETICIONES or len(filas) != finales:
                raise RuntimeError("Cantidad inesperada de movimientos o resultados.")
            if total is None or total <= 0 or total != sum(fila[2] for fila in filas):
                raise RuntimeError("El total de gastos no coincide con los resultados.")
            lineas = [
                "# Seguimiento 3: medición local con SQLite", "",
                f"- Python: {platform.python_version()}",
                f"- SQLite: {sqlite3.sqlite_version}",
                f"- Plataforma: {platform.platform()}",
                f"- Movimientos antes de medir: {iniciales}; al finalizar: {finales}.",
                "- Período inclusivo: 2026-01-01 a 2026-12-31; categoría de gasto: 1.",
                "- Base temporal creada con tempfile y eliminada al finalizar.",
                "- Esquema e índices originales de src/schema.sql; datos sintéticos.",
                "- Cinco repeticiones por operación, time.perf_counter y statistics.median.",
                "- Inserción: incluye INSERT y commit; consultas: incluyen lectura de resultados.",
                "- Orden: inserciones, consulta por categoría, suma; sin reiniciar la caché.",
                "- Preparación y validaciones fuera de los intervalos medidos.",
                "- Medición local; los tiempos dependen del equipo, disco y caché.", "",
                "| Operación | 1 (ms) | 2 (ms) | 3 (ms) | 4 (ms) | 5 (ms) | Mediana (ms) |",
                "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
            ]
            for nombre, tiempos in resultados:
                valores = [*tiempos, statistics.median(tiempos)]
                lineas.append(f"| {nombre} | " + " | ".join(f"{v:.6f}" for v in valores) + " |")
            lineas.extend([
                "", "Validaciones satisfactorias: foreign_keys=ON, foreign_key_check sin",
                "violaciones e integrity_check=ok (antes y después de medir).",
                f"La consulta devuelve {len(filas)} movimientos y SUM devuelve {total} céntimos,",
                "coincidente con la suma de las filas recuperadas.", "",
                "Ejecución desde la raíz del proyecto en PowerShell:",
                "```powershell", "py -3 scripts/benchmark_s3.py", "```", "",
                "El script rechaza sobrescribir esta evidencia si ya existe.",
            ])
            return "\n".join(lineas) + "\n"
        finally:
            conexion.close()


def main():
    if EVIDENCIA.exists():
        raise SystemExit(f"No se modificó ningún archivo: la evidencia ya existe: {EVIDENCIA}")
    reporte = ejecutar()
    EVIDENCIA.parent.mkdir(parents=True, exist_ok=True)
    with EVIDENCIA.open("x", encoding="utf-8") as archivo:
        archivo.write(reporte)
    print(reporte)
    print(f"Evidencia guardada en: {EVIDENCIA}")


if __name__ == "__main__":
    main()
