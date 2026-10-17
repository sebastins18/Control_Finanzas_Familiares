# Pasos manuales necesarios para entregar S1 en GitHub

**Importante:** estos pasos requieren acceso real al GitHub del grupo; no pueden demostrarse con un ZIP.

## 1. Crear repositorio

Crear en GitHub `grupo5-finanzas-familiares`, visibilidad **Public**, sin README inicial si se subirá el de este paquete. Agregar el remoto correcto:

```powershell
git init
git branch -M main
git add .
git commit -m "chore: base del proyecto de finanzas y arquitectura S1"
git remote add origin https://github.com/USUARIO-REAL/grupo5-finanzas-familiares.git
git push -u origin main
```

**Sustituir USUARIO-REAL** por el propietario; si el repositorio ya existe, no re-inicializarlo: copiar solo los archivos al repo y hacer commits normales.

## 2. Agregar colaboradores

GitHub → Settings → Collaborators → Add people. Invitar a Sebastián, Diego, Crystian y Mariano, mediante sus usuarios reales.

Cada integrante debe hacer al menos un commit **propio**, por ejemplo:

| Responsable sugerido | Archivo(s) a revisar/editar | Commit recomendado |
| --- | --- | --- |
| Sebastián | `src/app.py` | `feat: interfaz y rutas de movimientos` |
| Diego | `src/schema.sql` y `scripts/seed.py` | `feat: esquema sqlite y datos sinteticos` |
| Crystian | `docs/arquitectura/modelo-v1.md` y `src/db.py` | `docs: modelo y presupuestos` |
| Mariano | `README.md`, `tests/` y `docs/seguimientos/S1.md` | `test: validar instalacion y documentacion` |

El trabajo debe ser efectivo y cada persona debe poder explicarlo. **No fabricar commits a nombre de otros.**

## 3. Crear Issues / hitos

En GitHub Issues, crear al menos:

1. `[S1] Publicar repositorio, colaboradores y licencia` — dueño real / milestone S1.
2. `[S1] Arquitectura y modelo SQLite v1` — dueño real / milestone S1.
3. `[S1] Conexión y datos de prueba` — dueño real / milestone S1.
4. `[S2] Consolidar CRUD de movimientos y presupuestos` — dueño real / milestone S2.
5. `[S3] Comparación con/sin índices y pruebas` — dueño real / milestone S3.
6. `[S4] Instalación desde cero, video y release` — dueño real / milestone S4.

Crear los hitos en la sección de Milestones de GitHub (si no se puede, etiquetar los Issues con `S1`, `S2`, etc.). Registrar los enlaces en `docs/seguimientos/S1.md`.

## 4. Bitácora y tag

Antes de crear el tag:

```powershell
git status
git add docs/seguimientos/S1.md README.md
git commit -m "docs: bitacora de seguimiento 1 con evidencias reales"
git push

git tag -a v0.1.0 -m "Seguimiento 1 - arquitectura y repositorio"
git push origin v0.1.0
```

Verificar en GitHub que **v0.1.0 apunta al commit final** de S1 y que el archivo `docs/seguimientos/S1.md` está dentro del tag. El enunciado establece entrega a más tardar a las **6 p. m. del 16/10/2026**; si ya pasó, hacer la entrega de inmediato y aclarar la situación al profesor.

## 5. Verificar

- El repositorio es público y la licencia MIT aparece.
- No se versionó `data/*.sqlite3`, `.env` ni credenciales.
- Todos los integrantes están como colaboradores y tienen su propio commit.
- Issues con responsables y avance comprobable.
- `/health` responde `status: ok`; la app local muestra datos ficticios.
- Existe un tag remoto `v0.1.0` y el archivo de la bitácora.
