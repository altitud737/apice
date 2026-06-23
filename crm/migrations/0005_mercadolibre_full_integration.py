# MercadoLibre full integration: alter existing tables + create new models

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0006_systemnotification_usernotification'),
        ('crm', '0004_fix_table_names'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ---------------------------------------------------------------
        # 1. Alter existing MercadoLibreIntegration
        # ---------------------------------------------------------------
        migrations.RemoveField(
            model_name='mercadolibreintegration',
            name='user',
        ),
        migrations.AddField(
            model_name='mercadolibreintegration',
            name='company',
            field=models.ForeignKey(
                help_text='Empresa dueña de esta integración',
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='mercadolibre_integrations',
                to='accounts.company',
            ),
        ),
        migrations.AddField(
            model_name='mercadolibreintegration',
            name='connected_by',
            field=models.ForeignKey(
                help_text='Usuario que conectó esta integración',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='ml_integrations_connected',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='mercadolibreintegration',
            name='site_id',
            field=models.CharField(default='MLA', help_text='Sitio ML (MLA=Argentina)', max_length=10),
        ),
        migrations.AlterField(
            model_name='mercadolibreintegration',
            name='access_token',
            field=models.TextField(),
        ),
        migrations.AlterField(
            model_name='mercadolibreintegration',
            name='refresh_token',
            field=models.TextField(),
        ),
        migrations.AlterField(
            model_name='mercadolibreintegration',
            name='token_expires_at',
            field=models.DateTimeField(),
        ),
        migrations.AlterField(
            model_name='mercadolibreintegration',
            name='nickname',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AlterField(
            model_name='mercadolibreintegration',
            name='email',
            field=models.EmailField(blank=True, default='', max_length=254),
        ),
        migrations.AlterField(
            model_name='mercadolibreintegration',
            name='ml_user_id',
            field=models.CharField(db_index=True, max_length=100, unique=True),
        ),
        migrations.AlterField(
            model_name='mercadolibreintegration',
            name='is_active',
            field=models.BooleanField(default=True),
        ),
        migrations.AlterField(
            model_name='mercadolibreintegration',
            name='last_sync_at',
            field=models.DateTimeField(blank=True, null=True),
        ),

        # ---------------------------------------------------------------
        # 2. Alter existing MercadoLibreWebhookEvent
        # ---------------------------------------------------------------
        migrations.AddField(
            model_name='mercadolibrewebhookevent',
            name='application_id',
            field=models.CharField(blank=True, default='', max_length=50),
        ),
        migrations.AddField(
            model_name='mercadolibrewebhookevent',
            name='attempts',
            field=models.IntegerField(default=1),
        ),
        migrations.AddField(
            model_name='mercadolibrewebhookevent',
            name='retry_count',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='mercadolibrewebhookevent',
            name='sent_date',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='mercadolibrewebhookevent',
            name='integration',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='webhook_events',
                to='crm.mercadolibreintegration',
            ),
        ),
        migrations.AlterField(
            model_name='mercadolibrewebhookevent',
            name='topic',
            field=models.CharField(max_length=50),
        ),
        migrations.AlterField(
            model_name='mercadolibrewebhookevent',
            name='resource',
            field=models.CharField(max_length=500),
        ),
        migrations.AlterField(
            model_name='mercadolibrewebhookevent',
            name='ml_user_id',
            field=models.CharField(db_index=True, max_length=100),
        ),
        migrations.AlterField(
            model_name='mercadolibrewebhookevent',
            name='raw_payload',
            field=models.JSONField(),
        ),
        migrations.AlterField(
            model_name='mercadolibrewebhookevent',
            name='status',
            field=models.CharField(
                choices=[('pending', 'Pendiente'), ('processing', 'Procesando'), ('processed', 'Procesado'), ('failed', 'Fallido'), ('ignored', 'Ignorado')],
                db_index=True, default='pending', max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name='mercadolibrewebhookevent',
            name='error_message',
            field=models.TextField(blank=True, default=''),
        ),

        # ---------------------------------------------------------------
        # 3. Create new models
        # ---------------------------------------------------------------
        migrations.CreateModel(
            name='MercadoLibreProduct',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ml_item_id', models.CharField(db_index=True, max_length=50, unique=True)),
                ('title', models.CharField(max_length=500)),
                ('category_id', models.CharField(blank=True, default='', max_length=50)),
                ('price', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('currency_id', models.CharField(default='ARS', max_length=10)),
                ('available_quantity', models.IntegerField(default=0)),
                ('sold_quantity', models.IntegerField(default=0)),
                ('condition', models.CharField(default='new', max_length=20)),
                ('permalink', models.URLField(blank=True, default='', max_length=500)),
                ('thumbnail', models.URLField(blank=True, default='', max_length=500)),
                ('status', models.CharField(default='active', max_length=30)),
                ('raw_data', models.JSONField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ml_products', to='accounts.company')),
                ('integration', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='products', to='crm.mercadolibreintegration')),
            ],
            options={
                'verbose_name': 'Producto MercadoLibre',
                'verbose_name_plural': 'Productos MercadoLibre',
                'db_table': 'mercadolibre_products',
                'ordering': ['-updated_at'],
            },
        ),
        migrations.CreateModel(
            name='MercadoLibreOrder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ml_order_id', models.BigIntegerField(db_index=True, unique=True)),
                ('status', models.CharField(choices=[('confirmed', 'Confirmada'), ('payment_required', 'Pago Requerido'), ('payment_in_process', 'Pago en Proceso'), ('paid', 'Pagada'), ('partially_paid', 'Parcialmente Pagada'), ('cancelled', 'Cancelada'), ('invalid', 'Inválida')], default='confirmed', max_length=30)),
                ('status_detail', models.CharField(blank=True, default='', max_length=100)),
                ('buyer_id', models.BigIntegerField(db_index=True)),
                ('buyer_nickname', models.CharField(blank=True, default='', max_length=255)),
                ('buyer_first_name', models.CharField(blank=True, default='', max_length=255)),
                ('buyer_last_name', models.CharField(blank=True, default='', max_length=255)),
                ('buyer_email', models.EmailField(blank=True, default='', max_length=254)),
                ('buyer_phone', models.CharField(blank=True, default='', max_length=50)),
                ('total_amount', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('paid_amount', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('currency_id', models.CharField(default='ARS', max_length=10)),
                ('shipping_id', models.BigIntegerField(blank=True, null=True)),
                ('shipping_status', models.CharField(blank=True, default='', max_length=50)),
                ('date_created', models.DateTimeField(blank=True, null=True)),
                ('date_closed', models.DateTimeField(blank=True, null=True)),
                ('last_updated', models.DateTimeField(blank=True, null=True)),
                ('raw_data', models.JSONField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ml_orders', to='accounts.company')),
                ('contact', models.ForeignKey(blank=True, help_text='Contacto CRM creado a partir del comprador', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='ml_orders', to='crm.contact')),
                ('deal', models.ForeignKey(blank=True, help_text='Deal CRM creado a partir de la orden', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='ml_orders', to='crm.deal')),
                ('integration', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='orders', to='crm.mercadolibreintegration')),
                ('lead', models.ForeignKey(blank=True, help_text='Lead CRM creado a partir de la orden', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='ml_orders', to='crm.lead')),
            ],
            options={
                'verbose_name': 'Orden MercadoLibre',
                'verbose_name_plural': 'Órdenes MercadoLibre',
                'db_table': 'mercadolibre_orders',
                'ordering': ['-date_created'],
            },
        ),
        migrations.CreateModel(
            name='MercadoLibreOrderItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ml_item_id', models.CharField(max_length=50)),
                ('title', models.CharField(max_length=500)),
                ('quantity', models.IntegerField(default=1)),
                ('unit_price', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('currency_id', models.CharField(default='ARS', max_length=10)),
                ('category_id', models.CharField(blank=True, default='', max_length=50)),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='crm.mercadolibreorder')),
                ('product', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='order_items', to='crm.mercadolibreproduct')),
            ],
            options={
                'verbose_name': 'Item de Orden MercadoLibre',
                'verbose_name_plural': 'Items de Orden MercadoLibre',
                'db_table': 'mercadolibre_order_items',
            },
        ),
        migrations.CreateModel(
            name='MercadoLibreMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ml_message_id', models.CharField(db_index=True, max_length=100, unique=True)),
                ('pack_id', models.CharField(blank=True, db_index=True, default='', max_length=100)),
                ('sender_id', models.BigIntegerField()),
                ('sender_nickname', models.CharField(blank=True, default='', max_length=255)),
                ('receiver_id', models.BigIntegerField()),
                ('is_from_buyer', models.BooleanField(default=True)),
                ('text', models.TextField(blank=True, default='')),
                ('message_date', models.DateTimeField(blank=True, null=True)),
                ('status', models.CharField(default='available', max_length=30)),
                ('raw_data', models.JSONField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ml_messages', to='accounts.company')),
                ('contact', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='ml_messages', to='crm.contact')),
                ('integration', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='messages', to='crm.mercadolibreintegration')),
                ('order', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='messages', to='crm.mercadolibreorder')),
            ],
            options={
                'verbose_name': 'Mensaje MercadoLibre',
                'verbose_name_plural': 'Mensajes MercadoLibre',
                'db_table': 'mercadolibre_messages',
                'ordering': ['-message_date'],
            },
        ),
        migrations.CreateModel(
            name='MercadoLibreQuestion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ml_question_id', models.BigIntegerField(db_index=True, unique=True)),
                ('ml_item_id', models.CharField(db_index=True, max_length=50)),
                ('from_id', models.BigIntegerField(db_index=True)),
                ('from_nickname', models.CharField(blank=True, default='', max_length=255)),
                ('text', models.TextField()),
                ('status', models.CharField(choices=[('UNANSWERED', 'Sin Responder'), ('ANSWERED', 'Respondida'), ('CLOSED_UNANSWERED', 'Cerrada sin Respuesta'), ('UNDER_REVIEW', 'En Revisión'), ('DELETED', 'Eliminada')], default='UNANSWERED', max_length=30)),
                ('date_created', models.DateTimeField(blank=True, null=True)),
                ('answer_text', models.TextField(blank=True, default='')),
                ('answer_date', models.DateTimeField(blank=True, null=True)),
                ('raw_data', models.JSONField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ml_questions', to='accounts.company')),
                ('integration', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='questions', to='crm.mercadolibreintegration')),
                ('lead', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='ml_questions', to='crm.lead')),
                ('product', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='questions', to='crm.mercadolibreproduct')),
            ],
            options={
                'verbose_name': 'Pregunta MercadoLibre',
                'verbose_name_plural': 'Preguntas MercadoLibre',
                'db_table': 'mercadolibre_questions',
                'ordering': ['-date_created'],
            },
        ),

        # ---------------------------------------------------------------
        # 4. Indexes
        # ---------------------------------------------------------------
        migrations.AddIndex(
            model_name='mercadolibreorder',
            index=models.Index(fields=['buyer_id'], name='mercadolibr_buyer_i_e5a9e9_idx'),
        ),
        migrations.AddIndex(
            model_name='mercadolibreorder',
            index=models.Index(fields=['status', 'date_created'], name='mercadolibr_status_169102_idx'),
        ),
    ]
