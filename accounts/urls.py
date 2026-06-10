from django.urls import path
from . import views
from . import views_admin
from . import views_demo

app_name = 'accounts'

# Las URLs de autenticación ahora las maneja django-allauth
# Ver: /accounts/ (allauth.urls)
urlpatterns = [
    # Solicitud de Demo (público)
    path('request-demo/', views_demo.request_demo, name='request_demo'),
    path('demo-success/', views_demo.demo_success, name='demo_success'),
    
    # Panel de Super Administrador
    path('admin/dashboard/', views_admin.admin_dashboard, name='admin_dashboard'),
    
    # Gestión de Empresas
    path('admin/companies/', views_admin.admin_companies, name='admin_companies'),
    path('admin/companies/create/', views_admin.admin_create_client, name='admin_create_client'),
    path('admin/companies/<int:company_id>/', views_admin.admin_company_detail, name='admin_company_detail'),
    path('admin/companies/<int:company_id>/delete/', views_admin.admin_delete_company, name='admin_delete_company'),
    path('admin/companies/<int:company_id>/toggle-status/', views_admin.admin_toggle_company_status, name='admin_toggle_company_status'),
    path('admin/companies/<int:company_id>/configure-mail/', views_admin.admin_configure_mail, name='admin_configure_mail'),
    
    # Gestión de Usuarios
    path('admin/users/', views_admin.admin_users, name='admin_users'),
    path('admin/users/<int:user_id>/', views_admin.admin_user_detail, name='admin_user_detail'),
    path('admin/users/<int:user_id>/reset-password/', views_admin.admin_reset_password, name='admin_reset_password'),
    path('admin/users/<int:user_id>/impersonate/', views_admin.admin_impersonate_user, name='admin_impersonate_user'),
    path('admin/stop-impersonating/', views_admin.admin_stop_impersonating, name='admin_stop_impersonating'),
    
    # Gestión de Tickets de Soporte
    path('admin/tickets/', views_admin.admin_tickets, name='admin_tickets'),
    path('admin/tickets/<int:ticket_id>/', views_admin.admin_ticket_detail, name='admin_ticket_detail'),
    
    # Gestión de Solicitudes de Demo
    path('admin/demos/', views_admin.admin_demos, name='admin_demos'),
    path('admin/demos/<int:demo_id>/', views_admin.admin_demo_detail, name='admin_demo_detail'),
    
    # Notificaciones del Sistema (Admin)
    path('admin/notifications/', views_admin.admin_notifications, name='admin_notifications'),
    path('admin/notifications/create/', views_admin.admin_create_notification, name='admin_create_notification'),
    path('admin/notifications/<int:notification_id>/delete/', views_admin.admin_delete_notification, name='admin_delete_notification'),
]
