# Auditoría de cumplimiento — Seguimientos 1 y 2

**Universidad Nacional · Grupo 5 · revisión del 23/10/2026.**
**Repositorio:** https://github.com/sebastins18/Control_Finanzas_Familiares  
**Tablero existente:** https://github.com/users/sebastins18/projects/1  
**Despliegue académico:** https://diego01.grupo5.crnube.org/finanzas/login (únicamente datos sintéticos).

Esta matriz distingue **evidencia técnica comprobada** de requisitos de equipo que todavía no se pueden certificar. No reemplaza la evaluación del profesor.

## Seguimiento 1 — problema, arquitectura y repositorio (16/10)

| Criterio del enunciado | Estado comprobable | Evidencia |
| --- | --- | --- |
| Repositorio público, MIT, .gitignore y carpetas src/docs/data/scripts | CUMPLIDO | Repositorio, `LICENSE`, `.gitignore` y árbol de archivos |
| Todos los integrantes invitados y mínimo un commit propio | PENDIENTE DE VERIFICAR | Solo commits de `sebastins18` identificables en historial consultado; ver Issue #6 |
| README problema, usuario, MVP incluido/excluido | CUMPLIDO | `README.md` y `docs/seguimientos/S1.md` |
| Diagrama de arquitectura v1 | CUMPLIDO | `docs/arquitectura/diagrama.md` |
| Modelo de datos v1 | CUMPLIDO | `docs/arquitectura/modelo-v1.md`, cinco tablas base |
| Backlog con hitos/responsables | PARCIAL | Project #1 público, vinculado, con 11 ítems y estados/campos configurados; faltan responsables reales de compañeros |
| Fuente de datos abierta o sintética | CUMPLIDO | `scripts/seed.py`, movimientos ficticios |
| Hola mundo: conexión al motor | CUMPLIDO | `scripts/check_connection.py`, SQLite con WAL |
| Tag v0.1.0 + S1.md | CUMPLIDO CON SALVEDAD | Tag apunta a `1385132`; correcciones S1 posteriores quedaron fuera de ese snapshot |

## Seguimiento 2 — núcleo funcional (23/10)

| Criterio del enunciado | Estado comprobable | Evidencia |
| --- | --- | --- |
| Flujo principal de punta a punta con SQLite | CUMPLIDO | Interfaz, `src/app.py`, `src/db.py`, panel y pruebas HTTP |
| CRUD de movimientos desde interfaz | IMPLEMENTADO; DEMO MANUAL PENDIENTE | Código y pruebas; capturas CRUD completas pendientes en Issue #8 |
| Script reproducible de prueba/carga | CUMPLIDO | `scripts/seed.py` y `scripts/seed_bulk_s2.py`; carga 1000 en tests y 100000 en DB temporal aislada |
| .env.example y ausencia de secretos reales en repo | DOCUMENTADO; REVISIÓN FINAL PENDIENTE | `.env.example`, `.gitignore` y análisis de secretos en Issue #10; contraseñas ficticias de tests no son credenciales reales |
| Ramas y pull requests | CUMPLIDO | PR #5, rama de integración y merge a `main` en `abf92fb` |
| Issues de hito cerrados o reprogramados justificadamente | PARCIAL | #7 cerrado por tag resuelto; #2 abierto por aportes individuales, demo y acta, con dependencias #6/#8/#9/#11 |
| Tag v0.2.0 y bitácora S2.md | CUMPLIDO | `v0.2.0` apunta a `584971e` (V17 y bitácora S2); `v0.2.0-original` conserva `721a4a7`; Issue #7 cerrado |

### Comprobaciones reales de 23/10

- Windows: `py -m unittest discover -s tests -v` → **29/29 OK** (tras corregir ZIP V17 original que fallaba).
- CRNube Python 3.12.3: `python3 -m unittest discover -s tests -v` → **29/29 OK** (6.244 s).
- SQLite 3.45.1, modo WAL y 13 tablas en base de demostración privada.
- Backend `127.0.0.1:8010/finanzas/login` y URL pública `/finanzas/login`: **GET HTTP 200**; login y panel visualizados con datos ficticios.
- Código fusionado mediante [PR #5](https://github.com/sebastins18/Control_Finanzas_Familiares/pull/5), merge `abf92fb`. El servidor luego quedó en rama `main` siguiendo `origin/main`.
- El proceso fue iniciado con `nohup`, **sin** reinicio automático garantizado. HEAD devuelve 501 y GET 200; no confundir ambos estados.

## Cierre pendiente antes de marcar S1/S2 como completados

1. **Issue #6:** identificar y comprobar invitación y commits auténticos de los cuatro; no fabricar historial.
2. **Issue #7 (RESUELTO):** `v0.2.0` apunta a `584971e` y se preservó la etiqueta anterior como `v0.2.0-original`.
3. **Issue #8:** capturar demo manual CRUD + presupuestos/alertas con datos ficticios.
4. **Issue #9 (PARCIAL):** Project #1 se publicó y cargó vía GitHub CLI (11 ítems, estados y campos); faltan responsables reales y prueba de acceso sin sesión.
5. **Issue #11:** registrar asistencia y comentarios reales del profesor cuando sucedan.
6. **Issue #10:** mantener la aplicación de demo sin datos personales, con contraseña privada; documentar hardening pendiente.

**Fecha límite rubricada:** viernes 23/10/2026 antes de 18:00 (Costa Rica). Evitar afirmar entregas finalizadas antes de verificar cada punto.

## Registro de enlaces

- [Bitácora S1](S1.md) · [Bitácora S2](S2.md)
- [Evidencia de equipo/acta pendiente](EVIDENCIA_EQUIPO.md)
- [Project #1](https://github.com/users/sebastins18/projects/1)
- [Issues](https://github.com/sebastins18/Control_Finanzas_Familiares/issues)
- [Pull Request #5](https://github.com/sebastins18/Control_Finanzas_Familiares/pull/5)

### Nota posterior al etiquetado

El 23/10/2026 el usuario ejecutó GitHub CLI, publicó Project #1, configuró `Status`, `Seguimiento` y `Prioridad`, y registró 11 elementos; la salida JSON muestra las asignaciones. Ese mismo día creó el respaldo `v0.2.0-original` → `721a4a7` y actualizó explícitamente `v0.2.0` → `584971e` mediante `--force-with-lease`. Se verificaron ambas referencias en GitHub. Las posteriores correcciones de texto de esta matriz son documentación posetiquetado, no cambios de funcionalidad. No afirmar acceso público sin sesión hasta que un integrante lo pruebe.

### Verificación adicional de QA automatizada (posterior al tag S2)

- Cuatro pruebas HTTP integrales de S2 añadidas sin modificar la aplicación: CRUD, alertas 80/100 %, monto inválido, control de sesión.
- **33/33 pruebas OK** en una revisión aislada (Python 3.13.5); el servidor CRNube había confirmado 29/29 antes de añadirlas. No confundir esos dos resultados ni afirmar una ejecución de 33 pruebas en CRNube sin su terminal.
- Se añadió `scripts/evidencia_s2.py`: comprueba suite, WAL, claves foráneas, integridad, 1000 movimientos sintéticos e idempotencia en SQLite temporal. La demo manual y los aportes personales siguen abiertos.
- GitHub Actions automatiza la suite y la evidencia en pushes/PR; su resultado remoto requiere consultar la pestaña Actions una vez integrada la rama.
