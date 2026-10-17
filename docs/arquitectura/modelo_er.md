# Diagrama ER v1 — Modelo SQLite en uso

Este es el modelo real de **cinco tablas** utilizado por `src/db.py` y definido en `src/schema.sql`.

```mermaid
erDiagram
    usuarios ||--o{ categorias : configura
    usuarios ||--o{ cuentas : mantiene
    usuarios ||--o{ movimientos : registra
    usuarios ||--o{ presupuestos : establece
    categorias ||--o{ movimientos : clasifica
    categorias ||--o{ presupuestos : limita
    cuentas ||--o{ movimientos : registra

    usuarios {
      integer id_usuario PK
      text nombre
    }
    categorias {
      integer id_categoria PK
      integer id_usuario FK
      text nombre
      text tipo
    }
    cuentas {
      integer id_cuenta PK
      integer id_usuario FK
      text nombre
      integer saldo_inicial_centimos
    }
    movimientos {
      integer id_movimiento PK
      integer id_usuario FK
      integer id_cuenta FK
      integer id_categoria FK
      text tipo
      integer monto_centimos
      text fecha
    }
    presupuestos {
      integer id_presupuesto PK
      integer id_usuario FK
      integer id_categoria FK
      integer anio
      integer mes
      integer monto_limite_centimos
    }
```

El modelo ampliado de la presentación del Grupo 5 es una **propuesta para el futuro**; no es el esquema activo. Ver `docs/modelo_datos.md`.
