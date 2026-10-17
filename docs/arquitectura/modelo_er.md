# Modelo relacional — diagrama v1

La propuesta original incluye cuentas, usuarios, monedas, ingresos, gastos, transferencias, presupuestos, alertas y ahorros. Esta vista simplificada representa las relaciones principales.

```mermaid
erDiagram
    usuarios ||--o{ cuentas : tiene
    usuarios ||--o{ categorias : personaliza
    usuarios ||--o{ presupuestos : establece
    usuarios ||--o{ ingresos : registra
    usuarios ||--o{ gastos : registra
    usuarios ||--o{ metas_ahorro : define
    usuarios ||--o{ sesiones : abre
    monedas ||--o{ cuentas : denomina
    monedas ||--o{ metas_ahorro : denomina
    monedas ||--o{ tipos_cambio : origen
    categorias ||--o{ ingresos : clasifica
    categorias ||--o{ gastos : clasifica
    categorias ||--o{ presupuestos : limita
    cuentas ||--o{ ingresos : recibe
    cuentas ||--o{ gastos : paga
    cuentas ||--o{ transferencias : participa
    cuentas ||--o{ movimientos_ahorro : financia
    presupuestos ||--o{ alertas : genera
    metas_ahorro ||--o{ movimientos_ahorro : recibe
    gastos ||--o{ comprobantes : documenta
```

Las restricciones concretas, incluidas las dos cuentas de transferencia, se encuentran en `scripts/schema.sql`.
