# Control de Finanzas Familiares — Grupo 5

**Universidad Nacional · Tópicos Avanzados de Bases de Datos · II-2026**

Aplicación web de demostración en Python y SQLite para registrar movimientos financieros familiares, planificar presupuestos y consultar saldos. El objetivo es un MVP open source reproducible y medible, no un servicio bancario ni una aplicación apta para introducir datos financieros reales.

## Funciones de la versión integrada V17

- Ingresos y gastos: alta, consulta, edición y eliminación; panel mensual y alertas presupuestarias.
- Catálogos: categorías, cuentas y monedas; presupuestos, metas de ahorro, alertas y movimientos de ahorro.
- Transferencias entre cuentas; si las monedas son distintas, se **introduce un tipo de cambio manual positivo**. Esta versión **no** descarga cotizaciones automáticamente.
- Panel separado por divisas y reglas de conversión de gastos para presupuestos.
- Perfiles financieros locales, usuarios de acceso y contraseñas protegidas mediante PBKDF2-HMAC.
- Comprobantes de gastos en almacenamiento local; mensajes de error SQLite con registro rotativo.
- Arquitectura extendida a partir del modelo original de cinco tablas. `src/schema.sql` sigue creando las cinco tablas base; `src/extension.py` agrega las tablas del módulo extendido durante `db.init_db()`.

El código del módulo extendido proviene del ZIP V17 aportado por un integrante del grupo. La integración corrige incompatibilidades de las pruebas, protege archivos locales de versionado y añade soporte para prefijo de URL. Véanse `CAMBIOS_V17.md` y `docs/seguimientos/S2.md`.

## Instalación local desde cero (Python 3.10+)

No se necesita instalar dependencias de terceros.

```powershell
git clone https://github.com/sebastins18/Control_Finanzas_Familiares.git
cd Control_Finanzas_Familiares
py scripts/init_db.py
py scripts/seed.py
py -m unittest discover -s tests -v
py -m src.app
```

Abrir `http://127.0.0.1:8000/`. Para detener la aplicación, `Ctrl+C`. Ejecutar los comandos dentro de la raíz de un proyecto que **ya contenga los cambios de V17**, no solo el tag histórico `v0.2.0`.

**Acceso inicial:** la V17 recibida creaba una credencial de demostración conocida. Esta integración exige una contraseña inicial definida en el entorno cuando se configura el prefijo de despliegue. En ejecución local sin prefijo se conserva la contraseña histórica de demostración, únicamente para pruebas. **Cambiar la contraseña del usuario administrador antes de exponer cualquier instancia a una red**. Esta aplicación sigue sin disponer de todas las protecciones necesarias para Internet (por ejemplo CSRF, sesiones persistentes seguras y control exhaustivo por recurso). Úsese para evaluación académica local.

## Variables y almacenamiento

| Variable | Uso |
| --- | --- |
| `DB_PATH` | Ruta a SQLite (predeterminada: `data/finanzas.sqlite3`) |
| `APP_BASE_PATH` | Prefijo al publicar tras proxy (por ejemplo `/finanzas`); vacío para localhost |
| `FINANZAS_INITIAL_ADMIN_PASSWORD` | Contraseña inicial de **12 o más caracteres** obligatoria para crear credenciales nuevas con `APP_BASE_PATH` configurado. Solo se usa la primera vez. |

Las credenciales de autenticación, comprobantes y logs se guardan **junto al archivo de SQLite** indicado por `DB_PATH`, en `login_credentials.json`, `comprobantes/` y `logs/` respectivamente. `data/`, archivos SQLite, comprobantes, JSON de credenciales y logs nunca deben publicarse en el repositorio ni estar directamente accesibles desde un servidor web. Para CRNube, utilizar una carpeta privada **fuera de `public_html`** y establecer `DB_PATH` a su archivo SQLite.

### Proxy del servidor del curso

El Apache observado redirige `/finanzas/...` a un backend Python en `127.0.0.1:8010`. Para el código corregido:

```bash
export APP_BASE_PATH=/finanzas
export FINANZAS_INITIAL_ADMIN_PASSWORD="CAMBIE_ESTA_CLAVE_POR_UNA_SEGURA"
python3 -m src.app --host 127.0.0.1 --port 8010
```

Ejecutar desde la raíz del proyecto. Esto inicia un proceso temporal de demostración, **no** configura un servicio permanente. Los enlaces, formularios, redirecciones y cookies se adaptan al prefijo indicado. El proxy Apache y el proceso backend deben estar configurados y disponibles para que funcione.

**Advertencia:** no iniciar un despliegue público con la contraseña de demostración. El administrador del servidor debe revisar protección de datos, TLS, encabezados y gestión de procesos antes de publicar.

## Scripts y pruebas

```powershell
py scripts/init_db.py
py scripts/seed.py
py -m scripts.seed_bulk_s2 --count 1000
py -m unittest discover -s tests -v
```

`seed_bulk_s2.py` inserta movimientos sintéticos reproducibles dentro de una transacción. Por seguridad, en una base que ya contiene marcadores `SIM-S2-` no vuelve a cargar datos. Para la evidencia de **100 000 registros**, usá una base de ensayo independiente y `--count 100000`; documentá tiempo y EXPLAIN QUERY PLAN en S3, no sobre datos de demostración de la entrega.

### Diseño técnico

- SQLite: persistencia local, claves foráneas e índices; `PRAGMA journal_mode=WAL` al inicializar.
- Transacciones e importes representados como centavos enteros.
- Python estándar (`http.server`, `sqlite3`) para entorno de prueba y demostración local.
- Un solo motor (perfil A), por lo que se debe documentar profundidad con función avanzada WAL y experimentos con índices.

## Estado del curso

- **S1 (16 de octubre):** problema, repositorio, diagrama, tabla base, datos de prueba y `v0.1.0` (el tag inicial no incluía todas las correcciones posteriores).
- **S2 (23 de octubre):** integración V17 preparada en rama, pruebas corregidas, carga transaccional y bitácora `docs/seguimientos/S2.md`. El tag `v0.2.0` se creó antes de estos cambios; deberá acordarse su tratamiento, sin reescribirlo unilateralmente.
- **S3 (30 de octubre):** mediciones de tres operaciones con al menos tres ejecuciones y medianas, comparación con/sin índices y `EXPLAIN QUERY PLAN`.
- **S4 (6 de noviembre):** instalación limpia por otro integrante, capturas, video, release candidate, `portal.yml` y presentación.

### Colaboración

Backlog: https://github.com/sebastins18/Control_Finanzas_Familiares/issues

Tablero: https://github.com/users/sebastins18/projects/1/views/1

Los commits de integración no sustituyen los **commits auténticos de cada integrante** exigidos por la rúbrica. Registrar autores reales, ramas, pull requests y responsables en las bitácoras.

Licencia: MIT.
