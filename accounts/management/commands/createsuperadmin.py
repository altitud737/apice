"""
Comando para crear un super administrador
"""
from django.core.management.base import BaseCommand
from accounts.models import User, Company


class Command(BaseCommand):
    help = 'Crea un super administrador con acceso total al sistema'

    def add_arguments(self, parser):
        parser.add_argument('--email', type=str, help='Email del super admin')
        parser.add_argument('--password', type=str, help='Contraseña del super admin')

    def handle(self, *args, **options):
        email = options.get('email')
        password = options.get('password')

        # Si no se proporcionan argumentos, pedir interactivamente
        if not email:
            email = input('Email del super admin: ')
        
        if not password:
            from getpass import getpass
            password = getpass('Contraseña: ')
            password_confirm = getpass('Confirmar contraseña: ')
            
            if password != password_confirm:
                self.stdout.write(self.style.ERROR('Las contraseñas no coinciden'))
                return

        # Verificar si ya existe un super admin con este email
        if User.objects.filter(email=email).exists():
            self.stdout.write(self.style.ERROR(f'Ya existe un usuario con el email {email}'))
            return

        # Crear empresa para el super admin
        company, created = Company.objects.get_or_create(
            name='SDP - Administración',
            defaults={'name': 'SDP - Administración'}
        )

        # Crear super admin con username único
        import time
        base_username = email.split('@')[0]
        username = f"{base_username}_superadmin_{int(time.time())}"
        
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            company=company,
            is_superadmin=True,
            is_staff=True,
            is_superuser=True
        )

        self.stdout.write(self.style.SUCCESS(f'✓ Super administrador creado exitosamente'))
        self.stdout.write(self.style.SUCCESS(f'  Email: {email}'))
        self.stdout.write(self.style.SUCCESS(f'  Empresa: {company.name}'))
        self.stdout.write(self.style.SUCCESS(f'  Acceso total al sistema habilitado'))
