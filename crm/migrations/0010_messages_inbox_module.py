"""
Migration for Module B: Messages Inbox (Bandeja de Mensajes Post-venta)
Adds read_at to MercadoLibreMessage for read tracking.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('crm', '0009_questions_inbox_module'),
    ]

    operations = [
        migrations.AddField(
            model_name='mercadolibremessage',
            name='read_at',
            field=models.DateTimeField(blank=True, null=True, help_text='Fecha en que se leyó el mensaje'),
        ),
    ]
