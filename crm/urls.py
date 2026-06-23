from django.urls import path, include
from . import views
from . import api_views
from . import views_leads
from . import views_contacts
from . import views_integrations
from . import views_settings_new
from . import views_notifications

app_name = 'crm'

urlpatterns = [
    # API endpoints
    path('api/leads/', api_views.create_lead, name='api_create_lead'),
    
    # Web views
    path('', views.dashboard, name='dashboard'),
    
    # Notificaciones
    path('notifications/', views_notifications.notifications_list, name='notifications'),
    path('notifications/<int:notification_id>/read/', views_notifications.notification_mark_read, name='notification_mark_read'),
    path('notifications/mark-all-read/', views_notifications.notifications_mark_all_read, name='notifications_mark_all_read'),
    
    # Integrations
    path('integrations/', views_integrations.integrations, name='integrations'),
    path('integrations/web-forms/', views_integrations.integrations_web_forms, name='integrations_web_forms'),
    path('integrations/mercadolibre/', include('crm.integrations_mercadolibre_urls')),
    
    # Mail
    path('mail/', include('crm.mail_urls')),
    
    # WhatsApp
    path('whatsapp/', include('crm.whatsapp_urls')),
    
    # Settings
    path('settings/', views_settings_new.settings_index, name='settings'),
    path('settings/company/', views_settings_new.settings_company, name='settings_company'),
    path('settings/users/', views_settings_new.settings_users, name='settings_users'),
    path('settings/users/create/', views_settings_new.settings_user_create, name='settings_user_create'),
    path('settings/users/<int:user_id>/edit/', views_settings_new.settings_user_edit, name='settings_user_edit'),
    path('settings/users/<int:user_id>/delete/', views_settings_new.settings_user_delete, name='settings_user_delete'),
    path('settings/security/', views_settings_new.settings_security, name='settings_security'),
    path('settings/support/', views_settings_new.settings_support, name='settings_support'),
    path('settings/support/create/', views_settings_new.settings_support_create, name='settings_support_create'),
    path('settings/support/<int:ticket_id>/', views_settings_new.settings_support_view, name='settings_support_view'),
    
    # Leads
    path('leads/', views_leads.leads_list, name='leads_list'),
    path('leads/<int:lead_id>/convert/', views_leads.convert_lead_to_contact, name='convert_lead'),
    
    # Contacts
    path('contacts/', views.contacts_list, name='contacts'),
    path('contacts/create/', views.create_contact, name='create_contact'),
    path('contacts/<int:contact_id>/', views_contacts.contact_profile, name='contact_profile'),
    path('contacts/<int:contact_id>/note/', views_contacts.add_contact_note, name='add_contact_note'),
    path('contacts/<int:contact_id>/whatsapp/', views.get_whatsapp_url, name='get_whatsapp_url'),
    path('pipeline/', views.pipeline, name='pipeline'),
    path('pipelines/manage/', views.manage_pipelines, name='manage_pipelines'),
    path('pipelines/create/', views.create_pipeline, name='create_pipeline'),
    path('pipelines/<int:pipeline_id>/edit/', views.edit_pipeline, name='edit_pipeline'),
    path('pipelines/<int:pipeline_id>/delete/', views.delete_pipeline, name='delete_pipeline'),
    path('pipelines/<int:pipeline_id>/stages/create/', views.create_stage, name='create_stage'),
    path('stages/<int:stage_id>/edit/', views.edit_stage, name='edit_stage'),
    path('stages/<int:stage_id>/delete/', views.delete_stage, name='delete_stage'),
    path('deals/create/', views.create_deal, name='create_deal'),
    path('deals/<int:deal_id>/edit/', views.edit_deal, name='edit_deal'),
    path('deals/<int:deal_id>/delete/', views.delete_deal, name='delete_deal'),
    path('deals/<int:deal_id>/get/', views.get_deal, name='get_deal'),
    path('deals/<int:deal_id>/update-stage/', views.update_deal_stage, name='update_deal_stage'),
    path('templates/manage/', views.manage_templates, name='manage_templates'),
    path('templates/create/', views.create_template, name='create_template'),
    path('templates/<int:template_id>/edit/', views.edit_template, name='edit_template'),
    path('templates/<int:template_id>/delete/', views.delete_template, name='delete_template'),
    path('templates/json/', views.get_templates_json, name='get_templates_json'),
]
