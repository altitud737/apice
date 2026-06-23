"""
Vistas para el sistema de configuración del cliente
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from accounts.models import User, Company, SupportTicket
from django.contrib.auth.hashers import make_password
import uuid


@login_required
def settings_index(request):
    """
    Página principal de configuración
    """
    company = request.user.company
    
    context = {
        'company': company,
        'total_users': company.users.count() if company else 0,
    }
    return render(request, 'crm/settings/index.html', context)


@login_required
def settings_company(request):
    """
    Configuración del perfil de la empresa
    """
    company = request.user.company
    
    if not company:
        messages.error(request, 'No tienes una empresa asignada.')
        return redirect('crm:dashboard')
    
    if request.method == 'POST':
        company.name = request.POST.get('name', company.name)
        company.industry = request.POST.get('industry', company.industry)
        company.description = request.POST.get('description', '')
        company.location = request.POST.get('location', '')
        company.save()
        
        messages.success(request, '✓ Perfil de empresa actualizado correctamente.')
        return redirect('crm:settings_company')
    
    context = {
        'company': company,
        'industries': Company.INDUSTRY_CHOICES,
    }
    return render(request, 'crm/settings/company.html', context)


@login_required
def settings_users(request):
    """
    Gestión de usuarios de la empresa
    """
    company = request.user.company
    
    if not company:
        messages.error(request, 'No tienes una empresa asignada.')
        return redirect('crm:dashboard')
    
    # Verificar permisos
    if not (request.user.is_company_admin or request.user.can_manage_users):
        messages.error(request, 'No tienes permisos para gestionar usuarios.')
        return redirect('crm:settings')
    
    users = company.users.all().order_by('-date_joined')
    
    context = {
        'company': company,
        'users': users,
    }
    return render(request, 'crm/settings/users.html', context)


@login_required
def settings_user_create(request):
    """
    Crear nuevo usuario para la empresa
    """
    company = request.user.company
    
    if not company:
        messages.error(request, 'No tienes una empresa asignada.')
        return redirect('crm:dashboard')
    
    # Verificar permisos
    if not (request.user.is_company_admin or request.user.can_manage_users):
        messages.error(request, 'No tienes permisos para crear usuarios.')
        return redirect('crm:settings_users')
    
    if request.method == 'POST':
        try:
            email = request.POST.get('email')
            password = request.POST.get('password')
            first_name = request.POST.get('first_name', '')
            last_name = request.POST.get('last_name', '')
            
            # Validar que el email no exista
            if User.objects.filter(email=email).exists():
                messages.error(request, 'Ya existe un usuario con ese email.')
                return redirect('crm:settings_user_create')
            
            # Crear usuario
            username = email.split('@')[0] + '_' + str(uuid.uuid4())[:8]
            user = User.objects.create(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                company=company,
                password=make_password(password),
                is_company_admin=request.POST.get('is_company_admin') == 'on',
                can_send_emails=request.POST.get('can_send_emails') == 'on',
                can_view_contacts=request.POST.get('can_view_contacts') == 'on',
                can_view_deals=request.POST.get('can_view_deals') == 'on',
                can_view_pipeline=request.POST.get('can_view_pipeline') == 'on',
                can_view_settings=request.POST.get('can_view_settings') == 'on',
                can_manage_users=request.POST.get('can_manage_users') == 'on',
                can_view_integrations=request.POST.get('can_view_integrations') == 'on',
            )
            
            messages.success(request, f'✓ Usuario {email} creado correctamente.')
            messages.info(request, f'Contraseña: {password}')
            return redirect('crm:settings_users')
            
        except Exception as e:
            messages.error(request, f'Error al crear usuario: {str(e)}')
            return redirect('crm:settings_user_create')
    
    context = {
        'company': company,
    }
    return render(request, 'crm/settings/user_create.html', context)


@login_required
def settings_user_edit(request, user_id):
    """
    Editar permisos de un usuario
    """
    company = request.user.company
    user_to_edit = get_object_or_404(User, id=user_id, company=company)
    
    # Verificar permisos
    if not (request.user.is_company_admin or request.user.can_manage_users):
        messages.error(request, 'No tienes permisos para editar usuarios.')
        return redirect('crm:settings_users')
    
    if request.method == 'POST':
        user_to_edit.first_name = request.POST.get('first_name', user_to_edit.first_name)
        user_to_edit.last_name = request.POST.get('last_name', user_to_edit.last_name)
        user_to_edit.is_company_admin = request.POST.get('is_company_admin') == 'on'
        user_to_edit.can_send_emails = request.POST.get('can_send_emails') == 'on'
        user_to_edit.can_view_contacts = request.POST.get('can_view_contacts') == 'on'
        user_to_edit.can_view_deals = request.POST.get('can_view_deals') == 'on'
        user_to_edit.can_view_pipeline = request.POST.get('can_view_pipeline') == 'on'
        user_to_edit.can_view_settings = request.POST.get('can_view_settings') == 'on'
        user_to_edit.can_manage_users = request.POST.get('can_manage_users') == 'on'
        user_to_edit.can_view_integrations = request.POST.get('can_view_integrations') == 'on'
        user_to_edit.save()
        
        messages.success(request, f'✓ Usuario {user_to_edit.email} actualizado correctamente.')
        return redirect('crm:settings_users')
    
    context = {
        'company': company,
        'user_to_edit': user_to_edit,
    }
    return render(request, 'crm/settings/user_edit.html', context)


@login_required
def settings_user_delete(request, user_id):
    """
    Eliminar un usuario
    """
    company = request.user.company
    user_to_delete = get_object_or_404(User, id=user_id, company=company)
    
    # Verificar permisos
    if not (request.user.is_company_admin or request.user.can_manage_users):
        messages.error(request, 'No tienes permisos para eliminar usuarios.')
        return redirect('crm:settings_users')
    
    # No permitir eliminar al propio usuario
    if user_to_delete == request.user:
        messages.error(request, 'No puedes eliminarte a ti mismo.')
        return redirect('crm:settings_users')
    
    if request.method == 'POST':
        email = user_to_delete.email
        user_to_delete.delete()
        messages.success(request, f'✓ Usuario {email} eliminado correctamente.')
        return redirect('crm:settings_users')
    
    return redirect('crm:settings_users')


@login_required
def settings_security(request):
    """
    Configuración de seguridad de la cuenta
    """
    company = request.user.company
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'change_password':
            current_password = request.POST.get('current_password')
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')
            
            # Verificar contraseña actual
            if not request.user.check_password(current_password):
                messages.error(request, 'La contraseña actual es incorrecta.')
                return redirect('crm:settings_security')
            
            # Verificar que las contraseñas coincidan
            if new_password != confirm_password:
                messages.error(request, 'Las contraseñas no coinciden.')
                return redirect('crm:settings_security')
            
            # Cambiar contraseña
            request.user.set_password(new_password)
            request.user.save()
            
            messages.success(request, '✓ Contraseña actualizada correctamente.')
            return redirect('crm:settings_security')
        
        elif action == 'regenerate_api_key':
            if company:
                company.api_key = uuid.uuid4().hex
                company.save()
                messages.success(request, '✓ API Key regenerada correctamente.')
            return redirect('crm:settings_security')
    
    context = {
        'company': company,
        'api_key': company.api_key if company else None,
    }
    return render(request, 'crm/settings/security.html', context)


@login_required
def settings_support(request):
    """
    Centro de soporte - ver tickets enviados
    """
    company = request.user.company
    
    if not company:
        messages.error(request, 'No tienes una empresa asignada.')
        return redirect('crm:dashboard')
    
    tickets = SupportTicket.objects.filter(company=company).order_by('-created_at')
    
    context = {
        'company': company,
        'tickets': tickets,
    }
    return render(request, 'crm/settings/support.html', context)


@login_required
def settings_support_create(request):
    """
    Crear nuevo ticket de soporte
    """
    company = request.user.company
    
    if not company:
        messages.error(request, 'No tienes una empresa asignada.')
        return redirect('crm:dashboard')
    
    if request.method == 'POST':
        category = request.POST.get('category')
        subject = request.POST.get('subject')
        message = request.POST.get('message')
        
        ticket = SupportTicket.objects.create(
            user=request.user,
            company=company,
            category=category,
            subject=subject,
            message=message,
        )
        
        messages.success(request, '✓ Ticket enviado correctamente. El administrador lo revisará pronto.')
        return redirect('crm:settings_support')
    
    context = {
        'company': company,
        'categories': SupportTicket.CATEGORY_CHOICES,
    }
    return render(request, 'crm/settings/support_create.html', context)


@login_required
def settings_support_view(request, ticket_id):
    """
    Ver detalles de un ticket
    """
    company = request.user.company
    ticket = get_object_or_404(SupportTicket, id=ticket_id, company=company)
    
    context = {
        'company': company,
        'ticket': ticket,
    }
    return render(request, 'crm/settings/support_view.html', context)
