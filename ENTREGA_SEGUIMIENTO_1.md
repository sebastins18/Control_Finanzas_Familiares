# Seguimiento 1 — Estado verificado y cierre pendiente (16/10/2026)

**Proyecto:** Control de Finanzas Familiares · **Grupo 5** · Tópicos Avanzados de Bases de Datos · UNA.

Esta guía resume el **estado real**, no una plantilla de instalación ni una afirmación de que el profesor ya aprobó el seguimiento.

## Evidencias completadas

- [x] Repositorio GitHub público: https://github.com/sebastins18/Control_Finanzas_Familiares
- [x] README, licencia y estructura de carpetas.
- [x] Arquitectura y modelo SQLite con cinco tablas operativas (`src/schema.sql`).
- [x] Inicialización, conexión y carga de datos ficticios.
- [x] Prototipo web y ruta `/health` en ejecución local.
- [x] Pruebas: **10 de 10 correctas**, según la terminal del equipo (16 de octubre).
- [x] Issues #1–#4 para S1–S4.
- [x] GitHub Project creado e Issues importados: https://github.com/users/sebastins18/projects/1/views/1
- [x] `docs/seguimientos/S1.md` actualizado con evidencias y pendientes.
- [x] Tag remoto `v0.1.0` existente; **no contiene todas las correcciones posteriores de `main`**.

## Pendientes reales

- [ ] Cambiar la visibilidad de **GitHub Project** a **Public**. El repo ya es público, pero el tablero aparecía privado en la captura.
- [ ] Mover Issue **#1 a In Progress** en el tablero mientras se verifica el cierre de S1; dejar #2–#4 en Todo hasta que comiencen.
- [ ] Confirmar colaboradores Diego, Crystian y Mariano, con sus cuentas GitHub reales y al menos un commit propio comprobable por persona.
- [ ] Acordar responsables y asignar los Issues correspondientes.
- [ ] Registrar aprobación, asistencia, demostración y acuerdos del profesor.
- [ ] Coordinar si la referencia compartida `v0.1.0` requiere actualización; no reescribirla sin avisar al equipo.

### Verificación local (PowerShell)

```powershell
git status
git pull --ff-only origin main
py scripts/init_db.py
py scripts/seed.py
py scripts/check_connection.py
py -m unittest discover -s tests -v
py -m src.app
```

Luego abrir `http://127.0.0.1:8000/` y `http://127.0.0.1:8000/health`.

**No publicar archivos .env, credenciales ni datos financieros reales.** El proyecto está diseñado para una demo local académica.

Para actualizar tareas y trabajar en ramas: [PLAN_GITHUB](docs/PLAN_GITHUB.md).  
Para evidencia formal del seguimiento: [Bitácora S1](docs/seguimientos/S1.md).
