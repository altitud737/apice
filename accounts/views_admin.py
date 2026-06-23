"""
Vistas para el panel de super administrador
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.contrib.auth import login
from django.utils import timezone
from django.db.models import Count, Q
from datetime import timedelta
from .models import User, Company, SupportTicket, DemoRequest, SystemNotification, UserNotification
from crm.models import Lead, Contact, Deal, Activity, Task, Stage, Pipeline, MessageTemplate
from crm.mail_models import ZohoMailIntegration, EmailMessage, EmailDraft
from crm.integrations_mercadolibre_models import MercadoLibreIntegration, MercadoLibreWebhookEvent


def superadmin_required(view_func):
    """Decorador para verificar que el usuario es super admin"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('account_login')
        if not request.user.is_superadmin:
            messages.error(request, 'No tienes permisos para acceder a esta sección.')
            return redirect('crm:dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


@login_required
@superadmin_required
def admin_dashboard(request):
    """
    Dashboard principal del super administrador
    """
    # Estadísticas generales
    total_companies = Company.objects.count()
    active_companies = Company.objects.filter(is_active=True).count()
    suspended_companies = Company.objects.filter(is_active=False).count()
    total_users = User.objects.filter(is_superadmin=False).count()
    total_leads = Lead.objects.count()
    total_contacts = Contact.objects.count()
    total_deals = Deal.objects.count()
    
    # Tickets de soporte
    pending_tickets = SupportTicket.objects.filter(status='open').count()
    total_tickets = SupportTicket.objects.count()
    
    # Nuevos registros (últimos 7 días)
    seven_days_ago = timezone.now() - timedelta(days=7)
    new_companies = Company.objects.filter(created_at__gte=seven_days_ago).count()
    new_users = User.objects.filter(date_joined__gte=seven_days_ago, is_superadmin=False).count()
    
    # Usuarios activos hoy
    today = timezone.now().date()
    active_today = User.objects.filter(
        last_activity__date=today,
        is_superadmin=False
    ).count()
    
    # Empresas recientes
    recent_companies = Company.objects.order_by('-created_at')[:10]
    
    # Tickets recientes
    recent_tickets = SupportTicket.objects.order_by('-created_at')[:5]
    
    context = {
        'total_companies': total_companies,
        'active_companies': active_companies,
        'suspended_companies': suspended_companies,
        'total_users': total_users,
        'total_leads': total_leads,
        'total_contacts': total_contacts,
        'total_deals': total_deals,
        'pending_tickets': pending_tickets,
        'total_tickets': total_tickets,
        'new_companies': new_companies,
        'new_users': new_users,
        'active_today': active_today,
        'recent_companies': recent_companies,
        'recent_tickets': recent_tickets,
    }
    
    return render(request, 'accounts/admin_dashboard.html', context)


@login_required
@superadmin_required
def admin_companies(request):
    """
    Lista de todas las empresas (clientes)
    """
    companies = Company.objects.all().order_by('-created_at')
    
    # Agregar estadísticas por empresa
    for company in companies:
        company.user_count = company.users.count()
        company.lead_count = Lead.objects.filter(company=company).count()
        company.contact_count = Contact.objects.filter(company=company).count()
        company.deal_count = Deal.objects.filter(company=company).count()
    
    context = {
        'companies': companies,
    }
    
    return render(request, 'accounts/admin_companies.html', context)


@login_required
@superadmin_required
def admin_create_client(request):
    """
    Crear un nuevo cliente (empresa + usuario)
    """
    if request.method == 'POST':
        company_name = request.POST.get('company_name')
        user_email = request.POST.get('user_email')
        user_password = request.POST.get('user_password')
        user_first_name = request.POST.get('user_first_name', '')
        user_last_name = request.POST.get('user_last_name', '')
        
        # Validaciones
        if not company_name or not user_email or not user_password:
            messages.error(request, 'Todos los campos son obligatorios.')
            return redirect('accounts:admin_create_client')
        
        if User.objects.filter(email=user_email).exists():
            messages.error(request, f'Ya existe un usuario con el email {user_email}')
            return redirect('accounts:admin_create_client')
        
        try:
            with transaction.atomic():
                # Crear empresa
                company = Company.objects.create(name=company_name)
                
                # Crear usuario
                username = user_email.split('@')[0]
                user = User.objects.create_user(
                    username=username,
                    email=user_email,
                    password=user_password,
                    first_name=user_first_name,
                    last_name=user_last_name,
                    company=company
                )
                
                # Crear pipeline por defecto
                pipeline = Pipeline.objects.create(
                    company=company,
                    name='Pipeline Principal',
                    is_default=True
                )
                
                # Crear stages por defecto
                stages = [
                    {'name': 'Nuevo', 'order': 1},
                    {'name': 'Contactado', 'order': 2},
                    {'name': 'Calificado', 'order': 3},
                    {'name': 'Propuesta', 'order': 4},
                    {'name': 'Negociación', 'order': 5},
                    {'name': 'Ganado', 'order': 6},
                ]
                
                for stage_data in stages:
                    Stage.objects.create(
                        company=company,
                        pipeline=pipeline,
                        name=stage_data['name'],
                        order=stage_data['order']
                    )
                
                messages.success(request, f'✓ Cliente creado exitosamente: {company_name}')
                messages.info(request, f'Usuario: {user_email} | Contraseña: {user_password}')
                return redirect('accounts:admin_companies')
                
        except Exception as e:
            messages.error(request, f'Error al crear cliente: {str(e)}')
            return redirect('accounts:admin_create_client')
    
    return render(request, 'accounts/admin_create_client.html')


@login_required
@superadmin_required
def admin_company_detail(request, company_id):
    """
    Detalles de una empresa específica
    """
    company = get_object_or_404(Company, id=company_id)
    
    # Usuarios de la empresa
    users = company.users.all()
    
    # Estadísticas
    stats = {
        'leads': Lead.objects.filter(company=company).count(),
        'contacts': Contact.objects.filter(company=company).count(),
        'deals': Deal.objects.filter(company=company).count(),
        'activities': Activity.objects.filter(company=company).count(),
        'tasks': Task.objects.filter(company=company).count(),
        'pipelines': Pipeline.objects.filter(company=company).count(),
        'stages': Stage.objects.filter(company=company).count(),
        'templates': MessageTemplate.objects.filter(company=company).count(),
    }
    
    # Integraciones
    has_mercadolibre = MercadoLibreIntegration.objects.filter(company=company, is_active=True).exists()
    has_zoho_mail = ZohoMailIntegration.objects.filter(company=company).exists()
    
    context = {
        'company': company,
        'users': users,
        'stats': stats,
        'has_mercadolibre': has_mercadolibre,
        'has_zoho_mail': has_zoho_mail,
    }
    
    return render(request, 'accounts/admin_company_detail.html', context)


@login_required
@superadmin_required
def admin_delete_company(request, company_id):
    """
    Eliminar una empresa y todos sus datos
    """
    if request.method == 'POST':
        company = get_object_or_404(Company, id=company_id)
        company_name = company.name
        
        try:
            with transaction.atomic():
                # Django eliminará automáticamente todos los objetos relacionados
                # gracias a on_delete=CASCADE en los ForeignKeys
                company.delete()
                
                messages.success(request, f'✓ Empresa "{company_name}" y todos sus datos eliminados exitosamente.')
                return redirect('accounts:admin_companies')
                
        except Exception as e:
            messages.error(request, f'Error al eliminar empresa: {str(e)}')
            return redirect('accounts:admin_company_detail', company_id=company_id)
    
    return redirect('accounts:admin_companies')


@login_required
@superadmin_required
def admin_reset_password(request, user_id):
    """
    Resetear contraseña de un usuario
    """
    if request.method == 'POST':
        user = get_object_or_404(User, id=user_id)
        new_password = request.POST.get('new_password')
        
        if not new_password:
            messages.error(request, 'Debes proporcionar una nueva contraseña.')
            return redirect('accounts:admin_company_detail', company_id=user.company.id)
        
        user.set_password(new_password)
        user.save()
        
        messages.success(request, f'✓ Contraseña actualizada para {user.email}')
        messages.info(request, f'Nueva contraseña: {new_password}')
        return redirect('accounts:admin_company_detail', company_id=user.company.id)
    
    return redirect('accounts:admin_companies')


@login_required
@superadmin_required
def admin_configure_mail(request, company_id):
    """
    Configurar Zoho Mail para una empresa específica
    """
    company = get_object_or_404(Company, id=company_id)
    
    if request.method == 'POST':
        try:
            client_id = request.POST.get('client_id')
            client_secret = request.POST.get('client_secret')
            email_address = request.POST.get('email_address')
            region = request.POST.get('region', 'com')
            
            if not all([client_id, client_secret, email_address]):
                messages.error(request, 'Todos los campos son requeridos.')
                return redirect('accounts:admin_company_detail', company_id=company_id)
            
            # Crear o actualizar integración de Zoho Mail
            integration, created = ZohoMailIntegration.objects.update_or_create(
                company=company,
                defaults={
                    'client_id': client_id,
                    'client_secret': client_secret,
                    'email_address': email_address,
                    'region': region,
                    'is_active': False  # Se activará después del OAuth
                }
            )
            
            action = 'creada' if created else 'actualizada'
            messages.success(request, f'✓ Configuración de email {action} para {company.name}')
            messages.info(request, f'Email configurado: {email_address}')
            
        except Exception as e:
            messages.error(request, f'Error al configurar email: {str(e)}')
        
        return redirect('accounts:admin_company_detail', company_id=company_id)
    
    return redirect('accounts:admin_company_detail', company_id=company_id)


@login_required
@superadmin_required
def admin_toggle_company_status(request, company_id):
    """
    Suspender o activar una empresa
    """
    if request.method == 'POST':
        company = get_object_or_404(Company, id=company_id)
        company.is_active = not company.is_active
        company.save()
        
        status = 'activada' if company.is_active else 'suspendida'
        messages.success(request, f'✓ Empresa "{company.name}" {status} correctamente.')
        return redirect('accounts:admin_company_detail', company_id=company_id)
    
    return redirect('accounts:admin_companies')


@login_required
@superadmin_required
def admin_users(request):
    """
    Lista de todos los usuarios del sistema
    """
    users = User.objects.filter(is_superadmin=False).select_related('company').order_by('-date_joined')
    
    # Filtros
    company_filter = request.GET.get('company')
    if company_filter:
        users = users.filter(company_id=company_filter)
    
    # Agregar información adicional
    for user in users:
        user.ticket_count = SupportTicket.objects.filter(user=user).count()
    
    companies = Company.objects.all().order_by('name')
    
    context = {
        'users': users,
        'companies': companies,
        'selected_company': company_filter,
    }
    
    return render(request, 'accounts/admin_users.html', context)


@login_required
@superadmin_required
def admin_user_detail(request, user_id):
    """
    Detalles de un usuario específico
    """
    user_detail = get_object_or_404(User, id=user_id, is_superadmin=False)
    
    # Estadísticas del usuario
    stats = {
        'leads': Lead.objects.filter(company=user_detail.company).count(),
        'contacts': Contact.objects.filter(company=user_detail.company).count(),
        'deals': Deal.objects.filter(company=user_detail.company).count(),
        'tickets': SupportTicket.objects.filter(user=user_detail).count(),
    }
    
    # Tickets del usuario
    tickets = SupportTicket.objects.filter(user=user_detail).order_by('-created_at')[:10]
    
    context = {
        'user_detail': user_detail,
        'stats': stats,
        'tickets': tickets,
    }
    
    return render(request, 'accounts/admin_user_detail.html', context)


@login_required
@superadmin_required
def admin_impersonate_user(request, user_id):
    """
    Impersonar un usuario (login como ese usuario)
    """
    if request.method == 'POST':
        user_to_impersonate = get_object_or_404(User, id=user_id, is_superadmin=False)
        
        # Guardar el ID del super admin en la sesión
        request.session['_impersonate_admin_id'] = request.user.id
        
        # Hacer login como el usuario
        login(request, user_to_impersonate, backend='django.contrib.auth.backends.ModelBackend')
        
        messages.success(request, f'✓ Ahora estás viendo el sistema como {user_to_impersonate.email}')
        return redirect('crm:dashboard')
    
    return redirect('accounts:admin_users')


@login_required
def admin_stop_impersonating(request):
    """
    Detener la impersonación y volver a ser super admin
    """
    admin_id = request.session.get('_impersonate_admin_id')
    
    if admin_id:
        admin_user = get_object_or_404(User, id=admin_id, is_superadmin=True)
        
        # Eliminar la sesión de impersonación
        del request.session['_impersonate_admin_id']
        
        # Volver a hacer login como admin
        login(request, admin_user, backend='django.contrib.auth.backends.ModelBackend')
        
        messages.success(request, '✓ Has vuelto a tu cuenta de administrador.')
        return redirect('accounts:admin_dashboard')
    
    return redirect('crm:dashboard')


@login_required
@superadmin_required
def admin_tickets(request):
    """
    Lista de todos los tickets de soporte
    """
    tickets = SupportTicket.objects.all().select_related('user', 'company').order_by('-created_at')
    
    # Filtros
    status_filter = request.GET.get('status')
    category_filter = request.GET.get('category')
    
    if status_filter:
        tickets = tickets.filter(status=status_filter)
    if category_filter:
        tickets = tickets.filter(category=category_filter)
    
    context = {
        'tickets': tickets,
        'selected_status': status_filter,
        'selected_category': category_filter,
        'status_choices': SupportTicket.STATUS_CHOICES,
        'category_choices': SupportTicket.CATEGORY_CHOICES,
    }
    
    return render(request, 'accounts/admin_tickets.html', context)


@login_required
@superadmin_required
def admin_ticket_detail(request, ticket_id):
    """
    Ver y responder un ticket de soporte
    """
    ticket = get_object_or_404(SupportTicket, id=ticket_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'respond':
            response = request.POST.get('response')
            if response:
                ticket.admin_response = response
                ticket.status = 'in_progress'
                ticket.save()
                messages.success(request, '✓ Respuesta enviada correctamente.')
        
        elif action == 'change_status':
            new_status = request.POST.get('status')
            if new_status:
                ticket.status = new_status
                if new_status == 'resolved':
                    ticket.resolved_at = timezone.now()
                ticket.save()
                messages.success(request, f'✓ Estado actualizado a {ticket.get_status_display()}')
        
        return redirect('accounts:admin_ticket_detail', ticket_id=ticket_id)
    
    context = {
        'ticket': ticket,
        'status_choices': SupportTicket.STATUS_CHOICES,
    }
    
    return render(request, 'accounts/admin_ticket_detail.html', context)


@login_required
@superadmin_required
def admin_demos(request):
    """
    Lista de todas las solicitudes de demo
    """
    demos = DemoRequest.objects.all().order_by('-created_at')
    
    # Filtros
    status_filter = request.GET.get('status')
    if status_filter:
        demos = demos.filter(status=status_filter)
    
    context = {
        'demos': demos,
        'selected_status': status_filter,
        'status_choices': DemoRequest.STATUS_CHOICES,
    }
    
    return render(request, 'accounts/admin_demos.html', context)


@login_required
@superadmin_required
def admin_demo_detail(request, demo_id):
    """
    Ver y gestionar una solicitud de demo
    """
    demo = get_object_or_404(DemoRequest, id=demo_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'update_status':
            new_status = request.POST.get('status')
            if new_status:
                demo.status = new_status
                demo.save()
                messages.success(request, f'✓ Estado actualizado a {demo.get_status_display()}')
        
        elif action == 'add_notes':
            notes = request.POST.get('admin_notes')
            if notes:
                demo.admin_notes = notes
                demo.save()
                messages.success(request, '✓ Notas guardadas correctamente.')
        
        return redirect('accounts:admin_demo_detail', demo_id=demo_id)
    
    context = {
        'demo': demo,
        'status_choices': DemoRequest.STATUS_CHOICES,
    }
    
    return render(request, 'accounts/admin_demo_detail.html', context)


@login_required
@superadmin_required
def admin_notifications(request):
    """Lista de notificaciones del sistema enviadas por el admin"""
    notifications = SystemNotification.objects.all()
    
    context = {
        'notifications': notifications,
    }
    return render(request, 'accounts/admin_notifications.html', context)


@login_required
@superadmin_required
def admin_create_notification(request):
    """Crear y enviar una notificación a todos los usuarios"""
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        message_text = request.POST.get('message', '').strip()
        category = request.POST.get('category', 'announcement')
        
        if not title or not message_text:
            messages.error(request, 'El título y el mensaje son obligatorios.')
            return render(request, 'accounts/admin_create_notification.html', {
                'categories': SystemNotification.CATEGORY_CHOICES,
            })
        
        with transaction.atomic():
            notification = SystemNotification.objects.create(
                title=title,
                message=message_text,
                category=category,
                created_by=request.user,
            )
            
            # Crear UserNotification para todos los usuarios no-superadmin
            users = User.objects.filter(is_superadmin=False, is_active=True)
            user_notifications = [
                UserNotification(user=user, notification=notification)
                for user in users
            ]
            UserNotification.objects.bulk_create(user_notifications)
        
        messages.success(request, f'Notificación enviada a {len(user_notifications)} usuarios.')
        return redirect('accounts:admin_notifications')
    
    context = {
        'categories': SystemNotification.CATEGORY_CHOICES,
    }
    return render(request, 'accounts/admin_create_notification.html', context)


@login_required
@superadmin_required
def admin_delete_notification(request, notification_id):
    """Eliminar una notificación del sistema"""
    notification = get_object_or_404(SystemNotification, id=notification_id)
    if request.method == 'POST':
        notification.delete()
        messages.success(request, 'Notificación eliminada.')
    return redirect('accounts:admin_notifications')
