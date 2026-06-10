# Arquitectura Lead → Contact en el Apice

## 📋 Resumen

Este Apice implementa una separación clara entre **Leads** y **Contactos**, siguiendo las mejores prácticas de CRMs profesionales como HubSpot, Pipedrive y Salesforce.

### Diferencia Clave

- **Lead**: Persona que mostró interés (formulario, integración externa)
- **Contact**: Persona calificada como potencial cliente

```
Lead (automático) → Calificación → Contact (manual) → Deal → Cliente
```

---

## 🏗️ Modelos Implementados

### 1. Modelo Lead

**Ubicación:** `apice/models.py`

```python
class Lead(TenantModel):
    SOURCE_CHOICES = [
        ('website', 'Sitio Web'),
        ('facebook', 'Facebook'),
        ('instagram', 'Instagram'),
        ('mercadolibre', 'MercadoLibre'),
        ('whatsapp', 'WhatsApp'),
        ('landing', 'Landing Page'),
        ('google_ads', 'Google Ads'),
        ('referral', 'Referido'),
        ('other', 'Otro'),
    ]
    
    STATUS_CHOICES = [
        ('new', 'Nuevo'),
        ('contacted', 'Contactado'),
        ('qualified', 'Calificado'),
        ('converted', 'Convertido'),
        ('lost', 'Perdido'),
    ]
    
    # Campos básicos
    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=50, blank=True, null=True)
    message = models.TextField(blank=True, null=True)
    
    # Tracking
    source = models.CharField(max_length=100, choices=SOURCE_CHOICES, default='website')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    metadata = models.JSONField(null=True, blank=True)
    
    # Conversión
    converted_to_contact = models.ForeignKey(Contact, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Multi-tenant (heredado de TenantModel)
    company = models.ForeignKey('accounts.Company', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
```

**Características:**
- ✅ Multi-tenant (cada lead pertenece a una empresa)
- ✅ Source tracking (de dónde vino el lead)
- ✅ Status lifecycle (new → contacted → qualified → converted/lost)
- ✅ Metadata flexible para datos adicionales
- ✅ Relación con Contact cuando se convierte

---

### 2. Modelo Contact

**Ubicación:** `apice/models.py`

```python
class Contact(TenantModel):
    CONTACT_TYPE_CHOICES = [
        ('persona', 'Persona'),
        ('empresa', 'Empresa'),
    ]
    
    SOURCE_CHOICES = [
        ('website', 'Sitio Web'),
        ('facebook', 'Facebook'),
        ('instagram', 'Instagram'),
        ('mercadolibre', 'MercadoLibre'),
        ('whatsapp', 'WhatsApp'),
        ('landing', 'Landing Page'),
        ('google_ads', 'Google Ads'),
        ('referral', 'Referido'),
        ('manual', 'Manual'),
        ('other', 'Otro'),
    ]
    
    # Datos básicos
    contact_type = models.CharField(max_length=20, choices=CONTACT_TYPE_CHOICES, default='persona')
    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    company_name = models.CharField(max_length=255, blank=True, null=True)
    
    # Apice fields
    status = models.CharField(max_length=50, default='Nuevo')
    interest_level = models.CharField(max_length=50, default='Medio')
    next_action_date = models.DateField(blank=True, null=True)
    source = models.CharField(max_length=100, choices=SOURCE_CHOICES, default='manual')
    
    # Asignación
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    
    # Multi-tenant (heredado de TenantModel)
    company = models.ForeignKey('accounts.Company', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
```

**Características:**
- ✅ Contactos calificados manualmente
- ✅ Tipo de contacto (persona/empresa)
- ✅ Source tracking (origen del contacto)
- ✅ Asignación a vendedor (owner)
- ✅ Relación con Deals y Activities

---

## 🔄 Conversión Lead → Contact

### Función de Conversión

**Ubicación:** `apice/views_leads.py`

```python
@login_required
def convert_lead_to_contact(request, lead_id):
    """Convertir un lead en contacto"""
    company = request.company
    lead = get_object_or_404(Lead, id=lead_id, company=company)
    
    if request.method == 'POST':
        # 1. Crear contacto desde el lead
        contact = Contact.objects.create(
            company=company,
            name=lead.name,
            email=lead.email,
            phone=lead.phone,
            source=lead.source,  # Mantener origen
            status='Nuevo',
            owner=request.user
        )
        
        # 2. Actualizar lead
        lead.status = 'converted'
        lead.converted_to_contact = contact
        lead.save()
        
        # 3. Crear actividad
        Activity.objects.create(
            company=company,
            contact=contact,
            type='Note',
            description=f'Lead convertido a contacto. Mensaje original: {lead.message}',
            user=request.user
        )
        
        messages.success(request, f'Lead "{lead.name}" convertido a contacto exitosamente')
        return redirect('apice:contact_profile', contact_id=contact.id)
    
    return redirect('apice:leads_list')
```

### Proceso de Conversión

1. **Validación**: Verificar que el lead pertenece a la empresa
2. **Creación**: Crear Contact con datos del Lead
3. **Actualización**: Marcar Lead como "converted"
4. **Relación**: Vincular Lead con Contact creado
5. **Actividad**: Registrar conversión en timeline
6. **Redirección**: Llevar al perfil del nuevo contacto

---

## 🚫 Prevención de Duplicados

### Estrategia Implementada

```python
# Antes de convertir, verificar si ya existe un contacto con ese email
def convert_lead_to_contact(request, lead_id):
    company = request.company
    lead = get_object_or_404(Lead, id=lead_id, company=company)
    
    # Verificar duplicados por email
    existing_contact = Contact.objects.filter(
        company=company,
        email__iexact=lead.email
    ).first()
    
    if existing_contact:
        # Actualizar lead para apuntar al contacto existente
        lead.status = 'converted'
        lead.converted_to_contact = existing_contact
        lead.save()
        
        messages.info(request, f'Este lead ya tenía un contacto asociado: {existing_contact.name}')
        return redirect('apice:contact_profile', contact_id=existing_contact.id)
    
    # Si no existe, crear nuevo contacto
    # ... resto del código
```

### Recomendaciones Adicionales

1. **Validación por Email**: Siempre verificar antes de crear
2. **Validación por Teléfono**: Opcional, para casos sin email
3. **Merge de Contactos**: Función futura para unir duplicados
4. **Reglas de Deduplicación**: Configurables por empresa

---

## 📊 Ciclo de Vida del Lead

```
┌─────────┐
│   NEW   │ ← Lead llega desde formulario/integración
└────┬────┘
     │
     ▼
┌─────────────┐
│ CONTACTED   │ ← Vendedor contactó al lead
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ QUALIFIED   │ ← Lead calificado como potencial cliente
└──────┬──────┘
       │
       ├──────────────┐
       │              │
       ▼              ▼
┌───────────┐   ┌─────────┐
│ CONVERTED │   │  LOST   │
└───────────┘   └─────────┘
       │
       ▼
   CONTACT
```

---

## 🎯 Endpoint de Captura de Leads

### API Endpoint

**URL:** `POST /api/leads/`

**Headers:**
```
Content-Type: application/json
x-api-key: {API_KEY_DE_LA_EMPRESA}
```

**Body:**
```json
{
  "name": "Juan Perez",
  "email": "juan@example.com",
  "phone": "1133334444",
  "message": "Quiero más información",
  "source": "website",
  "metadata": {
    "page": "/contacto",
    "campaign": "verano_2024",
    "utm_source": "google"
  }
}
```

**Respuesta (201 Created):**
```json
{
  "success": true,
  "message": "Lead registrado exitosamente",
  "lead": {
    "id": 1,
    "name": "Juan Perez",
    "email": "juan@example.com",
    "source": "website",
    "created_at": "2024-03-09T21:30:00.000Z"
  }
}
```

### Características del Endpoint

- ✅ Autenticación por API Key
- ✅ Multi-tenant automático
- ✅ Rate limiting (60 req/min)
- ✅ Validación de datos
- ✅ Captura automática de IP y user agent
- ✅ CORS habilitado

---

## 🖥️ Panel del Apice

### Estructura del Menú

```
Dashboard
├── Leads          ← Leads sin calificar
├── Contactos      ← Contactos calificados
├── Pipeline       ← Deals en proceso
├── Mensajes       ← Plantillas de WhatsApp
├──────────────
├── Integraciones  ← Configuración de APIs
└── Configuración  ← Settings
```

### Vista de Leads

**URL:** `/leads/`

**Características:**
- Lista de todos los leads
- Filtros por status y source
- Búsqueda por nombre, email, teléfono
- Stats cards (Total, Nuevos, Contactados, Calificados)
- Botón "Convertir" en cada lead
- Icono WhatsApp clickeable
- Columna "Origen" con emojis visuales

### Vista de Contactos

**URL:** `/contacts/`

**Características:**
- Lista de contactos calificados
- Columna "Origen" (de dónde vino)
- Filas clickeables → Perfil del contacto
- Icono WhatsApp clickeable
- Filtros y búsqueda

### Perfil de Contacto

**URL:** `/contacts/<id>/`

**Características:**
- Datos del contacto
- Timeline de actividades
- Deals asociados
- Tareas pendientes
- Agregar notas
- Historial completo

---

## 📁 Estructura de Archivos

```
apice/
├── models.py
│   ├── Lead (modelo principal)
│   └── Contact (modelo principal)
│
├── views_leads.py
│   ├── leads_list()
│   └── convert_lead_to_contact()
│
├── views_contacts.py
│   ├── contact_profile()
│   └── add_contact_note()
│
├── api_views.py
│   └── create_lead() ← Endpoint externo
│
├── serializers.py
│   └── LeadSerializer
│
└── urls.py
    ├── /leads/
    ├── /leads/<id>/convert/
    ├── /contacts/
    ├── /contacts/<id>/
    └── /api/leads/

templates/apice/
├── leads.html
├── contacts.html
└── contact_profile.html
```

---

## 🔐 Multi-Tenant

### TenantModel Base

```python
class TenantModel(models.Model):
    company = models.ForeignKey('accounts.Company', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
```

**Todos los modelos heredan de TenantModel:**
- Lead
- Contact
- Deal
- Activity
- Task
- Pipeline
- Stage

**Middleware automático:**
```python
# accounts/middleware.py
class TenantMiddleware:
    def __call__(self, request):
        if request.user.is_authenticated:
            request.company = request.user.company
        response = self.get_response(request)
        return response
```

**Todas las queries filtran por company:**
```python
leads = Lead.objects.filter(company=request.company)
contacts = Contact.objects.filter(company=request.company)
```

---

## 🎨 Iconos de Origen

### Emojis por Source

```python
def get_source_icon(self):
    icons = {
        'website': '🌐',
        'facebook': '📘',
        'instagram': '📸',
        'mercadolibre': '🛒',
        'whatsapp': '🟢',
        'landing': '📄',
        'google_ads': '📢',
        'referral': '👥',
        'manual': '✍️',
        'other': '📌',
    }
    return icons.get(self.source, '📌')
```

**Uso en templates:**
```django
<span class="text-2xl">{{ lead.get_source_icon }}</span>
<p class="text-xs">{{ lead.get_source_display }}</p>
```

---

## 🚀 Flujo Completo

### 1. Lead llega desde formulario web

```javascript
fetch('https://tu-apice.com/api/leads/', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'x-api-key': 'API_KEY_EMPRESA'
    },
    body: JSON.stringify({
        name: 'Juan Perez',
        email: 'juan@example.com',
        phone: '1133334444',
        message: 'Quiero información',
        source: 'website'
    })
});
```

### 2. Lead aparece en `/leads/`

- Status: "Nuevo"
- Origen: 🌐 Sitio Web
- Botón: "Convertir"

### 3. Vendedor revisa y califica

- Lee el mensaje
- Contacta por WhatsApp (click en icono)
- Decide si es potencial cliente

### 4. Conversión a Contacto

- Click en "Convertir"
- Se crea Contact
- Lead queda como "Convertido"
- Redirección a perfil del contacto

### 5. Contacto en el Apice

- Aparece en `/contacts/`
- Tiene perfil completo
- Puede crear Deals
- Timeline de actividades

---

## ✅ Ventajas de esta Arquitectura

1. **Separación Clara**: Leads ≠ Contactos
2. **Calidad de Datos**: Solo contactos calificados en la base
3. **Tracking Completo**: Origen de cada lead/contacto
4. **Multi-tenant**: Aislamiento por empresa
5. **Escalable**: Fácil agregar integraciones
6. **Profesional**: Igual que CRMs enterprise

---

## 📝 Próximas Mejoras Sugeridas

- [ ] Merge de contactos duplicados
- [ ] Scoring automático de leads
- [ ] Asignación automática de leads a vendedores
- [ ] Notificaciones cuando llega un lead
- [ ] Reportes de conversión Lead → Contact
- [ ] Integración con email marketing
- [ ] Webhooks para eventos de leads

---

## 🔗 Referencias

- Documentación API: `API_LEADS_EXAMPLES.md`
- Métricas: `METRICAS_LEADS.md`
- Setup: `SETUP_API_LEADS.md`
