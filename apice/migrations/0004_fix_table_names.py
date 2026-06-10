# Fix db_table state for all models that already have correct table names in DB
# but Django migration state doesn't know about them.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('apice', '0003_sync_state'),
    ]

    operations = [
        migrations.AlterModelTable(name='activity', table='crm_activity'),
        migrations.AlterModelTable(name='contact', table='crm_contact'),
        migrations.AlterModelTable(name='deal', table='crm_deal'),
        migrations.AlterModelTable(name='lead', table='crm_lead'),
        migrations.AlterModelTable(name='messagetemplate', table='crm_messagetemplate'),
        migrations.AlterModelTable(name='pipeline', table='crm_pipeline'),
        migrations.AlterModelTable(name='stage', table='crm_stage'),
        migrations.AlterModelTable(name='task', table='crm_task'),
        migrations.AlterModelTable(name='emaildraft', table='crm_emaildraft'),
        migrations.AlterModelTable(name='emailmessage', table='crm_emailmessage'),
        migrations.AlterModelTable(name='zohomailintegration', table='crm_zohomailintegration'),
    ]
