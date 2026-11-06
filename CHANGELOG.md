# Registro de cambios

## v0.9.0 — Preparación del Seguimiento 4 (06/11/2026; sin publicar)

Esta sección registra cambios de preparación; no acredita un tag ni una release v0.9.0. El commit de código verificado para la instalación reportada es `94412a1`; las actualizaciones documentales de esta sección son posteriores a ese snapshot.

- README actualizado con problema, destinatarios, funciones reales, arquitectura, requisitos, instalación local desde cero, variables de entorno, SQLite WAL, datos ficticios, pruebas y arranque.
- Documentación alineada con autenticación en SQLite: una base nueva crea solo `admin`, con hash y salt, contraseña inicial configurable y valor público de demostración solo si la variable no está definida. El JSON se conserva únicamente para migrar usuarios antiguos sin autenticación SQLite; no se restablecen cuentas existentes.
- Corregidas referencias antiguas a cinco tablas como esquema vigente, credenciales operativas en JSON y un requisito de contraseña de 12 caracteres por prefijo que el código actual no impone.
- Revisada y corregida en la entrada histórica de v0.4.0 la referencia a `scripts/demo_temporal.py`: no está en el árbol actual ni en el tag local inspeccionado. Se documenta `scripts/seed.py` como cargador disponible.
- Bitácora [S4](docs/seguimientos/S4.md) con matriz de cumplimiento, evidencias y pendientes; mantiene separados el ensayo en copia independiente y la validación que debe realizar otro integrante con solo el README.
- Resultados aportados del 06/11/2026: instalación en copia independiente del commit `94412a1`, inicialización WAL, 5 movimientos ficticios y presupuestos de noviembre de 2026, 105 pruebas satisfactorias, arranque e inicio de sesión con visualización de movimientos y presupuestos. No se volvieron a ejecutar durante esta edición documental; faltan adjuntar salidas y capturas originales.
- Espacios preparados para capturas reales, enlace del video y roadmap. Licencia MIT revisada sin cambios.
- Revisión documental adicional: comprobación de SQLite en modo de solo lectura y procedimiento independiente completos en README; ficha de validación preparada en S4. Se aclara que el JSON local de calidad conserva 103 pruebas y no respalda por sí solo las 105 reportadas. También se distingue el commit del código de la revisión documental aún sin commit.
- [portal.yml](portal.yml) creado y validado conforme a la sección 7 de la guía oficial del profesor: 15 campos exactos del ejemplo, sintaxis YAML, tipos y ausencia de claves duplicadas comprobados. URL pública del login verificada por GET HTTPS con HTTP 200; video y captura vacíos, autores públicos como lista vacía hasta recibir autorización.
- Instalación principal del README basada en la rama publicada `main`, con registro del commit realmente instalado. `94412a1` queda únicamente como referencia histórica de la instalación verificada; v0.9.0 continúa sin publicar.
- Roadmap del README ampliado con mejoras previstas a un mes, a seis meses y la posibilidad de continuar como trabajo final de graduación, sujetos a implementación y aprobación académica según corresponda.
- La guía oficial ya está disponible según confirmación del equipo; se eliminaron las referencias a un cotejo pendiente de la matriz. Esto no acredita requisitos sin evidencia. Siguen pendientes las capturas, las salidas originales y la instalación independiente del equipo. Video y presentación final quedan fuera del alcance de esta preparación. Sin commit, push ni creación de tags.

## v0.1.0 — Seguimiento 1 (16/10/2026)
- Documentación del problema, usuarios, alcance y decisiones arquitectónicas.
- Prototipo local con servidor web Python y SQLite.
- Modelo MVP de cinco tablas, modo WAL, claves foráneas e índices iniciales.
- Scripts de inicialización, datos sintéticos y verificación de conectividad.
- Backlog en cuatro GitHub Issues y bitácora del seguimiento S1.
- Ajuste del test de conexión a la implementación real del MVP.
- Clarificación de la diferencia entre el DDL operativo y el modelo ampliado propuesto.

> Validación local documentada el 16/10/2026: **10/10 pruebas correctas**, tras corregir incompatibilidad del test de conexión y cierre explícito de conexiones en Windows. El tablero GitHub Projects fue creado con Issues #1–#4 y se vinculó en la bitácora.
>
> Pendiente de cierre: confirmar commits propios de los cuatro integrantes, hacer público el Project y coordinar con el equipo la versión definitiva del tag compartido `v0.1.0`. Los ajustes posteriores están en `main` y no cambian automáticamente el contenido del tag.

## Integración V17 / S2 — 23/10/2026 (PR #5 fusionado)
- Se incorporó el módulo ampliado desde ZIP V17 aportado por un integrante; autoría Git individual pendiente de acreditar.
- Ajustes a pruebas de autenticación y conversión manual, cobertura de prefijo `/finanzas`, carga masiva transaccional sintética.
- Protección de credenciales y comprobantes locales en `.gitignore`.
- La primera referencia de `v0.2.0` se publicó antes de V17; su respaldo histórico quedó como `v0.2.0-original` (`721a4a7`) y el tag de entrega `v0.2.0` fue corregido a `584971e` con `--force-with-lease`.

- PR #5 fusionado en `main` (commit `abf92fb`) con 29/29 pruebas en CRNube y Windows.
- URL de prueba `/finanzas/login` con HTTP 200; base SQLite separada del directorio público.
- Auditoría de rúbrica, evidencias del equipo y tareas pendientes documentadas; Issue #7 mantiene trazabilidad del tag `v0.2.0` preintegración.

## Evidencia posetiquetado — GitHub Project #1 (23/10/2026)

- Project #1 enlazado al repositorio y configurado público vía GitHub CLI autenticado.
- Campos de seguimiento/prioridad y 11 elementos confirmados con `gh project item-list`.
- El Issue #7 (ajuste del tag) quedó cerrado tras verificar las referencias en GitHub.
- Siguen abiertos los compromisos individuales, demo manual y acta del profesor; detalles en Issues #6, #8, #9 y #11.

## QA posterior a v0.2.0 — 23/10/2026

- Cobertura HTTP S2 incrementada de 29 a 33 casos de prueba en revisión aislada; sin cambios de funcionalidad ni migraciones.
- Incorporado generador de evidencia no destructiva con SQLite temporal, guía de demo paso a paso y GitHub Actions.
- Este registro **no** altera la etiqueta `v0.2.0` ya entregada.

## Sesión 30/10/2026 — Arranque, panel de calidad y documentación

- Corregido el arranque cuando la migración de `usuarios` intentaba añadir de nuevo la columna `username` (`src/auth.py`).
- Indicador de carga y estado «Iniciando…» en el panel de calidad `/admin/calidad`, con iluminación al pasar el cursor en sus botones.
- Página `/olvide-clave` sin cambios funcionales: la recuperación de contraseña sigue siendo solo por administrador (D-012).
- Actualizados `docs/seguimientos/S3.md` (registro de cambios) y `docs/decisiones.md` (D-011 a D-013).
- Salidas temporales de arranque añadidas a `.gitignore`.

## v0.4.0 — 03/11/2026 (rama `changes-3-nov`)

- **Integración:** `origin/main` (S3 de Diego Fonseca) fusionado con la rama de trabajo; versiones paralelas conservadas como `*_diego` y decisiones renumeradas (D-018).
- **Correcciones:** compatibilidad con Python 3.11 (f-string anidada en `extension.page`, fallaba el CI); la prueba S3 de caso normal ya no depende del mes actual.
- **Historial** (`/historial`): búsqueda y filtros por tipo, categoría, cuenta y fechas, paginación, totales por moneda y exportación CSV (D-019).
- **Reporte anual** (`/reportes/anual`): totales mensuales por categoría y moneda, con CSV (D-019).
- **Movimientos recurrentes:** plantillas mensuales y generación explícita e idempotente; tablas nuevas `movimientos_recurrentes` y `recurrentes_generados`, sin cambios en las existentes (D-020).
- **Formularios rediseñados**, brillo que sigue al puntero en paneles y botones, e indicador animado en selectores y pestañas; mismos nombres y valores enviados al servidor (D-021).
- **Datos de demostración (referencia corregida el 06/11/2026):** la revisión del árbol del tag local `v0.4.0` y del árbol actual no encuentra `scripts/demo_temporal.py`. La afirmación anterior de que estaba disponible en ese tag era incorrecta. `scripts/seed.py` y `scripts/seed_bulk_s2.py` sí están presentes; utilizarlos únicamente sobre bases de ensayo según el README.
- **Pruebas:** 103/103 en Python 3.11 y 3.12 (+18: `test_historial_reportes.py`, `test_formularios_v2.py`).
- Detalle de uso: [docs/consultas_reportes_recurrentes.md](docs/consultas_reportes_recurrentes.md).
