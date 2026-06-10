from django.contrib import admin
from .models import Contact, Stage, Deal, Activity, Task, Pipeline, MessageTemplate, Lead
from .integrations_mercadolibre_models import (
    MercadoLibreOAuthState, MercadoLibreIntegration, MercadoLibreWebhookEvent,
    MercadoLibreProduct, MercadoLibreOrder, MercadoLibreOrderItem,
    MercadoLibreMessage, MercadoLibreQuestion, MercadoLibreReplyTemplate,
)

@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ('name', 'company', 'status', 'owner')
    list_filter = ('company', 'status', 'owner')

@admin.register(Stage)
class StageAdmin(admin.ModelAdmin):
    list_display = ('name', 'company', 'order')
    list_filter = ('company',)

@admin.register(Deal)
class DealAdmin(admin.ModelAdmin):
    list_display = ('title', 'company', 'stage', 'value', 'owner')
    list_filter = ('company', 'stage', 'owner')

@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ('contact', 'type', 'user', 'created_at')
    list_filter = ('type', 'user')

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'company', 'due_date', 'priority', 'completed')
    list_filter = ('company', 'priority', 'completed')

@admin.register(Pipeline)
class PipelineAdmin(admin.ModelAdmin):
    list_display = ['name', 'company', 'is_default', 'color', 'created_at']
    list_filter = ['is_default', 'company', 'created_at']
    search_fields = ['name', 'description']

@admin.register(MessageTemplate)
class MessageTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'company', 'is_active', 'created_at']
    list_filter = ['is_active', 'company', 'created_at']
    search_fields = ['name', 'message', 'description']

@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'phone', 'company', 'source', 'created_at']
    list_filter = ['company', 'source', 'created_at']
    search_fields = ['name', 'email', 'phone', 'message']
    readonly_fields = ['created_at', 'updated_at', 'metadata']
    fieldsets = (
        ('Información del Lead', {
            'fields': ('name', 'email', 'phone', 'message', 'company')
        }),
        ('Origen y Tracking', {
            'fields': ('source', 'metadata')
        }),
        ('Fechas', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


# MercadoLibre Admin
@admin.register(MercadoLibreOAuthState)
class MercadoLibreOAuthStateAdmin(admin.ModelAdmin):
    list_display = ['state', 'user', 'company', 'created_at']
    list_filter = ['created_at']
    search_fields = ['state', 'user__email']
    readonly_fields = ['state', 'user', 'company', 'created_at']

@admin.register(MercadoLibreIntegration)
class MercadoLibreIntegrationAdmin(admin.ModelAdmin):
    list_display = ['nickname', 'company', 'ml_user_id', 'is_active', 'created_at']
    list_filter = ['is_active', 'site_id']
    search_fields = ['nickname', 'ml_user_id', 'email']

@admin.register(MercadoLibreOrder)
class MercadoLibreOrderAdmin(admin.ModelAdmin):
    list_display = ['ml_order_id', 'buyer_nickname', 'total_amount', 'status', 'company', 'date_created']
    list_filter = ['status', 'company']
    search_fields = ['ml_order_id', 'buyer_nickname', 'buyer_email']
    raw_id_fields = ['contact', 'deal', 'lead']

class MercadoLibreOrderItemInline(admin.TabularInline):
    model = MercadoLibreOrderItem
    extra = 0

@admin.register(MercadoLibreProduct)
class MercadoLibreProductAdmin(admin.ModelAdmin):
    list_display = ['ml_item_id', 'title', 'price', 'available_quantity', 'status', 'company']
    list_filter = ['status', 'company']
    search_fields = ['ml_item_id', 'title']

@admin.register(MercadoLibreMessage)
class MercadoLibreMessageAdmin(admin.ModelAdmin):
    list_display = ['ml_message_id', 'sender_nickname', 'is_from_buyer', 'text', 'message_date']
    list_filter = ['is_from_buyer', 'company']
    search_fields = ['sender_nickname', 'text']

@admin.register(MercadoLibreQuestion)
class MercadoLibreQuestionAdmin(admin.ModelAdmin):
    list_display = ['ml_question_id', 'from_nickname', 'text', 'status', 'date_created']
    list_filter = ['status', 'company']
    search_fields = ['from_nickname', 'text']

@admin.register(MercadoLibreWebhookEvent)
class MercadoLibreWebhookEventAdmin(admin.ModelAdmin):
    list_display = ['topic', 'ml_user_id', 'status', 'received_at', 'processed_at']
    list_filter = ['topic', 'status']
    search_fields = ['ml_user_id', 'resource']
    readonly_fields = ['raw_payload']

@admin.register(MercadoLibreReplyTemplate)
class MercadoLibreReplyTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'company', 'is_active', 'priority', 'usable_in_questions', 'usable_in_messages', 'times_used', 'created_at']
    list_filter = ['is_active', 'company', 'priority', 'usable_in_questions', 'usable_in_messages']
    search_fields = ['name', 'response_text']
