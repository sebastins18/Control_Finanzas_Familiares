# Guía de demostración S2 — Grupo 5 (23/10/2026)

**Objetivo del profesor:** flujo de punta a punta, CRUD de la entidad central, carga de datos reproducible, GitHub y bitácora. Esta guía describe una demostración que **debe ejecutarse realmente**; no sustituye capturas ni presencia en clase.

## Entorno y precauciones

- Web de demostración: https://diego01.grupo5.crnube.org/finanzas/login
- Código validado y versiones: [tag v0.2.0](https://github.com/sebastins18/Control_Finanzas_Familiares/tree/v0.2.0) y [S2.md](S2.md)
- Datos **ficticios**, sin información personal; no escribir contraseñas en grabaciones ni documentación.
- Para repetir una demo completa desde cero, preferir SQLite de prueba temporal y un servidor local; **no borrar** la base actual de CRNube.
- Las credenciales iniciales de demostración conocidas deben cambiarse por una privada.
- Si el docente solicita evidencia de aportes, mostrar commits reales de cada integrante y el Project. No presentar el ZIP V17 como commit individual.

## Guion operativo (cinco minutos)

| Tiempo | Acción visible | Evidencia que observar |
| --- | --- | --- |
| 0:00–0:40 | Abrir README, arquitectura y modelo de SQLite | Objetivo familiar, Python/SQLite, 13 tablas actuales y 5 tablas base de S1 |
| 0:40–1:25 | Iniciar sesión en la demo y mostrar dashboard | Saldos por cuenta y período, datos sintéticos |
| 1:25–2:50 | Crear movimiento ficticio; consultar; editar su monto; eliminarlo | El registro cambia en SQLite y en el historial. Capturar antes/después |
| 2:50–3:35 | Crear/mostrar presupuesto y gasto que llega al 80 % y luego al 100 % | Etiquetas “Cerca del límite” y “Excedido”. Preferir entorno aislado |
| 3:35–4:15 | Mostrar `python -m scripts.evidencia_s2 --output evidencia_s2_local.md` en **terminal secundaria** | Suite automatizada, WAL, `integrity_check`, claves foráneas y carga sintética transaccional |
| 4:15–5:00 | Mostrar Project #1, PR #5 y PR #12/#13, bitácoras y tags | Avances comprobados y pendientes auténticos del equipo |

## Datos manuales ficticios propuestos

Con un presupuesto NUEVO de `₡10.000` en Alimentación para el período actual de la prueba:

1. Crear gasto Alimentación de `₡8.500` con descripción **“Demo S2 ficticia”** (85 %): observar “Cerca del límite”.
2. Editar el mismo movimiento a `₡10.500` (105 %): observar “Excedido”.
3. Eliminar el movimiento: el saldo y el historial se actualizan. No borrar movimientos ajenos.
4. Intentar monto negativo y explicar la validación (HTTP 400). El navegador impide negativos por validación HTML; en la suite HTTP se verifica la protección del servidor.

**Advertencia:** en la base del servidor ya existen movimientos y presupuestos; para porcentajes exactos debe usarse una categoría/perfil de prueba sin gastos previos y con presupuesto propio, o la base temporal. No afirmar que los mismos valores producirán los umbrales sobre la base precargada.

## Evidencia reproducible no destructiva

Windows desde raíz del repositorio:

```powershell
py -m unittest discover -s tests -v
py -m scripts.evidencia_s2 --output evidencia_s2_local.md --count 1000
```

WebAdmin desde `~/finanzas_deploy/app`:

```bash
python3 -m unittest discover -s tests -v
python3 -m scripts.evidencia_s2 --output "$HOME/evidencia_s2_crnube.md" --count 1000
```

El script **siempre utiliza un SQLite temporal** incluso si el servidor tiene `DB_PATH` configurado; nunca usa la base de producción/demostración para la carga. El archivo de evidencia generado registra únicamente datos técnicos y fechas, no credenciales. No se comitean bases SQLite.

## Capturas a agregar por el equipo

- [ ] URL de login y dashboard auténticos, sin contraseña ni datos personales.
- [ ] Registro creado y listado en pantalla.
- [ ] Registro editado y cambio reflejado.
- [ ] Registro eliminado y ausencia en el historial.
- [ ] Presupuesto y alerta del 80 % y del 100 % (o video continuo).
- [ ] Captura de comando con resultado completo de `unittest`.
- [ ] Project público con estados, responsables y PRs.
- [ ] Tabla de commits individuales reales y notas del profesor en [EVIDENCIA_EQUIPO.md](EVIDENCIA_EQUIPO.md).

## Preguntas técnicas para la reunión

**¿Qué motor?** SQLite 3; permite claves foráneas, índices, transacciones y WAL. **¿Dónde queda la base?** En CRNube está fuera de `public_html`. **¿Qué ocurre si hay un error?** Se muestra un error controlado, no se simula una escritura exitosa. **¿Por qué un solo motor?** El modelo financiero es relacional, y el curso permite ese perfil si se profundiza en SQLite. **¿Qué falta S3?** Tres operaciones medidas al menos tres veces, medianas, consultas con/sin índice y `EXPLAIN QUERY PLAN`.

**Limitaciones:** esta es una aplicación académica con datos sintéticos, no apta para finanzas reales ni producción. Las pruebas HTTP no reemplazan verificación manual de UX, colaboración individual o aprobación del profesor.
