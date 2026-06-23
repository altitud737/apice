# Diseño del Sistema ERP - Configuración y Super Admin

## 📋 CONFIGURACIÓN DEL CLIENTE

### 1. Perfil de Empresa
- **Campos:**
  - Nombre de la empresa
  - Industria (selector con opciones: Metalúrgica, Construcción, Educación, etc.)
  - Descripción breve
  - Ubicación
  - Logo (futuro)

### 2. Usuarios
- **Funcionalidades:**
  - Listar usuarios de la empresa
  - Crear nuevo usuario (email, contraseña, permisos)
  - Editar permisos de usuario
  - Eliminar usuario
  
- **Permisos configurables:**
  - ✅ Puede enviar emails
  - ✅ Puede ver contactos
  - ✅ Puede ver deals
  - ✅ Puede ver pipeline
  - ✅ Puede ver configuración
  - ✅ Puede gestionar usuarios
  - ✅ Puede ver integraciones

### 3. Seguridad
- **Funcionalidades:**
  - Cambiar contraseña de la cuenta
  - Ver API Key
  - Regenerar API Key

### 4. Soporte
- **Categorías:**
  - 🔒 Problemas de Seguridad
  - 💡 Mejora
  - 🔌 Integraciones
  - 📝 Otro

- **Campos del ticket:**
  - Categoría
  - Asunto
  - Mensaje/Descripción
  - Estado (Abierto, En Progreso, Resuelto, Cerrado)

---

## 🎯 PANEL SUPER ADMIN

### 1. Dashboard
- **Estadísticas:**
  - Total de usuarios
  - Total de empresas
  - Empresas activas
  - Empresas suspendidas
  - Nuevos registros (últimos 7 días)
  - Usuarios activos hoy
  - Tickets pendientes

### 2. Gestión de Empresas
- **Funcionalidades:**
  - Ver todas las empresas
  - Crear empresa manualmente
  - Ver detalles de empresa
  - Editar empresa
  - Suspender/Activar empresa
  - Eliminar empresa
  - Ver usuarios de la empresa
  - Configurar Zoho Mail para la empresa

- **Información mostrada:**
  - Nombre
  - Industria
  - Fecha de registro
  - Estado (Activa/Suspendida)
  - Cantidad de usuarios
  - Última actividad

### 3. Gestión de Usuarios
- **Funcionalidades:**
  - Ver todos los usuarios del sistema
  - Filtrar por empresa
  - Ver detalles de usuario
  - Cambiar contraseña
  - Suspender/Activar usuario
  - Eliminar usuario
  - **Impersonar usuario** (login como ese usuario)
  - Ver última actividad

- **Información mostrada:**
  - Nombre/Email
  - Empresa
  - Rol (Admin empresa / Usuario)
  - Última actividad
  - Estado

### 4. Mensajes/Tickets de Soporte
- **Funcionalidades:**
  - Ver todos los tickets
  - Filtrar por categoría
  - Filtrar por estado
  - Ver detalles del ticket
  - Responder ticket
  - Cambiar estado (Abierto → En Progreso → Resuelto → Cerrado)
  - Marcar como resuelto

- **Vista del ticket:**
  - Usuario que lo envió
  - Empresa
  - Categoría
  - Asunto
  - Mensaje
  - Fecha
  - Estado
  - Respuesta del admin

### 5. Logs del Sistema (Futuro)
- Errores
- Logins fallidos
- Actividad de usuarios
- Cambios importantes

### 6. Configuración Global (Futuro)
- Nombre del SaaS
- Logo
- Modo mantenimiento
- Configuración de emails

---

## 🔐 PERMISOS Y ROLES

### Super Admin (Tú)
- Acceso total al sistema
- Panel de super admin
- Gestión de empresas
- Gestión de usuarios
- Ver tickets de soporte
- Impersonar usuarios

### Admin de Empresa
- Acceso a configuración de su empresa
- Gestión de usuarios de su empresa
- Ver/editar perfil de empresa
- Enviar tickets de soporte

### Usuario Normal
- Acceso según permisos configurados
- No puede acceder a configuración (a menos que tenga permiso)
- Puede enviar tickets de soporte

---

## 🎨 ESTRUCTURA DE URLs

### Cliente
```
/settings/                          # Página principal de configuración
/settings/company/                  # Perfil de empresa
/settings/users/                    # Gestión de usuarios
/settings/users/create/             # Crear usuario
/settings/users/<id>/edit/          # Editar usuario
/settings/users/<id>/delete/        # Eliminar usuario
/settings/security/                 # Seguridad
/settings/support/                  # Soporte
/settings/support/create/           # Crear ticket
/settings/support/<id>/             # Ver ticket
```

### Super Admin
```
/superadmin/dashboard/              # Dashboard principal
/superadmin/companies/              # Lista de empresas
/superadmin/companies/create/       # Crear empresa
/superadmin/companies/<id>/         # Detalles de empresa
/superadmin/companies/<id>/edit/    # Editar empresa
/superadmin/companies/<id>/suspend/ # Suspender empresa
/superadmin/companies/<id>/delete/  # Eliminar empresa
/superadmin/users/                  # Lista de usuarios
/superadmin/users/<id>/             # Detalles de usuario
/superadmin/users/<id>/impersonate/ # Impersonar usuario
/superadmin/tickets/                # Tickets de soporte
/superadmin/tickets/<id>/           # Ver ticket
/superadmin/tickets/<id>/respond/   # Responder ticket
```

---

## 📊 MODELOS

### Company
- name
- industry (choices)
- description
- location
- api_key
- is_active
- created_at
- updated_at

### User
- (campos de AbstractUser)
- company (FK)
- is_superadmin
- is_company_admin
- can_send_emails
- can_view_contacts
- can_view_deals
- can_view_pipeline
- can_view_settings
- can_manage_users
- can_view_integrations
- last_activity

### SupportTicket
- user (FK)
- company (FK)
- category (choices: security, improvement, integration, other)
- subject
- message
- status (choices: open, in_progress, resolved, closed)
- admin_response
- created_at
- updated_at
- resolved_at

---

## ✅ PRÓXIMOS PASOS

1. ✅ Actualizar modelos
2. ✅ Crear migraciones
3. ⏳ Crear vistas de Configuración del cliente
4. ⏳ Crear templates de Configuración del cliente
5. ⏳ Rediseñar panel Super Admin
6. ⏳ Implementar impersonar usuario
7. ⏳ Crear sistema de tickets
8. ⏳ Probar todo
