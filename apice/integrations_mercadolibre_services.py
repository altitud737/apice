"""
Servicios para integración con MercadoLibre OAuth2 y API.
Arquitectura desacoplada: OAuth → API Client → Event Processors → CRM Sync
"""
import requests
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.db import transaction
from datetime import timedelta
import logging
import re

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# OAuth Service
# ---------------------------------------------------------------------------
class MercadoLibreOAuthService:
    """Maneja OAuth2 con MercadoLibre: auth URL, token exchange, refresh."""

    AUTH_URL = "https://auth.mercadolibre.com.ar/authorization"
    TOKEN_URL = "https://api.mercadolibre.com/oauth/token"
    USER_INFO_URL = "https://api.mercadolibre.com/users/me"

    def __init__(self):
        self.client_id = settings.ML_CLIENT_ID
        self.client_secret = settings.ML_CLIENT_SECRET
        self.redirect_uri = settings.ML_REDIRECT_URI

    def get_authorization_url(self, state=None):
        from urllib.parse import urlencode
        params = {
            'response_type': 'code',
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
        }
        if state:
            params['state'] = state
        url = f"{self.AUTH_URL}?{urlencode(params)}"
        logger.info(f"ML Auth URL: {url}")
        return url

    def exchange_code_for_token(self, code):
        payload = {
            'grant_type': 'authorization_code',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': code,
            'redirect_uri': self.redirect_uri,
        }
        try:
            response = requests.post(self.TOKEN_URL, json=payload, timeout=15)
            response.raise_for_status()
            data = response.json()
            expires_in = data.get('expires_in', 21600)
            return {
                'access_token': data['access_token'],
                'refresh_token': data['refresh_token'],
                'user_id': str(data['user_id']),
                'expires_in': expires_in,
                'token_expires_at': timezone.now() + timedelta(seconds=expires_in),
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"ML OAuth exchange error: {e}")
            raise Exception(f"Error al obtener token de MercadoLibre: {e}")

    def refresh_access_token(self, refresh_token):
        payload = {
            'grant_type': 'refresh_token',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'refresh_token': refresh_token,
        }
        try:
            response = requests.post(self.TOKEN_URL, json=payload, timeout=15)
            response.raise_for_status()
            data = response.json()
            expires_in = data.get('expires_in', 21600)
            return {
                'access_token': data['access_token'],
                'refresh_token': data['refresh_token'],
                'expires_in': expires_in,
                'token_expires_at': timezone.now() + timedelta(seconds=expires_in),
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"ML token refresh error: {e}")
            raise Exception(f"Error al refrescar token: {e}")

    def get_user_info(self, access_token):
        headers = {'Authorization': f'Bearer {access_token}'}
        try:
            response = requests.get(self.USER_INFO_URL, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"ML user info error: {e}")
            raise Exception(f"Error al obtener info del usuario: {e}")


# ---------------------------------------------------------------------------
# API Client (with auto-refresh)
# ---------------------------------------------------------------------------
class MercadoLibreAPIClient:
    """
    Cliente HTTP para la API de MercadoLibre.
    Refresca tokens automáticamente cuando están por expirar.
    """
    BASE_URL = "https://api.mercadolibre.com"

    def __init__(self, integration):
        self.integration = integration
        self._ensure_valid_token()

    def _ensure_valid_token(self):
        if self.integration.needs_refresh():
            try:
                oauth = MercadoLibreOAuthService()
                new_tokens = oauth.refresh_access_token(self.integration.refresh_token)
                self.integration.access_token = new_tokens['access_token']
                self.integration.refresh_token = new_tokens['refresh_token']
                self.integration.token_expires_at = new_tokens['token_expires_at']
                self.integration.save(update_fields=[
                    'access_token', 'refresh_token', 'token_expires_at', 'updated_at'
                ])
                logger.info(f"Token refreshed for integration {self.integration.id}")
            except Exception as e:
                logger.error(f"Auto-refresh failed for integration {self.integration.id}: {e}")

    @property
    def _headers(self):
        return {
            'Authorization': f'Bearer {self.integration.access_token}',
            'Content-Type': 'application/json',
        }

    def get(self, endpoint, **kwargs):
        return self._request('GET', endpoint, **kwargs)

    def post(self, endpoint, **kwargs):
        return self._request('POST', endpoint, **kwargs)

    def put(self, endpoint, **kwargs):
        return self._request('PUT', endpoint, **kwargs)

    def _request(self, method, endpoint, _retried=False, **kwargs):
        url = endpoint if endpoint.startswith('http') else f"{self.BASE_URL}{endpoint}"
        try:
            resp = requests.request(method, url, headers=self._headers, timeout=15, **kwargs)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.HTTPError as e:
            # Auto-retry on 401: refresh token and try once more
            if e.response.status_code == 401 and not _retried:
                logger.warning(f"ML API 401 on {method} {endpoint} → attempting token refresh and retry")
                try:
                    self._force_refresh_token()
                    return self._request(method, endpoint, _retried=True, **kwargs)
                except Exception as refresh_err:
                    logger.error(f"ML API token refresh failed during retry: {refresh_err}")
            logger.error(f"ML API {method} {endpoint} → {e.response.status_code}: {e.response.text[:300]}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"ML API {method} {endpoint} → {e}")
            raise

    def _force_refresh_token(self):
        """Fuerza un refresh del token sin importar si está expirado o no."""
        oauth = MercadoLibreOAuthService()
        new_tokens = oauth.refresh_access_token(self.integration.refresh_token)
        self.integration.access_token = new_tokens['access_token']
        self.integration.refresh_token = new_tokens['refresh_token']
        self.integration.token_expires_at = new_tokens['token_expires_at']
        self.integration.save(update_fields=[
            'access_token', 'refresh_token', 'token_expires_at', 'updated_at'
        ])
        logger.info(f"Token force-refreshed for integration {self.integration.id}")

    # Convenience methods
    def get_order(self, order_id):
        return self.get(f"/orders/{order_id}")

    def get_item(self, item_id):
        return self.get(f"/items/{item_id}")

    def get_question(self, question_id):
        return self.get(f"/questions/{question_id}")

    def get_shipment(self, shipment_id):
        return self.get(f"/shipments/{shipment_id}")

    def get_shipment_label_pdf(self, shipment_id):
        """Returns raw PDF bytes for the shipment label."""
        url = f"{self.BASE_URL}/shipment_labels?shipment_ids={shipment_id}"
        self._ensure_token()
        headers = {
            'Authorization': f'Bearer {self.integration.access_token}',
            'Accept': 'application/pdf',
        }
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        return resp.content

    def get_message(self, resource_path):
        return self.get(resource_path)

    def get_user(self, user_id):
        return self.get(f"/users/{user_id}")

    def answer_question(self, question_id, text):
        return self.post('/answers', json={'question_id': question_id, 'text': text})

    def send_message(self, pack_id, seller_id, buyer_id, text):
        return self.post(f"/messages/packs/{pack_id}/sellers/{seller_id}", json={
            'from': {'user_id': seller_id},
            'to': {'user_id': buyer_id},
            'text': text,
        })

    def get_user_items(self, user_id, offset=0, limit=50):
        return self.get(f"/users/{user_id}/items/search", params={'offset': offset, 'limit': limit})

    def search_items_by_seller(self, seller_id, site_id='MLA', offset=0, limit=50):
        return self.get(f"/sites/{site_id}/search", params={
            'seller_id': seller_id, 'offset': offset, 'limit': limit,
        })

    def update_item(self, item_id, data):
        return self.put(f"/items/{item_id}", json=data)

    def get_buyer_claims(self, seller_id, buyer_id):
        """Get claims/reclamos for a specific buyer. May return 403 if no access."""
        return self.get(f"/v1/claims/search", params={
            'seller_id': seller_id,
            'receiver_id': buyer_id,
            'limit': 20,
        })

    def get_seller_reputation(self):
        """Get current seller's full user data including seller_reputation."""
        return self.get(f"/users/{self.integration.ml_user_id}")

    # --- Product Ads (Module F) ---
    def get_ad_campaigns(self):
        """List all Product Ads campaigns for the seller."""
        return self.get(f"/advertising/product_ads/campaigns/{self.integration.ml_user_id}")

    def get_campaign_detail(self, campaign_id):
        """Get a single campaign's details."""
        return self.get(f"/advertising/product_ads/campaigns/{self.integration.ml_user_id}/{campaign_id}")

    def update_campaign_status(self, campaign_id, new_status):
        """Pause or activate a campaign. new_status: 'paused' or 'active'."""
        return self.put(
            f"/advertising/product_ads/campaigns/{self.integration.ml_user_id}/{campaign_id}",
            json={'status': new_status},
        )

    def get_campaign_items(self, campaign_id):
        """Get items (ads) within a campaign."""
        return self.get(
            f"/advertising/product_ads/campaigns/{self.integration.ml_user_id}/{campaign_id}/items"
        )

    def update_campaign_budget(self, campaign_id, daily_budget):
        """Update a campaign's daily budget."""
        return self.put(
            f"/advertising/product_ads/campaigns/{self.integration.ml_user_id}/{campaign_id}",
            json={'daily_budget': float(daily_budget)},
        )

    # --- Promotions / Deals (Module G) ---
    def get_item_deals(self, item_id):
        """Get active deals/promotions for a specific item."""
        return self.get(f"/items/{item_id}/deals/search")

    def create_item_promotion(self, item_id, deal_price, start_date, finish_date):
        """Create a price discount on an item."""
        return self.post(f"/seller-promotions/items/{item_id}", json={
            'deal_price': float(deal_price),
            'start_date': start_date,
            'finish_date': finish_date,
        })

    def delete_item_promotion(self, item_id, promotion_id):
        """Delete/cancel a promotion from an item."""
        url = f"{self.BASE_URL}/seller-promotions/items/{item_id}/promotions/{promotion_id}"
        self._ensure_token()
        headers = {
            'Authorization': f'Bearer {self.integration.access_token}',
            'Content-Type': 'application/json',
        }
        resp = requests.delete(url, headers=headers, timeout=15)
        resp.raise_for_status()
        return resp.json() if resp.text else {}

    def get_available_campaigns(self):
        """Get commercial campaigns available to the seller (Hot Sale, CyberMonday, etc)."""
        return self.get(
            f"/seller-promotions/promotions/search",
            params={'seller_id': self.integration.ml_user_id, 'status': 'candidate'},
        )

    def get_seller_promotions(self):
        """Get all active promotions for the seller."""
        return self.get(
            f"/seller-promotions/items/search",
            params={'seller_id': self.integration.ml_user_id},
        )

    # --- Categories & Item Creation (Module H) ---
    def get_site_categories(self, site_id='MLA'):
        """Get root categories for a site."""
        return self.get(f"/sites/{site_id}/categories")

    def get_category(self, category_id):
        """Get category details including children_categories."""
        return self.get(f"/categories/{category_id}")

    def get_category_attributes(self, category_id):
        """Get required/optional attributes for listing in this category."""
        return self.get(f"/categories/{category_id}/attributes")

    def predict_category(self, title, site_id='MLA'):
        """Predict the best category for a given title."""
        return self.get(f"/sites/{site_id}/domain_discovery/search", params={'q': title})

    def get_listing_types(self, site_id='MLA'):
        """Get available listing types (gold_special, gold_pro, etc)."""
        return self.get(f"/sites/{site_id}/listing_types")

    def create_item(self, data):
        """Create a new item/listing on MercadoLibre."""
        return self.post("/items", json=data)

    def upload_item_description(self, item_id, plain_text):
        """Set the description for an item after creation."""
        return self.post(f"/items/{item_id}/description", json={
            'plain_text': plain_text,
        })

    def get_currency(self, currency_id='ARS'):
        """Get currency details."""
        return self.get(f"/currencies/{currency_id}")


# ---------------------------------------------------------------------------
# CRM Sync Service
# ---------------------------------------------------------------------------
class MercadoLibreCRMSync:
    """
    Crea/actualiza entidades CRM (Contact, Lead, Deal) a partir de datos de ML.
    """

    def __init__(self, integration):
        self.integration = integration
        self.company = integration.company

    def get_or_create_contact_from_buyer(self, buyer_id, buyer_data=None):
        """Busca o crea un Contact CRM a partir de un comprador ML."""
        from .models import Contact
        from .integrations_mercadolibre_models import MercadoLibreOrder

        # Check if we already have a contact linked to this buyer via previous orders
        existing_order = MercadoLibreOrder.objects.filter(
            buyer_id=buyer_id,
            contact__isnull=False,
            company=self.company,
        ).select_related('contact').first()

        if existing_order and existing_order.contact:
            return existing_order.contact, False

        # Fallback: search by name + source
        if buyer_data:
            nickname = buyer_data.get('nickname', '')
            first_name = buyer_data.get('first_name', '')
            last_name = buyer_data.get('last_name', '')
            full_name = f"{first_name} {last_name}".strip() or nickname

            if full_name:
                existing = Contact.objects.filter(
                    company=self.company,
                    name=full_name,
                    source='mercadolibre',
                ).first()
                if existing:
                    return existing, False

        # Create new contact
        nickname = ''
        first_name = ''
        last_name = ''
        email = ''
        phone = ''

        if buyer_data:
            nickname = buyer_data.get('nickname', '')
            first_name = buyer_data.get('first_name', '')
            last_name = buyer_data.get('last_name', '')
            email = buyer_data.get('email', '')
            phone_data = buyer_data.get('phone', {})
            if isinstance(phone_data, dict):
                area = phone_data.get('area_code', '')
                number = phone_data.get('number', '')
                phone = f"{area}{number}" if area or number else ''
            elif isinstance(phone_data, str):
                phone = phone_data

        full_name = f"{first_name} {last_name}".strip() or nickname or f"ML Buyer {buyer_id}"

        contact = Contact.objects.create(
            company=self.company,
            name=full_name,
            email=email,
            phone=phone,
            source='mercadolibre',
            status='Nuevo',
            interest_level='Alto',
        )
        logger.info(f"Contact created from ML buyer {buyer_id}: {contact.name}")
        return contact, True

    def create_lead_from_order(self, order_obj):
        """Crea un Lead CRM a partir de una orden ML."""
        from .models import Lead

        name = f"{order_obj.buyer_first_name} {order_obj.buyer_last_name}".strip()
        name = name or order_obj.buyer_nickname or f"ML Buyer {order_obj.buyer_id}"

        lead = Lead.objects.create(
            company=self.company,
            name=name,
            email=order_obj.buyer_email or f"ml_{order_obj.buyer_id}@mercadolibre.com",
            phone=order_obj.buyer_phone,
            source='mercadolibre',
            status='qualified',
            message=f"Orden ML #{order_obj.ml_order_id} - ${order_obj.total_amount}",
            metadata={
                'ml_order_id': order_obj.ml_order_id,
                'ml_buyer_id': order_obj.buyer_id,
                'ml_total': str(order_obj.total_amount),
            },
        )
        logger.info(f"Lead created from ML order #{order_obj.ml_order_id}: {lead.name}")
        return lead

    def create_deal_from_order(self, order_obj, contact):
        """Crea un Deal CRM a partir de una orden ML."""
        from .models import Deal, Pipeline, Stage

        pipeline = Pipeline.objects.filter(company=self.company, is_default=True).first()
        if not pipeline:
            pipeline = Pipeline.objects.filter(company=self.company).first()
        if not pipeline:
            logger.warning(f"No pipeline found for company {self.company.id}, skipping deal creation")
            return None

        # Elegir stage según status de la orden
        stage = None
        if order_obj.status in ('paid', 'confirmed'):
            stage = pipeline.stages.filter(name__icontains='ganad').first() or \
                    pipeline.stages.filter(name__icontains='cerrad').first() or \
                    pipeline.stages.order_by('-order').first()
        else:
            stage = pipeline.stages.order_by('order').first()

        if not stage:
            logger.warning(f"No stages in pipeline {pipeline.id}, skipping deal")
            return None

        items_desc = ", ".join([
            item.title for item in order_obj.items.all()
        ]) or "Productos MercadoLibre"

        deal = Deal.objects.create(
            company=self.company,
            title=f"ML #{order_obj.ml_order_id} - {items_desc[:100]}",
            value=order_obj.total_amount,
            contact=contact,
            stage=stage,
            probability=100 if order_obj.status == 'paid' else 70,
            expected_close_date=timezone.now().date() + timedelta(days=7),
        )
        logger.info(f"Deal created from ML order #{order_obj.ml_order_id}: {deal.title}")
        return deal

    def create_lead_from_question(self, question_obj):
        """Crea un Lead CRM a partir de una pregunta ML."""
        from .models import Lead

        product_title = question_obj.product.title if question_obj.product else "Publicación ML"
        name = question_obj.from_nickname or f"ML User {question_obj.from_id}"

        existing = Lead.objects.filter(
            company=self.company,
            source='mercadolibre',
            metadata__ml_question_id=question_obj.ml_question_id,
        ).first()
        if existing:
            return existing

        lead = Lead.objects.create(
            company=self.company,
            name=name,
            email=f"ml_{question_obj.from_id}@mercadolibre.com",
            source='mercadolibre',
            status='new',
            message=f"Pregunta sobre: {product_title}\n\n{question_obj.text}",
            metadata={
                'ml_question_id': question_obj.ml_question_id,
                'ml_item_id': question_obj.ml_item_id,
                'ml_from_id': question_obj.from_id,
            },
        )
        logger.info(f"Lead created from ML question #{question_obj.ml_question_id}")
        return lead


# ---------------------------------------------------------------------------
# Product Management Service
# ---------------------------------------------------------------------------
class MercadoLibreProductService:
    """
    Gestión de productos/publicaciones de MercadoLibre.
    Sincronización, edición de precio/stock, pausar/activar/cerrar.
    """

    LOW_STOCK_THRESHOLD = 3

    def __init__(self, integration):
        self.integration = integration
        self.company = integration.company
        self.api = MercadoLibreAPIClient(integration)

    def get_user_items(self):
        """
        Obtiene todos los IDs de items del usuario.
        Estrategia con fallbacks:
        1. GET /users/{id}/items/search (privado, producción)
        2. GET /sites/{site}/search?seller_id= (público)
        3. Recopilar IDs conocidos de la DB local (preguntas, productos existentes)
        """
        # Intento 1: endpoint privado
        try:
            ids = self._fetch_items_private()
            if ids:
                return ids
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 403:
                logger.warning("ProductSync: /users/items/search returned 403")
            else:
                raise

        # Intento 2: búsqueda pública
        try:
            ids = self._fetch_items_public()
            if ids:
                return ids
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 403:
                logger.warning("ProductSync: /sites/search returned 403")
            else:
                raise

        # Intento 3: recopilar IDs conocidos de la DB local
        logger.warning("ProductSync: API endpoints blocked, collecting item IDs from local DB")
        return self._collect_known_item_ids()

    def _fetch_items_private(self):
        """Obtiene IDs via endpoint privado /users/{id}/items/search."""
        all_item_ids = []
        offset = 0
        limit = 50

        while True:
            data = self.api.get_user_items(self.integration.ml_user_id, offset=offset, limit=limit)
            item_ids = data.get('results', [])
            total = data.get('paging', {}).get('total', 0)

            all_item_ids.extend(item_ids)
            offset += limit

            logger.info(f"ProductSync: (private) fetched {len(all_item_ids)}/{total} item IDs")

            if offset >= total or not item_ids:
                break

        return all_item_ids

    def _fetch_items_public(self):
        """Obtiene IDs via endpoint público /sites/{site}/search?seller_id=."""
        all_item_ids = []
        offset = 0
        limit = 50
        site_id = self.integration.site_id or 'MLA'

        while True:
            data = self.api.search_items_by_seller(
                self.integration.ml_user_id, site_id=site_id,
                offset=offset, limit=limit,
            )
            results = data.get('results', [])
            total = data.get('paging', {}).get('total', 0)

            for item in results:
                item_id = item.get('id', '')
                if item_id and item_id not in all_item_ids:
                    all_item_ids.append(item_id)

            offset += limit

            logger.info(f"ProductSync: (public) fetched {len(all_item_ids)}/{total} item IDs")

            if offset >= total or not results:
                break

        return all_item_ids

    def _collect_known_item_ids(self):
        """Recopila item IDs conocidos de fuentes locales (preguntas, productos, órdenes)."""
        from .integrations_mercadolibre_models import (
            MercadoLibreProduct, MercadoLibreQuestion, MercadoLibreOrderItem,
        )

        known_ids = set()

        # IDs de productos ya sincronizados
        existing = MercadoLibreProduct.objects.filter(
            company=self.company
        ).values_list('ml_item_id', flat=True)
        known_ids.update(existing)

        # IDs de preguntas recibidas
        question_ids = MercadoLibreQuestion.objects.filter(
            company=self.company
        ).values_list('ml_item_id', flat=True).distinct()
        known_ids.update(qid for qid in question_ids if qid)

        # IDs de items en órdenes
        order_item_ids = MercadoLibreOrderItem.objects.filter(
            order__company=self.company
        ).values_list('ml_item_id', flat=True).distinct()
        known_ids.update(oid for oid in order_item_ids if oid)

        known_ids.discard('')
        logger.info(f"ProductSync: collected {len(known_ids)} known item IDs from local DB")
        return list(known_ids)

    def get_item_detail(self, item_id):
        """Obtiene detalle completo de un item."""
        return self.api.get_item(item_id)

    def sync_products(self):
        """
        Sincronización completa: obtiene todos los items del usuario,
        consulta detalle de cada uno, y crea/actualiza en la DB.
        Si GET /items/{id} falla con 403 (cuentas test), se omite ese item.
        Returns: dict con stats {created, updated, errors, skipped, total}
        """
        from .integrations_mercadolibre_models import MercadoLibreProduct

        item_ids = self.get_user_items()
        stats = {'created': 0, 'updated': 0, 'errors': 0, 'skipped': 0, 'total': len(item_ids)}

        for item_id in item_ids:
            try:
                item_data = self.get_item_detail(item_id)
                product, created = MercadoLibreProduct.objects.update_or_create(
                    ml_item_id=item_data['id'],
                    defaults={
                        'integration': self.integration,
                        'company': self.company,
                        'title': item_data.get('title', ''),
                        'category_id': item_data.get('category_id', ''),
                        'price': Decimal(str(item_data.get('price', 0))),
                        'currency_id': item_data.get('currency_id', 'ARS'),
                        'available_quantity': item_data.get('available_quantity', 0),
                        'sold_quantity': item_data.get('sold_quantity', 0),
                        'condition': item_data.get('condition', 'new'),
                        'listing_type_id': item_data.get('listing_type_id', ''),
                        'permalink': item_data.get('permalink', ''),
                        'thumbnail': item_data.get('thumbnail', ''),
                        'status': item_data.get('status', 'active'),
                        'last_synced_at': timezone.now(),
                        'raw_data': item_data,
                    }
                )
                if created:
                    stats['created'] += 1
                else:
                    stats['updated'] += 1
            except requests.exceptions.HTTPError as e:
                if e.response is not None and e.response.status_code == 403:
                    stats['skipped'] += 1
                    logger.warning(f"ProductSync: 403 on item {item_id} (test account restriction), skipped")
                else:
                    stats['errors'] += 1
                    logger.error(f"ProductSync: error syncing item {item_id}: {e}")
            except Exception as e:
                stats['errors'] += 1
                logger.error(f"ProductSync: error syncing item {item_id}: {e}")

        # Update integration last_sync_at
        self.integration.last_sync_at = timezone.now()
        self.integration.save(update_fields=['last_sync_at', 'updated_at'])

        logger.info(
            f"ProductSync: completed for {self.integration.nickname} - "
            f"total={stats['total']}, created={stats['created']}, "
            f"updated={stats['updated']}, skipped={stats['skipped']}, errors={stats['errors']}"
        )
        return stats

    def update_product(self, product_id, data):
        """
        Actualiza un producto en MercadoLibre y en la DB local.
        data puede contener: price, available_quantity, title
        
        PUT /items/{item_id}
        """
        from .integrations_mercadolibre_models import MercadoLibreProduct

        product = MercadoLibreProduct.objects.get(id=product_id, company=self.company)

        # Construir payload para ML API (solo campos permitidos)
        ml_payload = {}
        if 'price' in data:
            ml_payload['price'] = float(data['price'])
        if 'available_quantity' in data:
            ml_payload['available_quantity'] = int(data['available_quantity'])
        if 'title' in data:
            ml_payload['title'] = str(data['title'])

        if not ml_payload:
            raise ValueError("No hay campos válidos para actualizar")

        # Enviar a ML
        logger.info(f"ProductUpdate: updating {product.ml_item_id} with {ml_payload}")
        self.api.update_item(product.ml_item_id, ml_payload)

        # Refrescar desde ML para obtener datos actualizados
        refreshed = self.get_item_detail(product.ml_item_id)
        product.title = refreshed.get('title', product.title)
        product.price = Decimal(str(refreshed.get('price', product.price)))
        product.available_quantity = refreshed.get('available_quantity', product.available_quantity)
        product.sold_quantity = refreshed.get('sold_quantity', product.sold_quantity)
        product.status = refreshed.get('status', product.status)
        product.last_synced_at = timezone.now()
        product.raw_data = refreshed
        product.save()

        logger.info(f"ProductUpdate: {product.ml_item_id} updated successfully")
        return product

    def change_product_status(self, product_id, new_status):
        """
        Cambia el estado de una publicación en MercadoLibre.
        new_status: 'paused', 'active', 'closed'
        
        PUT /items/{item_id} {"status": "paused"}
        """
        from .integrations_mercadolibre_models import MercadoLibreProduct

        valid_statuses = ('paused', 'active', 'closed')
        if new_status not in valid_statuses:
            raise ValueError(f"Estado inválido: {new_status}. Debe ser: {', '.join(valid_statuses)}")

        product = MercadoLibreProduct.objects.get(id=product_id, company=self.company)

        logger.info(f"ProductStatus: changing {product.ml_item_id} to '{new_status}'")
        self.api.update_item(product.ml_item_id, {'status': new_status})

        # Refrescar
        refreshed = self.get_item_detail(product.ml_item_id)
        product.status = refreshed.get('status', new_status)
        product.last_synced_at = timezone.now()
        product.raw_data = refreshed
        product.save()

        logger.info(f"ProductStatus: {product.ml_item_id} changed to '{product.status}'")
        return product

    def refresh_single_product(self, product_id):
        """Refresca un producto individual desde la API de ML."""
        from .integrations_mercadolibre_models import MercadoLibreProduct

        product = MercadoLibreProduct.objects.get(id=product_id, company=self.company)
        item_data = self.get_item_detail(product.ml_item_id)

        product.title = item_data.get('title', product.title)
        product.price = Decimal(str(item_data.get('price', product.price)))
        product.available_quantity = item_data.get('available_quantity', product.available_quantity)
        product.sold_quantity = item_data.get('sold_quantity', product.sold_quantity)
        product.status = item_data.get('status', product.status)
        product.listing_type_id = item_data.get('listing_type_id', product.listing_type_id)
        product.permalink = item_data.get('permalink', product.permalink)
        product.thumbnail = item_data.get('thumbnail', product.thumbnail)
        product.last_synced_at = timezone.now()
        product.raw_data = item_data
        product.save()

        return product


# ---------------------------------------------------------------------------
# Auto-Reply Engine
# ---------------------------------------------------------------------------
class MercadoLibreAutoReplyEngine:
    """
    Motor de respuestas automáticas para preguntas de MercadoLibre.
    Evalúa templates del usuario y reglas básicas de fallback.
    """

    # Reglas básicas de fallback (se usan si no hay templates que matcheen)
    FALLBACK_RULES = [
        {
            'keywords': ['stock', 'disponible', 'disponibilidad', 'queda', 'quedan', 'hay'],
            'response': '¡Sí! Tenemos stock disponible. ¡Cualquier duda estamos para ayudarte!',
        },
        {
            'keywords': ['envio', 'envío', 'envios', 'envíos', 'despacho', 'llega', 'demora', 'tarda'],
            'response': 'Hacemos envíos a todo el país. ¡Comprá tranquilo y lo recibís en tu domicilio!',
        },
        {
            'keywords': ['precio', 'descuento', 'oferta', 'rebaja', 'cuotas'],
            'response': 'El precio publicado es el vigente. ¡Cualquier duda estamos para ayudarte!',
        },
        {
            'keywords': ['garantia', 'garantía', 'devolucion', 'devolución', 'cambio'],
            'response': '¡Hola! Ofrecemos garantía según la política de MercadoLibre. ¡Comprá con confianza!',
        },
        {
            'keywords': ['medida', 'medidas', 'tamaño', 'talle', 'dimension', 'dimensiones', 'peso', 'grande', 'chico'],
            'response': 'Las medidas y especificaciones están en la descripción de la publicación. Si necesitás algo puntual, ¡consultanos!',
        },
        {
            'keywords': ['color', 'colores'],
            'response': 'Los colores disponibles están en las variantes de la publicación. ¡Consultanos si necesitás algo específico!',
        },
    ]

    def __init__(self, integration):
        self.integration = integration
        self.company = integration.company
        self.api = MercadoLibreAPIClient(integration)

    def generate_auto_reply(self, question_text):
        """
        Genera respuesta automática evaluando:
        1. Templates activos del usuario (prioridad alta)
        2. Reglas básicas de fallback
        
        Returns: (response_text, template_obj_or_None) or (None, None)
        """
        from .integrations_mercadolibre_models import MercadoLibreReplyTemplate

        text_lower = question_text.lower().strip()
        if not text_lower:
            return None, None

        # Nivel 2: Templates dinámicos del usuario (evaluados primero, prioridad alta)
        templates = MercadoLibreReplyTemplate.objects.filter(
            company=self.company,
            is_active=True,
        ).order_by('-priority', 'created_at')

        for template in templates:
            keywords = template.keywords if isinstance(template.keywords, list) else []
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    logger.info(
                        f"AutoReply: template '{template.name}' matched "
                        f"keyword '{keyword}' in question: {question_text[:60]}"
                    )
                    return template.response_text, template

        # Nivel 1: Reglas básicas de fallback
        for rule in self.FALLBACK_RULES:
            for keyword in rule['keywords']:
                if keyword in text_lower:
                    logger.info(
                        f"AutoReply: fallback rule matched "
                        f"keyword '{keyword}' in question: {question_text[:60]}"
                    )
                    return rule['response'], None

        logger.info(f"AutoReply: no match for question: {question_text[:60]}")
        return None, None

    def send_answer(self, question_id, text):
        """
        Envía respuesta a MercadoLibre via POST /answers.
        Returns: dict con respuesta de la API.
        Raises on failure so caller can handle specific errors.
        """
        logger.info(f"AutoReply: sending answer to question #{question_id}: {text[:80]}...")
        result = self.api.answer_question(question_id, text)
        logger.info(f"AutoReply: answer sent successfully to question #{question_id}")
        return result

    def process_auto_reply(self, question_obj):
        """
        Flujo completo de auto-reply para una pregunta:
        1. Verifica que sea UNANSWERED y no haya sido auto-respondida
        2. Genera respuesta
        3. Envía a MercadoLibre
        4. Actualiza la pregunta en DB
        
        Returns: True si se respondió, False si no
        """
        from .integrations_mercadolibre_models import MercadoLibreReplyTemplate

        # Validaciones
        if question_obj.status != 'UNANSWERED':
            logger.debug(f"AutoReply: skipping Q#{question_obj.ml_question_id} (status={question_obj.status})")
            return False

        if question_obj.auto_replied:
            logger.debug(f"AutoReply: skipping Q#{question_obj.ml_question_id} (already auto-replied)")
            return False

        if question_obj.answer_text:
            logger.debug(f"AutoReply: skipping Q#{question_obj.ml_question_id} (already has answer)")
            return False

        # Generar respuesta
        reply_text, template_used = self.generate_auto_reply(question_obj.text)

        if not reply_text:
            logger.info(f"AutoReply: no reply generated for Q#{question_obj.ml_question_id}")
            return False

        # Enviar a MercadoLibre
        try:
            result = self.send_answer(question_obj.ml_question_id, reply_text)
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response is not None else 'unknown'
            if status_code == 403:
                logger.warning(
                    f"AutoReply: 403 Forbidden on Q#{question_obj.ml_question_id} "
                    f"- cuenta de test no permite responder via API. "
                    f"La respuesta se guardará localmente para reintento."
                )
                # Save the generated reply locally so it can be retried later
                question_obj.raw_data = question_obj.raw_data or {}
                question_obj.raw_data['pending_auto_reply'] = reply_text
                question_obj.raw_data['auto_reply_error'] = f'403 Forbidden'
                question_obj.save(update_fields=['raw_data'])
            else:
                logger.error(f"AutoReply: HTTP {status_code} on Q#{question_obj.ml_question_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"AutoReply: unexpected error on Q#{question_obj.ml_question_id}: {e}", exc_info=True)
            return False

        # Actualizar pregunta en DB
        question_obj.auto_replied = True
        question_obj.answer_text = reply_text
        question_obj.answer_date = timezone.now()
        question_obj.status = 'ANSWERED'

        update_fields = ['auto_replied', 'answer_text', 'answer_date', 'status']

        if template_used:
            question_obj.auto_reply_template = template_used
            update_fields.append('auto_reply_template')
            # Actualizar métricas del template
            template_used.times_used += 1
            template_used.last_used_at = timezone.now()
            template_used.save(update_fields=['times_used', 'last_used_at', 'updated_at'])

        question_obj.save(update_fields=update_fields)

        logger.info(
            f"AutoReply: Q#{question_obj.ml_question_id} answered successfully "
            f"(template={'\"' + template_used.name + '\"' if template_used else 'fallback'})"
        )
        return True


# ---------------------------------------------------------------------------
# Event Processors
# ---------------------------------------------------------------------------
class MercadoLibreEventProcessor:
    """
    Procesa eventos de webhook y los convierte en entidades CRM.
    Cada método es idempotente (safe to re-run).
    """

    # In-memory cache for user nicknames to avoid repeated API calls
    _nickname_cache = {}

    def __init__(self, integration):
        self.integration = integration
        self.company = integration.company
        self.api = MercadoLibreAPIClient(integration)
        self.crm = MercadoLibreCRMSync(integration)

    def _get_user_nickname(self, user_id):
        """Fetch user nickname from ML API /users/{id}, with cache."""
        user_id = str(user_id)
        if user_id in self._nickname_cache:
            return self._nickname_cache[user_id]

        try:
            user_data = self.api.get_user(user_id)
            nickname = user_data.get('nickname', '')
            first_name = user_data.get('first_name', '')
            last_name = user_data.get('last_name', '')
            display_name = f"{first_name} {last_name}".strip() or nickname
            self._nickname_cache[user_id] = display_name
            return display_name
        except Exception as e:
            logger.warning(f"Could not fetch nickname for user {user_id}: {e}")
            return ''

    @transaction.atomic
    def process_order(self, resource_path):
        """Procesa evento de orden: crea/actualiza Order, Contact, Lead, Deal."""
        from .integrations_mercadolibre_models import (
            MercadoLibreOrder, MercadoLibreOrderItem, MercadoLibreProduct
        )

        # Extraer order_id del resource path
        order_id = self._extract_id(resource_path)
        if not order_id:
            logger.error(f"Could not extract order_id from {resource_path}")
            return None

        order_data = self.api.get_order(order_id)
        buyer = order_data.get('buyer', {})
        shipping = order_data.get('shipping', {})

        # Buyer info
        buyer_phone = ''
        phone_data = buyer.get('phone', {})
        if isinstance(phone_data, dict):
            area = phone_data.get('area_code', '')
            number = phone_data.get('number', '')
            buyer_phone = f"{area}{number}"

        # Create/update order
        order_obj, created = MercadoLibreOrder.objects.update_or_create(
            ml_order_id=order_data['id'],
            defaults={
                'integration': self.integration,
                'company': self.company,
                'status': order_data.get('status', 'confirmed'),
                'status_detail': order_data.get('status_detail', ''),
                'buyer_id': buyer.get('id', 0),
                'buyer_nickname': buyer.get('nickname', ''),
                'buyer_first_name': buyer.get('first_name', ''),
                'buyer_last_name': buyer.get('last_name', ''),
                'buyer_email': buyer.get('email', ''),
                'buyer_phone': buyer_phone,
                'total_amount': Decimal(str(order_data.get('total_amount', 0))),
                'paid_amount': Decimal(str(order_data.get('paid_amount', 0))),
                'currency_id': order_data.get('currency_id', 'ARS'),
                'shipping_id': shipping.get('id'),
                'shipping_status': shipping.get('status', ''),
                'date_created': parse_datetime(order_data['date_created']) if order_data.get('date_created') else None,
                'date_closed': parse_datetime(order_data['date_closed']) if order_data.get('date_closed') else None,
                'last_updated': parse_datetime(order_data['last_updated']) if order_data.get('last_updated') else None,
                'raw_data': order_data,
            }
        )

        # Create order items
        for item_data in order_data.get('order_items', []):
            item_info = item_data.get('item', {})
            ml_item_id = item_info.get('id', '')

            product = MercadoLibreProduct.objects.filter(ml_item_id=ml_item_id).first()

            MercadoLibreOrderItem.objects.update_or_create(
                order=order_obj,
                ml_item_id=ml_item_id,
                defaults={
                    'product': product,
                    'title': item_info.get('title', ''),
                    'quantity': item_data.get('quantity', 1),
                    'unit_price': Decimal(str(item_data.get('unit_price', 0))),
                    'currency_id': item_data.get('currency_id', 'ARS'),
                    'category_id': item_info.get('category_id', ''),
                }
            )

        # CRM: Contact + Lead + Deal (only on first creation or if not linked)
        if not order_obj.contact:
            contact, _ = self.crm.get_or_create_contact_from_buyer(
                buyer.get('id'), buyer
            )
            order_obj.contact = contact

        if not order_obj.lead:
            lead = self.crm.create_lead_from_order(order_obj)
            order_obj.lead = lead

        if not order_obj.deal and order_obj.contact:
            deal = self.crm.create_deal_from_order(order_obj, order_obj.contact)
            order_obj.deal = deal

        order_obj.save()
        logger.info(f"Order #{order_obj.ml_order_id} processed → contact={order_obj.contact_id}, deal={order_obj.deal_id}")
        return order_obj

    @transaction.atomic
    def process_question(self, resource_path):
        """Procesa evento de pregunta: crea/actualiza Question + Lead."""
        from .integrations_mercadolibre_models import MercadoLibreQuestion, MercadoLibreProduct

        question_id = self._extract_id(resource_path)
        if not question_id:
            logger.error(f"Could not extract question_id from {resource_path}")
            return None

        q_data = self.api.get_question(question_id)

        product = MercadoLibreProduct.objects.filter(
            ml_item_id=q_data.get('item_id', '')
        ).first()

        from_data = q_data.get('from', {})
        answer_data = q_data.get('answer', {})

        # Enrich with user nickname via /users/{id}
        from_id = from_data.get('id', 0)
        from_nickname = from_data.get('nickname', '')
        if from_id and not from_nickname:
            from_nickname = self._get_user_nickname(from_id)

        question_obj, created = MercadoLibreQuestion.objects.update_or_create(
            ml_question_id=q_data['id'],
            defaults={
                'integration': self.integration,
                'company': self.company,
                'ml_item_id': q_data.get('item_id', ''),
                'from_id': from_id,
                'from_nickname': from_nickname,
                'text': q_data.get('text', ''),
                'status': q_data.get('status', 'UNANSWERED'),
                'date_created': parse_datetime(q_data['date_created']) if q_data.get('date_created') else None,
                'answer_text': answer_data.get('text', '') if answer_data else '',
                'answer_date': parse_datetime(answer_data['date_created']) if answer_data and answer_data.get('date_created') else None,
                'product': product,
                'raw_data': q_data,
            }
        )

        # Create lead from unanswered question
        if created and q_data.get('status') == 'UNANSWERED' and not question_obj.lead:
            lead = self.crm.create_lead_from_question(question_obj)
            question_obj.lead = lead
            question_obj.save()

        # Auto-reply: only on new UNANSWERED questions AND if auto_reply_enabled
        if (created and question_obj.status == 'UNANSWERED'
                and not question_obj.auto_replied
                and self.integration.auto_reply_enabled):
            try:
                auto_reply_engine = MercadoLibreAutoReplyEngine(self.integration)
                auto_reply_engine.process_auto_reply(question_obj)
            except Exception as e:
                logger.error(f"AutoReply error for Q#{question_obj.ml_question_id}: {e}", exc_info=True)

        logger.info(f"Question #{question_obj.ml_question_id} processed (status={question_obj.status})")
        return question_obj

    @transaction.atomic
    def process_message(self, resource_path):
        """Procesa evento de mensaje post-venta."""
        from .integrations_mercadolibre_models import MercadoLibreMessage, MercadoLibreOrder

        msg_data = self.api.get_message(resource_path)

        # Messages API returns different structures
        messages_list = msg_data.get('messages', [msg_data]) if 'messages' not in msg_data else msg_data['messages']

        results = []
        for msg in messages_list:
            msg_id = str(msg.get('id', ''))
            if not msg_id:
                continue

            if MercadoLibreMessage.objects.filter(ml_message_id=msg_id).exists():
                continue

            sender = msg.get('from', {})
            receiver = msg.get('to', {})
            sender_id = sender.get('user_id', 0)
            is_from_buyer = str(sender_id) != str(self.integration.ml_user_id)

            # Try to find related order
            order = None
            resource_info = msg.get('resource', '')
            if resource_info:
                order_match = re.search(r'/orders/(\d+)', resource_info)
                if order_match:
                    order = MercadoLibreOrder.objects.filter(
                        ml_order_id=int(order_match.group(1))
                    ).first()

            message_obj = MercadoLibreMessage.objects.create(
                integration=self.integration,
                company=self.company,
                ml_message_id=msg_id,
                pack_id=str(msg.get('pack_id', '')),
                order=order,
                sender_id=sender_id,
                sender_nickname=sender.get('nickname', ''),
                receiver_id=receiver.get('user_id', 0),
                is_from_buyer=is_from_buyer,
                text=msg.get('text', ''),
                message_date=parse_datetime(msg['message_date']['created']) if msg.get('message_date', {}).get('created') else timezone.now(),
                status=msg.get('status', 'available'),
                contact=order.contact if order else None,
                raw_data=msg,
            )
            results.append(message_obj)

        logger.info(f"Processed {len(results)} messages from {resource_path}")
        return results

    @transaction.atomic
    def process_item(self, resource_path):
        """Procesa evento de publicación: crea/actualiza Product."""
        from .integrations_mercadolibre_models import MercadoLibreProduct

        item_id = self._extract_id(resource_path)
        if not item_id:
            return None

        item_data = self.api.get_item(item_id)

        product, created = MercadoLibreProduct.objects.update_or_create(
            ml_item_id=item_data['id'],
            defaults={
                'integration': self.integration,
                'company': self.company,
                'title': item_data.get('title', ''),
                'category_id': item_data.get('category_id', ''),
                'price': Decimal(str(item_data.get('price', 0))),
                'currency_id': item_data.get('currency_id', 'ARS'),
                'available_quantity': item_data.get('available_quantity', 0),
                'sold_quantity': item_data.get('sold_quantity', 0),
                'condition': item_data.get('condition', 'new'),
                'listing_type_id': item_data.get('listing_type_id', ''),
                'permalink': item_data.get('permalink', ''),
                'thumbnail': item_data.get('thumbnail', ''),
                'status': item_data.get('status', 'active'),
                'last_synced_at': timezone.now(),
                'raw_data': item_data,
            }
        )

        action = "created" if created else "updated"
        logger.info(f"Product {item_data['id']} {action}: {item_data.get('title', '')}")
        return product

    @transaction.atomic
    def process_shipment(self, resource_path):
        """Procesa evento de envío: actualiza estado del Deal."""
        from .integrations_mercadolibre_models import MercadoLibreOrder

        shipment_id = self._extract_id(resource_path)
        if not shipment_id:
            return None

        ship_data = self.api.get_shipment(shipment_id)
        ship_status = ship_data.get('status', '')

        # Find order by shipping_id
        order = MercadoLibreOrder.objects.filter(
            shipping_id=int(shipment_id),
            integration=self.integration,
        ).first()

        if order:
            order.shipping_status = ship_status
            order.save(update_fields=['shipping_status', 'updated_at'])

            # Update deal stage if delivered
            if ship_status == 'delivered' and order.deal:
                from .models import Stage
                delivered_stage = order.deal.stage.pipeline.stages.filter(
                    name__icontains='entregad'
                ).first() or order.deal.stage.pipeline.stages.filter(
                    name__icontains='ganad'
                ).first()
                if delivered_stage:
                    order.deal.stage = delivered_stage
                    order.deal.probability = 100
                    order.deal.save()
                    logger.info(f"Deal {order.deal.id} moved to stage '{delivered_stage.name}' (shipment delivered)")

        logger.info(f"Shipment #{shipment_id} processed (status={ship_status})")
        return ship_data

    def _extract_id(self, resource_path):
        """Extrae el ID numérico o alfanumérico del final de un resource path."""
        match = re.search(r'/([\w\d-]+)$', resource_path.rstrip('/'))
        return match.group(1) if match else None
