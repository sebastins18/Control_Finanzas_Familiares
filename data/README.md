# Datos

La base SQLite real (`*.db`, `*.sqlite3` y archivos WAL/SHM) se excluye del repositorio mediante `.gitignore`.

Para crearla de manera reproducible:

```powershell
py scripts/init_db.py
py scripts/seed.py
```

**Todos los registros de `seed.py` son ficticios.** Nunca subir movimientos financieros personales al repositorio público.
