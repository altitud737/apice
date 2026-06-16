# Apice CRM + ERP

Sistema CRM multi-tenant en evolución hacia ERP completo (Inventario y Ventas).
Stack: **Django 6 + PostgreSQL**.

## Apps principales

| App | Responsabilidad |
|---|---|
| `accounts` | Empresas (multi-tenant), usuarios, permisos, super-admin |
| `apice` | CRM clásico (contactos, deals, pipeline, leads) + integraciones MercadoLibre / Zoho Mail / WhatsApp |
| `erp_core` | Modelos base ERP: `TenantModel`, `Cliente`, `Vendedor` |
| `inventario` | Artículos, Almacenes, Stock, MovimientoStock |
| `ventas` | Pedidos, detalles, confirmación con descuento de stock atómico |

## Requisitos

- Python 3.10+
- PostgreSQL 13+
- Git

## Setup rápido

```bash
# 1. Clonar
git clone https://github.com/altitud737/apice.git
cd apice

# 2. Entorno virtual
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 3. Dependencias
pip install -r requirements.txt

# 4. Configurar entorno
cp .env.example .env
# Editar .env con tus credenciales de PostgreSQL
```

### Variables mínimas en `.env`

```env
SECRET_KEY="cambiar-por-clave-segura-en-produccion"
DEBUG=True

DATABASE_URL="postgresql://usuario:password@localhost:5432/apice_crm"

# Opcional: integraciones
ML_CLIENT_ID=""
ML_CLIENT_SECRET=""
ML_REDIRECT_URI="http://localhost:3000/integrations/mercadolibre/callback"
```

### Crear base de datos PostgreSQL

```bash
# Conectarse como superusuario
psql -U postgres
```
```sql
CREATE DATABASE apice_crm;
\q
```

## Inicialización

```bash
# Migrar
python manage.py migrate

# Crear superusuario
python manage.py createsuperuser

# (Opcional) datos demo
python setup_data.py

# Iniciar servidor
python manage.py runserver 3000
```

Acceder en:
- App: http://127.0.0.1:3000/
- Admin: http://127.0.0.1:3000/admin/

## Tests

```bash
python manage.py test
# Solo ERP:
python manage.py test ventas inventario erp_core
```

## Estructura

```
.
├── accounts/          # Tenant, usuarios, super-admin
├── apice/             # CRM + integraciones
├── erp_core/          # Base ERP (TenantModel, Cliente, Vendedor)
├── inventario/        # Artículos, Stock, Movimientos
├── ventas/            # Pedidos, confirmación, services transaccionales
├── core/              # settings.py, urls.py, wsgi.py, asgi.py
├── templates/         # Templates Django
├── static/            # CSS/JS/imágenes
├── manage.py
├── requirements.txt
├── .env.example
├── iniciar-crm.bat    # Atajo Windows: migrate + runserver
├── backup_db.bat      # Backup PostgreSQL via pg_dump
└── verificar_produccion.bat  # Checks pre-deploy
```

## Reglas de arquitectura ERP

- Todas las entidades ERP heredan de `erp_core.TenantModel` (FK obligatoria a `accounts.Company`).
- Modificaciones de stock **siempre** vía `inventario.services` (transaccionales con `select_for_update`).
- Confirmación de pedidos vía `ventas.services.confirmar_pedido` (atómico: valida → descuenta → registra movimiento → cambia estado).
- `Stock.cantidad >= 0` garantizado por `CheckConstraint` a nivel DB.

## Despliegue (resumen)

1. Definir `DATABASE_URL` en el entorno
2. `DJANGO_SETTINGS_MODULE=core.settings_production`
3. `python manage.py collectstatic --noinput`
4. `python manage.py migrate`
5. `gunicorn core.wsgi`

## Documentación adicional

- `MIGRACION_POSTGRESQL.md` — migración histórica
- `SISTEMA_SUPER_ADMIN.md` — gestión de empresas y permisos
- `API_LEADS_EXAMPLES.md` — captura de leads vía API
- `INTEGRACION_MERCADOLIBRE.md` — OAuth2 + sincronización
- `INTEGRACION_ZOHO_MAIL.md` — emails
- `ARQUITECTURA_LEADS_CONTACTOS.md` — diseño leads/contactos
- `AUTENTICACION_ALLAUTH.md` — login flow

## Licencia

Propiedad de Altitud737.
