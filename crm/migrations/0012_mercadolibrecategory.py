"""
Module H: MercadoLibreCategory model for caching ML categories locally.
"""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('crm', '0011_order_detail_module'),
    ]

    operations = [
        migrations.CreateModel(
            name='MercadoLibreCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ml_category_id', models.CharField(db_index=True, max_length=50, unique=True)),
                ('name', models.CharField(max_length=300)),
                ('ml_parent_id', models.CharField(blank=True, db_index=True, default='', max_length=50, help_text='ML category_id del padre (string)')),
                ('path_from_root', models.JSONField(blank=True, default=list, help_text='Lista de {id, name} desde la raíz hasta esta categoría')),
                ('picture', models.URLField(blank=True, default='', max_length=500)),
                ('total_items_in_this_category', models.IntegerField(default=0)),
                ('has_children', models.BooleanField(default=True)),
                ('site_id', models.CharField(default='MLA', max_length=10)),
                ('synced_at', models.DateTimeField(auto_now=True)),
                ('parent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='children_set', to='crm.mercadolibrecategory')),
            ],
            options={
                'verbose_name': 'Categoría MercadoLibre',
                'verbose_name_plural': 'Categorías MercadoLibre',
                'db_table': 'mercadolibre_categories',
                'ordering': ['name'],
            },
        ),
        migrations.AddIndex(
            model_name='mercadolibrecategory',
            index=models.Index(fields=['ml_parent_id', 'site_id'], name='mercadolibr_ml_pare_a1b2c3_idx'),
        ),
    ]
