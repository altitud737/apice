# apice/migrations/0009_questions_inbox_module.py
"""
Módulo A — Bandeja de Preguntas Pre-venta

1. Renombra MercadoLibreAutoReplyTemplate → MercadoLibreReplyTemplate
   - Renombra la tabla DB
   - Agrega campos usable_in_questions, usable_in_messages
   - Actualiza related_names en FKs de Company y User
   - Actualiza la FK en MercadoLibreQuestion para apuntar al modelo renombrado

2. Agrega campos a MercadoLibreQuestion:
   - answered_by (FK User)
   - is_ignored (BooleanField)
   - read_at (DateTimeField nullable)

3. Agrega campo a MercadoLibreIntegration:
   - auto_reply_enabled (BooleanField, default=False)
"""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def migrate_template_defaults(apps, schema_editor):
    """
    Después de renombrar el modelo y agregar los campos nuevos,
    setear usable_in_questions=True en todas las plantillas existentes.
    usable_in_messages ya tiene default=False, no hace falta tocarlo.
    """
    MercadoLibreReplyTemplate = apps.get_model('apice', 'MercadoLibreReplyTemplate')
    MercadoLibreReplyTemplate.objects.all().update(usable_in_questions=True)


def reverse_migrate_template_defaults(apps, schema_editor):
    """Reverse: no-op, los campos se borran con la migración reversa."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('apice', '0008_product_fields_update'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # =====================================================================
        # 1. Renombrar modelo MercadoLibreAutoReplyTemplate → MercadoLibreReplyTemplate
        # =====================================================================
        migrations.RenameModel(
            old_name='MercadoLibreAutoReplyTemplate',
            new_name='MercadoLibreReplyTemplate',
        ),

        # Renombrar tabla en la DB
        migrations.AlterModelTable(
            name='mercadolibrereplytemplate',
            table='mercadolibre_reply_templates',
        ),

        # Actualizar Meta del modelo renombrado
        migrations.AlterModelOptions(
            name='mercadolibrereplytemplate',
            options={
                'ordering': ['-priority', 'name'],
                'verbose_name': 'Plantilla de Respuesta ML',
                'verbose_name_plural': 'Plantillas de Respuesta ML',
            },
        ),

        # Actualizar related_name de Company FK (ml_auto_reply_templates → ml_reply_templates)
        migrations.AlterField(
            model_name='mercadolibrereplytemplate',
            name='company',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='ml_reply_templates',
                to='accounts.company',
            ),
        ),

        # Actualizar related_name de User FK (ml_auto_reply_templates → ml_reply_templates)
        migrations.AlterField(
            model_name='mercadolibrereplytemplate',
            name='created_by',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='ml_reply_templates',
                to=settings.AUTH_USER_MODEL,
            ),
        ),

        # Agregar campo usable_in_questions
        migrations.AddField(
            model_name='mercadolibrereplytemplate',
            name='usable_in_questions',
            field=models.BooleanField(
                default=True,
                help_text='Disponible como respuesta rápida en preguntas pre-venta',
            ),
        ),

        # Agregar campo usable_in_messages
        migrations.AddField(
            model_name='mercadolibrereplytemplate',
            name='usable_in_messages',
            field=models.BooleanField(
                default=False,
                help_text='Disponible como respuesta rápida en mensajes post-venta',
            ),
        ),

        # =====================================================================
        # 2. Actualizar FK de MercadoLibreQuestion.auto_reply_template
        #    Django ya trackea el rename del modelo, pero actualizamos el field
        #    para que apunte explícitamente al modelo renombrado con el nuevo related_name.
        # =====================================================================
        migrations.AlterField(
            model_name='mercadolibrequestion',
            name='auto_reply_template',
            field=models.ForeignKey(
                blank=True,
                help_text='Template usado para la respuesta automática',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='questions_answered',
                to='apice.mercadolibrereplytemplate',
            ),
        ),

        # =====================================================================
        # 3. Nuevos campos en MercadoLibreQuestion
        # =====================================================================
        migrations.AddField(
            model_name='mercadolibrequestion',
            name='answered_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='ml_questions_answered',
                to=settings.AUTH_USER_MODEL,
                help_text='Usuario que respondió manualmente',
            ),
        ),

        migrations.AddField(
            model_name='mercadolibrequestion',
            name='is_ignored',
            field=models.BooleanField(default=False),
        ),

        migrations.AddField(
            model_name='mercadolibrequestion',
            name='read_at',
            field=models.DateTimeField(blank=True, null=True),
        ),

        # =====================================================================
        # 4. Nuevo campo en MercadoLibreIntegration
        # =====================================================================
        migrations.AddField(
            model_name='mercadolibreintegration',
            name='auto_reply_enabled',
            field=models.BooleanField(
                default=False,
                help_text='Responder automáticamente preguntas usando plantillas con keywords',
            ),
        ),

        # =====================================================================
        # 5. RunPython: migrar datos existentes
        # =====================================================================
        migrations.RunPython(
            migrate_template_defaults,
            reverse_migrate_template_defaults,
        ),
    ]
