# 🔐 Autenticación con django-allauth - Documentación Completa

## 📋 Descripción

Implementación completa de autenticación con **django-allauth** para tu Apice multi-tenant. Incluye:

- ✅ **Login/Registro con Email**
- ✅ **OAuth Social** (Google, GitHub)
- ✅ **Recuperación de Contraseña**
- ✅ **Creación Automática de Empresas**
- ✅ **UI Moderna con TailwindCSS**
- ✅ **Multi-tenant Compatible**

---

## 🎯 Características Implementadas

### 1. Autenticación por Email
- Login con email (no username)
- Registro con email + contraseña
- Verificación de email opcional
- Recuperación de contraseña
- Sesión persistente ("Recordarme")

### 2. OAuth Social
- **Google OAuth** - Login con cuenta Google
- **GitHub OAuth** - Login con cuenta GitHub
- Auto-registro con datos del proveedor
- Vinculación de cuentas existentes

### 3. Multi-tenant Automático
- Cada usuario nuevo → Empresa nueva
- API Key generada automáticamente
- Aislamiento de datos por empresa
- Compatible con arquitectura actual

### 4. UI Profesional
- Templates con TailwindCSS
- Diseño moderno dark mode
- Botones OAuth con logos
- Mensajes de error/éxito
- Responsive design

---

## 🏗️ Arquitectura

### Flujo de Registro

```
Usuario → Formulario de Registro
    ↓
django-allauth valida datos
    ↓
AccountAdapter.save_user()
    ↓
Crea User + Company automáticamente
    ↓
Genera API Key
    ↓
Login automático
    ↓
Redirige a Dashboard
```

### Flujo OAuth Social

```
Usuario → Click "Continuar con Google"
    ↓
Redirige a Google OAuth
    ↓
Usuario autoriza
    ↓
Google redirige con token
    ↓
SocialAccountAdapter.save_user()
    ↓
Crea User + Company (si es nuevo)
    ↓
Login automático
    ↓
Redirige a Dashboard
```

---

## 📁 Archivos Creados/Modificados

### Backend

**1. `core/settings.py`**
```python
# Apps agregadas
'django.contrib.sites',
'allauth',
'allauth.account',
'allauth.socialaccount',
'allauth.socialaccount.providers.google',
'allauth.socialaccount.providers.github',

# Configuración
ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
SOCIALACCOUNT_AUTO_SIGNUP = True

# Adaptadores personalizados
ACCOUNT_ADAPTER = 'accounts.adapters.AccountAdapter'
SOCIALACCOUNT_ADAPTER = 'accounts.adapters.SocialAccountAdapter'
```

**2. `accounts/adapters.py`** (NUEVO)
- `AccountAdapter` - Crea empresa en registro normal
- `SocialAccountAdapter` - Crea empresa en OAuth

**3. `core/urls.py`**
```python
path('accounts/', include('allauth.urls')),
```

### Frontend

**4. Templates Creados:**
- `templates/account/login.html` - Login con OAuth
- `templates/account/signup.html` - Registro con OAuth
- `templates/account/password_reset.html` - Recuperar contraseña

### Configuración

**5. `.env.example`**
```env
GOOGLE_CLIENT_ID=""
GOOGLE_CLIENT_SECRET=""
GITHUB_CLIENT_ID=""
GITHUB_CLIENT_SECRET=""
```

**6. `requirements.txt`**
```
django-allauth>=0.57.0
```

---

## ⚙️ Configuración de OAuth Providers

### Google OAuth

**1. Ir a Google Cloud Console:**
https://console.cloud.google.com/

**2. Crear Proyecto:**
- Click "Select a project" → "New Project"
- Nombre: "Apice OAuth"
- Click "Create"

**3. Habilitar Google+ API:**
- Menú → "APIs & Services" → "Library"
- Buscar "Google+ API"
- Click "Enable"

**4. Crear Credenciales OAuth:**
- Menú → "APIs & Services" → "Credentials"
- Click "Create Credentials" → "OAuth client ID"
- Application type: "Web application"
- Name: "Apice Web Client"
- Authorized redirect URIs:
  ```
  http://localhost:8000/accounts/google/login/callback/
  https://tu-dominio.com/accounts/google/login/callback/
  ```
- Click "Create"

**5. Copiar Credenciales:**
```
Client ID: xxx.apps.googleusercontent.com
Client Secret: xxx
```

**6. Agregar a `.env`:**
```env
GOOGLE_CLIENT_ID="xxx.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET="xxx"
```

---

### GitHub OAuth

**1. Ir a GitHub Settings:**
https://github.com/settings/developers

**2. Crear OAuth App:**
- Click "New OAuth App"
- Application name: "Apice"
- Homepage URL: `http://localhost:8000`
- Authorization callback URL:
  ```
  http://localhost:8000/accounts/github/login/callback/
  ```
- Click "Register application"

**3. Generar Client Secret:**
- Click "Generate a new client secret"
- Copiar el secret (solo se muestra una vez)

**4. Copiar Credenciales:**
```
Client ID: xxx
Client Secret: xxx
```

**5. Agregar a `.env`:**
```env
GITHUB_CLIENT_ID="xxx"
GITHUB_CLIENT_SECRET="xxx"
```

---

## 🚀 Configuración en Django Admin

### 1. Crear Superusuario (si no existe)
```bash
python manage.py createsuperuser
```

### 2. Acceder al Admin
```
http://localhost:8000/admin
```

### 3. Configurar Site
- Ir a "Sites"
- Editar "example.com"
- Domain name: `localhost:8000` (desarrollo) o `tudominio.com` (producción)
- Display name: `Apice`
- Save

### 4. Agregar Social Applications

**Para Google:**
- Ir a "Social applications" → "Add"
- Provider: `Google`
- Name: `Google OAuth`
- Client id: (copiar de .env)
- Secret key: (copiar de .env)
- Sites: Seleccionar tu site
- Save

**Para GitHub:**
- Ir a "Social applications" → "Add"
- Provider: `GitHub`
- Name: `GitHub OAuth`
- Client id: (copiar de .env)
- Secret key: (copiar de .env)
- Sites: Seleccionar tu site
- Save

---

## 🧪 Testing

### 1. Iniciar Servidor
```bash
python manage.py runserver
```

### 2. Probar Registro con Email
- Ir a: `http://localhost:8000/accounts/signup/`
- Ingresar email y contraseña
- Click "Crear Cuenta"
- Verificar:
  - ✅ Usuario creado
  - ✅ Empresa creada automáticamente
  - ✅ API Key generada
  - ✅ Redirige a dashboard

### 3. Probar Login con Email
- Ir a: `http://localhost:8000/accounts/login/`
- Ingresar email y contraseña
- Click "Iniciar Sesión"
- Verificar redirección a dashboard

### 4. Probar OAuth con Google
- Click "Continuar con Google"
- Autorizar en Google
- Verificar:
  - ✅ Usuario creado con email de Google
  - ✅ Empresa creada automáticamente
  - ✅ Login exitoso

### 5. Probar OAuth con GitHub
- Click "Continuar con GitHub"
- Autorizar en GitHub
- Verificar:
  - ✅ Usuario creado con email de GitHub
  - ✅ Empresa creada automáticamente
  - ✅ Login exitoso

### 6. Probar Recuperación de Contraseña
- Click "¿Olvidaste tu contraseña?"
- Ingresar email
- Verificar email recibido (en consola si DEBUG=True)

---

## 📊 Verificar en Base de Datos

```bash
python manage.py shell
```

```python
from accounts.models import User, Company

# Ver usuarios creados
users = User.objects.all()
for user in users:
    print(f"{user.email} - Company: {user.company.name} - API Key: {user.company.api_key}")

# Ver empresas
companies = Company.objects.all()
for company in companies:
    print(f"{company.name} - API Key: {company.api_key}")
```

---

## 🔧 Personalización

### Cambiar Textos

Editar templates en `templates/account/`:
- `login.html` - Textos de login
- `signup.html` - Textos de registro
- `password_reset.html` - Textos de recuperación

### Agregar Más Providers

**1. Instalar provider:**
```bash
pip install django-allauth[facebook]
```

**2. Agregar a INSTALLED_APPS:**
```python
'allauth.socialaccount.providers.facebook',
```

**3. Configurar en SOCIALACCOUNT_PROVIDERS:**
```python
'facebook': {
    'METHOD': 'oauth2',
    'SCOPE': ['email', 'public_profile'],
    'APP': {
        'client_id': env('FACEBOOK_CLIENT_ID', default=''),
        'secret': env('FACEBOOK_CLIENT_SECRET', default=''),
    }
}
```

**4. Agregar botón en templates:**
```html
<a href="{% url 'facebook_login' %}" class="...">
    Continuar con Facebook
</a>
```

### Providers Disponibles

- Google ✅ (Implementado)
- GitHub ✅ (Implementado)
- Facebook
- Twitter/X
- LinkedIn
- Microsoft
- Apple
- Discord
- Slack
- +50 más

---

## 🔒 Seguridad

### Email Verification

**Cambiar a obligatorio:**
```python
ACCOUNT_EMAIL_VERIFICATION = 'mandatory'
```

Esto requiere configurar SMTP para enviar emails.

### Configurar SMTP (Producción)

En `.env`:
```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=tu-email@gmail.com
EMAIL_HOST_PASSWORD=tu-app-password
DEFAULT_FROM_EMAIL=noreply@tuapice.com
```

En `settings.py`:
```python
if not DEBUG:
    EMAIL_BACKEND = env('EMAIL_BACKEND')
    EMAIL_HOST = env('EMAIL_HOST')
    EMAIL_PORT = env.int('EMAIL_PORT')
    EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS')
    EMAIL_HOST_USER = env('EMAIL_HOST_USER')
    EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD')
    DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL')
```

---

## 🚀 Producción

### 1. Actualizar Redirect URIs

**Google:**
```
https://tudominio.com/accounts/google/login/callback/
```

**GitHub:**
```
https://tudominio.com/accounts/github/login/callback/
```

### 2. Actualizar Site en Admin
```
Domain: tudominio.com
```

### 3. Variables de Entorno
```env
DEBUG=False
ALLOWED_HOSTS=tudominio.com,www.tudominio.com
ACCOUNT_EMAIL_VERIFICATION=mandatory
```

---

## 📈 Ventajas de django-allauth

### vs Sistema Nativo Django
- ✅ OAuth social out-of-the-box
- ✅ UI moderna incluida
- ✅ Verificación de email
- ✅ Recuperación de contraseña
- ✅ Manejo de sesiones
- ✅ Muy bien documentado
- ✅ Mantenido activamente

### vs Clerk
- ✅ Funciona con Django templates
- ✅ Gratis (open source)
- ✅ Sin vendor lock-in
- ✅ Control total del código
- ✅ Compatible con multi-tenant
- ❌ UI menos moderna (pero personalizable)

---

## 🐛 Troubleshooting

### Error: "Site matching query does not exist"
```bash
python manage.py shell
```
```python
from django.contrib.sites.models import Site
Site.objects.create(domain='localhost:8000', name='Apice')
```

### OAuth no funciona
1. Verificar credenciales en `.env`
2. Verificar Social Application en admin
3. Verificar redirect URI coincide exactamente
4. Verificar Site configurado correctamente

### Email no se envía
- En desarrollo: Ver consola (emails se imprimen)
- En producción: Configurar SMTP correctamente

### Usuario sin empresa
```python
from accounts.models import User, Company
import secrets

user = User.objects.get(email='usuario@email.com')
company = Company.objects.create(
    name=f"Empresa de {user.email.split('@')[0]}",
    api_key=secrets.token_urlsafe(32)
)
user.company = company
user.save()
```

---

## ✅ Checklist de Implementación

- [x] django-allauth instalado
- [x] Settings configurado
- [x] URLs configuradas
- [x] Migraciones aplicadas
- [x] Templates creados con TailwindCSS
- [x] Adaptadores personalizados
- [x] Multi-tenant compatible
- [ ] OAuth providers configurados (Google, GitHub)
- [ ] Site configurado en admin
- [ ] Social Applications creadas en admin
- [ ] Probado registro con email
- [ ] Probado login con email
- [ ] Probado OAuth con Google
- [ ] Probado OAuth con GitHub

---

## 🎉 Conclusión

Tu Apice ahora tiene un sistema de autenticación profesional con:

- ✅ Login/Registro moderno
- ✅ OAuth social (Google, GitHub)
- ✅ Multi-tenant automático
- ✅ UI profesional con TailwindCSS
- ✅ Listo para producción

**Próximos pasos:**
1. Configurar OAuth providers en Google/GitHub
2. Agregar credenciales a `.env`
3. Configurar Social Applications en admin
4. Probar todo el flujo
5. Deploy a producción

**Tu Apice está listo para escalar con autenticación delegada a django-allauth.** 🚀
