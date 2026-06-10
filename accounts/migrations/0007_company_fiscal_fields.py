"""
Migration for Module E: Dashboard de Métricas
Adds fiscal fields to Company for profit estimation.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0006_systemnotification_usernotification'),
    ]

    operations = [
        migrations.AddField(
            model_name='company',
            name='iva_condition',
            field=models.CharField(
                max_length=30,
                blank=True,
                default='',
                choices=[
                    ('responsable_inscripto', 'Responsable Inscripto'),
                    ('monotributo', 'Monotributo'),
                    ('exento', 'Exento'),
                ],
                verbose_name='Condición IVA',
            ),
        ),
        migrations.AddField(
            model_name='company',
            name='iibb_rate',
            field=models.DecimalField(
                max_digits=5,
                decimal_places=2,
                default=0,
                verbose_name='Alícuota IIBB (%)',
                help_text='Alícuota de Ingresos Brutos en porcentaje',
            ),
        ),
        migrations.AddField(
            model_name='company',
            name='province',
            field=models.CharField(
                max_length=50,
                blank=True,
                default='',
                verbose_name='Provincia',
            ),
        ),
        migrations.AddField(
            model_name='company',
            name='ml_commission_rate',
            field=models.DecimalField(
                max_digits=5,
                decimal_places=2,
                default=13,
                verbose_name='Comisión ML (%)',
                help_text='Porcentaje estimado de comisión de MercadoLibre',
            ),
        ),
    ]
