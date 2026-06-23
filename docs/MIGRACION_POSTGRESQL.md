# Migración de SQLite a PostgreSQL

## 🎯 Por qué PostgreSQL

Tu ERP es **multi-tenant** con integraciones externas. PostgreSQL es necesario porque:

1. **Concurrencia**: Múltiples clientes accediendo simultáneamente
2. **Integraciones**: Webhooks y APIs recibiendo datos constantemente
3. **Escalabilidad**: Soporta miles de leads y contactos sin degradación
4. **Transacciones**: ACID completo para operaciones críticas
5. **JSON nativo**: Mejor manejo del campo `metadata` en Leads
6. **Producción**: Estándar de la industria para SaaS

SQLite es excelente para desarrollo, pero PostgreSQL es esencial para producción multi-tenant.

---

## 📋 Pasos de Migración

### 1. Instalar PostgreSQL

**Windows:**
- Descargar: https://www.postgresql.org/download/windows/
- Instalar PostgreSQL 15 o superior
- Durante instalación, configurar:
  - Usuario: `postgres`
  - Contraseña: `postgres` (o la que prefieras)
  - Puerto: `5432`

**Verificar instalación:**
```bash
psql --version
```

---

### 2. Crear Base de Datos

**Opción A: Desde pgAdmin (GUI)**
1. Abrir pgAdmin
2. Click derecho en "Databases" → Create → Database
3. Nombre: `erp_db`
4. Owner: `postgres`
5. Save

**Opción B: Desde terminal**
```bash
# Conectar a PostgreSQL
psql -U postgres

# Crear base de datos
CREATE DATABASE erp_db;

# Salir
\q
```

**Opción C: Ejecutar script SQL**
```bash
psql -U postgres -f create_postgres_db.sql
```

---

### 3. Actualizar Configuración

✅ **Ya actualizado en `core/settings.py`:**

```python
DATABASES = {
    'default': env.db('DATABASE_URL', 
        default='postgresql://postgres:postgres@localhost:5432/erp_db')
}
```

**Si usas contraseña diferente**, crea archivo `.env`:
```
DATABASE_URL=postgresql://postgres:TU_PASSWORD@localhost:5432/erp_db
```

---

### 4. Instalar Dependencias

✅ **Ya actualizado en `requirements.txt`:**

```bash
pip install psycopg2-binary djangorestframework django-cors-headers
```

---

### 5. Migrar Estructura

```bash
# Aplicar todas las migraciones a PostgreSQL
python manage.py migrate
```

Esto creará todas las tablas en PostgreSQL:
- accounts_company
- accounts_user
- crm_contact
- crm_lead
- crm_deal
- crm_activity
- crm_task
- crm_pipeline
- crm_stage
- crm_messagetemplate

---

### 6. Migrar Datos de SQLite (Opcional)

Si tienes datos importantes en SQLite que quieres conservar:

**Opción A: Dump manual**
```bash
# 1. Exportar datos de SQLite
python manage.py dumpdata --natural-foreign --natural-primary -e contenttypes -e auth.Permission > data.json

# 2. Cambiar a PostgreSQL en settings.py

# 3. Aplicar migraciones
python manage.py migrate

# 4. Importar datos
python manage.py loaddata data.json
```

**Opción B: Recrear datos de prueba**
```bash
# Ejecutar script de setup
python setup_data.py
```

---

### 7. Crear Superusuario

```bash
python manage.py createsuperuser
```

Datos sugeridos:
- Username: `admin`
- Email: `admin@example.com`
- Password: (tu elección)

---

### 8. Verificar Funcionamiento

```bash
# Iniciar servidor
python manage.py runserver

# Probar en navegador
http://localhost:8000
```

**Verificar:**
- ✅ Login funciona
- ✅ Dashboard carga
- ✅ Crear contacto
- ✅ Crear lead desde API
- ✅ Integraciones muestra API Key

---

## 🔧 Configuración Avanzada

### Optimización para Producción

Agregar a `settings.py`:

```python
# Optimizaciones PostgreSQL
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'erp_db',
        'USER': 'postgres',
        'PASSWORD': 'postgres',
        'HOST': 'localhost',
        'PORT': '5432',
        'OPTIONS': {
            'connect_timeout': 10,
        },
        'CONN_MAX_AGE': 600,  # Conexiones persistentes
    }
}
```

### Índices para Performance

```python
# En crm/models.py, agregar a los modelos:

class Lead(TenantModel):
    # ... campos existentes ...
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['company', 'status']),
            models.Index(fields=['company', 'source']),
            models.Index(fields=['email']),
            models.Index(fields=['-created_at']),
        ]

class Contact(TenantModel):
    # ... campos existentes ...
    
    class Meta:
        indexes = [
            models.Index(fields=['company', 'status']),
            models.Index(fields=['email']),
            models.Index(fields=['phone']),
        ]
```

Luego:
```bash
python manage.py makemigrations
python manage.py migrate
```

---

## 🚀 Ventajas Obtenidas

### Antes (SQLite):
- ❌ Bloqueos con múltiples usuarios
- ❌ Lento con +10,000 registros
- ❌ No soporta concurrencia real
- ❌ Problemas con webhooks simultáneos

### Ahora (PostgreSQL):
- ✅ Miles de usuarios concurrentes
- ✅ Millones de registros sin degradación
- ✅ Transacciones ACID completas
- ✅ Webhooks e integraciones sin problemas
- ✅ Backups y replicación nativos
- ✅ Full-text search nativo
- ✅ JSON queries optimizadas

---

## 📊 Monitoreo

### Ver conexiones activas:
```sql
SELECT * FROM pg_stat_activity WHERE datname = 'erp_db';
```

### Ver tamaño de base de datos:
```sql
SELECT pg_size_pretty(pg_database_size('erp_db'));
```

### Ver tablas más grandes:
```sql
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

---

## 🔐 Seguridad

### Crear usuario específico para producción:

```sql
-- Crear usuario
CREATE USER crm_user WITH PASSWORD 'password_seguro_aqui';

-- Dar permisos
GRANT ALL PRIVILEGES ON DATABASE erp_db TO crm_user;

-- Conectar a la base de datos
\c erp_db

-- Dar permisos en el schema
GRANT ALL ON SCHEMA public TO crm_user;
GRANT ALL ON ALL TABLES IN SCHEMA public TO crm_user;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO crm_user;
```

Actualizar `.env`:
```
DATABASE_URL=postgresql://crm_user:password_seguro_aqui@localhost:5432/erp_db
```

---

## 🆘 Troubleshooting

### Error: "could not connect to server"
```bash
# Verificar que PostgreSQL esté corriendo
# Windows: Services → PostgreSQL
# O desde terminal:
pg_ctl status
```

### Error: "password authentication failed"
```bash
# Verificar credenciales en settings.py o .env
# Resetear password de postgres:
psql -U postgres
ALTER USER postgres PASSWORD 'nueva_password';
```

### Error: "database does not exist"
```bash
# Crear la base de datos
psql -U postgres
CREATE DATABASE erp_db;
```

### Error de migración
```bash
# Borrar migraciones y empezar de cero
python manage.py migrate --fake-initial
```

---

## 📝 Checklist Final

- [ ] PostgreSQL instalado y corriendo
- [ ] Base de datos `erp_db` creada
- [ ] `psycopg2-binary` instalado
- [ ] `settings.py` actualizado
- [ ] Migraciones aplicadas (`python manage.py migrate`)
- [ ] Superusuario creado
- [ ] Servidor funciona (`python manage.py runserver`)
- [ ] API de leads funciona
- [ ] Datos de prueba cargados (opcional)

---

## 🎯 Próximos Pasos

1. **Backups automáticos**
   ```bash
   pg_dump -U postgres erp_db > backup.sql
   ```

2. **Replicación** (para alta disponibilidad)

3. **Conexión pooling** (PgBouncer)

4. **Monitoreo** (pg_stat_statements)

5. **Optimización de queries** (EXPLAIN ANALYZE)

---

Tu ERP ahora está listo para escalar a cientos de clientes con miles de leads diarios. 🚀
