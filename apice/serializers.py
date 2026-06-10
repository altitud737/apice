from rest_framework import serializers
from .models import Lead

class LeadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lead
        fields = ['name', 'email', 'phone', 'message', 'source', 'metadata']
        extra_kwargs = {
            'source': {'required': False, 'default': 'website'},
            'metadata': {'required': False}
        }
    
    def validate_email(self, value):
        """Validar formato de email"""
        if not value:
            raise serializers.ValidationError("El email es requerido")
        return value.lower()
    
    def validate_name(self, value):
        """Validar que el nombre no esté vacío"""
        if not value or not value.strip():
            raise serializers.ValidationError("El nombre es requerido")
        return value.strip()
    
    def validate_source(self, value):
        """Validar que source sea uno de los valores permitidos"""
        valid_sources = [choice[0] for choice in Lead.SOURCE_CHOICES]
        if value and value not in valid_sources:
            # Si no es válido, usar 'other' como fallback
            return 'other'
        return value or 'website'
