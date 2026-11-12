# Consolidación del aporte documental de Diego Fonseca

**Autor:** Diego Fonseca · [`dfonseca15`](https://github.com/dfonseca15).
**Commit original:** [`4b0bfed6ae37e527daf72fc3b6aa8727e990e199`](https://github.com/sebastins18/Control_Finanzas_Familiares/commit/4b0bfed6ae37e527daf72fc3b6aa8727e990e199), 6/11/2026.
**Origen:** `origin/respaldo-documentacion-s4`. **Base vigente:** `origin/main`, `8a88aeb3a743c345ba62da650a437795272a5d05`.

## Comparación actual y preservación de autoría

La consulta de referencias remotas confirmó ambos extremos. `git rev-list --left-right --count origin/respaldo-documentacion-s4...origin/main` devuelve **0 y 9**: main está nueve commits por delante y la rama histórica no contiene commits exclusivos pendientes de integrar. `4b0bfed` ya pertenece a la ascendencia de main mediante la integración documental existente. No se necesita un nuevo merge para recuperar su explicación más extensa.

El registro anterior comparaba la rama con `d1a1749` y anotaba **1 por delante y 7 por detrás**. Se conserva aquí exclusivamente como antecedente de aquella revisión, no como estado actual. El respaldo de Diego partía de `94412a1`, anterior a las mejoras técnicas S4.

Esta consolidación edita el contenido manualmente sobre main y conserva el crédito y el commit original. No usa checkout/restore de archivos históricos ni un merge completo. No reemplaza el aporte de Diego por una atribución exclusiva a quien consolida.

## Contenido recuperado y destino

| Aporte detallado de Diego | Destino vigente | Actualización aplicada |
| --- | --- | --- |
| Problema, usuarios, propósito y módulos | [README](../../README.md) | Funciones contrastadas con main; Python estándar y SQLite como único motor |
| Arquitectura, autenticación y modelo | README y [arquitectura S4](../arquitectura/ARQUITECTURA_S4.md) | 17 tablas actuales, credenciales SQLite y reglas fuertes de main |
| Instalación Windows/Linux y variables | README y [guía](../INSTALACION_S4.md) | Base nueva de ensayo, seed del mes, contraseña privada y comandos existentes |
| Inspección SQLite de solo lectura | README y guía | URI `mode=ro`, WAL, tablas, integridad, FK, movimientos y presupuestos |
| Matriz académica S4 y ficha de validación independiente | [S4](S4.md), [entrega](ENTREGA_S4.md) y [acta](ACTA_S4.md) | Se distinguen automatización, persona verificadora y aprobación docente |
| Verificación de ficha oficial de 15 campos | [portal.yml](../../portal.yml) y S4 | Se mantienen campos, tipos y valores; comentarios actualizados sin enlaces ficticios |
| Roadmap a un mes, seis meses y TFG | [ROADMAP](../ROADMAP.md) y README | Mejoras futuras separadas de funciones existentes |
| Registro de cambios y límites | [CHANGELOG](../../CHANGELOG.md) y S4 | Historial preservado; evidencia actual y pendientes reales identificados |

## Diferencias resueltas con la evidencia posterior

| Afirmación histórica | Tratamiento actual |
| --- | --- |
| 105 pruebas sobre `94412a1` | Antecedente aportado, sin consola original incorporada; no es resultado vigente |
| `data/quality/suite.json` con 103 | Registro histórico separado; nunca se combina con las 105 ni con las 109 |
| S4 sin desplegar | Desplegado el 6/11/2026 sobre `8a88aeb`, según responsable, con respaldo previo consistente |
| Capturas inexistentes o video no grabado | Existen capturas y grabación auténticas locales; final sincronizado en preparación, publicación pendiente |
| Contraseña inicial de demostración sin exigencia por prefijo | Se preserva la seguridad posterior de main: 12+ caracteres en base nueva con prefijo o flag estricto; hashes existentes intactos |
| Comparación WAL/DELETE necesaria para cerrar S3 | Issue #3 cerrado técnicamente; volumen e índices/EQP satisfacen la profundidad; WAL/DELETE opcional |
| `demo_temporal.py` disponible en v0.4.0 | No aparece en el árbol inspeccionado del tag ni del HEAD; usar seed sobre base temporal |
| Portal con espacios pendientes | 15 campos conservados; video/captura sin URL autorizada; autores públicos vacíos |
| `v0.9.0` en preparación | Tag no encontrado en consulta remota real al corte; no se declara publicado |
| Instalación por otra persona | Sigue pendiente de evidencia humana identificada; el runner no la sustituye |

La evidencia histórica local del 6/11/2026 es **109/109 de regresión y 27/27 E2E**, con capturas y video auténtico; [fuentes en S4](S4.md#evidencia-vigente-y-procedencia). SQLite del despliegue: WAL, 17 tablas, integridad `ok`, FK 0, según responsable. El GET público no demuestra esos datos por sí mismo.

## Alcance de la consolidación

Se preservan los cambios locales anteriores de `mejora/video-s4-sincronizado`, incluidas herramientas E2E, grabaciones, audio, capturas, informes y ZIP. Los documentos reorganizados incorporan sus hechos sin convertir material local en publicación. Se conserva el registro previo de cambios y un inventario SHA-256 para verificar los archivos ajenos a esta edición.

No se modifica código ejecutable, credenciales, bases de datos, CI ni pruebas. No se accede a WebAdmin ni se altera CRNube. No se ejecutan commit, push, merge, tags o publicaciones. La revisión y el diff quedan disponibles antes de preparar cualquier commit.
