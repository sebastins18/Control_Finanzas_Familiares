# MisFinanzas — Control de Finanzas Familiares

**Grupo 5 · Universidad Nacional · Tópicos Avanzados de Bases de Datos · II-2026**

MisFinanzas ayuda a personas y familias a registrar ingresos y gastos, organizar presupuestos y consultar en qué utilizan su dinero. Está dirigido a quienes necesitan llevar un control doméstico por cuentas y categorías, con perfiles financieros separados e invitados.

Prototipo académico web en Python y SQLite, con datos ficticios para demostración. Preparación del Seguimiento 4 del **06/11/2026**, versión objetivo **v0.9.0**, todavía sin tag ni publicación de esa versión. La instalación de prueba reportada corresponde al commit `94412a1`; la validación por otro integrante está pendiente. Véase la [bitácora S4](docs/seguimientos/S4.md).

## Funcionalidades actuales

- Registro, consulta, edición y eliminación de ingresos y gastos; resumen mensual y alertas de presupuesto.
- Cuentas, categorías, monedas, presupuestos, metas y movimientos de ahorro; transferencias entre cuentas.
- Historial con filtros, paginación y exportación CSV; reporte anual por categoría y moneda.
- Plantillas de movimientos recurrentes con generación explícita e idempotente.
- Perfiles financieros con propietario e invitados, separados de las cuentas de acceso.
- Registro e inicio de sesión, cambio de contraseña y mantenimiento de usuarios exclusivo para administradores activos. La recuperación de contraseña requiere un administrador.
- Comprobantes guardados localmente y panel de calidad para administradores.
- Importes en centavos enteros; totales por moneda. Las transferencias entre divisas requieren un tipo de cambio manual positivo; no hay descarga automática de cotizaciones.

## Arquitectura y tecnologías

Perfil A: **SQLite como único motor**, sin Redis ni motor secundario. El navegador recibe HTML y CSS del servidor HTTP de la biblioteca estándar de Python. Las escrituras usan SQL parametrizado y transacciones; SQLite emplea WAL y claves foráneas. Las sesiones y la caché de lectura viven en memoria y se pierden al reiniciar el proceso.

| Componente | Archivos y responsabilidad |
| --- | --- |
| Servidor e interfaz | `src/app.py`, `src/static/`: rutas, sesiones, formularios y estilos |
| Persistencia | `src/db.py`, `src/schema.sql`: conexiones, esquema base e inicialización |
| Autenticación | `src/auth.py`: usuarios SQLite, roles, migraciones, PBKDF2-HMAC-SHA256 y salt |
| Finanzas y perfiles | `src/extension.py`, `src/finance.py`, `src/profiles.py`: extensiones y aislamiento financiero |
| Consultas y recurrencias | `src/reportes.py`, `src/recurrentes.py` |
| Errores, caché y calidad | `src/read_cache.py`, `src/quality.py`, manejo de errores en `src/app.py` y `src/db.py` |
| Herramientas y pruebas | `scripts/`, `tests/`, `.github/workflows/ci.yml` |

`src/schema.sql` no representa por sí solo todo el modelo: `db.init_db()` también inicializa autenticación, extensiones, perfiles y cotizaciones. El resultado actual es de **17 tablas de aplicación**; las cinco tablas citadas en documentos de S1 son históricas.

Referencias: [decisiones](docs/decisiones.md), [usuarios y migraciones](docs/usuarios_roles.md), [perfiles y permisos](docs/perfiles_financieros.md), [historial, reportes y recurrencias](docs/consultas_reportes_recurrentes.md). Los diagramas de [arquitectura](docs/arquitectura/README.md) conservan modelos de etapas anteriores y deben interpretarse junto con el código actual.

## Requisitos

- Git para obtener el repositorio.
- Python **3.11 o superior** con `sqlite3` disponible. La matriz de CI está configurada para Python 3.11 y 3.12; eso no acredita por sí solo una ejecución exitosa de CI.
- Navegador y una carpeta local con permiso de escritura para SQLite y sus archivos WAL.
- No hay dependencias de terceros que instalar con `pip`. No se requiere el ejecutable de consola de SQLite.

Los ejemplos usan `python`; en Windows puede sustituirse por `py` y en Linux por `python3`, según la instalación. Usar el mismo intérprete en todos los pasos.

## Instalación desde cero

El procedimiento principal utiliza el código publicado en la rama `main` del repositorio, sin fijar un commit histórico ni presuponer una release v0.9.0. Ejecutar en una **copia nueva e independiente**, sin reutilizar bases ni credenciales de otra instalación:

```bash
git clone --branch main https://github.com/sebastins18/Control_Finanzas_Familiares.git
cd Control_Finanzas_Familiares
python --version
git rev-parse --short HEAD
```

Registrar el commit obtenido con `git rev-parse` para identificar la versión realmente instalada. `94412a1` se conserva únicamente como referencia de la instalación histórica verificada el 06/11/2026; no es un paso del procedimiento principal. El tag `v0.4.0` corresponde a otra etapa. **v0.9.0 sigue en preparación y no se declara publicada.**

Para validar este README actualizado, conservar también esta revisión documental: todavía no está incluida en un commit o tag. Registrar por separado el commit del código y la revisión del README entregada al integrante que hará la validación.

### Configuración

En una copia nueva destinada a demostración local, dejar `APP_BASE_PATH` vacío y comprobar que `DB_PATH` no apunta a una base existente. `.env.example` sirve de referencia: **la aplicación no carga automáticamente archivos `.env`**.

Para separar la base de demostración, se puede definir lo siguiente antes de inicializar (escoger el bloque del sistema operativo):

```powershell
# PowerShell; variables válidas en esta terminal
$env:DB_PATH = './data/demo_s4.sqlite3'
$env:APP_BASE_PATH = ''
```

```bash
# Linux/macOS; variables válidas en esta terminal
export DB_PATH=./data/demo_s4.sqlite3
export APP_BASE_PATH=
```

### Inicializar SQLite y cargar datos ficticios

```bash
python scripts/init_db.py
python scripts/check_connection.py
python scripts/seed.py
```

La inicialización crea 17 tablas y activa `journal_mode=wal`. Solo crea el usuario `admin`, con rol `administrador` y estado activo. Su contraseña inicial local es **`admin123!`** cuando `FINANZAS_INITIAL_ADMIN_PASSWORD` no está definida; este es un valor público de demostración, no una contraseña real del equipo. Si la variable está definida, se usa su valor para la creación inicial. La contraseña se almacena mediante hash y salt.

En bases ya inicializadas se conservan usuarios y contraseñas. Una instalación nueva ignora `login_credentials.json`; su lectura se conserva únicamente para migrar bases antiguas con usuarios que aún no tienen autenticación SQLite. No copiar ese JSON para preparar una instalación nueva.

`seed.py` carga **5 movimientos ficticios** en el perfil inicial y prepara **4 presupuestos del mes y año de ejecución**. El 06/11/2026 corresponde a noviembre de 2026; el script no fija ese período. Si el perfil 1 ya tiene movimientos, no agrega los cinco ejemplos; los presupuestos se insertan sin duplicar la combinación existente. Repetir `init_db.py` no restablece contraseñas.

Para comprobar la base recién creada sin modificarla, ejecutar desde la misma terminal, después de la carga:

```bash
python -c "import os, sqlite3; from pathlib import Path; p=Path(os.environ.get('DB_PATH', 'data/finanzas.sqlite3')).resolve(); c=sqlite3.connect(p.as_uri()+'?mode=ro', uri=True); print('SQLite:', sqlite3.sqlite_version); print('Journal:', c.execute('PRAGMA journal_mode').fetchone()[0]); print('Tablas:', c.execute('SELECT COUNT(*) FROM sqlite_master WHERE type=? AND name NOT LIKE ?', ('table', 'sqlite_%')).fetchone()[0]); print('Movimientos del perfil inicial:', c.execute('SELECT COUNT(*) FROM movimientos WHERE id_perfil=1').fetchone()[0]); print('Presupuestos por periodo:', c.execute('SELECT anio,mes,COUNT(*) FROM presupuestos WHERE id_perfil=1 GROUP BY anio,mes').fetchall()); c.close()"
```

Resultado esperado en una base nueva después de `seed.py`: `Journal: wal`, `Tablas: 17`, cinco movimientos y una fila de presupuestos con el año, mes y cantidad `4`. Si la ruta no existe, el modo de solo lectura falla en lugar de crear otra base. No se consultan hashes ni contraseñas.

### Ejecutar pruebas

```bash
python -m unittest discover -s tests -v
```

Las pruebas usan bases temporales. Resultado reportado para la instalación del 06/11/2026 en `94412a1`: **105 pruebas satisfactorias**. Es evidencia de esa ejecución, no una promesa de un número fijo para futuras versiones ni una nueva ejecución durante esta edición documental.

El archivo local `data/quality/suite.json` revisado contiene un resultado distinto de **103 pruebas**; se conserva intacto y no se utiliza como respaldo de las 105. Falta adjuntar la salida original de la instalación reportada.

La CI en `.github/workflows/ci.yml` ejecuta la suite y el generador de evidencia S2 en Ubuntu con Python 3.11 y 3.12.

### Iniciar la aplicación y comprobar el flujo

```bash
python -m src.app
```

Abrir **http://127.0.0.1:8000/**. Ingresar con `admin` y la contraseña inicial utilizada; seleccionar el perfil financiero inicial. En el resumen, verificar los cinco movimientos y, en **Planificación → Presupuestos**, los cuatro presupuestos del período de carga. Si se ejecuta en otro mes, seleccionar el período correspondiente. Detener con `Ctrl+C` en la terminal.

Para una prueba local en otro puerto disponible, el servidor admite `--host` y `--port`:

```bash
python -m src.app --host 127.0.0.1 --port 8001
```

Cambiar la contraseña desde **Seguridad → Cambiar contraseña** antes de exponer una instancia. La variable inicial no cambia contraseñas de cuentas ya creadas. El servidor es un prototipo académico y requiere una revisión de seguridad y operación antes de un uso público con datos reales.

### Validación por otro integrante usando solo este README

El integrante debe realizar los pasos anteriores sin reutilizar la instalación de prueba y registrar:

1. Nombre, fecha, sistema operativo, versión de Python, commit del código y revisión del README utilizada.
2. Salidas de inicialización, conexión, carga, comprobación de solo lectura y suite completa. Conservar el total real, errores u omisiones; no sustituirlo por el resultado histórico de 105.
3. Inicio de sesión, selección del perfil y visualización de movimientos y presupuestos del período cargado, junto con las capturas indicadas más abajo.
4. Resultado y dificultades: indicar si pudo completar todo utilizando solamente el README. Si necesitó instrucciones externas, documentarlas para corregir la guía y repetir los pasos afectados.

Guardar las evidencias en una ubicación de ensayo y entregar al equipo sus rutas o enlaces reales, sin contraseñas ni datos privados. Esta validación todavía no se ha acreditado; completar las instrucciones y el formulario documental no demuestra que se haya realizado.

## Variables y almacenamiento

| Variable | Comportamiento actual |
| --- | --- |
| `DB_PATH` | Archivo SQLite; por defecto `data/finanzas.sqlite3` dentro del proyecto. Las rutas relativas se resuelven desde la carpeta de ejecución. |
| `APP_BASE_PATH` | Prefijo de URL; vacío para localhost. La instalación existente usa `/finanzas`. |
| `FINANZAS_INITIAL_ADMIN_PASSWORD` | Contraseña para crear el administrador inicial. Solo si no está definida se usa `admin123!`. No se impone aquí un mínimo especial por usar un prefijo de URL. |

Las cuentas y hashes están en la tabla `usuarios` de SQLite, no en un JSON operativo. Comprobantes y registros de errores se guardan junto a la base, en `comprobantes/` y `logs/`. El panel de calidad utiliza `data/quality/`. No publicar bases, credenciales, comprobantes ni logs con información privada.

**Despliegue existente:** Virtualmin mantiene el backend en `127.0.0.1:8010` y el prefijo `/finanzas`. Esta guía local no cambia ese despliegue, su proceso ni su proxy. No ejecutar la carga de ejemplos sobre su base. El administrador debe mantener sus variables y almacenamiento privado fuera del directorio público.

## Herramientas adicionales

Ejecutar desde la raíz. Las herramientas que escriben informes deben apuntar a un archivo nuevo para conservar evidencias anteriores.

| Comando | Alcance |
| --- | --- |
| `python -m scripts.seed_bulk_s2 --count 1000` | Carga sintética en la base indicada por `DB_PATH`; usar exclusivamente una base de ensayo. Evita repetir marcadores `SIM-S2-`. |
| `python -m scripts.evidencia_s2 --output evidencia_s4_local.md --count 1000` | Ejecuta suite y carga masiva sobre SQLite temporal; escribe el informe indicado. No equivale a validación manual de S4. |
| `python -m scripts.benchmark_s3 --count 100000 --runs 5 --output mediciones_s4_local.md` | Tres operaciones, medianas y planes sobre una base temporal; escribir una salida distinta de los informes existentes. |

Las variantes `scripts/benchmark_s3_diego.py` y `scripts/indices_s3.py` se conservan por trazabilidad; sus salidas existentes y límites están documentados en S3. No ejecutarlas sobre evidencias que se deban conservar. `scripts/demo_temporal.py` **no existe en el árbol actual ni en el tag local `v0.4.0` inspeccionado**; para la demostración actual se utiliza `scripts/seed.py`.

## Capturas de pantalla

Pendientes de capturar y adjuntar; el logotipo de `src/static/logo.png` no es evidencia de uso. No se incluyen imágenes simuladas ni enlaces a archivos inexistentes.

| Captura necesaria | Qué debe mostrar |
| --- | --- |
| Inicio de sesión | Página de acceso, sin contraseñas visibles |
| Resumen del perfil de demostración | Los movimientos ficticios y el período seleccionado |
| Presupuestos | Los presupuestos del mismo período |
| Historial o reporte anual | Filtros y resultados usando solamente datos inventados |

Registrar el commit, la fecha, el entorno y la persona responsable al adjuntarlas. Su estado se mantiene en [S4](docs/seguimientos/S4.md).

## Video demostrativo

**Enlace pendiente de incorporar después de la grabación.** Recorrido propuesto: instalación y WAL, carga ficticia, pruebas, inicio de sesión, movimientos, presupuestos, historial y límites del prototipo. La grabación y la presentación final quedan fuera de esta preparación.

## Estado de entregas

- S1 y S2: modelo inicial, integración V17, carga transaccional y pruebas; conservar su contexto histórico en las bitácoras y el [CHANGELOG](CHANGELOG.md).
- S3: pruebas de errores, mediciones e índices; [bitácora](docs/seguimientos/S3.md), [mediciones](docs/seguimientos/S3_mediciones.md) y [evidencia de índices](docs/seguimientos/indices_s3.md). La comparación experimental WAL frente a DELETE sigue pendiente.
- S4 / v0.9.0 en preparación: [portal.yml](portal.yml) **creado y validado conforme a la sección 7 de la guía oficial del profesor**, con los 15 campos exactos del ejemplo. La URL de demo se comprobó mediante GET HTTPS al login; el video y la captura permanecen vacíos y los autores no se publican sin autorización. Siguen pendientes las evidencias detalladas en [S4](docs/seguimientos/S4.md), incluida la instalación por otro integrante usando solamente este README.
- Video, presentación y eventual publicación del tag: pendientes; no se declara publicada v0.9.0 ni se sustituyen las evidencias reales por la ficha del portal.

## Roadmap

Horizontes propuestos a partir del 06/11/2026, sujetos a priorización y disponibilidad del equipo. Son mejoras previstas, no funcionalidades implementadas ni compromisos de entrega aprobados.

| Horizonte | Mejoras previstas | Cómo verificar el avance |
| --- | --- | --- |
| En un mes — diciembre de 2026 | Mejorar la experiencia de usuario; fortalecer la seguridad de sesiones y los controles de acceso existentes; incorporar un mecanismo seguro de recuperación de contraseñas con verificación de identidad, ampliando el procedimiento actual que requiere un administrador. | Revisión de usabilidad y pruebas de sesiones, permisos y recuperación de contraseñas antes de habilitar los cambios. |
| En seis meses — mayo de 2027 | Incorporar gráficos para analizar ingresos y gastos; ampliar los reportes financieros y las opciones de exportación existentes, incluida la exportación CSV; mejorar las notificaciones relacionadas con los presupuestos y las metas de ahorro existentes, partiendo de las alertas presupuestarias actuales. | Verificar gráficos contra los datos financieros, probar las ampliaciones de reportes y exportación, y validar las nuevas notificaciones sin duplicar las alertas existentes. |
| Posible trabajo final de graduación | Investigar el análisis de patrones de gastos y recomendaciones personalizadas para mejorar la planificación financiera familiar. | Definir una propuesta académica y una metodología de evaluación y protección de datos, sujetas a aprobación universitaria. Es una posibilidad de investigación; el análisis y las recomendaciones no se presentan como funcionalidades implementadas ni como un trabajo de graduación aprobado. |

## Colaboración y licencia

[Issues del proyecto](https://github.com/sebastins18/Control_Finanzas_Familiares/issues) · [Tablero](https://github.com/users/sebastins18/projects/1) · [Evidencias del equipo](docs/seguimientos/EVIDENCIA_EQUIPO.md).

Los commits de integración no sustituyen la evidencia individual exigida por el curso. La [matriz S4](docs/seguimientos/S4.md) distingue los requisitos documentados de las evidencias todavía pendientes, sin atribuirles una aprobación del profesor.

Código bajo licencia **MIT**, según [LICENSE](LICENSE), copyright 2026 Grupo 5, Universidad Nacional. Se debe conservar el aviso de copyright y la licencia al redistribuirlo.
