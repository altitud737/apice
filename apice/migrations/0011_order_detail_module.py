"""
Migration for Module C: Order Detail View
Adds shipping/payment fields to Order and thumbnail/variation fields to OrderItem.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('apice', '0010_messages_inbox_module'),
    ]

    operations = [
        # MercadoLibreOrder: shipping extended
        migrations.AddField(
            model_name='mercadolibreorder',
            name='shipping_tracking_number',
            field=models.CharField(max_length=100, blank=True, default=''),
        ),
        migrations.AddField(
            model_name='mercadolibreorder',
            name='shipping_carrier',
            field=models.CharField(max_length=100, blank=True, default=''),
        ),
        migrations.AddField(
            model_name='mercadolibreorder',
            name='shipping_receiver_address',
            field=models.JSONField(null=True, blank=True, help_text='Dirección del comprador'),
        ),
        # MercadoLibreOrder: payment
        migrations.AddField(
            model_name='mercadolibreorder',
            name='payment_method',
            field=models.CharField(max_length=50, blank=True, default=''),
        ),
        # MercadoLibreOrderItem: thumbnail + variations
        migrations.AddField(
            model_name='mercadolibreorderitem',
            name='thumbnail',
            field=models.URLField(max_length=500, blank=True, default=''),
        ),
        migrations.AddField(
            model_name='mercadolibreorderitem',
            name='variation_id',
            field=models.BigIntegerField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='mercadolibreorderitem',
            name='variation_attributes',
            field=models.JSONField(null=True, blank=True, help_text='Ej: [{"name": "Color", "value": "Azul"}]'),
        ),
    ]
