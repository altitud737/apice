"""
Adaptadores personalizados para django-allauth
Maneja la creación de usuarios y empresas en el flujo de registro
"""
from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.conf import settings
from .models import Company
from apice.email_service import EmailService
import secrets


class AccountAdapter(DefaultAccountAdapter):
    """
    Adaptador personalizado para manejar registro de usuarios
    """
    
    def authentication_failed(self, request, **kwargs):
        """
        Personaliza el mensaje de error cuando falla la autenticación
        para no revelar si el usuario existe o no
        """
        from django.contrib import messages
        messages.error(request, "Mail o contraseña incorrecta")
    
    def save_user(self, request, user, form, commit=True):
        """
        Guarda el usuario y crea automáticamente una empresa asociada
        """
        user = super().save_user(request, user, form, commit=False)
        
        # Crear empresa automáticamente para nuevos usuarios
        if not hasattr(user, 'company') or user.company is None:
            company = Company.objects.create(
                name=f"Empresa de {user.email.split('@')[0]}",
                api_key=secrets.token_urlsafe(32)
            )
            user.company = company
        
        if commit:
            user.save()
            # Enviar email de bienvenida
            EmailService.send_welcome_email(user)
        
        return user


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Adaptador personalizado para OAuth social (Google, GitHub, etc.)
    """
    
    def pre_social_login(self, request, sociallogin):
        """
        Invocado justo después de que un usuario se autentica con OAuth
        """
        # Si el usuario ya existe, no hacer nada
        if sociallogin.is_existing:
            return
        
        # Si el email ya existe en el sistema, conectar la cuenta social
        try:
            email = sociallogin.account.extra_data.get('email')
            if email:
                from accounts.models import User
                existing_user = User.objects.get(email=email)
                sociallogin.connect(request, existing_user)
        except User.DoesNotExist:
            pass
    
    def save_user(self, request, sociallogin, form=None):
        """
        Guarda el usuario de OAuth y crea empresa automáticamente
        """
        user = super().save_user(request, sociallogin, form)
        
        # Crear empresa automáticamente si no existe
        if not hasattr(user, 'company') or user.company is None:
            # Obtener nombre del proveedor OAuth
            provider = sociallogin.account.provider
            email = sociallogin.account.extra_data.get('email', 'usuario')
            
            company = Company.objects.create(
                name=f"Empresa de {email.split('@')[0]}",
                api_key=secrets.token_urlsafe(32)
            )
            user.company = company
            user.save()
            
            # Enviar email de bienvenida
            EmailService.send_welcome_email(user)
        
        return user
    
    def populate_user(self, request, sociallogin, data):
        """
        Pobla los datos del usuario desde el proveedor OAuth
        """
        user = super().populate_user(request, sociallogin, data)
        
        # Asegurar que el email esté configurado
        if not user.email and data.get('email'):
            user.email = data['email']
        
        return user
