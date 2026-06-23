# Renombres de apps — guía de transición para bases existentes

Esta refactorización renombró dos apps Django. Las **bases nuevas** funcionan
sin pasos extra. Las **bases que ya tenían migraciones aplicadas** requieren
un único ajuste manual antes del primer `migrate`.

## Cambios aplicados

| Antes | Después | Motivo |
|---|---|---|
| `apice/` (app) | `crm/` (app) | El módulo siempre fue CRM; se eliminó el nombre comercial |
| `erp_core/` (app) | `core/` (app) | Núcleo ERP sin sufijo redundante |
| `core/` (proyecto Django) | `config/` (proyecto Django) | Convención `cookiecutter-django`; libera `core` para dominio |

Las migraciones físicas se conservaron (no se hizo squash). Las dependencias
internas (`('apice', '00XX')`, `to='apice.<modelo>'`, `('erp_core', '00XX')`,
`to='erp_core.<modelo>'`) fueron reescritas a `crm` y `core`.

## Pasos para una base existente

### 1. Backup obligatorio

```bash
pg_dump -U postgres -h localhost -F c -f backup_pre_rename.dump erp_db
```

### 2. Renombrar las apps en `django_migrations`

Conectarse a la base y ejecutar:

```sql
BEGIN;

-- Renombrar apice → crm
UPDATE django_migrations SET app = 'crm' WHERE app = 'apice';

-- Renombrar erp_core → core
UPDATE django_migrations SET app = 'core' WHERE app = 'erp_core';

-- Verificar (deben aparecer crm y core; NO apice ni erp_core)
SELECT app, COUNT(*) FROM django_migrations GROUP BY app ORDER BY app;

COMMIT;
```

### 3. Renombrar las apps en `django_content_type`

```sql
BEGIN;

UPDATE django_content_type SET app_label = 'crm'  WHERE app_label = 'apice';
UPDATE django_content_type SET app_label = 'core' WHERE app_label = 'erp_core';

-- Verificar
SELECT app_label, COUNT(*) FROM django_content_type GROUP BY app_label ORDER BY app_label;

COMMIT;
```

### 4. (Opcional) Verificar permisos

Si hay permisos personalizados referenciados por `app_label`:

```sql
SELECT * FROM auth_permission p
JOIN django_content_type c ON c.id = p.content_type_id
WHERE c.app_label IN ('crm', 'core');
```

### 5. Aplicar migraciones

```bash
python manage.py migrate
```

Debe reportar **"No migrations to apply"** porque las migraciones ya estaban
aplicadas bajo los nombres anteriores y el `UPDATE` las renombró.

### 6. Verificar funcionamiento

```bash
python manage.py check
python manage.py showmigrations
python manage.py test
```

## Nota sobre nombres de tablas

Los nombres físicos de tablas **no cambian**:

- `crm_contact`, `crm_lead`, `crm_deal`, ... (siempre tuvieron prefijo `crm_*`)
- `idioma`, `cliente`, `vendedor` (definidos con `db_table=` explícito)
- `mercadolibre_*` (definidos con `db_table=` explícito)

Por lo tanto **no hay renombre físico de tablas** y los datos quedan
intactos. El ajuste se reduce a actualizar las dos tablas internas de Django.

## Nota sobre nombres de índices históricos

La migración `crm/0013_rename_apice_email_integra_*` renombra dos índices
físicos cuyo nombre histórico empezaba con `apice_`. Esto no es un dato
"pendiente de limpiar": son los nombres reales de los objetos en la DB,
y la migración 0013 ya los renombra a `crm_*` cuando se ejecuta.

En una base nueva, el flujo es:

1. `0001_initial` crea los índices con nombre `apice_email_integra_*` y `apice_email_message_*`.
2. `0013_rename_*` los renombra a `crm_emailme_integra_*` y `crm_emailme_message_*`.

En una base existente que ya aplicó hasta `0013`, los índices ya están con el
nombre nuevo y la migración está marcada como aplicada — no se repite.
