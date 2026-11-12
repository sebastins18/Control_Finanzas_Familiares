# MisFinanzas — Control de Finanzas Familiares

**Grupo 5 · Universidad Nacional · Tópicos Avanzados de Bases de Datos · II-2026**

MisFinanzas ayuda a personas y familias a registrar ingresos y gastos, organizar cuentas y categorías, planificar presupuestos y consultar cómo utilizan su dinero. Responde al problema de tener movimientos domésticos dispersos y poca visibilidad de los saldos y límites del mes. Los perfiles financieros permiten separar la información de cada familia e invitar a otros usuarios.

Es un MVP académico open source con datos ficticios. El backend utiliza Python estándar y un único motor SQLite; la interfaz web sirve HTML, CSS y JavaScript. Las dependencias de Playwright y edición de video pertenecen a las herramientas de QA, no al funcionamiento de la aplicación.

## Estado verificable al 6/11/2026

| Área | Situación actual | Procedencia |
| --- | --- | --- |
| Base técnica | `main`, commit `8a88aeb`; se conservan código, seguridad, respaldo, CI y pruebas de S4 | Historial Git; PR #20, #21 y #22 |
| CRNube | S4 desplegado el **6/11/2026 sobre `8a88aeb`**, con respaldo SQLite consistente anterior a la actualización | Confirmación del responsable; esta revisión documental no administra el servidor |
| SQLite del despliegue | **WAL, 17 tablas, integridad `ok` y 0 errores de claves foráneas** | Verificación del despliegue aportada por el responsable; comprobaciones locales separadas |
| Regresión | **109/109 pruebas correctas** en el registro histórico del 6/11/2026 | [Matriz histórica S4](docs/seguimientos/ENTREGA_S4.md); consola y reporte de comprobaciones originales no disponibles en este checkout. La ejecución del 11/11/2026 se documenta por separado en la tabla de evidencias |
| Navegador | **27/27 E2E satisfactorias, 0 fallidas y 0 omitidas**, según el registro histórico del 6/11/2026 | [Matriz histórica S4](docs/seguimientos/ENTREGA_S4.md); reporte original no disponible en este checkout, sin nueva ejecución E2E |
| S3 | Cerrado técnicamente en [Issue #3](https://github.com/sebastins18/Control_Finanzas_Familiares/issues/3) | GitHub: `closed`, motivo `completed`; sin atribuir aprobación docente |
| Video | Hay grabaciones y versiones de trabajo locales; el **video final sincronizado sigue en preparación para la entrega y no está publicado** | [Estado y evidencias audiovisuales](docs/seguimientos/VIDEO_S4.md) |
| Versión | **`v0.9.0` no aparece en las etiquetas remotas consultadas**; requiere revisión y autorización | Consulta de `git ls-remote --heads --tags origin` del 6/11/2026 |

El login público es [MisFinanzas en CRNube](https://diego01.grupo5.crnube.org/finanzas/login). La [bitácora histórica S4](docs/seguimientos/S4.md#evidencia-vigente-y-procedencia) registra un GET HTTPS con HTTP 200 sin autenticación; el reporte original no está disponible en este checkout; ese GET no comprueba por sí solo el commit ni los datos internos del servidor. La [matriz de entrega S4](docs/seguimientos/ENTREGA_S4.md) distingue evidencias locales, comprobaciones remotas y validaciones humanas pendientes.

Los reportes de Virtualmin `suite.json` y `benchmark.md`, junto con el documento `docs/seguimientos/evidencia_final_pruebas.md`, ya están publicados en el repositorio de GitHub mediante el commit `cb8e7f9`. Las capturas enlazadas y las guías de `scripts/e2e/` están disponibles en esta copia de trabajo; los reportes históricos ausentes se identifican expresamente. La publicación de estos documentos no acredita un enlace público al video final ni la disponibilidad del reporte E2E histórico; esas pruebas no se ejecutaron nuevamente.

## Funcionalidades actuales

- Registro, consulta, edición y eliminación de ingresos y gastos; resumen mensual y saldos por cuenta.
- Cuentas, categorías, monedas, presupuestos, metas y movimientos de ahorro; transferencias entre cuentas.
- Presupuestos por categoría y período, con estados del **80 % y 100 %** y alertas persistidas.
- Historial con búsqueda, filtros, paginación, totales por moneda y exportación CSV; reporte anual por categoría y moneda.
- Plantillas de movimientos recurrentes con generación explícita e idempotente.
- Perfiles financieros con propietario e invitados, separados de las cuentas y roles de acceso.
- Registro, login, cambio de contraseña y mantenimiento de usuarios para administradores activos. La recuperación de contraseña requiere un administrador.
- Comprobantes en almacenamiento local privado, panel de calidad y tratamiento controlado de errores SQLite.
- Importes en centavos enteros. Los totales no mezclan monedas; las transferencias entre divisas usan una cotización manual positiva, sin descarga automática de tasas.

## Arquitectura, datos y seguridad

**Perfil A: SQLite como único motor**, sin Redis ni otro motor secundario. El navegador accede directamente a Python en localhost; en CRNube, Apache publica `/finanzas` por HTTPS y actúa como proxy hacia el backend local. Las sesiones y la caché acotada de lectura viven en memoria y se pierden al reiniciar.

| Componente | Archivos y responsabilidad |
| --- | --- |
| Servidor e interfaz | `src/app.py`, `src/static/`: rutas, formularios, sesiones, respuestas y estilos |
| Persistencia | `src/db.py`, `src/schema.sql`: conexiones, transacciones, esquema base e inicialización |
| Autenticación | `src/auth.py`: usuarios y roles en SQLite, migraciones y PBKDF2-HMAC-SHA256 con salt |
| Finanzas y perfiles | `src/extension.py`, `src/finance.py`, `src/profiles.py`, `src/request_ctx.py`: extensiones, cálculos, pertenencia y permisos |
| Consultas y recurrencias | `src/reportes.py`, `src/recurrentes.py`: filtros, CSV, reporte anual y generación idempotente |
| Errores y calidad | `src/read_cache.py`, `src/quality.py`, manejo de errores en `src/app.py` y `src/db.py` |
| Respaldo e instalación | `scripts/backup_sqlite_s4.py`, `scripts/verify_clean_install_s4.py` |
| Pruebas y CI | `tests/`, `.github/workflows/ci.yml`; automatización local adicional en `scripts/e2e/` |

`src/schema.sql` contiene las cinco tablas iniciales; **no representa por sí solo las 17 tablas actuales**. `db.init_db()` inicializa también autenticación, extensiones, perfiles, recurrencias y cotizaciones. Las escrituras utilizan SQL parametrizado, transacciones, claves foráneas y WAL. La arquitectura y los flujos están desarrollados en [Arquitectura S4](docs/arquitectura/ARQUITECTURA_S4.md).

Las cuentas y hashes están en `usuarios`; los roles admitidos son `administrador` y `usuario`, sin tabla ni mantenimiento de roles separado. El JSON heredado solo interviene en determinadas migraciones antiguas, no es el almacenamiento operativo de autenticación. Véanse [usuarios y migraciones](docs/usuarios_roles.md), [perfiles y permisos](docs/perfiles_financieros.md) y [consultas, reportes y recurrencias](docs/consultas_reportes_recurrentes.md).

S4 mantiene la exigencia de contraseña inicial fuerte para una base nueva bajo prefijo web, las cookies seguras configurables y las cabeceras de protección. El MVP todavía usa `http.server`, sesiones en memoria y defensas CSRF y de fuerza bruta incompletas. Trabajar con datos ficticios; no se presenta como un servicio bancario ni como una certificación de seguridad.

## Requisitos

- Git y Python **3.11 o 3.12** con `sqlite3`; la CI contempla Linux 3.11/3.12 y Windows 3.12.
- Navegador y una carpeta de ensayo con permiso de escritura para SQLite y WAL.
- La aplicación y su suite Python no requieren paquetes de terceros ni el ejecutable de consola de SQLite.
- La suite E2E y el trabajo audiovisual tienen un entorno separado: [QA Windows](scripts/e2e/README.md) y [presentación](scripts/e2e/PRESENTACION.md).

Los comandos siguientes se ejecutan en una **copia nueva**, desde la raíz del repositorio, con una base ficticia que no exista todavía. No reutilizar el `DB_PATH` ni las credenciales de CRNube. `.env.example` documenta variables: la aplicación **no carga automáticamente un archivo `.env`**.

## Instalación desde cero

### Obtener y registrar la versión

```bash
git clone --branch main https://github.com/sebastins18/Control_Finanzas_Familiares.git
cd Control_Finanzas_Familiares
python --version
git rev-parse --short HEAD
```

En Windows puede usarse `py`; en Linux, `python3`. Emplear el mismo intérprete en todos los pasos. Registrar el commit realmente instalado; `8a88aeb` identifica el despliegue confirmado al corte. El commit histórico `94412a1` y el tag `v0.4.0` no sustituyen la base técnica actual. Para validar esta revisión del README, conservar también su diff o el futuro commit documental.

### Configurar una base nueva en Windows / PowerShell

```powershell
$env:DB_PATH = Join-Path $PWD 'data/demo_s4.sqlite3'
if (Test-Path -LiteralPath $env:DB_PATH) { throw 'La base de ensayo ya existe; elegir otra ruta.' }
$env:APP_BASE_PATH = ''
$env:FINANZAS_COOKIE_SECURE = '0'
$env:FINANZAS_REQUIRE_STRONG_ADMIN_PASSWORD = '1'
$claveInicial = Read-Host 'Clave inicial privada de 12 o más caracteres' -AsSecureString
$env:FINANZAS_INITIAL_ADMIN_PASSWORD = ([System.Net.NetworkCredential]::new('', $claveInicial)).Password
```

### Configurar una base nueva en Linux

```bash
export DB_PATH="$PWD/data/demo_s4.sqlite3"
test ! -e "$DB_PATH" || { printf '%s\n' 'La base de ensayo ya existe; elegir otra ruta.'; exit 1; }
export APP_BASE_PATH=''
export FINANZAS_COOKIE_SECURE=0
export FINANZAS_REQUIRE_STRONG_ADMIN_PASSWORD=1
read -r -s -p 'Clave inicial privada de 12 o más caracteres: ' FINANZAS_INITIAL_ADMIN_PASSWORD
printf '\n'
export FINANZAS_INITIAL_ADMIN_PASSWORD
```

No mostrar la variable de contraseña ni guardarla en el repositorio. Estos bloques configuran solo la terminal actual y utilizan una clave privada también para el ensayo local.

### Inicializar y cargar ejemplos

```bash
python scripts/init_db.py
python scripts/check_connection.py
python scripts/seed.py
```

Una inicialización nueva crea el administrador `admin`, su perfil y los catálogos iniciales. La contraseña queda como hash y salt. Las bases existentes conservan usuarios y contraseñas; la variable inicial no las restablece.

`seed.py` carga **5 movimientos ficticios y 4 presupuestos del mes y año de ejecución**. No fija noviembre de 2026 permanentemente. Si el perfil inicial ya tiene movimientos, no repite los cinco ejemplos; los presupuestos tampoco duplican la combinación existente. La inicialización activa WAL y el esquema actual contiene 17 tablas de aplicación.

### Comprobar SQLite en modo de solo lectura

Desde la misma terminal, con el `DB_PATH` de ensayo ya definido:

```bash
python -c "import os,sqlite3; from pathlib import Path; p=Path(os.environ['DB_PATH']).resolve(); c=sqlite3.connect(p.as_uri()+'?mode=ro',uri=True); print('SQLite:',sqlite3.sqlite_version); print('WAL:',c.execute('PRAGMA journal_mode').fetchone()[0]); print('Tablas:',c.execute('SELECT COUNT(*) FROM sqlite_master WHERE type=? AND name NOT LIKE ?',('table','sqlite_%')).fetchone()[0]); print('Integridad:',c.execute('PRAGMA integrity_check').fetchone()[0]); print('Errores FK:',len(c.execute('PRAGMA foreign_key_check').fetchall())); print('Movimientos:',c.execute('SELECT COUNT(*) FROM movimientos WHERE id_perfil=1').fetchone()[0]); print('Presupuestos:',c.execute('SELECT anio,mes,COUNT(*) FROM presupuestos WHERE id_perfil=1 GROUP BY anio,mes').fetchall()); c.close()"
```

En una base recién inicializada y sembrada se esperan `wal`, 17 tablas, integridad `ok`, 0 errores FK, 5 movimientos y 4 presupuestos del período. `mode=ro` impide crear otra base si la ruta no existe. Esta inspección no lee contraseñas ni hashes. Se recupera y amplía el procedimiento documental de Diego; [procedencia y decisiones de consolidación](docs/seguimientos/S4_APORTE_RESPALDO_DIEGO.md).

### Pruebas, arranque y flujo de uso

```bash
python -m unittest discover -s tests -v
python -m scripts.verify_clean_install_s4 --report evidencia_s4_nueva_instalacion.md
python -m src.app --host 127.0.0.1 --port 8000
```

Abrir `http://127.0.0.1:8000/login`, ingresar como `admin` con la clave privada elegida y seleccionar el perfil inicial. Comprobar los cinco movimientos en el resumen y los cuatro presupuestos en **Planificación → Presupuestos**, usando el período de carga. El servidor admite otro puerto libre mediante `--port`. Detener con `Ctrl+C`.

El verificador de instalación usa su propia SQLite temporal, seed idempotente, integridad, WAL, login HTTP y cookie Secure; no utiliza la base del despliegue. La suite vigente tiene **109 resultados correctos documentados**. Registrar siempre el total real de una nueva ejecución, incluidos errores u omisiones. Los resultados antiguos de **103 y 105** se conservan exclusivamente como antecedentes en [S4](docs/seguimientos/S4.md) y [CHANGELOG](CHANGELOG.md).

### Validación independiente por otro integrante

La instalación automatizada no acredita esta validación. Otra persona debe seguir exclusivamente este README en una copia y base nuevas, y registrar:

1. Identidad autorizada, fecha, sistema, Python/SQLite, commit del código y revisión del README.
2. Comandos y salidas de inicialización, conexión, seed, comprobación de solo lectura y suite, con el conteo realmente observado.
3. Login, selección del perfil, movimientos y presupuestos del período; prueba manual de CRUD y capturas ficticias sin secretos.
4. Si completó el procedimiento sin ayuda, dificultades, instrucciones externas y repetición de los pasos corregidos.

Usar la [ficha de S4](docs/seguimientos/S4.md#validación-independiente-por-otro-integrante) y el [acta](docs/seguimientos/ACTA_S4.md). La identidad y el resultado no se completan por inferencia ni por haber clonado otra copia.

## Variables, almacenamiento y despliegue

| Variable | Comportamiento vigente |
| --- | --- |
| `DB_PATH` | Archivo SQLite; por defecto `data/finanzas.sqlite3` dentro del proyecto. Las rutas configuradas relativas se resuelven desde la carpeta de ejecución. |
| `APP_BASE_PATH` | Vacío para localhost; `/finanzas` detrás del proxy del curso. |
| `FINANZAS_INITIAL_ADMIN_PASSWORD` | Crea la clave inicial, no cambia las existentes. En una base nueva con prefijo web se exigen 12+ caracteres y se rechaza el valor público de demostración. |
| `FINANZAS_REQUIRE_STRONG_ADMIN_PASSWORD` | Con `1`, exige esa regla fuerte también al crear una base local sin prefijo. |
| `FINANZAS_COOKIE_SECURE` | Usar `1` bajo HTTPS/proxy; `0` para el ensayo local HTTP. |

El modo local histórico sin prefijo admite una credencial pública de demostración si no se fija la variable inicial; los pasos de esta guía emplean una clave privada. La afirmación anterior al S4 de que el prefijo no exigía una clave fuerte quedó superada por `src/auth.py` de `main`.

Usuarios y hashes viven en SQLite; comprobantes y logs se guardan junto a la base, y el panel de calidad utiliza `QUALITY_DIR` o la carpeta `quality/` junto a la base. No publicar SQLite, credenciales, adjuntos ni logs privados. En CRNube, el código y `DB_PATH` se mantienen fuera de `public_html`; Apache publica `/finanzas` hacia `127.0.0.1:8010`.

El despliegue del **6/11/2026 en `8a88aeb`** y su respaldo previo fueron confirmados por el responsable. La verificación interna del servidor se atribuye a esa evidencia; el GET de login no la sustituye. No ejecutar seed, carga masiva, pruebas destructivas ni migraciones contra esa base. La configuración de un despliegue nuevo y el respaldo se describen en [Instalación S4](docs/INSTALACION_S4.md), separados del ensayo local.

## Herramientas de verificación y respaldo

| Comando | Alcance |
| --- | --- |
| `python -m scripts.backup_sqlite_s4 DESTINO_NUEVO` | Respalda la base indicada por `DB_PATH` mediante `sqlite3.Connection.backup`, valida integridad/FK y no sobrescribe el destino. Usar una ubicación privada. |
| `python -m scripts.seed_bulk_s2 --count 1000` | Escribe datos sintéticos en `DB_PATH`; exclusivamente sobre otra base de ensayo. Evita repetir marcadores `SIM-S2-`. |
| `python -m scripts.evidencia_s2 --output evidencia_s2_nueva.md --count 1000` | Suite y carga sobre SQLite temporal; conserva su alcance de evidencia automática. |
| `python -m scripts.benchmark_s3 --count 100000 --runs 5 --output mediciones_nuevas.md` | Tres operaciones, medianas y planes sobre bases temporales. No reemplazar los informes S3 históricos. |
| `python scripts/e2e/run_e2e.py --pace 0 --output evidencias/ejecucion_nueva` | Recorrido local de navegador; requiere el entorno QA separado y un destino vacío. |

No copiar directamente un archivo SQLite activo en WAL como sustituto de la API de respaldo. La [guía de QA](scripts/e2e/README.md) explica preparación, captura, reportes y límites. Las variantes `benchmark_s3_diego.py` e `indices_s3.py` conservan su trazabilidad. `scripts/demo_temporal.py` no está en el árbol actual ni en el tag `v0.4.0` inspeccionado; la demostración actual utiliza `scripts/seed.py`.

## Evidencias locales, publicación y cierre académico

| Material | Evidencia existente | Pendiente |
| --- | --- | --- |
| Pruebas y mediciones del 11/11/2026 | [109/109 regresiones](evidencias/s4_final/reportes/virtualmin/suite.json), [mediciones con y sin índices](evidencias/s4_final/reportes/virtualmin/benchmark.md) y [procedencia, hashes y alcance](docs/seguimientos/evidencia_final_pruebas.md). La [matriz histórica S4](docs/seguimientos/ENTREGA_S4.md) conserva las 27 E2E y los registros del 6/11/2026 de regresión, instalación, carga y respaldo | `suite.json`, `benchmark.md` y el documento de evidencia publicados en GitHub en `cb8e7f9`; reporte E2E histórico original no disponible en este checkout, sin nueva ejecución E2E |
| Capturas auténticas | [Login](evidencias/s4_final/capturas/01_login.png), [dashboard](evidencias/s4_final/capturas/02_dashboard.png), [presupuesto](evidencias/s4_final/capturas/07_presupuestos.png), [historial](evidencias/s4_final/capturas/10_historial.png), [reporte](evidencias/s4_final/capturas/11_reporte_anual.png) y CRUD en la misma carpeta | Publicación selectiva tras revisión |
| Video auténtico | [Primera toma local](evidencias/s4/video/MisFinanzas_S4.mp4), guiones y versiones de trabajo sincronizadas en `evidencias/s4_final/` | **Video final sincronizado en preparación**, revisión del grupo, URL y permisos del profesor |
| Ficha del portal | [portal.yml](portal.yml): 15 campos académicos y cuatro integrantes registrados en `autores_publicos` | `demo_video` y `captura` vacíos hasta disponer de URL aprobadas |
| Entrega | [Matriz S4](docs/seguimientos/ENTREGA_S4.md) y [acta](docs/seguimientos/ACTA_S4.md) | Instalación independiente, participación y comentarios docentes, presentación/PDF y decisión sobre tags |

Los archivos cuyo nombre incluye `FINAL` son versiones de trabajo locales conservadas; su existencia y sus verificaciones técnicas no equivalen a aceptación editorial ni publicación. Los ZIP y reportes anteriores permanecen como snapshots de sus ejecuciones. El estado de entrega solicitado por el responsable sigue siendo **preparación del video final**. No hay un enlace público de video acreditado.

## Seguimientos y CI

- **S1:** problema, arquitectura y modelo inicial; [bitácora](docs/seguimientos/S1.md).
- **S2:** integración V17, CRUD, carga transaccional y pruebas; [bitácora](docs/seguimientos/S2.md). Los tags históricos no incorporan automáticamente cambios posteriores.
- **S3:** cierre técnico confirmado en [Issue #3](https://github.com/sebastins18/Control_Finanzas_Familiares/issues/3); [mediciones originales](docs/seguimientos/S3_mediciones.md), [índices](docs/seguimientos/indices_s3.md) y [bitácora](docs/seguimientos/S3.md). Incluye [pruebas de funcionamiento: caso normal, errores de conexión SQLite y datos inválidos](docs/seguimientos/pruebas_s3.md), y [tabla de mediciones e interpretación de resultados](docs/seguimientos/mediciones_s3.md). La comparación WAL/DELETE es opcional, no reabre el cierre ni cambia los resultados medidos.
- **S4:** [bitácora](docs/seguimientos/S4.md), [matriz](docs/seguimientos/ENTREGA_S4.md), [exposición](docs/seguimientos/GUIA_DEMO_FINAL.md) y [video](docs/seguimientos/VIDEO_S4.md). Cierre técnico y evidencia automática no equivalen a aprobación académica.

La CI existente conserva Ubuntu con Python 3.11/3.12 y un trabajo Windows 3.12 para instalación, seguridad y respaldo. La [ejecución histórica del merge S4](https://github.com/sebastins18/Control_Finanzas_Familiares/actions/runs/42303414421) documenta los tres trabajos; esta consolidación documental no declara una nueva ejecución de CI ni modifica su configuración.

## Roadmap

Propuestas desde el 6/11/2026, sujetas a priorización del equipo; no se presentan como funciones ya implementadas ni compromisos aprobados.

| Horizonte | Mejoras previstas | Cómo verificar |
| --- | --- | --- |
| Un mes — diciembre de 2026 | Completar evidencias del curso; mejorar usabilidad/accesibilidad; ampliar CSRF, sesiones, límites de intentos y controles de acceso; diseñar recuperación de contraseña con verificación de identidad; ensayar restauración | Revisión de UX, pruebas de seguridad/permisos y restauración sobre ensayo antes de habilitar cambios |
| Seis meses — mayo de 2027 | Gráficos, comparaciones y ampliación de reportes/CSV y notificaciones; operación supervisada, sesiones persistentes, monitoreo y backups | Contrastar gráficos y exportaciones con SQLite, no duplicar alertas existentes, comprobar operación y recuperación |
| Posible TFG | Investigar patrones de gastos, planificación y recomendaciones explicables, con evaluación de usabilidad | Propuesta, consentimiento, protección de datos y metodología sujetos a aprobación universitaria |

[Roadmap desarrollado](docs/ROADMAP.md). El análisis predictivo y las recomendaciones personalizadas son posibilidades de investigación, no prestaciones actuales.

## Colaboración, atribución y licencia

**Diego Fonseca (`dfonseca15`)** aportó la explicación detallada del proyecto, arquitectura, instalación, verificación de solo lectura, matriz S4, ficha académica y roadmap en [`4b0bfed`](https://github.com/sebastins18/Control_Finanzas_Familiares/commit/4b0bfed6ae37e527daf72fc3b6aa8727e990e199). Esta consolidación recupera y actualiza ese contenido sobre `main`, conservando la seguridad y las evidencias posteriores. La rama histórica no tiene commits exclusivos pendientes; `main` está nueve commits por delante al corte. [Comparación y atribución detalladas](docs/seguimientos/S4_APORTE_RESPALDO_DIEGO.md).

Los aportes de los demás integrantes conservan sus commits, PR y [registro del equipo](docs/seguimientos/EVIDENCIA_EQUIPO.md); no se reasigna autoría ni se inventan participaciones o aprobaciones. [Issues](https://github.com/sebastins18/Control_Finanzas_Familiares/issues) · [Project](https://github.com/users/sebastins18/projects/1) · [CHANGELOG](CHANGELOG.md).

Licencia [MIT](LICENSE), copyright 2026 Grupo 5, Universidad Nacional. Conservar el aviso y la licencia al redistribuir. No publicar cédulas, credenciales ni datos personales sin autorización.
