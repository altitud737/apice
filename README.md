# ERP

Base de un ERP multi-tenant construido sobre **Django 6 + PostgreSQL**.

Diseñado para que múltiples desarrolladores puedan clonar el repositorio,
levantar el entorno y trabajar en módulos independientes (CRM, Inventario,
Ventas, etc.) bajo una arquitectura común.

---

## Arquitectura

| App | Responsabilidad |
|---|---|
| `config` | Configuración Django (`settings`, `urls`, `wsgi`, `asgi`) |
| `core` | Núcleo ERP: `TenantModel`, `Cliente`, `Vendedor`, `Idioma` |
| `accounts` | Tenants (`Company`), usuarios, permisos y super-admin |
| `crm` | Contactos, Leads, Pipeline, Deals, Plantillas, Notificaciones e integraciones (MercadoLibre, Zoho Mail, WhatsApp) |
| `inventario` | Artículos, Almacenes, Stock y movimientos transaccionales |
| `ventas` | Pedidos, confirmación atómica con descuento de stock |

### Reglas de arquitectura

- Toda entidad ERP hereda de `core.TenantModel` (FK obligatoria a `accounts.Company`).
- Toda modificación de stock pasa por `inventario.services` (transaccional, `select_for_update`).
- La confirmación de pedidos vive en `ventas.services.confirmar_pedido` (validar → descontar → registrar movimiento → cambiar estado, todo atómico).
- `Stock.cantidad >= 0` se valida en `Stock.clean()` y en la capa de servicios.

---

## Requisitos

- Python 3.12+
- PostgreSQL 14+ (recomendado 16+)
- Git
- (Opcional) `psql`, `pg_dump` para administración local.

---

## Instalación

```bash
# 1. Clonar el repositorio
git clone <url-del-repositorio> erp
cd erp

# 2. Entorno virtual
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 3. Dependencias
pip install -r requirements.txt

# 4. Variables de entorno
cp .env.example .env     # Linux/Mac
copy .env.example .env   # Windows
# Editar .env con las credenciales locales
```

### Configuración mínima en `.env`

```env
SECRET_KEY="cambiar-por-clave-segura"
DEBUG=True
DATABASE_URL="postgresql://postgres:tu_password@localhost:5432/erp_db"
```

Alternativamente se pueden usar variables individuales:
`DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`.

---

## PostgreSQL

```bash
psql -U postgres
```

```sql
CREATE DATABASE erp_db;
\q
```

> El proyecto **solo soporta PostgreSQL**. Si no se configura `DATABASE_URL`
> o las variables `DB_*`, Django no arranca (ver `core/settings.py`).

---

## Inicialización

```bash
# Aplicar migraciones
python manage.py migrate

# Crear superusuario
python manage.py createsuperuser

# (Opcional) datos de demostración
python scripts/setup_data.py

# Servidor de desarrollo
python manage.py runserver 3000
```

URLs:

- App: <http://127.0.0.1:3000/>
- Admin Django: <http://127.0.0.1:3000/admin/>
- Panel super-admin: <http://127.0.0.1:3000/superadmin/>

---

## Tests

```bash
# Todos
python manage.py test

# Por módulo ERP
python manage.py test ventas inventario core
```

---

## Verificación rápida

```bash
python manage.py check
python manage.py showmigrations
```

Atajos:

- `iniciar-erp.bat` (raíz, Windows) — `migrate` + `runserver`.
- `scripts/run.sh` (Linux/CI) — bootstrap completo.
- `scripts/backup_db.bat` (Windows) — backup vía `pg_dump`.
- `scripts/verificar_produccion.bat` (Windows) — checks pre-deploy.

Ver `scripts/README.md` para el detalle de cada utilidad.

---

## Estructura del repositorio

```
.
├── config/          # Configuración Django (settings, urls, wsgi, asgi)
├── core/            # Núcleo ERP: TenantModel, Cliente, Vendedor, Idioma
├── accounts/        # Tenants, usuarios, super-admin
├── crm/             # Contactos, leads, pipeline, integraciones
├── inventario/      # Artículos, stock, movimientos
├── ventas/          # Pedidos, confirmación transaccional
├── templates/       # Templates Django (un subdirectorio por app)
├── static/          # CSS / JS / imágenes
├── docs/            # Documentación técnica detallada
├── scripts/         # Utilidades operativas (backup, seed, deploy checks)
├── manage.py
├── iniciar-erp.bat  # Atajo Windows: migrate + runserver
├── requirements.txt
├── .env.example
└── README.md
```

---

## Despliegue (resumen)

1. Definir `DATABASE_URL`, `SECRET_KEY`, `ALLOWED_HOSTS` en el entorno.
2. `DJANGO_SETTINGS_MODULE=config.settings_production`
3. `python manage.py collectstatic --noinput`
4. `python manage.py migrate`
5. `gunicorn config.wsgi`

Variables adicionales relevantes en producción:
`ZOHO_ZEPTOMAIL_API_KEY_TOKEN`, `ML_CLIENT_ID`, `ML_CLIENT_SECRET`,
`ML_REDIRECT_URI`, `EMAIL_HOST*`, `REDIS_URL`.

---

## Documentación adicional

Toda la documentación técnica vive en `docs/`:

- `docs/MIGRACION_POSTGRESQL.md` — migración histórica a PostgreSQL.
- `docs/SISTEMA_SUPER_ADMIN.md` — gestión de empresas y permisos.
- `docs/API_LEADS_EXAMPLES.md` / `docs/SETUP_API_LEADS.md` — captura de leads vía API.
- `docs/ARQUITECTURA_LEADS_CONTACTOS.md` — diseño Leads/Contactos.
- `docs/INTEGRACION_MERCADOLIBRE.md` — OAuth2 y sincronización ML.
- `docs/INTEGRACION_ZOHO_MAIL.md` — integración de correo.
- `docs/AUTENTICACION_ALLAUTH.md` — flujo de login.
- `docs/PRODUCCION_READY.md` — checklist de producción.
- `docs/METRICAS_LEADS.md` — métricas y reportes.
- `docs/DISEÑO_SISTEMA.md` — visión general del sistema.
