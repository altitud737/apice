from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.db.models import Sum, Count, Q
from .models import Contact, Stage, Deal, Activity, Task, Pipeline, MessageTemplate, Lead
from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string
from django.contrib import messages
from datetime import datetime
from urllib.parse import quote

@login_required
def dashboard(request):
    company = request.company
    
    # Stats
    open_deals = Deal.objects.filter(company=company).exclude(stage__name__in=['Cerrada Ganada', 'Cerrada Perdida'])
    closed_won = Deal.objects.filter(company=company, stage__name='Cerrada Ganada')
    
    stats = {
        'open_deals_count': open_deals.count(),
        'closed_won_count': closed_won.count(),
        'pipeline_value': open_deals.aggregate(total=Sum('value'))['total'] or 0,
        'revenue_forecast': open_deals.aggregate(
            forecast=Sum('value', field='value * probability / 100')
        )['forecast'] or 0, # Note: This is simplified, real SQL would be different
    }
    
    # Recent deals
    recent_deals = Deal.objects.filter(company=company).order_by('-created_at')[:5]
    
    # Deals by stage for chart
    deals_by_stage = Stage.objects.filter(company=company).annotate(
        count=Count('deals'),
        total_value=Sum('deals__value')
    )
    
    context = {
        'stats': stats,
        'recent_deals': recent_deals,
        'deals_by_stage': deals_by_stage,
    }
    return render(request, 'crm/dashboard.html', context)

@login_required
def contacts_list(request):
    company = request.company
    contacts = Contact.objects.filter(company=company).order_by('-created_at')
    
    # Simple search
    search = request.GET.get('search')
    if search:
        contacts = contacts.filter(name__icontains=search)
        
    context = {
        'contacts': contacts,
    }
    return render(request, 'crm/contacts.html', context)

@login_required
def pipeline(request):
    company = request.company
    
    # Obtener pipeline seleccionado o el por defecto
    pipeline_id = request.GET.get('pipeline')
    if pipeline_id:
        from crm.models import Pipeline
        current_pipeline = get_object_or_404(Pipeline, id=pipeline_id, company=company)
    else:
        from crm.models import Pipeline
        current_pipeline = Pipeline.objects.filter(company=company, is_default=True).first()
        if not current_pipeline:
            current_pipeline = Pipeline.objects.filter(company=company).first()
    
    # Obtener todos los pipelines para el selector
    from crm.models import Pipeline
    pipelines = Pipeline.objects.filter(company=company)
    
    # Obtener stages del pipeline actual
    if current_pipeline:
        stages = Stage.objects.filter(company=company, pipeline=current_pipeline).prefetch_related('deals__contact', 'deals__owner')
    else:
        stages = Stage.objects.filter(company=company).prefetch_related('deals__contact', 'deals__owner')
    
    # Calcular total_value para cada stage
    for stage in stages:
        stage.total_value = sum(deal.value for deal in stage.deals.all())
    
    contacts = Contact.objects.filter(company=company).order_by('name')
    
    context = {
        'stages': stages,
        'contacts': contacts,
        'pipelines': pipelines,
        'current_pipeline': current_pipeline,
    }
    return render(request, 'crm/pipeline.html', context)

@login_required
def update_deal_stage(request, deal_id):
    if request.method == 'POST':
        company = request.company
        deal = get_object_or_404(Deal, id=deal_id, company=company)
        stage_id = request.POST.get('stage_id')
        stage = get_object_or_404(Stage, id=stage_id, company=company)
        
        deal.stage = stage
        deal.save()
        
        # Log activity
        Activity.objects.create(
            company=company,
            contact=deal.contact,
            type='StatusChange',
            description=f'Oportunidad "{deal.title}" movida a {stage.name}',
            user=request.user
        )
        
        return HttpResponse(status=204)
    return HttpResponse(status=405)

@login_required
def create_deal(request):
    if request.method == 'POST':
        company = request.company
        
        title = request.POST.get('title')
        value = request.POST.get('value')
        probability = request.POST.get('probability', 50)
        contact_id = request.POST.get('contact')
        stage_id = request.POST.get('stage')
        expected_close_date = request.POST.get('expected_close_date')
        
        # Validar contacto
        contact = get_object_or_404(Contact, id=contact_id, company=company)
        
        # Obtener stage - si no se especifica o está vacío, usar la primera
        if stage_id and stage_id.strip():
            try:
                stage = Stage.objects.get(id=stage_id, company=company)
            except Stage.DoesNotExist:
                stage = Stage.objects.filter(company=company).order_by('order').first()
        else:
            stage = Stage.objects.filter(company=company).order_by('order').first()
        
        # Verificar que existe al menos una stage
        if not stage:
            messages.error(request, 'No hay etapas configuradas. Por favor contacte al administrador.')
            return redirect('crm:pipeline')
        
        # Crear deal
        deal = Deal.objects.create(
            company=company,
            title=title,
            value=value,
            probability=probability,
            contact=contact,
            stage=stage,
            expected_close_date=expected_close_date if expected_close_date else None,
            owner=request.user
        )
        
        # Crear actividad
        Activity.objects.create(
            company=company,
            contact=contact,
            type='DealCreated',
            description=f'Oportunidad "{deal.title}" creada por ${deal.value}',
            user=request.user
        )
        
        messages.success(request, f'Oportunidad "{title}" creada exitosamente')
        return redirect('crm:pipeline')
    
    return redirect('crm:pipeline')

@login_required
def create_contact(request):
    if request.method == 'POST':
        company = request.company
        
        contact_type = request.POST.get('contact_type', 'persona')
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        company_name = request.POST.get('company_name')
        status = request.POST.get('status', 'Nuevo')
        interest_level = request.POST.get('interest_level', 'Medio')
        
        contact = Contact.objects.create(
            company=company,
            contact_type=contact_type,
            name=name,
            email=email,
            phone=phone,
            company_name=company_name,
            status=status,
            interest_level=interest_level,
            owner=request.user
        )
        
        tipo_texto = 'Empresa' if contact_type == 'empresa' else 'Contacto'
        messages.success(request, f'{tipo_texto} "{name}" creado exitosamente')
        return redirect('crm:contacts')
    
    return redirect('crm:contacts')

@login_required
def edit_deal(request, deal_id):
    company = request.company
    deal = get_object_or_404(Deal, id=deal_id, company=company)
    
    if request.method == 'POST':
        deal.title = request.POST.get('title')
        deal.value = request.POST.get('value')
        deal.probability = request.POST.get('probability', 50)
        
        contact_id = request.POST.get('contact')
        deal.contact = get_object_or_404(Contact, id=contact_id, company=company)
        
        stage_id = request.POST.get('stage')
        if stage_id:
            deal.stage = get_object_or_404(Stage, id=stage_id, company=company)
        
        expected_close_date = request.POST.get('expected_close_date')
        deal.expected_close_date = expected_close_date if expected_close_date else None
        
        deal.save()
        
        messages.success(request, f'Oportunidad "{deal.title}" actualizada exitosamente')
        return redirect('crm:pipeline')
    
    return redirect('crm:pipeline')

@login_required
def delete_deal(request, deal_id):
    if request.method == 'POST':
        company = request.company
        deal = get_object_or_404(Deal, id=deal_id, company=company)
        title = deal.title
        deal.delete()
        
        messages.success(request, f'Oportunidad "{title}" eliminada exitosamente')
        return HttpResponse(status=204)
    
    return HttpResponse(status=405)

@login_required
def get_deal(request, deal_id):
    company = request.company
    deal = get_object_or_404(Deal, id=deal_id, company=company)
    
    data = {
        'id': deal.id,
        'title': deal.title,
        'value': str(deal.value),
        'probability': deal.probability,
        'contact_id': deal.contact.id,
        'stage_id': deal.stage.id,
        'expected_close_date': deal.expected_close_date.isoformat() if deal.expected_close_date else '',
    }
    
    return JsonResponse(data)

@login_required
def manage_pipelines(request):
    company = request.company
    pipelines = Pipeline.objects.filter(company=company).prefetch_related('stages')
    
    context = {
        'pipelines': pipelines,
    }
    return render(request, 'crm/manage_pipelines.html', context)

@login_required
def create_pipeline(request):
    if request.method == 'POST':
        company = request.company
        
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        color = request.POST.get('color', '#10b981')
        is_default = request.POST.get('is_default') == 'on'
        
        # Si se marca como default, desmarcar otros
        if is_default:
            Pipeline.objects.filter(company=company, is_default=True).update(is_default=False)
        
        pipeline = Pipeline.objects.create(
            company=company,
            name=name,
            description=description,
            color=color,
            is_default=is_default
        )
        
        # Crear stages por defecto
        default_stages = [
            {'name': 'Nuevo Lead', 'order': 1},
            {'name': 'Contactado', 'order': 2},
            {'name': 'Calificado', 'order': 3},
            {'name': 'Propuesta', 'order': 4},
            {'name': 'Negociación', 'order': 5},
            {'name': 'Cerrado Ganado', 'order': 6},
        ]
        
        for stage_data in default_stages:
            Stage.objects.create(
                company=company,
                pipeline=pipeline,
                name=stage_data['name'],
                order=stage_data['order']
            )
        
        messages.success(request, f'Pipeline "{name}" creado exitosamente con 6 etapas por defecto')
        return redirect('crm:manage_pipelines')
    
    return redirect('crm:manage_pipelines')

@login_required
def edit_pipeline(request, pipeline_id):
    company = request.company
    pipeline = get_object_or_404(Pipeline, id=pipeline_id, company=company)
    
    if request.method == 'POST':
        pipeline.name = request.POST.get('name')
        pipeline.description = request.POST.get('description', '')
        pipeline.color = request.POST.get('color', '#10b981')
        is_default = request.POST.get('is_default') == 'on'
        
        # Si se marca como default, desmarcar otros
        if is_default and not pipeline.is_default:
            Pipeline.objects.filter(company=company, is_default=True).update(is_default=False)
        
        pipeline.is_default = is_default
        pipeline.save()
        
        messages.success(request, f'Pipeline "{pipeline.name}" actualizado exitosamente')
        return redirect('crm:manage_pipelines')
    
    return redirect('crm:manage_pipelines')

@login_required
def delete_pipeline(request, pipeline_id):
    if request.method == 'POST':
        company = request.company
        pipeline = get_object_or_404(Pipeline, id=pipeline_id, company=company)
        
        # No permitir eliminar si es el único pipeline
        if Pipeline.objects.filter(company=company).count() <= 1:
            messages.error(request, 'No puedes eliminar el único pipeline. Crea otro primero.')
            return redirect('crm:manage_pipelines')
        
        # Si era default, marcar otro como default
        if pipeline.is_default:
            other_pipeline = Pipeline.objects.filter(company=company).exclude(id=pipeline_id).first()
            if other_pipeline:
                other_pipeline.is_default = True
                other_pipeline.save()
        
        name = pipeline.name
        pipeline.delete()
        
        messages.success(request, f'Pipeline "{name}" eliminado exitosamente')
        return redirect('crm:manage_pipelines')
    
    return redirect('crm:manage_pipelines')

@login_required
def create_stage(request, pipeline_id):
    if request.method == 'POST':
        company = request.company
        pipeline = get_object_or_404(Pipeline, id=pipeline_id, company=company)
        
        name = request.POST.get('name')
        order = Stage.objects.filter(company=company, pipeline=pipeline).count() + 1
        
        Stage.objects.create(
            company=company,
            pipeline=pipeline,
            name=name,
            order=order
        )
        
        messages.success(request, f'Etapa "{name}" agregada al pipeline')
        return redirect('crm:manage_pipelines')
    
    return redirect('crm:manage_pipelines')

@login_required
def edit_stage(request, stage_id):
    if request.method == 'POST':
        company = request.company
        stage = get_object_or_404(Stage, id=stage_id, company=company)
        
        stage.name = request.POST.get('name')
        stage.save()
        
        messages.success(request, f'Etapa actualizada exitosamente')
        return redirect('crm:manage_pipelines')
    
    return redirect('crm:manage_pipelines')

@login_required
def delete_stage(request, stage_id):
    if request.method == 'POST':
        company = request.company
        stage = get_object_or_404(Stage, id=stage_id, company=company)
        
        # Verificar que no sea la última etapa del pipeline
        pipeline = stage.pipeline
        if Stage.objects.filter(pipeline=pipeline).count() <= 1:
            messages.error(request, 'No puedes eliminar la única etapa del pipeline')
            return redirect('crm:manage_pipelines')
        
        # Si hay deals en esta etapa, moverlos a la primera etapa del pipeline
        deals_count = Deal.objects.filter(stage=stage).count()
        if deals_count > 0:
            first_stage = Stage.objects.filter(pipeline=pipeline).exclude(id=stage_id).order_by('order').first()
            Deal.objects.filter(stage=stage).update(stage=first_stage)
            messages.warning(request, f'{deals_count} oportunidades movidas a "{first_stage.name}"')
        
        name = stage.name
        stage.delete()
        
        messages.success(request, f'Etapa "{name}" eliminada exitosamente')
        return redirect('crm:manage_pipelines')
    
    return redirect('crm:manage_pipelines')

@login_required
def manage_templates(request):
    company = request.company
    templates = MessageTemplate.objects.filter(company=company)
    
    context = {
        'templates': templates,
    }
    return render(request, 'crm/manage_templates.html', context)

@login_required
def create_template(request):
    if request.method == 'POST':
        company = request.company
        
        name = request.POST.get('name')
        message = request.POST.get('message')
        description = request.POST.get('description', '')
        is_active = request.POST.get('is_active') == 'on'
        
        MessageTemplate.objects.create(
            company=company,
            name=name,
            message=message,
            description=description,
            is_active=is_active
        )
        
        messages.success(request, f'Plantilla "{name}" creada exitosamente')
        return redirect('crm:manage_templates')
    
    return redirect('crm:manage_templates')

@login_required
def edit_template(request, template_id):
    company = request.company
    template = get_object_or_404(MessageTemplate, id=template_id, company=company)
    
    if request.method == 'POST':
        template.name = request.POST.get('name')
        template.message = request.POST.get('message')
        template.description = request.POST.get('description', '')
        template.is_active = request.POST.get('is_active') == 'on'
        template.save()
        
        messages.success(request, f'Plantilla "{template.name}" actualizada exitosamente')
        return redirect('crm:manage_templates')
    
    return redirect('crm:manage_templates')

@login_required
def delete_template(request, template_id):
    if request.method == 'POST':
        company = request.company
        template = get_object_or_404(MessageTemplate, id=template_id, company=company)
        name = template.name
        template.delete()
        
        messages.success(request, f'Plantilla "{name}" eliminada exitosamente')
        return redirect('crm:manage_templates')
    
    return redirect('crm:manage_templates')

@login_required
def get_whatsapp_url(request, contact_id):
    company = request.company
    contact = get_object_or_404(Contact, id=contact_id, company=company)
    
    platform = request.GET.get('platform', 'web')
    template_id = request.GET.get('template')
    
    # Limpiar número de teléfono
    phone = contact.phone.replace(' ', '').replace('-', '').replace('(', '').replace(')', '') if contact.phone else ''
    
    # Obtener mensaje de la plantilla o usar mensaje por defecto
    if template_id:
        template = get_object_or_404(MessageTemplate, id=template_id, company=company)
        message = template.message
        # Reemplazar variables en el mensaje
        message = message.replace('{nombre}', contact.name)
        message = message.replace('{empresa}', contact.company_name or '')
    else:
        message = f'Hola {contact.name}'
    
    # Codificar mensaje para URL
    encoded_message = quote(message)
    
    # Generar URL según plataforma
    if platform == 'desktop':
        url = f'whatsapp://send?phone={phone}&text={encoded_message}'
    else:
        url = f'https://api.whatsapp.com/send?phone={phone}&text={encoded_message}'
    
    return JsonResponse({'url': url, 'phone': phone, 'message': message})

@login_required
def get_templates_json(request):
    company = request.company
    templates = MessageTemplate.objects.filter(company=company, is_active=True)
    
    templates_data = [
        {
            'id': template.id,
            'name': template.name,
            'message': template.message
        }
        for template in templates
    ]
    
    return JsonResponse({'templates': templates_data})
