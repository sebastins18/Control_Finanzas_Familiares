# Consultas, reportes y movimientos recurrentes (v0.4.0)

Funciones agregadas el 03/11/2026. Todas trabajan sobre el **perfil financiero activo**
(`current_profile_id()`); los datos de otros perfiles nunca aparecen. Decisiones asociadas:
[D-019 a D-021](decisiones.md).

## Historial (`/historial`)

- Filtros por texto (descripción o categoría), tipo, categoría, cuenta y rango de fechas.
  El texto se busca como literal: `%` y `_` no actúan como comodines.
- Paginación de 25 movimientos; una página fuera de rango muestra la última.
- Totales por moneda de los movimientos filtrados (no se suman monedas distintas).
- Un filtro inválido (fecha mal escrita, rango invertido, tipo desconocido) responde HTTP 400
  con el motivo.
- **Exportar CSV** (`/historial.csv`) aplica los mismos filtros.
- Código: [src/reportes.py](../src/reportes.py) (`parse_filters`, `history`, `history_page`, `history_csv`).

## Reporte anual (`/reportes/anual?anio=2026`)

- Totales mensuales por categoría, separados por moneda, con subtotales de ingresos y gastos
  y balance mensual. Año entre 2000 y 2100 (por defecto, el actual).
- Exportación CSV (`/reportes/anual.csv?anio=2026`) en formato de una fila por moneda, tipo y categoría.
- La consulta usa un rango cerrado-abierto de fechas y aprovecha `idx_movimientos_fecha_tipo`
  (verificado con `EXPLAIN QUERY PLAN`).

## Exportación CSV

- Codificación UTF-8 con BOM para que Excel muestre bien las tildes.
- Montos con punto decimal (`1234.56`), igual que el formato que acepta el servidor.
- Los textos que empiezan con `=`, `+`, `-`, `@`, tabulador o retorno se exportan precedidos de
  `'` para que una hoja de cálculo no los ejecute como fórmula.

## Movimientos recurrentes (`/admin/movimientos_recurrentes`)

- Plantillas mensuales (salario, alquiler…): descripción, tipo, categoría, cuenta, monto,
  día del mes (1 a 28, existe en todos los meses), fecha de inicio y estado activo/pausado.
- Se administran con el mantenimiento genérico de `extension.CONFIG`; solo el propietario del
  perfil crea, edita o elimina plantillas.
- **Nada se genera automáticamente.** El botón **Generar pendientes** (`POST /recurrentes/generar`)
  crea en una sola transacción los movimientos vencidos hasta hoy; el panel principal avisa
  cuando hay pendientes. Invitados y propietario pueden generarlos.
- Idempotencia en la base: `recurrentes_generados` tiene clave primaria `(id_recurrente, periodo)`.
  Un mismo mes no puede generarse dos veces, ni con solicitudes simultáneas. Si se elimina un
  movimiento generado, su período queda marcado y no se vuelve a crear.
- Tope de 500 movimientos por ejecución para respetar el límite de 8 s de `db.connect()`;
  si quedan más, se informa y se vuelve a pulsar.
- Un perfil con plantillas no puede eliminarse (igual que con movimientos).
- Código: [src/recurrentes.py](../src/recurrentes.py).

### Tablas nuevas

```sql
movimientos_recurrentes(id_recurrente PK, id_perfil FK, id_cuenta FK, id_categoria FK,
    tipo CHECK(ingreso|gasto), monto_centimos CHECK(>0), descripcion,
    dia_mes CHECK(1..28), fecha_inicio, activo CHECK(0|1))
recurrentes_generados(id_recurrente FK ON DELETE CASCADE, periodo 'AAAA-MM',
    id_movimiento FK ON DELETE SET NULL, PRIMARY KEY(id_recurrente, periodo))
```

Se crean con `CREATE TABLE IF NOT EXISTS` al iniciar la aplicación (`extension.init()`).
No modifican tablas existentes. Se verificó la actualización sobre una base de la versión
anterior (`997ad10`): todas las tablas previas conservan contenido idéntico y la versión
anterior sigue arrancando sobre la base actualizada.

## Formularios, brillo y animaciones (solo presentación)

- Los formularios usan un sistema de campos común (ver lienzo de diseño "Formularios MisFinanzas"):
  selector segmentado con radios reales para Gasto/Ingreso y Aporte/Retiro, interruptor
  (checkbox + campo oculto `0`) para Activo/Leída, campo de día con − y +, monto con moneda.
  **Envían los mismos nombres y valores que antes**; lo verifica
  [tests/test_formularios_v2.py](../tests/test_formularios_v2.py) leyendo el HTML real y
  comprobando lo guardado en SQLite.
- El brillo que sigue al puntero se ve también sobre paneles y botones claros; el indicador de
  los selectores segmentados y de las pestañas de perfil se desliza. Todo se desactiva con
  `prefers-reduced-motion` y no se usa en pantallas táctiles.
- En [src/static/styles.css](../src/static/styles.css) cada cambio está en un bloque
  autocontenido al final ("Formularios v2", "Brillo v2", "Animaciones v1"); quitar el bloque
  revierte su efecto.

## Datos de prueba

`python -m scripts.demo_temporal` crea el perfil **«DEMO · Datos de prueba»** (propietario `admin`)
con unos 14 meses de movimientos ficticios, una cuenta en USD, plantillas recurrentes y
presupuestos. `--borrar` lo elimina por completo. Respalda la base antes de cargar.
**No usarlo contra la base del servidor.**
