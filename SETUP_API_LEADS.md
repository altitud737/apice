# Configuración del Sistema de Captura de Leads

## 📋 Resumen

Este sistema permite capturar leads desde formularios web externos y registrarlos automáticamente en el Apice. Cada empresa cliente tiene su propia API Key para autenticación.

---

## 🚀 Instalación

### 1. Instalar dependencias

```bash
pip install djangorestframework django-cors-headers
```

### 2. Crear migraciones

```bash
python manage.py makemigrations accounts
python manage.py makemigrations Apice
python manage.py migrate
```

### 3. Generar API Keys para empresas existentes

```bash
python manage.py shell < generate_api_keys.py
```

Este script generará API Keys únicas para todas las empresas que aún no tienen una.

---

## 🔑 Obtener API Key de una Empresa

### Opción 1: Desde el Admin de Django

1. Accede a `/admin/`
2. Ve a **Accounts → Companies**
3. Selecciona la empresa
4. Copia el valor del campo **Api key**

### Opción 2: Desde el Shell de Django

```python
python manage.py shell

from accounts.models import Company

# Listar todas las empresas con sus API Keys
for company in Company.objects.all():
    print(f"{company.name}: {company.api_key}")

# Obtener API Key de una empresa específica
company = Company.objects.get(name="Nombre de la Empresa")
print(company.api_key)
```

---

## 📡 Endpoint de la API

### URL
```
POST /api/leads/
```

### Headers requeridos
```
Content-Type: application/json
x-api-key: [API_KEY_DE_LA_EMPRESA]
```

### Body (JSON)
```json
{
  "name": "Juan Perez",
  "email": "juan@gmail.com",
  "phone": "1133334444",
  "message": "Quiero más información"
}
```

### Respuesta exitosa (201)
```json
{
  "success": true,
  "message": "Lead registrado exitosamente",
  "lead": {
    "id": 1,
    "name": "Juan Perez",
    "email": "juan@gmail.com",
    "created_at": "2024-03-09T18:30:00.000Z"
  }
}
```

---

## 🌐 Configuración en Sitios Web de Clientes

### Ejemplo básico con HTML + JavaScript

```html
<form id="contactForm">
    <input type="text" name="name" placeholder="Nombre" required>
    <input type="email" name="email" placeholder="Email" required>
    <input type="tel" name="phone" placeholder="Teléfono">
    <textarea name="message" placeholder="Mensaje"></textarea>
    <button type="submit">Enviar</button>
</form>

<script>
const API_KEY = 'API_KEY_DEL_CLIENTE_AQUI';
const API_URL = 'https://tu-apice.com/api/leads/';

document.getElementById('contactForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    const data = Object.fromEntries(formData);
    
    try {
        const response = await fetch(API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'x-api-key': API_KEY
            },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            alert('¡Gracias! Nos pondremos en contacto pronto.');
            e.target.reset();
        } else {
            alert('Error: ' + result.error);
        }
    } catch (error) {
        alert('Error de conexión');
    }
});
</script>
```

---

## 🔒 Seguridad

### CORS
El sistema está configurado para aceptar peticiones desde cualquier origen. Esto es necesario para que los formularios web externos puedan enviar datos.

### Autenticación
- Cada petición debe incluir el header `x-api-key`
- Las API Keys son únicas por empresa
- Las API Keys se generan automáticamente al crear una empresa
- No se requiere CSRF token para este endpoint

### Validaciones
- Email obligatorio y validado
- Nombre obligatorio
- Teléfono y mensaje opcionales
- Todos los datos son sanitizados antes de guardar

---

## 📊 Ver Leads en el Apice

### Desde el Admin
1. Accede a `/admin/`
2. Ve a **Apice → Leads**
3. Filtra por empresa, fuente o fecha

### Campos del Lead
- **Name**: Nombre del contacto
- **Email**: Email del contacto
- **Phone**: Teléfono (opcional)
- **Message**: Mensaje o consulta (opcional)
- **Source**: Origen del lead (default: "website")
- **Company**: Empresa a la que pertenece
- **Created at**: Fecha y hora de creación

---

## 🧪 Testing

### Test local con cURL

```bash
# Reemplaza API_KEY_AQUI con una API Key real
curl -X POST http://localhost:8000/api/leads/ \
  -H "Content-Type: application/json" \
  -H "x-api-key: API_KEY_AQUI" \
  -d '{
    "name": "Test User",
    "email": "test@example.com",
    "phone": "1234567890",
    "message": "Lead de prueba"
  }'
```

### Test con Postman

1. Método: **POST**
2. URL: `http://localhost:8000/api/leads/`
3. Headers:
   - `Content-Type: application/json`
   - `x-api-key: [TU_API_KEY]`
4. Body (raw JSON):
```json
{
  "name": "Test User",
  "email": "test@example.com",
  "phone": "1234567890",
  "message": "Lead de prueba"
}
```

---

## 🔧 Troubleshooting

### Error: "API Key requerida"
- Verifica que estés enviando el header `x-api-key`
- El nombre del header debe ser exactamente `x-api-key` (minúsculas)

### Error: "API Key inválida"
- Verifica que la API Key sea correcta
- Asegúrate de copiar la API Key completa sin espacios

### Error: "Datos inválidos"
- Verifica que `name` y `email` estén presentes
- Verifica que el email tenga formato válido

### Error de CORS
- Verifica que `corsheaders` esté instalado
- Verifica que `CORS_ALLOW_ALL_ORIGINS = True` esté en settings.py

---

## 📝 Workflow Completo

1. **Crear empresa en Apice**
   - Se genera automáticamente una API Key única

2. **Desarrollar sitio web del cliente**
   - Incluir formulario de contacto
   - Configurar JavaScript para enviar a `/api/leads/`
   - Usar la API Key de la empresa en el header

3. **Usuario completa formulario**
   - Datos se envían al Apice vía POST
   - Lead se registra automáticamente
   - Usuario recibe confirmación

4. **Ver leads en Apice**
   - Acceder al admin o crear vista personalizada
   - Leads filtrados por empresa
   - Convertir leads en contactos/oportunidades

---

## 🎯 Próximos Pasos Sugeridos

- [ ] Crear vista en el Apice para gestionar leads
- [ ] Agregar notificaciones por email cuando llega un lead
- [ ] Implementar conversión de lead a contacto
- [ ] Agregar campos personalizados según necesidad
- [ ] Implementar rate limiting para prevenir spam
- [ ] Agregar webhook para integraciones externas

---

## 📚 Archivos Creados

- `accounts/models.py` - Campo `api_key` agregado a Company
- `apice/models.py` - Modelo Lead
- `apice/serializers.py` - Serializer para Lead
- `apice/api_views.py` - Vista API para crear leads
- `apice/urls.py` - URL del endpoint
- `apice/admin.py` - Registro de Lead en admin
- `core/settings.py` - Configuración CORS y REST Framework
- `generate_api_keys.py` - Script para generar API Keys
- `API_LEADS_EXAMPLES.md` - Ejemplos de uso
- `SETUP_API_LEADS.md` - Este archivo

---

## ✅ Checklist de Implementación

- [x] Modelo Company con api_key
- [x] Modelo Lead
- [x] Serializer para Lead
- [x] API View para crear leads
- [x] URL configurada
- [x] CORS configurado
- [x] Admin configurado
- [x] Documentación creada
- [ ] Migraciones ejecutadas
- [ ] API Keys generadas
- [ ] Endpoint testeado
- [ ] Formulario web implementado
