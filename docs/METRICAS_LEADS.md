# Métricas y Análisis de Leads por Canal

## 📊 Análisis de Leads por Source

Con los campos `source` y `metadata` implementados, puedes generar reportes poderosos para tus clientes.

---

## Consultas SQL Útiles

### 1. Leads por Canal (Últimos 30 días)

```sql
SELECT 
    source,
    COUNT(*) as total_leads,
    COUNT(*) * 100.0 / SUM(COUNT(*)) OVER() as porcentaje
FROM crm_lead
WHERE created_at >= datetime('now', '-30 days')
GROUP BY source
ORDER BY total_leads DESC;
```

### 2. Leads por Campaña (desde metadata)

```sql
SELECT 
    json_extract(metadata, '$.campaign') as campaign,
    COUNT(*) as total_leads,
    source
FROM crm_lead
WHERE metadata IS NOT NULL
    AND json_extract(metadata, '$.campaign') IS NOT NULL
GROUP BY campaign, source
ORDER BY total_leads DESC;
```

### 3. Leads por Página de Origen

```sql
SELECT 
    json_extract(metadata, '$.page') as page,
    COUNT(*) as total_leads
FROM crm_lead
WHERE metadata IS NOT NULL
    AND json_extract(metadata, '$.page') IS NOT NULL
GROUP BY page
ORDER BY total_leads DESC;
```

---

## Consultas Django ORM

### 1. Leads por Canal

```python
from django.db.models import Count
from crm.models import Lead

# Leads por source
leads_by_source = Lead.objects.values('source').annotate(
    total=Count('id')
).order_by('-total')

for item in leads_by_source:
    print(f"{item['source']}: {item['total']} leads")
```

### 2. Leads del Último Mes por Canal

```python
from django.db.models import Count
from django.utils import timezone
from datetime import timedelta
from crm.models import Lead

last_month = timezone.now() - timedelta(days=30)

leads_by_source = Lead.objects.filter(
    created_at__gte=last_month
).values('source').annotate(
    total=Count('id')
).order_by('-total')

print("Leads últimos 30 días:")
for item in leads_by_source:
    print(f"  {item['source']}: {item['total']} leads")
```

### 3. Extraer Datos de Metadata

```python
from crm.models import Lead

# Leads con campaña específica
leads_campaign = Lead.objects.filter(
    metadata__campaign='google_ads_verano'
)

# Leads desde una página específica
leads_page = Lead.objects.filter(
    metadata__page='/contacto'
)

# Leads con UTM source = google
leads_google = Lead.objects.filter(
    metadata__utm_source='google'
)
```

---

## Dashboard de Métricas (Ejemplo para Vista Django)

```python
# views.py
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
from crm.models import Lead

def leads_dashboard(request):
    company = request.company
    last_30_days = timezone.now() - timedelta(days=30)
    
    # Total de leads
    total_leads = Lead.objects.filter(company=company).count()
    
    # Leads últimos 30 días
    recent_leads = Lead.objects.filter(
        company=company,
        created_at__gte=last_30_days
    ).count()
    
    # Leads por canal
    leads_by_source = Lead.objects.filter(
        company=company,
        created_at__gte=last_30_days
    ).values('source').annotate(
        total=Count('id')
    ).order_by('-total')
    
    # Top 5 campañas
    # Nota: Esto requiere PostgreSQL para funcionar correctamente
    # En SQLite es más limitado
    
    context = {
        'total_leads': total_leads,
        'recent_leads': recent_leads,
        'leads_by_source': leads_by_source,
    }
    
    return render(request, 'crm/leads_dashboard.html', context)
```

---

## Visualización con Chart.js (Frontend)

```html
<!-- leads_dashboard.html -->
<div class="container">
    <h2>Leads por Canal (Últimos 30 días)</h2>
    <canvas id="leadsChart"></canvas>
</div>

<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
const ctx = document.getElementById('leadsChart').getContext('2d');

// Datos desde Django (pasados al template)
const leadsData = {
    labels: [
        {% for item in leads_by_source %}
            '{{ item.source }}',
        {% endfor %}
    ],
    datasets: [{
        label: 'Leads',
        data: [
            {% for item in leads_by_source %}
                {{ item.total }},
            {% endfor %}
        ],
        backgroundColor: [
            '#10b981', // website
            '#3b82f6', // facebook
            '#ec4899', // instagram
            '#f59e0b', // mercadolibre
            '#22c55e', // whatsapp
            '#8b5cf6', // landing
            '#ef4444', // google_ads
            '#06b6d4', // referral
            '#6b7280', // other
        ]
    }]
};

const chart = new Chart(ctx, {
    type: 'doughnut',
    data: leadsData,
    options: {
        responsive: true,
        plugins: {
            legend: {
                position: 'bottom',
            },
            title: {
                display: true,
                text: 'Distribución de Leads por Canal'
            }
        }
    }
});
</script>
```

---

## Reportes para Clientes

### Ejemplo de Reporte Mensual

```python
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.db.models import Count
from datetime import datetime, timedelta
from crm.models import Lead

def send_monthly_report(company):
    """Enviar reporte mensual de leads a la empresa"""
    
    # Calcular período
    today = datetime.now()
    first_day = today.replace(day=1)
    last_month = first_day - timedelta(days=1)
    first_day_last_month = last_month.replace(day=1)
    
    # Obtener leads del mes pasado
    leads = Lead.objects.filter(
        company=company,
        created_at__gte=first_day_last_month,
        created_at__lt=first_day
    )
    
    # Estadísticas
    total_leads = leads.count()
    leads_by_source = leads.values('source').annotate(
        total=Count('id')
    ).order_by('-total')
    
    # Renderizar email
    context = {
        'company': company,
        'month': last_month.strftime('%B %Y'),
        'total_leads': total_leads,
        'leads_by_source': leads_by_source,
    }
    
    html_message = render_to_string('emails/monthly_report.html', context)
    
    # Enviar email
    send_mail(
        subject=f'Reporte de Leads - {last_month.strftime("%B %Y")}',
        message='',
        html_message=html_message,
        from_email='noreply@tuempresa.com',
        recipient_list=[company.email],
    )
```

---

## Mejores Prácticas para Metadata

### 1. Tracking de UTM Parameters

```javascript
// Capturar UTM params automáticamente
function getUtmParams() {
    const urlParams = new URLSearchParams(window.location.search);
    return {
        utm_source: urlParams.get('utm_source'),
        utm_medium: urlParams.get('utm_medium'),
        utm_campaign: urlParams.get('utm_campaign'),
        utm_term: urlParams.get('utm_term'),
        utm_content: urlParams.get('utm_content')
    };
}

// Enviar con el lead
const metadata = {
    page: window.location.pathname,
    ...getUtmParams(),
    referrer: document.referrer
};

fetch('https://tuempresa.com/api/leads/', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'x-api-key': API_KEY
    },
    body: JSON.stringify({
        name: formData.name,
        email: formData.email,
        phone: formData.phone,
        message: formData.message,
        source: 'landing',
        metadata: metadata
    })
});
```

### 2. Tracking de Eventos de Google Analytics

```javascript
// Enviar evento a GA cuando se captura un lead
gtag('event', 'lead_captured', {
    'event_category': 'Lead',
    'event_label': formData.source,
    'value': 1
});
```

### 3. Estructura Recomendada de Metadata

```json
{
  "page": "/contacto",
  "campaign": "verano_2024",
  "utm_source": "google",
  "utm_medium": "cpc",
  "utm_campaign": "verano_promo",
  "utm_term": "servicios+marketing",
  "utm_content": "banner_principal",
  "referrer": "https://google.com",
  "device": "mobile",
  "browser": "Chrome"
}
```

---

## KPIs Importantes

### Métricas a Monitorear

1. **Total de Leads por Canal**
   - ¿Qué canal trae más leads?

2. **Costo por Lead (CPL)**
   - Inversión en ads / Leads generados

3. **Tasa de Conversión por Canal**
   - Leads que se convierten en clientes

4. **Tiempo de Respuesta**
   - ¿Cuánto tardas en contactar al lead?

5. **ROI por Canal**
   - ¿Qué canal genera más ingresos?

---

## Exportar Leads a CSV

```python
import csv
from django.http import HttpResponse
from crm.models import Lead

def export_leads_csv(request):
    company = request.company
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="leads.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Nombre', 'Email', 'Teléfono', 'Origen', 'Fecha', 'Campaña', 'Página'])
    
    leads = Lead.objects.filter(company=company).order_by('-created_at')
    
    for lead in leads:
        campaign = lead.metadata.get('campaign', '') if lead.metadata else ''
        page = lead.metadata.get('page', '') if lead.metadata else ''
        
        writer.writerow([
            lead.name,
            lead.email,
            lead.phone or '',
            lead.get_source_display(),
            lead.created_at.strftime('%Y-%m-%d %H:%M'),
            campaign,
            page
        ])
    
    return response
```

---

## Conclusión

Con `source` y `metadata` implementados, tu ERP puede:

✅ Rastrear de dónde vienen los leads  
✅ Medir ROI por canal de marketing  
✅ Optimizar campañas basándose en datos  
✅ Generar reportes automáticos para clientes  
✅ Tomar decisiones basadas en métricas reales  

Esto convierte tu ERP en una herramienta de **marketing intelligence** profesional. 🚀
