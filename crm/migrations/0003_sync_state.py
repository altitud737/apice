# Migración para sincronizar el estado de las tablas
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('crm', '0002_whatsapp_models'),
    ]

    operations = [
        # Las tablas ya existen con los nombres correctos (crm_*)
        # Esta migración solo sincroniza el estado
    ]
