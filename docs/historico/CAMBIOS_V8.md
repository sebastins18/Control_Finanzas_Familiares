# V8 — consultas de cambio bajo demanda

- Se elimina la actualización automática al cargar el panel principal.
- Solo al guardar una transferencia entre monedas distintas se busca una cotización.
- Primero se consulta SQLite: para el día actual se exige una cotización del día; para fechas anteriores se reutiliza la última cotización almacenada que no sea posterior a la fecha indicada.
- Solo si no existe cotización adecuada se consulta la API externa. Si falla, se informa que falta una cotización y no se completa la transferencia.
- Ingresos, gastos y transferencias entre cuentas de igual moneda no consultan el servicio.
- Los presupuestos consultan cotizaciones históricas locales, sin solicitudes externas.
- Pruebas: `python -m unittest discover -s tests -q`.

Nota: las cotizaciones son referencias de mercado; no equivalen necesariamente a tipos bancarios de compra o venta. La API no fue comprobada en vivo en esta entrega.
