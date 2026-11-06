# Registro del respaldo documental S4 — aporte de Diego

**Rama original:** [`respaldo-documentacion-s4`](https://github.com/sebastins18/Control_Finanzas_Familiares/tree/respaldo-documentacion-s4)  
**Commit original de Diego:** [`4b0bfed`](https://github.com/sebastins18/Control_Finanzas_Familiares/commit/4b0bfed6ae37e527daf72fc3b6aa8727e990e199) · 6/11/2026  
**Autor confirmado por GitHub:** `dfonseca15`  
**Rama principal existente al revisarlo:** `d1a1749`, posterior al cierre S4 de los PR #20 y #21.

## Evaluación realizada

El commit original aportó una versión ampliada de:

- `README.md`: propósito de MisFinanzas, usuarios, módulos actuales, instalación desde cero, lectura SQLite sin modificar, pruebas, verificación independiente, variables de entorno, roadmap, capturas y video pendientes.
- `docs/seguimientos/S4.md`: matriz de cumplimiento, verificación de 15 campos del `portal.yml`, evidencia histórica y formato para la instalación por otra persona.
- `CHANGELOG.md`: registro detallado de la preparación del Seguimiento 4.
- `portal.yml`: ficha académica con los 15 campos del ejemplo recibido por Diego.

Se conserva el **commit original como segundo padre de la integración** para acreditar su trabajo en Git; no se sustituye su contenido por un commit atribuido a otro integrante ni se borra su rama.

## Motivo para no sustituir los cuatro archivos de `main` directamente

La rama se basó en el commit `94412a1`, anterior a la integración de S4. Al revisarla, estaba **un commit por delante y siete por detrás** de `main`. Varias afirmaciones de su fecha son históricas y no pueden desplazar la evidencia actual:

| Dato del respaldo | Interpretación correcta después de integrar S4 |
| --- | --- |
| Ensayo de 105 pruebas atribuido a `94412a1` | Historial informado por Diego, sin consola original incorporada |
| `data/quality/suite.json` con 103 casos | Otro resultado histórico, no prueba la suite completa de S4 |
| Suite local del responsable | **109/109 pruebas OK** aportadas por Windows; [matriz actual](ENTREGA_S4.md) |
| `v0.9.0` en preparación | Sigue sin publicarse en esta integración documental |
| Contraseña local predeterminada aceptada | Solo en demostración local sin prefijo; **en una base nueva bajo `APP_BASE_PATH`** ahora se exige contraseña inicial de 12+ caracteres |
| Portal con 15 campos | Se conserva la ficha de `main`, que ya incluye esos campos y deja video/capturas sin inventar |
| Instalación hecha por otro integrante | **No acreditada**; se requiere nombre, sistema, commit, consola y capturas reales |

## Qué se incorporó a la documentación vigente

Se incorporó una sección de **comprobación SQLite en modo lectura** en [INSTALACION_S4.md](../INSTALACION_S4.md), aclaraciones de procedencia histórica en [S4.md](S4.md) y enlaces en README y CHANGELOG.

**No se modificó ningún código ejecutable, ninguna credencial, la base SQLite del profesor ni WebAdmin.** La rama histórica se conserva y su commit queda conectado al historial de la integración, sin afirmar aprobaciones académicas ni ejecución del video.
