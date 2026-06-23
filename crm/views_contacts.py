from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from .models import Contact, Activity, Deal, Task

@login_required
def contact_profile(request, contact_id):
    """Vista de perfil detallado de un contacto"""
    company = request.company
    contact = get_object_or_404(Contact, id=contact_id, company=company)
    
    # Obtener actividades del contacto
    activities = Activity.objects.filter(
        company=company,
        contact=contact
    ).order_by('-created_at')[:20]
    
    # Obtener deals del contacto
    deals = Deal.objects.filter(
        company=company,
        contact=contact
    ).order_by('-created_at')
    
    # Obtener tareas del contacto
    tasks = Task.objects.filter(
        company=company,
        contact=contact,
        completed=False
    ).order_by('due_date')
    
    # Estadísticas
    stats = {
        'total_deals': deals.count(),
        'total_value': deals.aggregate(total=Sum('value'))['total'] or 0,
        'open_tasks': tasks.count(),
        'activities_count': activities.count(),
    }
    
    context = {
        'contact': contact,
        'activities': activities,
        'deals': deals,
        'tasks': tasks,
        'stats': stats,
    }
    
    return render(request, 'crm/contact_profile.html', context)


@login_required
def add_contact_note(request, contact_id):
    """Agregar nota a un contacto"""
    company = request.company
    contact = get_object_or_404(Contact, id=contact_id, company=company)
    
    if request.method == 'POST':
        description = request.POST.get('description', '').strip()
        
        if description:
            Activity.objects.create(
                company=company,
                contact=contact,
                type='Note',
                description=description,
                user=request.user
            )
            messages.success(request, 'Nota agregada exitosamente')
        else:
            messages.error(request, 'La nota no puede estar vacía')
    
    return redirect('crm:contact_profile', contact_id=contact_id)
