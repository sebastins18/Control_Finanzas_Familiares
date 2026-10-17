# Modelo de datos v1 (SQLite)

Baseado en la propuesta del Grupo 5, con ajustes de implementación para el MVP. Las tablas se crean en `scripts/schema.sql`.

| Tabla | Responsabilidad |
|---|---|
| usuarios | Personas autorizadas (hash de contraseña; sin contraseñas planas) |
| sesiones | Sesiones futuras, con hash del token y caducidad |
| monedas | Código ISO, nombre y símbolo |
| tipos_cambio | Tipo de cambio por fecha y par de monedas |
| categorias | Clasificación de ingreso/gasto, global o por usuario |
| cuentas | Saldo inicial y moneda por cuenta |
| ingresos | Entradas de dinero por usuario, cuenta y categoría |
| gastos | Salidas de dinero por usuario, cuenta y categoría |
| transferencias | Movimientos entre cuentas, incluidos cruces de moneda |
| presupuestos | Límite por categoría, usuario y mes |
| alertas | Alertas asociadas al presupuesto |
| metas_ahorro | Objetivos de ahorro por usuario y moneda |
| movimientos_ahorro | Aportes/retiros a una meta desde una cuenta |
| comprobantes | Rutas relativas de archivos asociados a gastos |

## Convenciones
- Importes en **centavos enteros**, nunca floats de dinero. La presentación divide entre 100.
- Claves primarias enteras y claves foráneas habilitadas con `PRAGMA foreign_keys=ON`.
- Fechas ISO `YYYY-MM-DD` y registros de tipo de cambio como un entero escalado a 1 000 000.
- `UNIQUE` para códigos ISO, correos y presupuestos por período.
- Validaciones relacionales y reglas de dominio en SQL y, en S2, en Python.
- No registrar datos personales reales ni adjuntos privados.

## Evolución del diseño
En S2 se revisará si `ingresos` y `gastos` permanecen separados o si conviene una tabla única de movimientos, manteniendo una migración reproducible. El diagrama de la propuesta es una referencia conceptual, no un CRUD implementado.

Consultar también [diagrama Mermaid](arquitectura/modelo_er.md).
