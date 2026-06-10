"""
Comando de Django para probar la integración de WhatsApp
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apice.whatsapp_service import get_whatsapp_service
from apice.whatsapp_models import WhatsAppIntegration, WhatsAppMessage
from accounts.models import Company

User = get_user_model()


class Command(BaseCommand):
    help = 'Prueba la integración de WhatsApp'

    def add_arguments(self, parser):
        parser.add_argument(
            '--send',
            type=str,
            help='Enviar mensaje de prueba a un número (formato: 5491112345678)'
        )
        parser.add_argument(
            '--message',
            type=str,
            default='Mensaje de prueba desde Apice CRM',
            help='Texto del mensaje a enviar'
        )
        parser.add_argument(
            '--company-id',
            type=int,
            help='ID de la empresa (opcional, usa la primera activa si no se especifica)'
        )
        parser.add_argument(
            '--status',
            action='store_true',
            help='Mostrar estado de la integración'
        )
        parser.add_argument(
            '--messages',
            action='store_true',
            help='Listar últimos mensajes'
        )

    def handle(self, *args, **options):
        # Obtener la empresa
        if options['company_id']:
            try:
                company = Company.objects.get(id=options['company_id'])
            except Company.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Empresa con ID {options["company_id"]} no encontrada'))
                return
        else:
            company = Company.objects.first()
            if not company:
                self.stdout.write(self.style.ERROR('No hay empresas en el sistema'))
                return

        self.stdout.write(self.style.SUCCESS(f'Usando empresa: {company.name}'))

        # Mostrar estado
        if options['status']:
            self.show_status(company)
            return

        # Listar mensajes
        if options['messages']:
            self.list_messages(company)
            return

        # Enviar mensaje
        if options['send']:
            self.send_message(company, options['send'], options['message'])
            return

        # Si no se especifica ninguna acción, mostrar ayuda
        self.stdout.write(self.style.WARNING('Uso:'))
        self.stdout.write('  python manage.py test_whatsapp --status')
        self.stdout.write('  python manage.py test_whatsapp --messages')
        self.stdout.write('  python manage.py test_whatsapp --send 5491112345678 --message "Hola"')

    def show_status(self, company):
        """Muestra el estado de la integración"""
        try:
            integration = WhatsAppIntegration.objects.get(company=company, is_active=True)
            
            self.stdout.write(self.style.SUCCESS('\n✓ Integración de WhatsApp ACTIVA'))
            self.stdout.write(f'  Phone Number ID: {integration.phone_number_id}')
            self.stdout.write(f'  Número: {integration.phone_number or "No configurado"}')
            self.stdout.write(f'  Webhook URL: {integration.webhook_url or "No configurado"}')
            self.stdout.write(f'  Auto-crear leads: {"Sí" if integration.auto_create_leads else "No"}')
            self.stdout.write(f'  Auto-crear contactos: {"Sí" if integration.auto_create_contacts else "No"}')
            
            # Estadísticas
            total_messages = WhatsAppMessage.objects.filter(company=company).count()
            inbound = WhatsAppMessage.objects.filter(company=company, direction='inbound').count()
            outbound = WhatsAppMessage.objects.filter(company=company, direction='outbound').count()
            
            self.stdout.write(f'\n📊 Estadísticas:')
            self.stdout.write(f'  Total mensajes: {total_messages}')
            self.stdout.write(f'  Entrantes: {inbound}')
            self.stdout.write(f'  Salientes: {outbound}')
            
        except WhatsAppIntegration.DoesNotExist:
            self.stdout.write(self.style.ERROR('\n✗ No hay integración de WhatsApp activa'))
            self.stdout.write('  Configura WhatsApp en: http://localhost:8000/whatsapp/settings/')

    def list_messages(self, company):
        """Lista los últimos mensajes"""
        messages = WhatsAppMessage.objects.filter(
            company=company
        ).order_by('-timestamp')[:10]

        if not messages:
            self.stdout.write(self.style.WARNING('No hay mensajes'))
            return

        self.stdout.write(self.style.SUCCESS(f'\n📱 Últimos {len(messages)} mensajes:\n'))
        
        for msg in messages:
            direction = '→' if msg.direction == 'outbound' else '←'
            status_color = self.style.SUCCESS if msg.status in ['delivered', 'read'] else self.style.WARNING
            
            self.stdout.write(
                f'{direction} {msg.timestamp.strftime("%d/%m %H:%M")} | '
                f'{msg.from_number} → {msg.to_number} | '
                f'{status_color(msg.status.upper())} | '
                f'{msg.text_body[:50]}...' if len(msg.text_body or '') > 50 else msg.text_body or ''
            )

    def send_message(self, company, to_number, message_text):
        """Envía un mensaje de prueba"""
        service = get_whatsapp_service(company)
        
        if not service:
            self.stdout.write(self.style.ERROR('No hay integración de WhatsApp activa'))
            return

        self.stdout.write(f'\n📤 Enviando mensaje a {to_number}...')
        
        result = service.send_text_message(
            to_number=to_number,
            message_text=message_text
        )

        if result['success']:
            self.stdout.write(self.style.SUCCESS(f'✓ Mensaje enviado exitosamente'))
            self.stdout.write(f'  Message ID: {result["message_id"]}')
        else:
            self.stdout.write(self.style.ERROR(f'✗ Error al enviar mensaje'))
            self.stdout.write(f'  {result["error"]}')
