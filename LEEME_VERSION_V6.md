# Versión V6: moneda de cuenta y conversión exclusiva en transferencias
- Los ingresos y gastos se registran sin conversión, en la moneda de la cuenta seleccionada.
- La moneda de la cuenta se indica junto al monto y cambia al seleccionar otra cuenta.
- Las transferencias entre cuentas de igual moneda conservan el monto 1:1.
- Las transferencias entre monedas distintas obtienen automáticamente el cambio disponible para la fecha, guardan el identificador de la cotización y calculan el monto recibido.
- No se solicita elegir una cotización ni introducir el monto de destino.
- La fuente de cambio es una tasa de referencia (open.er-api.com), no la tasa bancaria de compra/venta.
- La vista de presupuestos y métricas globales de la versión original todavía puede mezclar importes de distintas monedas; revisar antes de usar esos totales para decisiones.
