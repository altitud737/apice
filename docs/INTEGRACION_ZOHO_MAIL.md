# Integración Zoho ZeptoMail - ERP

## 📧 Descripción

Este ERP está integrado con **Zoho ZeptoMail** para el envío de emails transaccionales. Esta integración es ideal para el modelo de negocio donde cada cliente tiene su propio dominio de email personalizado.

---

## 🎯 Casos de Uso

### Para el Negocio
- **Cada cliente tiene su propio dominio**: `cliente1.com`, `cliente2.com`, etc.
- **Emails personalizados**: `info@cliente1.com`, `ventas@cliente2.com`
- **Emails transaccionales dERP**: Notificaciones, bienvenida, recuperación de contraseña
- **Branding personalizado**: Cada cliente recibe emails desde su propio dominio

### Emails Implementados
1. **Email de Bienvenida**: Al registrarse un nuevo usuario
2. **Notificación de Lead**: Cuando se crea un nuevo lead
3. **Recuperación de Contraseña**: Para reset de contraseña
4. **Emails Personalizados**: API flexible para cualquier tipo de email

---

## 🔧 Configuración

### 1. Crear Cuenta en Zoho ZeptoMail

1. Ir a [https://www.zoho.com/zeptomail/](https://www.zoho.com/zeptomail/)
2. Crear cuenta gratuita (hasta 10,000 emails/mes)
3. Verificar tu email

### 2. Agregar y Verificar Dominio

**Para cada cliente:**

1. En Zoho ZeptoMail → **Mail Agents** → **Add Mail Agent**
2. Ingresar el dominio del cliente: `cliente1.com`
3. Verificar el dominio agregando registros DNS:
   - **TXT Record**: Para verificación de propiedad
   - **SPF Record**: Para autenticación de email
   - **DKIM Record**: Para firma digital
   - **DMARC Record**: Para política de seguridad (opcional)

**Ejemplo de registros DNS:**
```
TXT:  zeptomail-verification=xxxxxxxxxxxxx
SPF:  v=spf1 include:zeptomail.zoho.com ~all
DKIM: zeptomail._domainkey IN TXT "v=DKIM1; k=rsa; p=MIGfMA0GCS..."
```

### 3. Obtener API Token

1. En Zoho ZeptoMail → **Mail Agents** → Seleccionar el agente
2. Ir a **SMTP/API** tab
3. Copiar el **Send Mail Token**
4. Guardar el token de forma segura

### 4. Configurar Variables de Entorno

Editar tu archivo `.env`:

```env
# Zoho ZeptoMail Configuration
ZOHO_ZEPTOMAIL_API_KEY_TOKEN=tu_token_aqui
ZOHO_ZEPTOMAIL_HOSTED_REGION=zeptomail.zoho.com
DEFAULT_FROM_EMAIL=noreply@tudominio.com
SERVER_EMAIL=noreply@tudominio.com

# En producción, cambiar DEBUG a False
DEBUG=False
```

**Regiones disponibles:**
- US: `zeptomail.zoho.com`
- EU: `zeptomail.zoho.eu`
- IN: `zeptomail.zoho.in`
- AU: `zeptomail.zoho.com.au`

### 5. Instalar Dependencias

```bash
pip install -r requirements.txt
```

Esto instalará `django-zoho-zeptomail==1.0.0`

---

## 📝 Uso del Servicio de Email

### Importar el Servicio

```python
from crm.email_service import EmailService
```

### 1. Email de Bienvenida (Automático)

Se envía automáticamente al registrarse un usuario:

```python
# Esto se ejecuta automáticamente en accounts/adapters.py
EmailService.send_welcome_email(user)
```

### 2. Notificación de Lead

```python
from crm.email_service import EmailService
from crm.models import Lead

# Cuando se crea un lead
lead = Lead.objects.get(id=1)
user = request.user

EmailService.send_lead_notification(lead, user)
```

### 3. Email Personalizado

```python
# Email simple (texto plano)
EmailService.send_custom_email(
    to_email='cliente@ejemplo.com',
    subject='Asunto del Email',
    message='Contenido del email en texto plano'
)

# Email con HTML
html_content = """
<html>
<body>
    <h1>Hola Cliente</h1>
    <p>Este es un email con <strong>HTML</strong>.</p>
</body>
</html>
"""

EmailService.send_custom_email(
    to_email='cliente@ejemplo.com',
    subject='Email con HTML',
    message='Versión en texto plano',
    html_message=html_content
)
```

### 4. Email Masivo

```python
recipients = ['cliente1@ejemplo.com', 'cliente2@ejemplo.com', 'cliente3@ejemplo.com']

EmailService.send_bulk_email(
    recipients=recipients,
    subject='Actualización Importante',
    message='Contenido del mensaje',
    html_message='<h1>Contenido HTML</h1>'
)
```

---

## 🏗️ Arquitectura

### Flujo de Email en Desarrollo

```
Usuario se registra
    ↓
AccountAdapter.save_user()
    ↓
EmailService.send_welcome_email()
    ↓
EMAIL_BACKEND = 'console' (DEBUG=True)
    ↓
Email se muestra en consola/terminal
```

### Flujo de Email en Producción

```
Usuario se registra
    ↓
AccountAdapter.save_user()
    ↓
EmailService.send_welcome_email()
    ↓
EMAIL_BACKEND = 'zoho_zeptomail' (DEBUG=False)
    ↓
Django → Zoho ZeptoMail API
    ↓
Zoho ZeptoMail → Destinatario
```

---

## 🎨 Personalización de Templates

### Crear Template HTML Personalizado

1. Crear archivo `templates/emails/welcome.html`:

```html
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background-color: #10b981; color: white; padding: 20px; }
        .content { padding: 20px; }
        .footer { background-color: #f3f4f6; padding: 15px; text-align: center; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Bienvenido a {{ company_name }}</h1>
        </div>
        <div class="content">
            <p>Hola {{ username }},</p>
            <p>Tu cuenta ha sido creada exitosamente.</p>
            <p><strong>API Key:</strong> {{ api_key }}</p>
        </div>
        <div class="footer">
            <p>&copy; 2026 {{ company_name }}. Todos los derechos reservados.</p>
        </div>
    </div>
</body>
</html>
```

2. Usar el template en el servicio:

```python
from django.template.loader import render_to_string

html_content = render_to_string('emails/welcome.html', {
    'username': user.username,
    'company_name': user.company.name,
    'api_key': user.company.api_key,
})

EmailService.send_custom_email(
    to_email=user.email,
    subject='Bienvenido',
    message='Texto plano',
    html_message=html_content
)
```

---

## 🔐 Seguridad

### Mejores Prácticas

1. **Nunca hardcodear el API Token**
   ```python
   # ❌ MAL
   ZOHO_ZEPTOMAIL_API_KEY_TOKEN = 'mi_token_secreto'
   
   # ✅ BIEN
   ZOHO_ZEPTOMAIL_API_KEY_TOKEN = env('ZOHO_ZEPTOMAIL_API_KEY_TOKEN')
   ```

2. **Usar variables de entorno**
   - Agregar `.env` al `.gitignore`
   - Nunca commitear tokens en el repositorio

3. **Validar emails antes de enviar**
   ```python
   from django.core.validators import validate_email
   from django.core.exceptions import ValidationError
   
   try:
       validate_email(email)
       EmailService.send_custom_email(...)
   except ValidationError:
       # Email inválido
       pass
   ```

4. **Rate Limiting**
   - Zoho ZeptoMail tiene límites de envío
   - Plan gratuito: 10,000 emails/mes
   - Implementar throttling si es necesario

---

## 📊 Monitoreo

### Logs de Email

Los emails se registran automáticamente en los logs de Django:

```python
import logging
logger = logging.getLogger(__name__)

# En email_service.py
logger.info(f"Email de bienvenida enviado a {to_email}")
logger.error(f"Error enviando email: {e}")
```

### Ver Logs en Desarrollo

```bash
# Los emails se muestran en la consola cuando DEBUG=True
python manage.py runserver
```

### Dashboard de Zoho ZeptoMail

1. Ir a [https://zeptomail.zoho.com/](https://zeptomail.zoho.com/)
2. Ver estadísticas de emails enviados
3. Monitorear tasas de entrega, rebotes, etc.

---

## 🚀 Despliegue en Producción

### Checklist Pre-Producción

- [ ] Dominio verificado en Zoho ZeptoMail
- [ ] Registros DNS configurados (SPF, DKIM, DMARC)
- [ ] API Token generado y guardado
- [ ] Variables de entorno configuradas en servidor
- [ ] `DEBUG=False` en producción
- [ ] `DEFAULT_FROM_EMAIL` configurado con dominio verificado
- [ ] Probar envío de email de prueba

### Configuración en Servidor

**Ejemplo con variables de entorno en servidor:**

```bash
export ZOHO_ZEPTOMAIL_API_KEY_TOKEN="tu_token_produccion"
export ZOHO_ZEPTOMAIL_HOSTED_REGION="zeptomail.zoho.com"
export DEFAULT_FROM_EMAIL="noreply@tudominio.com"
export DEBUG="False"
```

**O usando archivo `.env` en servidor:**

```bash
# Copiar .env.example a .env
cp .env.example .env

# Editar .env con valores de producción
nano .env
```

---

## 🧪 Testing

### Probar Email en Desarrollo

```bash
# Iniciar servidor
python manage.py runserver

# Registrar un usuario nuevo
# El email se mostrará en la consola
```

### Probar Email en Producción (Sandbox)

```python
# En Django shell
python manage.py shell

from accounts.models import User
from crm.email_service import EmailService

# Obtener un usuario
user = User.objects.first()

# Enviar email de prueba
EmailService.send_welcome_email(user)
```

### Verificar Entrega

1. Revisar logs de Django
2. Revisar dashboard de Zoho ZeptoMail
3. Verificar bandeja de entrada del destinatario

---

## 🔄 Multi-Tenant con Múltiples Dominios

### Escenario: Cada Cliente con su Dominio

**Cliente 1:**
- Dominio: `cliente1.com`
- Email: `info@cliente1.com`
- Token: `token_cliente1`

**Cliente 2:**
- Dominio: `cliente2.com`
- Email: `ventas@cliente2.com`
- Token: `token_cliente2`

### Implementación Avanzada (Futuro)

Para soportar múltiples dominios por empresa:

```python
# Agregar a Company model
class Company(models.Model):
    name = models.CharField(max_length=255)
    api_key = models.CharField(max_length=64, unique=True)
    
    # Configuración de email por empresa
    email_from = models.EmailField(default='noreply@example.com')
    zoho_api_token = models.CharField(max_length=255, blank=True)
    zoho_region = models.CharField(max_length=50, default='zeptomail.zoho.com')
```

---

## 📚 Recursos Adicionales

### Documentación Oficial
- [Zoho ZeptoMail Docs](https://www.zoho.com/zeptomail/help/)
- [Django Email Backend](https://docs.djangoproject.com/en/stable/topics/email/)
- [django-zoho-zeptomail GitHub](https://github.com/zoho/zeptomail-python)

### Soporte
- Zoho ZeptoMail Support: [https://help.zoho.com/portal/en/community/zeptomail](https://help.zoho.com/portal/en/community/zeptomail)
- Django Email Issues: [https://docs.djangoproject.com/en/stable/topics/email/](https://docs.djangoproject.com/en/stable/topics/email/)

---

## ❓ Troubleshooting

### Error: "Authentication failed"

**Causa**: Token inválido o expirado

**Solución**:
1. Verificar que el token esté correcto en `.env`
2. Regenerar token en Zoho ZeptoMail
3. Actualizar variable de entorno

### Error: "Domain not verified"

**Causa**: El dominio del `DEFAULT_FROM_EMAIL` no está verificado

**Solución**:
1. Ir a Zoho ZeptoMail → Mail Agents
2. Verificar que el dominio esté verificado (check verde)
3. Si no, agregar registros DNS y verificar

### Emails no se envían en producción

**Checklist**:
1. ✅ `DEBUG=False` en settings
2. ✅ `ZOHO_ZEPTOMAIL_API_KEY_TOKEN` configurado
3. ✅ `DEFAULT_FROM_EMAIL` usa dominio verificado
4. ✅ Revisar logs de Django para errores
5. ✅ Verificar límites de envío en Zoho

### Emails van a spam

**Solución**:
1. Configurar registros SPF, DKIM, DMARC correctamente
2. Usar dominio verificado y con buena reputación
3. Evitar palabras spam en asunto/contenido
4. Incluir link de unsubscribe (para emails masivos)

---

## 💰 Planes de Zoho ZeptoMail

| Plan | Emails/Mes | Precio |
|------|------------|--------|
| Free | 10,000 | $0 |
| Starter | 25,000 | $2.50 |
| Professional | 100,000 | $8.75 |
| Enterprise | Custom | Custom |

**Recomendación**: Empezar con plan Free y escalar según necesidad.

---

## ✅ Resumen

**Integración Completada:**
- ✅ Zoho ZeptoMail configurado
- ✅ EmailService creado con métodos útiles
- ✅ Email de bienvenida automático
- ✅ Soporte para HTML y texto plano
- ✅ Multi-tenant ready
- ✅ Desarrollo (console) y Producción (Zoho) separados

**Próximos Pasos:**
1. Configurar dominio en Zoho ZeptoMail
2. Obtener API Token
3. Configurar variables de entorno
4. Probar envío de emails
5. Personalizar templates según branding

---

**Tu ERP ahora tiene un sistema profesional de emails transaccionales listo para producción.** 📧✨

---

## 📬 Gestión de Email Integrada en el ERP

### Funcionalidades Implementadas

El ERP ahora incluye un **cliente de email completo** integrado que permite a cada empresa gestionar sus emails directamente desde el crm:

**1. Configuración Multi-Tenant:**
- Cada empresa puede conectar su propia cuenta de Zoho Mail
- Credenciales almacenadas de forma segura por empresa
- OAuth 2.0 para autenticación segura

**2. Bandeja de Entrada:**
- Ver emails recibidos en tiempo real
- Organización por carpetas (Inbox, Sent, Drafts, etc.)
- Indicadores de emails no leídos
- Búsqueda y filtrado
- Vista previa de emails

**3. Envío de Emails:**
- Componer y enviar emails desde el ERP
- Soporte para CC y BCC
- Formato HTML y texto plano
- Responder emails directamente

**4. Integración con crm:**
- Enviar emails a leads y contactos con un click
- Historial de comunicaciones
- Templates de email

---

## 🔧 Configuración para Clientes

### Paso 1: Obtener Credenciales de Zoho Mail

1. **Ir a Zoho API Console:**
   ```
   https://api-console.zoho.com/
   ```

2. **Crear Cliente OAuth:**
   - Click en "Add Client"
   - Seleccionar "Server-based Applications"
   - Nombre: "ERP Mail Integration"

3. **Configurar Redirect URI:**
   ```
   https://tudominio.com/crm/mail/callback/
   ```
   (En desarrollo: `http://localhost:8000/crm/mail/callback/`)

4. **Copiar Credenciales:**
   - Client ID
   - Client Secret

### Paso 2: Configurar en el ERP

1. **Ir a Mail → Configuración:**
   ```
   /crm/mail/settings/
   ```

2. **Ingresar Credenciales:**
   - Email de Zoho Mail
   - Client ID
   - Client Secret
   - Región (US, EU, IN, AU, JP)

3. **Guardar y Conectar:**
   - Click en "Guardar Configuración"
   - Click en "Conectar Zoho Mail"
   - Autorizar en Zoho Mail
   - ¡Listo!

### Paso 3: Usar el Cliente de Email

**Bandeja de Entrada:**
```
/crm/mail/inbox/
```

**Componer Email:**
```
/crm/mail/compose/
```

**Ver Email:**
```
/crm/mail/view/{message_id}/
```

---

## 🎯 Casos de Uso

### 1. Enviar Email a un Lead

```python
# Desde la vista de lead, agregar botón:
<a href="{% url 'crm:mail_compose' %}?to={{ lead.email }}&subject=Seguimiento">
    Enviar Email
</a>
```

### 2. Responder Email Directamente

- Abrir email en bandeja de entrada
- Click en "Responder"
- El destinatario y asunto se pre-cargan automáticamente

### 3. Gestionar Comunicaciones

- Todos los emails enviados/recibidos se sincronizan
- Historial completo de comunicaciones
- Búsqueda por remitente, asunto, fecha

---

## 🔐 Seguridad

### OAuth 2.0

- **No se almacenan contraseñas**: Solo tokens OAuth
- **Tokens encriptados**: Access y refresh tokens seguros
- **Refresh automático**: Los tokens se renuevan automáticamente
- **Revocación**: El cliente puede desconectar en cualquier momento

### Permisos Requeridos

```
ZohoMail.messages.ALL    # Leer y enviar emails
ZohoMail.folders.ALL     # Acceder a carpetas
ZohoMail.accounts.READ   # Info de la cuenta
```

### Aislamiento Multi-Tenant

- Cada empresa solo ve sus propios emails
- Credenciales aisladas por empresa
- Sin acceso cruzado entre empresas

---

## 📊 Arquitectura Técnica

### Modelos

**ZohoMailIntegration:**
```python
- company (FK a Company)
- client_id, client_secret
- access_token, refresh_token
- email_address, region
- is_active, last_sync
```

**EmailMessage:**
```python
- integration (FK a ZohoMailIntegration)
- message_id, subject, body
- from_address, to_addresses
- is_read, folder
- date_received
```

**EmailDraft:**
```python
- integration (FK a ZohoMailIntegration)
- to_addresses, subject, body
- is_sent, sent_at
```

### Servicios

**ZohoMailService:**
```python
- get_oauth_url()           # Generar URL OAuth
- exchange_code_for_token() # Intercambiar código
- refresh_access_token()    # Refrescar token
- get_messages()            # Obtener emails
- send_email()              # Enviar email
- mark_as_read()            # Marcar leído
- delete_message()          # Eliminar email
```

### Vistas

```python
mail_settings()   # Configuración
mail_connect()    # Iniciar OAuth
mail_callback()   # Callback OAuth
mail_inbox()      # Bandeja de entrada
mail_view()       # Ver email
mail_compose()    # Componer email
mail_delete()     # Eliminar email
```

---

## 🚀 Roadmap Futuro

### Funcionalidades Planeadas

- [ ] **Sincronización en Background**: Celery para sync automático
- [ ] **Búsqueda Avanzada**: Filtros por fecha, remitente, etiquetas
- [ ] **Etiquetas y Categorías**: Organizar emails
- [ ] **Adjuntos**: Subir y descargar archivos
- [ ] **Firmas de Email**: Firmas personalizadas por usuario
- [ ] **Templates de Email**: Plantillas reutilizables
- [ ] **Tracking de Emails**: Saber si el email fue abierto
- [ ] **Programar Envíos**: Enviar emails en fecha/hora específica
- [ ] **Integración con Leads**: Auto-crear leads desde emails
- [ ] **Respuestas Automáticas**: Respuestas predefinidas

---

## 💡 Tips de Uso

### Para Administradores

1. **Configurar una vez por empresa**: Cada cliente configura sus credenciales
2. **Monitorear uso**: Ver estadísticas de emails enviados/recibidos
3. **Backup de emails**: Los emails se sincronizan localmente

### Para Usuarios

1. **Usar desde ERP**: No necesitas abrir Zoho Mail
2. **Responder rápido**: Todo en un solo lugar
3. **Historial completo**: Busca emails antiguos fácilmente

---

**Tu ERP ahora tiene un sistema profesional de emails transaccionales Y un cliente de email completo listo para producción.** 📧✨
