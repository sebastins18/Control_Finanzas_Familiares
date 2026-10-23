# V11 — Uso exclusivo del tipo de cambio en transferencias

- Se elimina `id_tipo_cambio` de `movimientos` en bases existentes durante la inicialización.
- El registro de ingresos y gastos no guarda ni consulta cotizaciones.
- El esquema conceptual elimina la referencia de ingresos y gastos.
- Se conserva `tipos_cambio` como caché de cotizaciones y `transferencias.id_tipo_cambio` para auditoría histórica.
- La migración conserva los registros de movimientos y sus montos.

**Antes de actualizar:** hacer una copia de `data/finanzas.sqlite3` si contiene datos importantes.
