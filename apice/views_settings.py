from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.models import Company, User

@login_required
def settings(request):
    """Vista principal de configuración"""
    company = request.company
    
    # Estadísticas de usuarios
    total_users = User.objects.filter(company=company).count()
    
    context = {
        'company': company,
        'total_users': total_users,
    }
    
    return render(request, 'apice/settings.html', context)


@login_required
def settings_company(request):
    """Configuración de la empresa"""
    company = request.company
    
    if request.method == 'POST':
        company.name = request.POST.get('name', company.name)
        company.save()
        
        messages.success(request, 'Configuración de empresa actualizada')
        return redirect('apice:settings_company')
    
    context = {
        'company': company,
    }
    
    return render(request, 'apice/settings_company.html', context)


@login_required
def settings_users(request):
    """Gestión de usuarios"""
    company = request.company
    users = User.objects.filter(company=company)
    
    context = {
        'users': users,
    }
    
    return render(request, 'apice/settings_users.html', context)


@login_required
def settings_security(request):
    """Configuración de seguridad"""
    company = request.company
    
    context = {
        'company': company,
        'api_key': company.api_key,
    }
    
    return render(request, 'apice/settings_security.html', context)
