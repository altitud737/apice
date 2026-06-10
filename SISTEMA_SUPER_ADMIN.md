# Sistema de Super Administrador - Apice Apice

## 📋 Resumen

Sistema completo de super administrador para gestionar clientes del Apice Apice. El registro público está deshabilitado y solo el super admin puede crear nuevos clientes.

---

## 🔐 Acceso al Sistema

### Super Administrador Principal
```
URL: http://localhost:8000/accounts/login/
Email: admin@sdp.com
Contraseña: Admin123!
```

### Panel de Administración
```
URL: http://localhost:8000/superadmin/admin/dashboard/
```

---

## ✨ Características Implementadas

### 1. **Autenticación Simplificada**
- ✅ Solo login con email y contraseña
- ✅ Registro público deshabilitado
- ✅ OAuth de Google eliminado
- ✅ Recuperación de contraseña eliminada
- ✅ Sin opciones de registro para usuarios finales

### 2. **Panel de Super Administrador**

#### Dashboard Principal (`/superadmin/admin/dashboard/`)
- Estadísticas globales del sistema
- Total de empresas, usuarios, leads, contactos y deals
- Lista de empresas recientes
- Accesos rápidos a funciones principales

#### Gestión de Empresas (`/superadmin/admin/companies/`)
- Lista completa de todas las empresas/clientes
- Estadísticas por empresa (usuarios, leads, contactos, deals)
- Acceso a detalles de cada empresa
- Botón para crear nuevos clientes

#### Crear Cliente (`/superadmin/admin/companies/create/`)
- Formulario simple para crear empresa + usuario
- Campos requeridos:
  - Nombre de empresa
  - Email del usuario
  - Contraseña temporal
  - Nombre y apellido (opcional)
- Creación automática de:
  - Empresa con API Key único
  - Usuario con acceso completo
  - Pipeline principal con 6 stages
  - Configuración inicial lista

#### Detalles de Empresa (`/superadmin/admin/companies/{id}/`)
- Información completa de la empresa
- Lista de usuarios de la empresa
- Estadísticas detalladas
- Estado de integraciones (MercadoLibre, Zoho Mail)
- Opción para resetear contraseñas
- Opción para eliminar empresa completa

### 3. **Gestión de Usuarios**
- Ver todos los usuarios de cada empresa
- Resetear contraseñas de cualquier usuario
- Eliminar empresas completas con todos sus datos

### 4. **Seguridad**
- Decorador `@superadmin_required` en todas las vistas
- Solo usuarios con `is_superadmin=True` pueden acceder
- Redirección automática si no es super admin
- Confirmación antes de eliminar empresas
- Eliminación en cascada de todos los datos relacionados

---

## 🚀 Flujo de Trabajo

### Crear un Nuevo Cliente

1. **Login como Super Admin**
   ```
   http://localhost:8000/accounts/login/
   Email: admin@sdp.com
   Contraseña: Admin123!
   ```

2. **Acceder al Panel**
   - Click en "Super Admin" en el menú lateral (icono rojo)
   - O ir directamente a `/superadmin/admin/dashboard/`

3. **Crear Cliente**
   - Click en "Crear Cliente" o ir a `/superadmin/admin/companies/create/`
   - Completar formulario:
     ```
     Nombre de Empresa: Empresa Demo S.A.
     Email: cliente@empresa.com
     Contraseña: TempPass123!
     Nombre: Juan
     Apellido: Pérez
     ```
   - Click "Crear Cliente"

4. **Resultado**
   - ✅ Empresa creada con API Key único
   - ✅ Usuario creado con acceso completo
   - ✅ Pipeline "Principal" con 6 stages:
     - Nuevo
     - Contactado
     - Calificado
     - Propuesta
     - Negociación
     - Ganado
   - ✅ Sistema listo para usar

5. **Enviar Credenciales al Cliente**
   ```
   Email: cliente@empresa.com
   Contraseña: TempPass123!
   URL: http://localhost:8000/accounts/login/
   ```

### Gestionar Cliente Existente

1. **Ver Lista de Empresas**
   - Panel Admin → Empresas
   - Ver estadísticas de cada empresa

2. **Ver Detalles**
   - Click en "Ver Detalles"
   - Ver usuarios, estadísticas, integraciones

3. **Resetear Contraseña**
   - En detalles de empresa
   - Click "Resetear Contraseña" junto al usuario
   - Ingresar nueva contraseña
   - Enviar nueva contraseña al cliente

4. **Eliminar Empresa**
   - En detalles de empresa
   - Click "Eliminar Empresa"
   - Confirmar eliminación
   - **ADVERTENCIA**: Elimina TODOS los datos:
     - Usuarios
     - Leads
     - Contactos
     - Deals
     - Actividades
     - Tareas
     - Pipelines
     - Stages
     - Templates
     - Integraciones
     - Emails

---

## 🛠️ Comandos Útiles

### Crear Super Administrador

```bash
# Interactivo
python manage.py createsuperadmin

# Con argumentos
python manage.py createsuperadmin --email admin@empresa.com --password MiPassword123!
```

### Migraciones

```bash
# Crear migraciones
python manage.py makemigrations

# Aplicar migraciones
python manage.py migrate
```

---

## 📊 Modelo de Datos

### User (Extendido)
```python
class User(AbstractUser):
    company = ForeignKey(Company)
    is_superadmin = BooleanField(default=False)  # Nuevo campo
```

### Company
```python
class Company(Model):
    name = CharField(max_length=255)
    api_key = CharField(max_length=64, unique=True)
    created_at = DateTimeField(auto_now_add=True)
```

---

## 🔒 Configuración de Seguridad

### Settings.py
```python
# Deshabilitar registro público
ACCOUNT_ALLOW_REGISTRATION = False

# Solo login con email
ACCOUNT_LOGIN_METHODS = {'email'}

# Adaptador personalizado
ACCOUNT_ADAPTER = 'accounts.adapters.AccountAdapter'
```

### Decorador de Seguridad
```python
@login_required
@superadmin_required
def vista_admin(request):
    # Solo accesible para super admins
    pass
```

---

## 📁 Archivos Importantes

### Backend
- `accounts/models.py` - Modelo User con is_superadmin
- `accounts/views_admin.py` - Vistas del panel de administración
- `accounts/urls.py` - URLs del panel
- `accounts/management/commands/createsuperadmin.py` - Comando CLI
- `core/settings.py` - Configuración de allauth

### Frontend
- `templates/account/login.html` - Página de login simplificada
- `templates/accounts/admin_dashboard.html` - Dashboard del super admin
- `templates/accounts/admin_companies.html` - Lista de empresas
- `templates/accounts/admin_create_client.html` - Formulario crear cliente
- `templates/accounts/admin_company_detail.html` - Detalles de empresa
- `templates/base.html` - Menú con enlace a Super Admin

---

## 🎯 URLs del Sistema

### Autenticación
```
/accounts/login/          - Login (único punto de acceso público)
/accounts/logout/         - Logout
```

### Panel de Super Admin
```
/superadmin/admin/dashboard/                      - Dashboard
/superadmin/admin/companies/                      - Lista de empresas
/superadmin/admin/companies/create/               - Crear cliente
/superadmin/admin/companies/{id}/                 - Detalles empresa
/superadmin/admin/companies/{id}/delete/          - Eliminar empresa
/superadmin/admin/users/{id}/reset-password/      - Resetear contraseña
```

### Apice (Usuarios Normales)
```
/                         - Dashboard del Apice
/apice/leads/              - Gestión de leads
/apice/contacts/           - Gestión de contactos
/apice/pipeline/           - Pipeline de ventas
/apice/mail/               - Email integrado
/apice/integrations/       - Integraciones
/apice/settings/           - Configuración
```

---

## ✅ Checklist de Implementación

- [x] Campo `is_superadmin` agregado al modelo User
- [x] Comando `createsuperadmin` creado
- [x] Super admin principal creado (admin@sdp.com)
- [x] Vistas del panel de administración implementadas
- [x] Templates del panel creados
- [x] URLs configuradas
- [x] Decorador de seguridad implementado
- [x] Registro público deshabilitado
- [x] OAuth de Google eliminado
- [x] Link de recuperar contraseña eliminado
- [x] Link de registro eliminado
- [x] Menú actualizado con sección Super Admin
- [x] Migraciones aplicadas
- [x] Sistema probado y funcional

---

## 🚨 Notas Importantes

### Seguridad
- **NUNCA** compartas las credenciales del super admin
- Cambia la contraseña por defecto en producción
- Usa HTTPS en producción
- Mantén el `SECRET_KEY` seguro

### Eliminación de Datos
- La eliminación de empresas es **IRREVERSIBLE**
- Todos los datos relacionados se eliminan en cascada
- Siempre hay confirmación antes de eliminar
- Considera hacer backups antes de eliminar empresas grandes

### Escalabilidad
- El sistema soporta múltiples super admins
- Cada empresa está completamente aislada (multi-tenant)
- Las API Keys son únicas por empresa
- No hay límite de empresas/clientes

---

## 📞 Soporte

Para crear más super administradores o resolver problemas:

```bash
python manage.py createsuperadmin
```

O contacta al administrador del sistema.

---

**Sistema implementado y funcional - Marzo 2026**
