from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Lead, Contact

@login_required
def leads_list(request):
    """Vista para listar todos los leads"""
    company = request.company
    
    # Filtrar por status si se proporciona
    status_filter = request.GET.get('status', '')
    source_filter = request.GET.get('source', '')
    search = request.GET.get('search', '')
    
    leads = Lead.objects.filter(company=company)
    
    if status_filter:
        leads = leads.filter(status=status_filter)
    
    if source_filter:
        leads = leads.filter(source=source_filter)
    
    if search:
        leads = leads.filter(
            Q(name__icontains=search) |
            Q(email__icontains=search) |
            Q(phone__icontains=search)
        )
    
    # Estadísticas
    stats = {
        'total': Lead.objects.filter(company=company).count(),
        'new': Lead.objects.filter(company=company, status='new').count(),
        'contacted': Lead.objects.filter(company=company, status='contacted').count(),
        'qualified': Lead.objects.filter(company=company, status='qualified').count(),
    }
    
    context = {
        'leads': leads,
        'stats': stats,
        'status_filter': status_filter,
        'source_filter': source_filter,
        'search': search,
    }
    
    return render(request, 'crm/leads.html', context)


@login_required
def convert_lead_to_contact(request, lead_id):
    """Convertir un lead en contacto"""
    company = request.company
    lead = get_object_or_404(Lead, id=lead_id, company=company)
    
    if request.method == 'POST':
        # Crear contacto desde el lead
        contact = Contact.objects.create(
            company=company,
            name=lead.name,
            email=lead.email,
            phone=lead.phone,
            source=lead.source,
            status='Nuevo',
            owner=request.user
        )
        
        # Actualizar lead
        lead.status = 'converted'
        lead.converted_to_contact = contact
        lead.save()
        
        # Crear actividad
        Activity.objects.create(
            company=company,
            contact=contact,
            type='Note',
            description=f'Lead convertido a contacto. Mensaje original: {lead.message}',
            user=request.user
        )
        
        messages.success(request, f'Lead "{lead.name}" convertido a contacto exitosamente')
        return redirect('crm:contact_profile', contact_id=contact.id)
    
    return redirect('crm:leads_list')
