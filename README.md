# Apice CRM

Sistema CRM multi-tenant con integraciones para MercadoLibre, Zoho Mail y WhatsApp.

## Credenciales de Acceso

### Superadmin
- **Email:** admin@sdp.com
- **Contraseña:** Apice2024!
- **Permisos:** Acceso total al sistema, puede gestionar empresas y usuarios

### Usuario Regular
- **Email:** martindesia@hotmail.com
- **Contraseña:** Apice2024!
- **Permisos:** Usuario estándar con acceso limitado a su empresa

## Instalación

### Prerrequisitos
- Python 3.9+
- pip (gestor de paquetes de Python)

### Pasos de Instalación

1. **Clonar el repositorio**
   ```bash
   git clone https://github.com/altitud737/apice.git
   cd apice
   ```

2. **Crear y activar entorno virtual**
   ```bash
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # Linux/Mac:
   source venv/bin/activate
   ```

3. **Instalar dependencias**
   ```bash
   pip install -r requirements.txt
   ```

4. **Ejecutar migraciones**
   ```bash
   python manage.py migrate
   ```

5. **Crear datos de prueba (opcional)**
   ```bash
   python setup_data.py
   ```

## Cómo Abrir el Proyecto

### Opción 1: Usar VS Code

1. Abrir VS Code
2. File → Open Folder
3. Seleccionar la carpeta `apice` (la carpeta del proyecto)
4. Abrir una terminal en VS Code (Ctrl + `)
5. Activar el entorno virtual:
   ```bash
   venv\Scripts\activate
   ```

### Opción 2: Desde el Explorador de Archivos

1. Ir a la carpeta del proyecto
2. Hacer doble clic en `iniciar-crm.bat`
3. El servidor se iniciará automáticamente en http://127.0.0.1:3000/

### Opción 3: Manual desde Terminal

1. Abrir terminal en la carpeta del proyecto
2. Activar entorno virtual:
   ```bash
   venv\Scripts\activate
   ```
3. Iniciar servidor:
   ```bash
   python manage.py runserver 3000
   ```

## Acceder a la Aplicación

Una vez iniciado el servidor, abrir en el navegador:
- **URL:** http://127.0.0.1:3000/

## Base de Datos

El proyecto usa **SQLite** por defecto en desarrollo (`db.sqlite3`), pero está configurado para usar **PostgreSQL** en producción si se configura la variable `DATABASE_URL` en el archivo `.env`.

## Tablas y Columnas

### accounts (Cuentas y Usuarios)

**accounts_company**
- id, name, industry, description, location, api_key, is_active, created_at, updated_at
- iva_condition, iibb_rate, province, ml_commission_rate

**accounts_user**
- id, username, email, password, first_name, last_name, is_superuser, is_staff, is_active, date_joined, last_login
- company (FK), is_superadmin, is_company_admin
- can_send_emails, can_view_contacts, can_view_deals, can_view_pipeline, can_view_settings, can_manage_users, can_view_integrations
- last_activity

**accounts_supportticket**
- id, user (FK), company (FK), category, subject, message, status, admin_response, created_at, updated_at, resolved_at

**accounts_systemnotification**
- id, title, message, category, created_by (FK), is_active, created_at

**accounts_usernotification**
- id, user (FK), notification (FK), is_read, read_at

**accounts_demorequest**
- id, name, email, company, message, status, admin_notes, created_at, updated_at

### apice (CRM Core)

**crm_pipeline**
- id, company (FK), name, description, is_default, color, created_at, updated_at

**crm_contact**
- id, company (FK), contact_type, name, email, phone, company_name, status, interest_level, next_action_date, source, owner (FK), created_at, updated_at

**crm_stage**
- id, company (FK), pipeline (FK), name, order, created_at, updated_at

**crm_deal**
- id, company (FK), title, value, probability, contact (FK), stage (FK), expected_close_date, owner (FK), created_at, updated_at

**crm_activity**
- id, company (FK), contact (FK), type, description, user (FK), created_at, updated_at

**crm_task**
- id, company (FK), title, due_date, priority, completed, contact (FK), owner (FK), created_at, updated_at

**crm_messagetemplate**
- id, company (FK), name, message, description, is_active, created_at, updated_at

**crm_lead**
- id, company (FK), name, email, phone, message, source, status, metadata (JSON), converted_to_contact (FK), created_at, updated_at

### MercadoLibre Integration

**mercadolibre_oauth_states**
- id, state, user (FK), company (FK), created_at

**mercadolibre_integrations**
- id, company (FK), connected_by (FK), ml_user_id, nickname, email, site_id, access_token, refresh_token, token_expires_at, is_active, created_at, updated_at, last_sync_at, auto_reply_enabled

**mercadolibre_products**
- id, integration (FK), company (FK), ml_item_id, title, description, category_id, price, currency_id, available_quantity, sold_quantity, condition, listing_type_id, permalink, thumbnail, status, last_synced_at, raw_data (JSON), created_at, updated_at

**mercadolibre_orders**
- id, integration (FK), company (FK), ml_order_id, status, status_detail, buyer_id, buyer_nickname, buyer_first_name, buyer_last_name, buyer_email, buyer_phone, total_amount, paid_amount, currency_id, shipping_id, shipping_status, shipping_tracking_number, shipping_carrier, shipping_receiver_address (JSON), payment_method, contact (FK), deal (FK), lead (FK), date_created, date_closed, last_updated, raw_data (JSON), created_at, updated_at

**mercadolibre_order_items**
- id, order (FK), product (FK), ml_item_id, title, quantity, unit_price, currency_id, category_id, thumbnail, variation_id, variation_attributes (JSON)

**mercadolibre_messages**
- id, integration (FK), company (FK), ml_message_id, pack_id, order (FK), sender_id, sender_nickname, receiver_id, is_from_buyer, text, message_date, status, contact (FK), read_at, raw_data (JSON), created_at

**mercadolibre_questions**
- id, integration (FK), company (FK), ml_question_id, ml_item_id, from_id, from_nickname, text, status, date_created, answer_text, answer_date, product (FK), lead (FK), auto_replied, auto_reply_template (FK), answered_by (FK), is_ignored, read_at, raw_data (JSON), created_at

**mercadolibre_reply_templates**
- id, company (FK), created_by (FK), name, keywords (JSON), response_text, is_active, priority, usable_in_questions, usable_in_messages, times_used, last_used_at, created_at, updated_at

**mercadolibre_categories**
- id, ml_category_id, name, ml_parent_id, parent (FK), path_from_root (JSON), picture, total_items_in_this_category, has_children, site_id, synced_at

**mercadolibre_webhook_events**
- id, integration (FK), topic, resource, ml_user_id, application_id, attempts, sent_date, raw_payload (JSON), status, error_message, retry_count, received_at, processed_at

### Zoho Mail Integration

**crm_zohomailintegration**
- id, company (FK), client_id, client_secret, refresh_token, access_token, token_expires_at, account_id, email_address, region, is_active, last_sync, created_at, updated_at

**crm_emailmessage**
- id, integration (FK), message_id, thread_id, from_address, from_name, to_addresses (JSON), cc_addresses (JSON), bcc_addresses (JSON), subject, body_text, body_html, date_sent, date_received, is_read, is_starred, is_draft, folder, has_attachments, attachments_data (JSON), created_at, updated_at

**crm_emaildraft**
- id, integration (FK), to_addresses, cc_addresses, bcc_addresses, subject, body, is_sent, sent_at, created_at, updated_at

### WhatsApp Integration

**crm_whatsapp_integration**
- id, company (FK), phone_number_id, business_account_id, access_token, verify_token, webhook_url, phone_number, is_active, auto_create_leads, auto_create_contacts, created_at, updated_at

**crm_whatsapp_message**
- id, company (FK), integration (FK), message_id, wamid, from_number, to_number, contact_name, message_type, direction, status, text_body, media_url, media_id, caption, timestamp, raw_data (JSON), lead (FK), contact (FK), sent_by (FK)

**crm_whatsapp_webhook_event**
- id, company (FK), integration (FK), event_type, raw_payload (JSON), processed, processed_at, error_message, created_at

**crm_whatsapp_template**
- id, company (FK), integration (FK), name, language, category, status, header_text, body_text, footer_text, template_id, components (JSON), is_active

## Estructura del Proyecto

```
apice/
├── accounts/          # App de cuentas y usuarios
├── apice/             # App principal del CRM
├── core/              # Configuración de Django
├── templates/         # Templates HTML
├── static/            # Archivos estáticos
├── venv/              # Entorno virtual (no subir a git)
├── db.sqlite3         # Base de datos SQLite (no subir a git)
├── manage.py          # Script de gestión de Django
├── requirements.txt   # Dependencias de Python
├── iniciar-crm.bat    # Script para iniciar el servidor (Windows)
└── setup_data.py      # Script para crear datos de prueba
```

## Integraciones

### MercadoLibre
- OAuth2 authentication
- Sincronización de productos, órdenes, preguntas y mensajes
- Auto-reply con plantillas
- Webhook events

### Zoho Mail
- Integración OAuth2
- Sincronización de emails
- Envío de emails desde el CRM

### WhatsApp
- WhatsApp Business API
- Webhook para mensajes entrantes
- Plantillas de mensajes aprobadas

## Desarrollo

### Ejecutar migraciones
```bash
python manage.py migrate
```

### Crear superusuario
```bash
python manage.py createsuperuser
```

### Ejecutar servidor de desarrollo
```bash
python manage.py runserver 3000
```

## Variables de Entorno

Crear archivo `.env` en la raíz del proyecto:

```env
SECRET_KEY=django-insecure-apice-secret-key
DEBUG=True
DATABASE_URL=sqlite:///db.sqlite3
ML_CLIENT_ID=tu_client_id
ML_CLIENT_SECRET=tu_client_secret
ML_REDIRECT_URI=http://localhost:3000/integrations/mercadolibre/callback
```

## Licencia

Este proyecto es propiedad de Altitud737.
