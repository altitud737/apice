# API de Captura de Leads - Ejemplos de Uso

## Endpoint
```
POST https://tu-dominio.com/api/leads/
```

## Autenticación
Todas las peticiones deben incluir el header `x-api-key` con la API Key de la empresa.

---

## Ejemplo 1: Request con cURL

```bash
curl -X POST https://tu-dominio.com/api/leads/ \
  -H "Content-Type: application/json" \
  -H "x-api-key: TU_API_KEY_AQUI" \
  -d '{
    "name": "Juan Perez",
    "email": "juan@gmail.com",
    "phone": "1133334444",
    "message": "Quiero más información sobre sus servicios",
    "source": "facebook",
    "metadata": {
      "page": "/contacto",
      "campaign": "verano_2024",
      "utm_source": "facebook",
      "utm_medium": "cpc"
    }
  }'
```

### Respuesta exitosa (201 Created):
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

## Ejemplo 2: Formulario HTML con JavaScript (fetch)

```html
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Formulario de Contacto</title>
    <style>
        .form-container {
            max-width: 500px;
            margin: 50px auto;
            padding: 20px;
            border: 1px solid #ddd;
            border-radius: 8px;
        }
        .form-group {
            margin-bottom: 15px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
        }
        input, textarea {
            width: 100%;
            padding: 8px;
            border: 1px solid #ccc;
            border-radius: 4px;
        }
        button {
            background-color: #10b981;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }
        button:hover {
            background-color: #059669;
        }
        .message {
            padding: 10px;
            margin-top: 15px;
            border-radius: 4px;
        }
        .success {
            background-color: #d1fae5;
            color: #065f46;
        }
        .error {
            background-color: #fee2e2;
            color: #991b1b;
        }
    </style>
</head>
<body>
    <div class="form-container">
        <h2>Contáctanos</h2>
        <form id="contactForm">
            <div class="form-group">
                <label for="name">Nombre *</label>
                <input type="text" id="name" name="name" required>
            </div>
            
            <div class="form-group">
                <label for="email">Email *</label>
                <input type="email" id="email" name="email" required>
            </div>
            
            <div class="form-group">
                <label for="phone">Teléfono</label>
                <input type="tel" id="phone" name="phone">
            </div>
            
            <div class="form-group">
                <label for="message">Mensaje</label>
                <textarea id="message" name="message" rows="4"></textarea>
            </div>
            
            <button type="submit">Enviar</button>
        </form>
        
        <div id="responseMessage"></div>
    </div>

    <script>
        // IMPORTANTE: Reemplaza con tu API Key real
        const API_KEY = 'TU_API_KEY_AQUI';
        const API_URL = 'https://tu-dominio.com/api/leads/';

        document.getElementById('contactForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = {
                name: document.getElementById('name').value,
                email: document.getElementById('email').value,
                phone: document.getElementById('phone').value,
                message: document.getElementById('message').value
            };
            
            const messageDiv = document.getElementById('responseMessage');
            messageDiv.innerHTML = 'Enviando...';
            
            try {
                const response = await fetch(API_URL, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'x-api-key': API_KEY
                    },
                    body: JSON.stringify(formData)
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    messageDiv.className = 'message success';
                    messageDiv.innerHTML = '✓ ' + data.message + '<br>Nos pondremos en contacto pronto.';
                    document.getElementById('contactForm').reset();
                } else {
                    messageDiv.className = 'message error';
                    messageDiv.innerHTML = '✗ Error: ' + (data.error || 'No se pudo enviar el formulario');
                }
            } catch (error) {
                messageDiv.className = 'message error';
                messageDiv.innerHTML = '✗ Error de conexión. Por favor intenta nuevamente.';
                console.error('Error:', error);
            }
        });
    </script>
</body>
</html>
```

---

## Ejemplo 3: React Component

```jsx
import React, { useState } from 'react';

const API_KEY = 'TU_API_KEY_AQUI';
const API_URL = 'https://tu-dominio.com/api/leads/';

function ContactForm() {
    const [formData, setFormData] = useState({
        name: '',
        email: '',
        phone: '',
        message: ''
    });
    const [status, setStatus] = useState({ type: '', message: '' });
    const [loading, setLoading] = useState(false);

    const handleChange = (e) => {
        setFormData({
            ...formData,
            [e.target.name]: e.target.value
        });
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setStatus({ type: '', message: '' });

        try {
            const response = await fetch(API_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'x-api-key': API_KEY
                },
                body: JSON.stringify(formData)
            });

            const data = await response.json();

            if (response.ok) {
                setStatus({ type: 'success', message: data.message });
                setFormData({ name: '', email: '', phone: '', message: '' });
            } else {
                setStatus({ type: 'error', message: data.error || 'Error al enviar' });
            }
        } catch (error) {
            setStatus({ type: 'error', message: 'Error de conexión' });
        } finally {
            setLoading(false);
        }
    };

    return (
        <form onSubmit={handleSubmit}>
            <input
                type="text"
                name="name"
                value={formData.name}
                onChange={handleChange}
                placeholder="Nombre"
                required
            />
            <input
                type="email"
                name="email"
                value={formData.email}
                onChange={handleChange}
                placeholder="Email"
                required
            />
            <input
                type="tel"
                name="phone"
                value={formData.phone}
                onChange={handleChange}
                placeholder="Teléfono"
            />
            <textarea
                name="message"
                value={formData.message}
                onChange={handleChange}
                placeholder="Mensaje"
            />
            <button type="submit" disabled={loading}>
                {loading ? 'Enviando...' : 'Enviar'}
            </button>
            {status.message && (
                <div className={status.type}>{status.message}</div>
            )}
        </form>
    );
}

export default ContactForm;
```

---

## Respuestas de Error

### Error 401 - API Key faltante:
```json
{
  "error": "API Key requerida. Incluya el header x-api-key"
}
```

### Error 401 - API Key inválida:
```json
{
  "error": "API Key inválida"
}
```

### Error 400 - Datos inválidos:
```json
{
  "error": "Datos inválidos",
  "details": {
    "email": ["Este campo es requerido"],
    "name": ["Este campo es requerido"]
  }
}
```

---

## Cómo Obtener tu API Key

1. Inicia sesión en el ERP como administrador
2. Ve al panel de administración de Django: `/admin/`
3. Busca tu empresa en "Companies"
4. Copia el valor del campo "Api key"
5. Usa esa API Key en el header `x-api-key` de tus peticiones

**IMPORTANTE:** Mantén tu API Key segura y no la compartas públicamente.

---

## Campos del Lead

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| name | string | Sí | Nombre del contacto |
| email | string | Sí | Email del contacto |
| phone | string | No | Teléfono del contacto |
| message | string | No | Mensaje o consulta |
| source | string | No | Origen del lead (default: "website") |
| metadata | object | No | Datos adicionales (JSON) |

### Valores válidos para `source`:
- `website` - Sitio Web (default)
- `facebook` - Facebook
- `instagram` - Instagram
- `mercadolibre` - MercadoLibre
- `whatsapp` - WhatsApp
- `landing` - Landing Page
- `google_ads` - Google Ads
- `referral` - Referido
- `other` - Otro

### Estructura de `metadata` (opcional):
```json
{
  "page": "/contacto",
  "campaign": "google_ads_verano",
  "utm_source": "google",
  "utm_medium": "cpc",
  "utm_campaign": "verano2024"
}
```

**Nota:** El sistema agrega automáticamente `ip` y `user_agent` al metadata.

---

## Testing

Para probar el endpoint localmente:

```bash
# Primero obtén la API Key de tu empresa desde el admin
# Luego ejecuta:

curl -X POST http://localhost:8000/api/leads/ \
  -H "Content-Type: application/json" \
  -H "x-api-key: tu-api-key-aqui" \
  -d '{
    "name": "Test User",
    "email": "test@example.com",
    "phone": "1234567890",
    "message": "Este es un lead de prueba"
  }'
```
