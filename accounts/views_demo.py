"""
Vistas para el sistema de solicitud de demos
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from .models import DemoRequest


def request_demo(request):
    """
    Formulario para solicitar una demo
    """
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        company = request.POST.get('company')
        message = request.POST.get('message')
        
        # Validaciones
        if not all([name, email, company, message]):
            messages.error(request, 'Todos los campos son obligatorios.')
            return redirect('accounts:request_demo')
        
        # Crear solicitud
        demo = DemoRequest.objects.create(
            name=name,
            email=email,
            company=company,
            message=message
        )
        
        # Enviar email al admin
        try:
            admin_email = getattr(settings, 'ADMIN_EMAIL', 'admin@sdp.com')
            send_mail(
                subject=f'Nueva solicitud de demo - {company}',
                message=f'''
Nueva solicitud de demo recibida:

Nombre: {name}
Email: {email}
Empresa: {company}

Mensaje:
{message}

---
Puedes gestionar esta solicitud desde el panel de administración.
                ''',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[admin_email],
                fail_silently=True,
            )
        except Exception as e:
            print(f"Error enviando email: {e}")
        
        return redirect('accounts:demo_success')
    
    return render(request, 'accounts/request_demo.html')


def demo_success(request):
    """
    Página de confirmación después de solicitar demo
    """
    return render(request, 'accounts/demo_success.html')
