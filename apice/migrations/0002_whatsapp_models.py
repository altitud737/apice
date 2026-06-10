# Generated manually for WhatsApp integration

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('apice', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='WhatsAppIntegration',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('phone_number_id', models.CharField(help_text='ID del número de teléfono de WhatsApp Business', max_length=255)),
                ('business_account_id', models.CharField(help_text='ID de la cuenta de WhatsApp Business', max_length=255)),
                ('access_token', models.CharField(help_text='Token de acceso permanente de Meta', max_length=500)),
                ('verify_token', models.CharField(help_text='Token de verificación para el webhook', max_length=255)),
                ('webhook_url', models.URLField(blank=True, help_text='URL actual del webhook (ngrok)', null=True)),
                ('phone_number', models.CharField(blank=True, help_text='Número de teléfono formateado', max_length=50, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('auto_create_leads', models.BooleanField(default=True, help_text='Crear leads automáticamente de mensajes nuevos')),
                ('auto_create_contacts', models.BooleanField(default=False, help_text='Crear contactos automáticamente')),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='accounts.company')),
            ],
            options={
                'verbose_name': 'Integración de WhatsApp',
                'verbose_name_plural': 'Integraciones de WhatsApp',
                'db_table': 'crm_whatsapp_integration',
            },
        ),
        migrations.CreateModel(
            name='WhatsAppTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(help_text='Nombre de la plantilla en Meta', max_length=255)),
                ('language', models.CharField(default='es', help_text='Código de idioma (ej: es, en)', max_length=10)),
                ('category', models.CharField(help_text='Categoría de la plantilla', max_length=50)),
                ('status', models.CharField(choices=[('pending', 'Pendiente'), ('approved', 'Aprobada'), ('rejected', 'Rechazada')], default='pending', max_length=20)),
                ('header_text', models.CharField(blank=True, max_length=60, null=True)),
                ('body_text', models.TextField(help_text='Texto del cuerpo de la plantilla')),
                ('footer_text', models.CharField(blank=True, max_length=60, null=True)),
                ('template_id', models.CharField(blank=True, help_text='ID de la plantilla en Meta', max_length=255, null=True)),
                ('components', models.JSONField(blank=True, help_text='Componentes de la plantilla', null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='accounts.company')),
                ('integration', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='templates', to='apice.whatsappintegration')),
            ],
            options={
                'verbose_name': 'Plantilla de WhatsApp',
                'verbose_name_plural': 'Plantillas de WhatsApp',
                'db_table': 'crm_whatsapp_template',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='WhatsAppWebhookEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('event_type', models.CharField(choices=[('message', 'Mensaje'), ('status', 'Estado'), ('error', 'Error'), ('other', 'Otro')], max_length=20)),
                ('raw_payload', models.JSONField(help_text='Payload completo del webhook')),
                ('processed', models.BooleanField(default=False)),
                ('processed_at', models.DateTimeField(blank=True, null=True)),
                ('error_message', models.TextField(blank=True, null=True)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='accounts.company')),
                ('integration', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='webhook_events', to='apice.whatsappintegration')),
            ],
            options={
                'verbose_name': 'Evento de Webhook WhatsApp',
                'verbose_name_plural': 'Eventos de Webhook WhatsApp',
                'db_table': 'crm_whatsapp_webhook_event',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='WhatsAppMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('message_id', models.CharField(help_text='ID del mensaje de WhatsApp', max_length=255, unique=True)),
                ('wamid', models.CharField(blank=True, help_text='WhatsApp Message ID', max_length=255, null=True)),
                ('from_number', models.CharField(help_text='Número de teléfono del remitente', max_length=50)),
                ('to_number', models.CharField(help_text='Número de teléfono del destinatario', max_length=50)),
                ('contact_name', models.CharField(blank=True, help_text='Nombre del contacto', max_length=255, null=True)),
                ('message_type', models.CharField(choices=[('text', 'Texto'), ('image', 'Imagen'), ('document', 'Documento'), ('audio', 'Audio'), ('video', 'Video'), ('location', 'Ubicación'), ('contacts', 'Contactos'), ('template', 'Plantilla')], default='text', max_length=20)),
                ('direction', models.CharField(choices=[('inbound', 'Entrante'), ('outbound', 'Saliente')], max_length=10)),
                ('status', models.CharField(choices=[('sent', 'Enviado'), ('delivered', 'Entregado'), ('read', 'Leído'), ('failed', 'Fallido'), ('received', 'Recibido')], default='sent', max_length=20)),
                ('text_body', models.TextField(blank=True, help_text='Contenido del mensaje de texto', null=True)),
                ('media_url', models.URLField(blank=True, help_text='URL del archivo multimedia', null=True)),
                ('media_id', models.CharField(blank=True, help_text='ID del archivo multimedia', max_length=255, null=True)),
                ('caption', models.TextField(blank=True, help_text='Descripción de la imagen/video', null=True)),
                ('timestamp', models.DateTimeField(help_text='Timestamp del mensaje de WhatsApp')),
                ('raw_data', models.JSONField(blank=True, help_text='Datos completos del webhook', null=True)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='accounts.company')),
                ('contact', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='whatsapp_messages', to='apice.contact')),
                ('integration', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='messages', to='apice.whatsappintegration')),
                ('lead', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='whatsapp_messages', to='apice.lead')),
                ('sent_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Mensaje de WhatsApp',
                'verbose_name_plural': 'Mensajes de WhatsApp',
                'db_table': 'crm_whatsapp_message',
                'ordering': ['-timestamp'],
            },
        ),
    ]
