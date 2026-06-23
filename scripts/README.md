# scripts/

Scripts auxiliares del proyecto. Ninguno es necesario para que el ERP
arranque por primera vez; son utilidades de operación, mantenimiento y
seeding.

Todos los scripts se posicionan automáticamente en la raíz del proyecto al
ejecutarse, por lo que pueden invocarse desde cualquier directorio.

## Inventario

| Script | Plataforma | Propósito |
|---|---|---|
| `run.sh` | Linux/macOS/CI | Bootstrap completo: instala deps, migra, collectstatic, crea superuser opcional y arranca `runserver 0.0.0.0:3000`. |
| `backup_db.bat` | Windows | Backup de PostgreSQL via `pg_dump`. Lee credenciales desde la configuración Django. Mantiene los últimos 30 días en `backups/`. |
| `verificar_produccion.bat` | Windows | Checks pre-deploy: `manage.py check`, migraciones pendientes, conexión PostgreSQL, modelos clave, `collectstatic`. |
| `setup_data.py` | Multiplataforma | Seed idempotente de datos demo (empresa, superadmin, usuario regular, contactos, pipeline). Credenciales por env vars `DEMO_SUPERADMIN_EMAIL/PASSWORD`, `DEMO_USER_EMAIL/PASSWORD`. |

## Uso

```bash
# Bootstrap Linux/CI
bash scripts/run.sh

# Backup manual (Windows)
scripts\backup_db.bat

# Verificación pre-deploy (Windows)
scripts\verificar_produccion.bat

# Seed de datos demo (multiplataforma)
python scripts/setup_data.py
```

> Para arrancar el servidor en Windows en uso diario existe el atajo
> `iniciar-erp.bat` en la raíz del proyecto.
