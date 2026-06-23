from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from accounts.models import Company
from .models import Lead
from .serializers import LeadSerializer

def get_client_ip(request):
    """Obtener la IP real del cliente considerando proxies"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def create_lead(request):
    """
    Endpoint para recibir leads desde formularios web externos.
    
    Requiere header: x-api-key con la API Key de la empresa.
    
    Body JSON:
    {
        "name": "Juan Perez",
        "email": "juan@gmail.com",
        "phone": "1133334444",
        "message": "Quiero más información",
        "source": "facebook",  // Opcional: website, facebook, instagram, etc.
        "metadata": {  // Opcional: datos adicionales
            "page": "/contacto",
            "campaign": "google_ads_verano",
            "utm_source": "google",
            "utm_medium": "cpc"
        }
    }
    """
    # Obtener API Key del header
    api_key = request.headers.get('x-api-key')
    
    if not api_key:
        return Response(
            {'error': 'API Key requerida. Incluya el header x-api-key'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    # Buscar la empresa por API Key
    try:
        company = Company.objects.get(api_key=api_key)
    except Company.DoesNotExist:
        return Response(
            {'error': 'API Key inválida'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    # Validar datos del lead
    serializer = LeadSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(
            {'error': 'Datos inválidos', 'details': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Agregar IP del cliente al metadata si no existe
    lead_data = serializer.validated_data
    if 'metadata' not in lead_data or lead_data['metadata'] is None:
        lead_data['metadata'] = {}
    
    # Agregar IP automáticamente
    lead_data['metadata']['ip'] = get_client_ip(request)
    lead_data['metadata']['user_agent'] = request.META.get('HTTP_USER_AGENT', '')
    
    # Crear el lead asociado a la empresa
    lead = Lead.objects.create(company=company, **lead_data)
    
    return Response(
        {
            'success': True,
            'message': 'Lead registrado exitosamente',
            'lead': {
                'id': lead.id,
                'name': lead.name,
                'email': lead.email,
                'source': lead.source,
                'created_at': lead.created_at.isoformat()
            }
        },
        status=status.HTTP_201_CREATED
    )
