from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .integrations_mercadolibre_models import MercadoLibreIntegration
from .whatsapp_models import WhatsAppIntegration

@login_required
def integrations(request):
    """Vista principal de integraciones"""
    company = request.company
    
    # Verificar estado de MercadoLibre
    ml_integration = MercadoLibreIntegration.objects.filter(
        company=company,
        is_active=True
    ).first()
    ml_status = 'connected' if ml_integration else 'not_connected'
    ml_url = 'crm:mercadolibre:status' if ml_integration else 'crm:mercadolibre:connect'
    
    # Verificar estado de WhatsApp
    wa_integration = WhatsAppIntegration.objects.filter(
        company=company,
        is_active=True
    ).first()
    wa_status = 'connected' if wa_integration else 'not_connected'
    wa_url = 'crm:whatsapp:settings'
    
    # Estado de integraciones
    integrations_status = [
        {
            'name': 'Formularios Web',
            'icon': '🌐',
            'status': 'connected',
            'description': 'Captura leads desde formularios web',
            'url': 'crm:integrations_web_forms'
        },
        {
            'name': 'MercadoLibre',
            'icon': '�️',
            'status': ml_status,
            'description': 'Gestiona preguntas, mensajes y ventas',
            'url': ml_url
        },
        {
            'name': 'WooCommerce',
            'icon': '�',
            'status': 'not_connected',
            'description': 'Sincroniza clientes y pedidos',
            'url': '#'
        },
        {
            'name': 'WhatsApp Business',
            'icon': '💬',
            'status': wa_status,
            'description': 'Mensajería automática con clientes',
            'url': wa_url
        },
        {
            'name': 'Facebook Leads',
            'icon': '📘',
            'status': 'not_connected',
            'description': 'Importa leads de Facebook',
            'url': '#'
        },
        {
            'name': 'Google Sheets',
            'icon': '📊',
            'status': 'not_connected',
            'description': 'Exporta datos a hojas de cálculo',
            'url': '#'
        },
    ]
    
    context = {
        'integrations': integrations_status,
    }
    
    return render(request, 'crm/integrations.html', context)


@login_required
def integrations_web_forms(request):
    """Vista de integración de formularios web"""
    company = request.company
    
    # URL del endpoint
    base_url = request.build_absolute_uri('/')[:-1]  # Remove trailing slash
    endpoint_url = f"{base_url}/api/leads/"
    
    # Código de ejemplo JavaScript
    js_example = f"""fetch("{endpoint_url}", {{
  method: "POST",
  headers: {{
    "Content-Type": "application/json",
    "x-api-key": "{company.api_key}"
  }},
  body: JSON.stringify({{
    name: "Juan Perez",
    email: "juan@example.com",
    phone: "1133334444",
    message: "Quiero más información",
    source: "website"
  }})
}})
.then(response => response.json())
.then(data => {{
  console.log("Lead registrado:", data);
  alert("¡Gracias! Nos pondremos en contacto pronto.");
}})
.catch(error => {{
  console.error("Error:", error);
}});"""

    # Código de ejemplo cURL
    curl_example = f"""curl -X POST {endpoint_url} \\
  -H "Content-Type: application/json" \\
  -H "x-api-key: {company.api_key}" \\
  -d '{{
    "name": "Juan Perez",
    "email": "juan@example.com",
    "phone": "1133334444",
    "message": "Quiero más información",
    "source": "website"
  }}'"""

    # Código de ejemplo HTML completo
    html_example = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Formulario de Contacto</title>
</head>
<body>
    <form id="contactForm">
        <input type="text" name="name" placeholder="Nombre" required>
        <input type="email" name="email" placeholder="Email" required>
        <input type="tel" name="phone" placeholder="Teléfono">
        <textarea name="message" placeholder="Mensaje"></textarea>
        <button type="submit">Enviar</button>
    </form>

    <script>
    const API_KEY = '{company.api_key}';
    const API_URL = '{endpoint_url}';

    document.getElementById('contactForm').addEventListener('submit', async (e) => {{
        e.preventDefault();
        
        const formData = new FormData(e.target);
        const data = Object.fromEntries(formData);
        data.source = 'website';
        
        try {{
            const response = await fetch(API_URL, {{
                method: 'POST',
                headers: {{
                    'Content-Type': 'application/json',
                    'x-api-key': API_KEY
                }},
                body: JSON.stringify(data)
            }});
            
            const result = await response.json();
            
            if (response.ok) {{
                alert('¡Gracias! Nos pondremos en contacto pronto.');
                e.target.reset();
            }} else {{
                alert('Error: ' + result.error);
            }}
        }} catch (error) {{
            alert('Error de conexión');
        }}
    }});
    </script>
</body>
</html>"""
    
    context = {
        'company': company,
        'endpoint_url': endpoint_url,
        'api_key': company.api_key,
        'js_example': js_example,
        'curl_example': curl_example,
        'html_example': html_example,
    }
    
    return render(request, 'crm/integrations_web_forms.html', context)
