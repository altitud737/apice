"""
URLs para integración con MercadoLibre
"""
from django.urls import path
from . import integrations_mercadolibre_views as views

app_name = 'mercadolibre'

urlpatterns = [
    # OAuth flow
    path('connect/', views.mercadolibre_connect, name='connect'),
    path('callback/', views.mercadolibre_callback, name='callback'),
    path('disconnect/', views.mercadolibre_disconnect, name='disconnect'),
    
    # Webhook
    path('webhook/', views.mercadolibre_webhook, name='webhook'),
    
    # Status
    path('status/', views.mercadolibre_status, name='status'),
    
    # Auto-Reply Templates CRUD
    path('autoreply/', views.autoreply_templates_list, name='autoreply_list'),
    path('autoreply/create/', views.autoreply_template_create, name='autoreply_create'),
    path('autoreply/<int:template_id>/edit/', views.autoreply_template_edit, name='autoreply_edit'),
    path('autoreply/<int:template_id>/delete/', views.autoreply_template_delete, name='autoreply_delete'),
    path('autoreply/<int:template_id>/toggle/', views.autoreply_template_toggle, name='autoreply_toggle'),
    
    # Product Management
    path('products/', views.products_list, name='products_list'),
    path('products/sync/', views.products_sync, name='products_sync'),
    path('products/<int:product_id>/edit/', views.product_edit, name='product_edit'),
    path('products/<int:product_id>/pause/', views.product_change_status, {'new_status': 'paused'}, name='product_pause'),
    path('products/<int:product_id>/activate/', views.product_change_status, {'new_status': 'active'}, name='product_activate'),
    path('products/<int:product_id>/close/', views.product_change_status, {'new_status': 'closed'}, name='product_close'),
    
    # Questions Inbox (Module A)
    path('questions/', views.questions_inbox, name='questions_inbox'),
    path('questions/list/', views.questions_inbox_list, name='questions_inbox_list'),
    path('questions/<int:question_id>/', views.question_detail, name='question_detail'),
    path('questions/<int:question_id>/reply/', views.question_reply, name='question_reply'),
    path('questions/<int:question_id>/ignore/', views.question_ignore, name='question_ignore'),
    
    # Messages Inbox (Module B)
    path('messages/', views.messages_inbox, name='messages_inbox'),
    path('messages/list/', views.messages_inbox_list, name='messages_inbox_list'),
    path('messages/<str:pack_id>/', views.conversation_detail, name='conversation_detail'),
    path('messages/<str:pack_id>/reply/', views.message_reply, name='message_reply'),
    
    # Orders (Module C)
    path('orders/', views.orders_list, name='orders_list'),
    path('orders/<int:order_id>/', views.order_detail, name='order_detail'),
    path('orders/<int:order_id>/label/', views.shipment_label_download, name='shipment_label'),
    
    # Buyer Profile (Module D)
    path('buyer/<int:buyer_id>/', views.buyer_profile, name='buyer_profile'),
    
    # Metrics Dashboard (Module E)
    path('metrics/', views.metrics_dashboard, name='metrics_dashboard'),
    
    # Product Ads (Module F)
    path('ads/', views.ads_list, name='ads_list'),
    path('ads/<str:campaign_id>/toggle/', views.ad_campaign_toggle, name='ad_campaign_toggle'),
    path('ads/<str:campaign_id>/budget/', views.ad_campaign_budget, name='ad_campaign_budget'),
    
    # Promotions (Module G)
    path('promotions/', views.promotions_list, name='promotions_list'),
    path('promotions/<str:item_id>/create/', views.promotion_create, name='promotion_create'),
    path('promotions/<str:item_id>/<str:promotion_id>/delete/', views.promotion_delete, name='promotion_delete'),
    
    # Categories & Item Creation (Module H)
    path('categories/', views.categories_index, name='categories_index'),
    path('items/create/', views.item_create, name='item_create'),
    
    # JSON APIs
    path('api/products/', views.products_api_list, name='products_api'),
    path('api/status/', views.status_api, name='status_api'),
    path('api/categories/root/', views.root_categories_api, name='root_categories_api'),
    path('api/categories/<str:category_id>/children/', views.category_children_api, name='category_children_api'),
    path('api/categories/<str:category_id>/attributes/', views.category_attributes_api, name='category_attributes_api'),
    path('api/categories/predict/', views.predict_category_api, name='predict_category_api'),
]
