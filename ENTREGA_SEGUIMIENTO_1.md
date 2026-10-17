# Qué hacer HOY — Grupo 5 — 16/10/2026

Esta es una base **local y verificable** para el Seguimiento 1 de **Control de Finanzas Familiares**. La propuesta proviene de la presentación del grupo (9/10/2026). **No representa una entrega hecha automáticamente a GitHub.**

## Archivos listos

- `README.md`: problema, usuario, arquitectura, alcance, instalación y ruta de trabajo.
- `src/schema.sql`: SQLite con 5 tablas de MVP.
- `docs/arquitectura/diagrama.md`: diagrama y flujo entre aplicación y SQLite.
- `docs/arquitectura/modelo-v1.md`: modelo relacional simplificado a partir del v4 de la propuesta.
- `scripts/check_connection.py`: evidencia "hola mundo" de SQLite.
- `scripts/seed.py`: datos de prueba totalmente inventados.
- `docs/seguimientos/S1.md`: bitácora con estados y espacios para completar enlaces a evidencias reales.
- `docs/seguimientos/guion_demo_S1.md`: guía oral de 5 minutos.
- `.gitignore`, `.env.example`, `LICENSE`, `tests/`.

## Cómo mostrarlo en VS Code (Windows)

```powershell
py scripts/init_db.py
py scripts/seed.py
py scripts/check_connection.py
py -m unittest discover -s tests -v
py -m src.app
```

Abrir `http://127.0.0.1:8000/` y probar registrar un gasto; abrir `/health` para la conexión.

## Falta hacerlo con el GitHub del grupo

1. Publicar estos archivos en un repositorio **público**.
2. Agregar colaboradores y registrar **un commit propio por cada integrante** (Sebastián, Diego, Crystian y Mariano).
3. Crear **Issues** con responsables e hitos S1/S2/S3/S4.
4. Actualizar los marcadores `PENDIENTE` de `docs/seguimientos/S1.md` con los enlaces reales.
5. Crear y subir el tag remoto **`v0.1.0`** del commit que incluya la bitácora actualizada.
6. Mostrar el avance al profesor y registrar los acuerdos en la bitácora.

El enunciado especifica **6:00 p. m.** como hora límite previa al seguimiento del 16 de octubre; esa hora ya transcurrió. Conviene publicar inmediatamente y comunicarlo al profesor.

**Cuidado:** no subir archivos SQLite con información personal ni el `.env` local.
