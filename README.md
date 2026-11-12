# MisFinanzas — Control de Finanzas Familiares

**Grupo 5 · Universidad Nacional · Tópicos Avanzados de Bases de Datos · II-2026**

MisFinanzas ayuda a personas y familias a registrar ingresos y gastos, organizar cuentas y categorías, planificar presupuestos y consultar cómo utilizan su dinero. Responde al problema de tener movimientos domésticos dispersos y poca visibilidad de los saldos y límites del mes. Los perfiles financieros permiten separar la información de cada familia e invitar a otros usuarios.

Es un MVP académico open source con datos ficticios. El backend utiliza Python estándar y un único motor SQLite; la interfaz web sirve HTML, CSS y JavaScript. Las dependencias de Playwright y edición de video pertenecen a las herramientas de QA, no al funcionamiento de la aplicación.

**Versión final: `v1.0.0` — viernes 13 de noviembre de 2026.**

## Estado de la entrega final

| Área                  | Situación actual                                                                                                                         | Procedencia                                                                                                                                                                                                             |
| --------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Base técnica          | Rama main, con el código, las funcionalidades, las pruebas y la documentación correspondientes a los seguimientos S1 a S4.                                                   | Historial Git; PR #20, #21 y #22                                                                                                                                                                                        |
| CRNube                | S4 desplegado el **6/11/2026 sobre `8a88aeb`**, con respaldo SQLite consistente anterior a la actualización                              | Confirmación del responsable; esta revisión documental no administra el servidor                                                                                                                                        |
| SQLite del despliegue | **WAL, 17 tablas, integridad `ok` y 0 errores de claves foráneas**                                                                       | Verificación del despliegue aportada por el responsable; comprobaciones locales separadas                                                                                                                               |
| Pruebas automatizadas finales | **122/122 exitosas**, 0 fallos, 0 errores y 0 omisiones; **123,43 segundos** | Virtualmin, **12/11/2026**; [suite original](evidencias/s4_final/reportes/virtualmin/suite.json) y [detalle de la ejecución](docs/seguimientos/evidencia_final_pruebas.md) |
| Navegador             | **27/27 E2E satisfactorias, 0 fallidas y 0 omitidas**, según el registro histórico del 6/11/2026                                         | [Matriz histórica S4](docs/seguimientos/ENTREGA_S4.md); reporte original no disponible en este checkout, sin nueva ejecución E2E                                                                                        |
| S3                    | Cerrado técnicamente en [Issue #3](https://github.com/sebastins18/Control_Finanzas_Familiares/issues/3)                                  | GitHub: `closed`, motivo `completed`; sin atribuir aprobación docente                                                                                                                                                   |
| Video                 | Hay grabaciones y versiones de trabajo locales; el **video final sincronizado sigue en preparación para la entrega y no está publicado** | [Estado y evidencias audiovisuales](docs/seguimientos/VIDEO_S4.md)                                                                                                                                                      |
| Versión final | **`v1.0.0` — viernes 13 de noviembre de 2026** | [Registro de cambios](CHANGELOG.md) |

La aplicación se encuentra publicada en [MisFinanzas en CRNube](https://diego01.grupo5.crnube.org/finanzas/login). Las verificaciones del despliegue y sus evidencias se encuentran documentadas en la [matriz de entrega S4](docs/seguimientos/ENTREGA_S4.md).

La ejecución final registró **122 pruebas exitosas**, sin fallos, errores ni omisiones, en **123,43 segundos**. Las evidencias están incorporadas en el repositorio y permiten consultar los resultados de las verificaciones realizadas. La [documentación de evidencias](docs/seguimientos/evidencia_final_pruebas.md) conserva la procedencia, los hashes y los antecedentes históricos.

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

MisFinanzas incorpora requisitos de contraseña inicial fuerte para bases nuevas bajo prefijo web, cookies seguras configurables y cabeceras de protección. Como proyecto académico, todavía requiere mejoras en la gestión de sesiones, la protección contra solicitudes no autorizadas y la prevención de intentos repetidos de acceso. El servidor utiliza `http.server` y sesiones en memoria; las defensas CSRF y contra fuerza bruta son incompletas. Por esta razón, se recomienda utilizar datos ficticios y no emplear la aplicación para gestionar información financiera sensible en producción.

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

En Windows puede usarse py; en Linux, python3. Emplear el mismo intérprete en todos los pasos y registrar el commit instalado para mantener la trazabilidad.

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

En una base recién inicializada y sembrada se esperan `wal`, 17 tablas, integridad `ok`, 0 errores FK, 5 movimientos y 4 presupuestos del período. `mode=ro` impide crear otra base si la ruta no existe. Esta inspección no lee contraseñas ni hashes.
### Pruebas, arranque y flujo de uso

```bash
python -m unittest discover -s tests -v
python -m scripts.verify_clean_install_s4 --report evidencia_s4_nueva_instalacion.md
python -m src.app --host 127.0.0.1 --port 8000
```

Abrir `http://127.0.0.1:8000/login`, ingresar como `admin` con la clave privada elegida y seleccionar el perfil inicial. Comprobar los cinco movimientos en el resumen y los cuatro presupuestos en **Planificación → Presupuestos**, usando el período de carga. El servidor admite otro puerto libre mediante `--port`. Detener con `Ctrl+C`.

El verificador de instalación usa su propia SQLite temporal, seed idempotente, integridad, WAL, login HTTP y cookie Secure; no utiliza la base del despliegue. Al ejecutar las pruebas, se debe registrar el total real de resultados, incluidos los fallos, errores u omisiones que puedan presentarse.

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

El modo local sin prefijo admite una credencial de demostración si no se configura una contraseña inicial. Para una instalación nueva, se recomienda utilizar una contraseña privada y segura, como se indica en esta guía.

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

No copiar directamente un archivo SQLite activo en WAL como sustituto de la API de respaldo. La [guía de QA](scripts/e2e/README.md) explica preparación, captura, reportes y límites. Las variantes `benchmark_s3_diego.py` e `indices_s3.py` conservan su trazabilidad.

## Evidencias locales, publicación y cierre académico

| Material | Evidencia existente | Pendiente |
| --- | --- | --- |
| Pruebas y mediciones de Virtualmin del 12/11/2026 | [122/122 pruebas exitosas](evidencias/s4_final/reportes/virtualmin/suite.json), sin fallos, errores ni omisiones, en 123,43 segundos; [mediciones de rendimiento](evidencias/s4_final/reportes/virtualmin/benchmark.md) y [trazabilidad](docs/seguimientos/evidencia_final_pruebas.md) | Reporte E2E histórico original no incluido; no se realizó una nueva ejecución E2E |
| Capturas auténticas | [Login](evidencias/s4_final/capturas/01_login.png), [dashboard](evidencias/s4_final/capturas/02_dashboard.png), [presupuesto](evidencias/s4_final/capturas/07_presupuestos.png), [historial](evidencias/s4_final/capturas/10_historial.png), [reporte](evidencias/s4_final/capturas/11_reporte_anual.png) y CRUD en la misma carpeta | Publicación selectiva tras revisión |
| Video auténtico | Primera toma local — `evidencias/s4/video/MisFinanzas_S4.mp4` (archivo histórico no incluido en este checkout), guiones y versiones de trabajo sincronizadas en `evidencias/s4_final/` | **Video final sincronizado en preparación**, revisión del grupo, URL y permisos del profesor |
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

Las siguientes mejoras son propuestas futuras, sujetas a evaluación y priorización del equipo; no son funcionalidades implementadas ni compromisos aprobados.

| Horizonte | Mejoras propuestas | Verificación prevista |
| --- | --- | --- |
| Un mes — diciembre de 2026 | Mejorar usabilidad y accesibilidad; fortalecer la seguridad de sesiones y los controles de acceso; diseñar recuperación segura de contraseñas; realizar pruebas de restauración de datos | Pruebas de usabilidad, seguridad, permisos y recuperación de información |
| Seis meses — mayo de 2027 | Incorporar gráficos y comparaciones financieras; ampliar reportes, exportaciones y notificaciones; mejorar monitoreo, gestión de sesiones y copias de seguridad | Contrastar los resultados con los registros de SQLite y comprobar las nuevas funcionalidades |
| Posible TFG | Investigar patrones de ingresos y gastos; estudiar herramientas de apoyo a la planificación financiera; explorar recomendaciones personalizadas y explicables | Propuesta de investigación con metodología, evaluación de usabilidad y protección de datos, sujeta a aprobación universitaria |

El [roadmap desarrollado](docs/ROADMAP.md) detalla las propuestas y sus criterios de verificación.

## Colaboración, atribución y licencia

MisFinanzas es el resultado del trabajo grupal de desarrollo, integración, pruebas y documentación. Los aportes individuales se respaldan en el historial de Git, los pull requests y la [documentación de seguimiento](docs/seguimientos/S4.md), junto con el [registro del equipo](docs/seguimientos/EVIDENCIA_EQUIPO.md) y los [antecedentes de atribución documental](docs/seguimientos/S4_APORTE_RESPALDO_DIEGO.md). Estos registros conservan la autoría y la trazabilidad de las contribuciones.

[Issues](https://github.com/sebastins18/Control_Finanzas_Familiares/issues) · [Project](https://github.com/users/sebastins18/projects/1) · [CHANGELOG](CHANGELOG.md).

Licencia [MIT](LICENSE), copyright 2026 Grupo 5, Universidad Nacional. Conservar el aviso y la licencia al redistribuir. No publicar cédulas, credenciales ni datos personales sin autorización.
