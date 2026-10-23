# Arquitectura integrada V17 — Seguimiento 2

> La documentación debajo del encabezado **S1 histórico** describe el estado al 16/10. La arquitectura actual incluye funcionalidades ampliadas del ZIP V17 y debe revisarse junto con [`modelo-v17.md`](modelo-v17.md).

```mermaid
flowchart LR
    U[Usuario] --> B[Navegador]
    B -->|HTTP / o /finanzas/| A[src/app.py]
    A --> AUTH[Autenticación local en JSON privado]
    A --> CORE[src/db.py]
    A --> EXT[src/extension.py]
    CORE --> SQLITE[(SQLite + WAL)]
    EXT --> SQLITE
    BULK[scripts/seed_bulk_s2.py] --> SQLITE
```

**SQLite** es el único motor persistente; no hay sincronización entre motores. `src/schema.sql` crea cinco tablas base, `src/extension.py` crea siete tablas adicionales y `app_config`, y hace migraciones sobre `cuentas`, `movimientos` y `presupuestos`. Los archivos del usuario y las credenciales quedan fuera de Git. `APP_BASE_PATH=/finanzas` adapta URLs detrás del proxy del curso. La autorización por usuario y la protección CSRF todavía no son suficientes para un despliegue público.

---

## S1 histórico

**Arquitectura implementada:** aplicación web local con Python 3.10+ (biblioteca estándar), una base de datos SQLite y datos sintéticos.

```mermaid
flowchart TD
    U[Usuario en navegador] -->|HTTP localhost:8000| A[src/app.py: servidor web Python]
    A --> B[src/db.py: validación y consultas parametrizadas]
    B --> D[(SQLite local: data/finanzas.sqlite3)]
    I[scripts/init_db.py] --> B
    S[scripts/seed.py] --> B
```

## Responsabilidad de cada componente

- `src/app.py`: páginas HTML, rutas HTTP y formularios del prototipo.
- `src/db.py`: validación de montos, fechas y relaciones; operaciones sobre SQLite.
- `src/schema.sql`: **único DDL usado para inicializar el MVP**. Contiene las tablas `usuarios`, `categorias`, `cuentas`, `movimientos` y `presupuestos`.
- `scripts/init_db.py`: inicialización del esquema, WAL y catálogos de ejemplo.
- `scripts/seed.py`: datos sintéticos reproducibles.
- `tests/`: casos de CRUD, conexión, errores y HTTP.

## Decisiones

- **Perfil A, un motor:** SQLite es suficiente para un MVP local. Se documentarán el modo WAL, los índices y, en S3, el análisis de `EXPLAIN QUERY PLAN` con comparaciones.
- **Datos coherentes:** claves foráneas habilitadas y parámetros SQL; montos expresados en centavos enteros.
- **Alcance reducido:** un hogar ficticio en CRC; sin autenticación, bancos reales, multimoneda o despliegue público.
- **Propuesta de expansión:** `scripts/schema.sql` y el diagrama de la presentación son **referenciales** y NO se usan en la aplicación actual. No ejecutar ese archivo contra la base MVP.

## Pruebas y fallos

La inicialización y conexión SQLite fueron exitosas en la ejecución local informada el 16/10/2026. Los casos de CRUD y HTTP también pasaron. Se corrigió un import incorrecto de la prueba de conexión; aún falta repetir la batería completa tras esa corrección.

Si SQLite no puede abrir o escribir el archivo, las operaciones deben producir un error y la transacción debe revertirse. Se recomienda probar explícitamente el caso de fallo en S3.

## Evolución esperada

S2: consolidar CRUD, validaciones, PRs y carga. S3: casos de error, índices, métricas (tres operaciones y mediana de tres repeticiones). S4: instalación desde cero por otra persona y demostración final.
