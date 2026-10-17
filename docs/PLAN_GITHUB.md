# Trabajo colaborativo en GitHub — Control de Finanzas Familiares (Grupo 5)

**Actualización:** 16 de octubre de 2026. El repositorio y el Project ya existen. No crear repositorios ni volver a ejecutar `git init`.

## Enlaces reales

- [Repositorio público](https://github.com/sebastins18/Control_Finanzas_Familiares)
- [GitHub Project — tablero](https://github.com/users/sebastins18/projects/1/views/1)
- [Issues del repositorio](https://github.com/sebastins18/Control_Finanzas_Familiares/issues)
- [Bitácora S1](seguimientos/S1.md)
- [Tag v0.1.0](https://github.com/sebastins18/Control_Finanzas_Familiares/tree/v0.1.0)

## Estado inicial verificado

- Repositorio: **público**; rama principal `main`.
- Project: **creado** e incluye los cuatro Issues de S1–S4.
- El tablero aparecía **privado** (candado en la captura); hace falta cambiar la visibilidad a **Public** desde la configuración del Project.
- Issues #1 y #2 tienen a `sebastins18` como **coordinador inicial**. Los responsables reales del resto deben acordarse con el equipo.
- La ejecución local del 16/10 reportó **10 pruebas / 10 OK**, SQLite con WAL, 5 tablas y datos de prueba.
- `v0.1.0` fue publicado inicialmente antes de las correcciones posteriores que están en `main`. No modificar el tag compartido unilateralmente.

## 1. Configurar el GitHub Project

Desde [el tablero](https://github.com/users/sebastins18/projects/1/views/1):

1. En el menú de opciones del Project, abrir **Settings** y pasar **Visibility** a **Public** para que el docente pueda revisar el tablero. No es lo mismo que hacer público el repositorio.
2. Mover el **Issue #1 (S1)** a **In Progress** hasta que esté completo, y mantener **#2 (S2), #3 (S3) y #4 (S4)** en **Todo**.
3. Abrir cada Issue para acordar y agregar **Assignees**. No atribuir commits o tareas a personas que no hayan participado.
4. Cuando se completen realmente las evidencias y el docente dé por cerrado S1, mover el Issue #1 a **Done** y cerrarlo.

> El tablero puede mostrar un estado de proyecto diferente de si un Issue está abierto o cerrado. Revisar ambos cuando corresponda.

## 2. Invitar a los integrantes y comprobar los commits

Ir a **Repositorio → Settings → Collaborators → Add people** e invitar los perfiles GitHub reales de **Diego, Crystian y Mariano**. Deben aceptar la invitación.

Cada integrante realiza al menos un cambio **real** desde su cuenta, preferiblemente en una rama y mediante pull request. Verificar las atribuciones en **Insights → Contributors** o en el historial de commits.

No compartir cuentas ni simular autores distintos. Cada persona debe poder explicar su trabajo.

| Integrante | Propuesta de responsabilidad S2 (por confirmar) |
| --- | --- |
| Sebastián | Integración y demo del CRUD de movimientos |
| Diego | Esquema SQLite, índices iniciales y datos sintéticos |
| Crystian | Presupuestos, validaciones y alertas |
| Mariano | QA, README e instalación desde cero |

## 3. Trabajo seguro para evitar conflictos

**Antes de empezar a editar desde PowerShell:**

```powershell
git status
git pull --ff-only origin main
git switch -c feature/nombre-corto
```

Editar y probar los cambios:

```powershell
py -m unittest discover -s tests -v
git add .
git commit -m "feat: descripcion del cambio"
git push -u origin feature/nombre-corto
```

Abrir un pull request contra `main`, revisarlo y fusionarlo. **No usar `git push --force` en `main`**. Si aparece conflicto o `git pull --ff-only` falla, detenerse y resolver antes de publicar.

Si ya existe una rama con ese nombre, elegir otro nombre al crearla.

## 4. Evidencias mínimas y próximos hitos

| Seguimiento | Fecha viernes | Entrega |
| --- | --- | --- |
| S1 | 16 oct 2026 | `v0.1.0` + `docs/seguimientos/S1.md` |
| S2 | 23 oct 2026 | `v0.2.0` + `docs/seguimientos/S2.md`, CRUD e integración |
| S3 | 30 oct 2026 | `v0.3.0` + `docs/seguimientos/S3.md`, pruebas y mediciones |
| S4 | 6 nov 2026 | `v0.9.0` + `docs/seguimientos/S4.md`, release candidate |

El profesor exige subir la bitácora y el tag **antes de las 6:00 p. m. del día correspondiente**. Los plazos y lo que ya se completó deben quedar registrados con fechas reales, sin afirmar entregas retroactivas.

## 5. Nota sobre el tag v0.1.0

Como se ha publicado y compartido `v0.1.0`, moverlo cambia el significado de una versión existente. Si el equipo y el docente necesitan que incluya las correcciones y bitácoras definitivas, **coordinarlo antes** para que nadie dependa de la referencia anterior. Las nuevas correcciones de `main` no pasan automáticamente al tag.

**Última verificación requerida para S1:** aprobación del alcance, colaboración de los cuatro, visibilidad pública del Project, participación en la reunión y registro de acuerdos.
