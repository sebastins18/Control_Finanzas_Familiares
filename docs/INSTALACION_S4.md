# Instalación y verificación independiente — S4

Proyecto de demostración académica. Solo datos **ficticios**; no es apto para uso financiero real ni para exposición abierta sin endurecimiento adicional.

## Requisitos
- Python 3.11 o 3.12 (probado por GitHub Actions); no requiere instalar paquetes de terceros.
- Git (para descargar el repositorio).
- Permiso de escritura en una carpeta privada fuera de la carpeta web.
- SQLite está incluido en el módulo estándar `sqlite3` de Python.

## A. Instalación nueva en Windows (PowerShell)

```powershell
git clone https://github.com/sebastins18/Control_Finanzas_Familiares.git
cd Control_Finanzas_Familiares
$PrivateDir = Join-Path $HOME "finanzas_s4_private"
New-Item -ItemType Directory -Force $PrivateDir | Out-Null
$env:DB_PATH = Join-Path $PrivateDir "finanzas.sqlite3"
$env:APP_BASE_PATH = ""
$secreta = Read-Host "Clave inicial de admin (12+ caracteres)" -AsSecureString
$env:FINANZAS_INITIAL_ADMIN_PASSWORD = ([System.Net.NetworkCredential]::new("", $secreta)).Password
py scripts/init_db.py
py scripts/seed.py
py scripts/check_connection.py
py -m unittest discover -s tests -v
py -m scripts.verify_clean_install_s4 --report "$HOME\finanzas_s4_prueba.md"
py -m src.app --host 127.0.0.1 --port 8000
```

Abrir `http://127.0.0.1:8000/login`; usuario `admin` y contraseña privada definida. Detener el servidor con `Ctrl+C`. No compartir la clave ni guardarla en GitHub. No subir la base SQLite.

## B. Instalación nueva en Linux (terminal WebAdmin/CRNube)

```bash
cd "$HOME"
git clone https://github.com/sebastins18/Control_Finanzas_Familiares.git finanzas_s4_nueva
cd "$HOME/finanzas_s4_nueva"
mkdir -p "$HOME/finanzas_s4_private"
chmod 700 "$HOME/finanzas_s4_private"
umask 077
export DB_PATH="$HOME/finanzas_s4_private/finanzas.sqlite3"
export APP_BASE_PATH=""
read -r -s -p "Clave inicial admin (12+ caracteres): " FINANZAS_INITIAL_ADMIN_PASSWORD
echo
export FINANZAS_INITIAL_ADMIN_PASSWORD
python3 scripts/init_db.py
python3 scripts/seed.py
python3 scripts/check_connection.py
python3 -m unittest discover -s tests -v
python3 -m scripts.verify_clean_install_s4 --report "$HOME/finanzas_s4_prueba.md"
python3 -m src.app --host 127.0.0.1 --port 8000
```

En el servidor del curso, no iniciar un segundo proceso en el puerto 8010 si ya está ocupado por la demo original. **No copiar ni sobrescribir** `/home/grupo5/finanzas_private/finanzas.sqlite3`. El ejemplo anterior usa una carpeta privada independiente.

## C. Verificación automática de instalación LIMPIA

```bash
python3 -m scripts.verify_clean_install_s4 --report evidencia_s4_instalacion.md
```

Este comando crea un SQLite temporal nuevo con una contraseña aleatoria, ejecuta inicialización, seed dos veces, verificación de conexión, consulta `PRAGMA integrity_check`, `foreign_key_check`, WAL, login HTTP y comprobación de cookie segura. El SQLite temporal se elimina al terminar. **No equivale a la instalación realizada por otro integrante** exigida por la rúbrica: recoger nombre, fecha, máquina y resultado de esa prueba humana en la bitácora.

## D. Configuración Apache / proxy del curso (no cambiar la instancia existente sin respaldo)

El código Python se mantiene fuera de `public_html` y escucha en `127.0.0.1:8010`. El proxy de CRNube publica `/finanzas`. Para una nueva instalación gestionada por el administrador:

```bash
export APP_BASE_PATH=/finanzas
export FINANZAS_COOKIE_SECURE=1
read -r -s -p "Clave admin nueva (12+ caracteres): " FINANZAS_INITIAL_ADMIN_PASSWORD
 echo
export FINANZAS_INITIAL_ADMIN_PASSWORD
export DB_PATH="$HOME/finanzas_private/finanzas.sqlite3"
python3 -m src.app --host 127.0.0.1 --port 8010
```

**No ejecutar el bloque anterior sobre el servidor del curso sin revisar el proceso en ejecución, el respaldo y las credenciales existentes.** `FINANZAS_INITIAL_ADMIN_PASSWORD` solo crea una clave inicial en una base nueva; no cambia contraseñas existentes. La opción `FINANZAS_COOKIE_SECURE=1` exige HTTPS en el navegador y debe establecerse cuando Apache termina TLS. Las sesiones aún viven en la memoria del proceso; `nohup` no garantiza recuperación tras reinicios. No usar este prototipo como servicio productivo.

## E. Respaldo antes de migrar SQLite

Con el entorno `DB_PATH` apuntando a la base que se desea respaldar, hacer un backup consistente en un **directorio privado**:

```bash
mkdir -p "$HOME/finanzas_backups"
chmod 700 "$HOME/finanzas_backups"
python3 -m scripts.backup_sqlite_s4 "$HOME/finanzas_backups/finanzas_antes_migracion.sqlite3"
```

La herramienta usa `sqlite3.Connection.backup` y valida integridad y claves foráneas. No sobrescribe respaldos. Evitar copiar directamente el archivo `.sqlite3` mientras el proceso usa WAL.

## F. Evidencia que debe realizar un integrante distinto

1. Abrir el README en una máquina limpia o perfil del sistema nuevo.
2. Seguir solo los comandos, sin recibir instrucciones verbales adicionales.
3. Registrar versiones de Python/SQLite, sistema operativo, fecha y resultado de pruebas.
4. Crear un gasto ficticio, editarlo, eliminarlo y mostrar el estado en la interfaz.
5. Guardar capturas sin contraseñas, nombres reales ni datos financieros.
6. Escribir en `docs/seguimientos/S4.md` quién hizo la prueba, errores encontrados, correcciones y enlace a la evidencia.

**Importante:** nunca incluir cédulas ni credenciales reales en el repositorio público.
