import os
from pathlib import Path
import environ

env = environ.Env(
    DEBUG=(bool, False)
)

BASE_DIR = Path(__file__).resolve().parent.parent

# Read .env file
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

SECRET_KEY = env('SECRET_KEY', default='django-insecure-dev-secret-key-change-in-production')

DEBUG = env('DEBUG', default=True)

ALLOWED_HOSTS = ['*']

CSRF_TRUSTED_ORIGINS = [
    'http://localhost:3000',
    'http://127.0.0.1:3000',
    'http://localhost:58908',
    'http://127.0.0.1:58908',
    'https://bcfb-181-230-38-73.ngrok-free.app',
]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',  # Required by allauth
    
    # Third party
    'rest_framework',
    'corsheaders',
    'django_htmx',
    'crispy_forms',
    'crispy_tailwind',
    
    # Allauth
    'allauth',
    'allauth.account',
    
    # Local apps
    'accounts',
    'apice',

    # ERP apps
    'erp_core',
    'inventario',
    'ventas',
]

SITE_ID = 1

# Email Configuration
# En desarrollo usa console, en producción usa Zoho ZeptoMail
if DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    EMAIL_BACKEND = 'zoho_zeptomail.backend.zeptomail_backend.ZohoZeptoMailEmailBackend'
    ZOHO_ZEPTOMAIL_API_KEY_TOKEN = env('ZOHO_ZEPTOMAIL_API_KEY_TOKEN', default='')
    ZOHO_ZEPTOMAIL_HOSTED_REGION = env('ZOHO_ZEPTOMAIL_HOSTED_REGION', default='zeptomail.zoho.com')

DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='noreply@example.com')
SERVER_EMAIL = env('SERVER_EMAIL', default='noreply@example.com')

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',  # Allauth middleware
    'django_htmx.middleware.HtmxMiddleware',
    'accounts.middleware.TenantMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apice.context_processors.unread_notifications',
                'apice.context_processors.mercadolibre_integration',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

# Database - PostgreSQL es la única base soportada.
# Prioridad: DATABASE_URL > Variables individuales (DB_NAME, DB_USER, ...).
# Si ninguna está configurada, el proyecto NO arranca.
from django.core.exceptions import ImproperlyConfigured

if env('DATABASE_URL', default=None):
    # Formato: postgresql://user:password@host:port/dbname
    DATABASES = {
        'default': env.db('DATABASE_URL'),
    }
elif env('DB_NAME', default=None):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': env('DB_NAME'),
            'USER': env('DB_USER'),
            'PASSWORD': env('DB_PASSWORD'),
            'HOST': env('DB_HOST', default='localhost'),
            'PORT': env('DB_PORT', default='5432'),
        }
    }
else:
    raise ImproperlyConfigured(
        "Debe configurarse DATABASE_URL o las variables DB_NAME/DB_USER/DB_PASSWORD "
        "en el archivo .env. SQLite no está soportado en este proyecto."
    )

# Validación: solo PostgreSQL está soportado.
_engine = DATABASES['default'].get('ENGINE', '')
if 'postgresql' not in _engine:
    raise ImproperlyConfigured(
        f"Motor de base de datos no soportado: {_engine!r}. "
        "Solo se admite PostgreSQL (django.db.backends.postgresql)."
    )

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'es-es'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'accounts.User'

CRISPY_ALLOWED_TEMPLATE_PACKS = "tailwind"
CRISPY_TEMPLATE_PACK = "tailwind"

LOGIN_REDIRECT_URL = 'apice:dashboard'
LOGOUT_REDIRECT_URL = 'accounts:login'

# CORS Configuration - Permitir requests desde cualquier origen para la API de leads
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
    'x-api-key',
]

# REST Framework Configuration
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '60/minute',  # Máximo 60 requests por minuto desde IPs anónimas
    },
}
LOGIN_URL = '/accounts/login/'  # Allauth login URL

# MercadoLibre Integration Settings
ML_CLIENT_ID = env('ML_CLIENT_ID', default='')
ML_CLIENT_SECRET = env('ML_CLIENT_SECRET', default='')
ML_REDIRECT_URI = env('ML_REDIRECT_URI', default='http://localhost:8000/integrations/mercadolibre/callback')

# Django Allauth Configuration
AUTHENTICATION_BACKENDS = [
    # Django backend (username/password)
    'django.contrib.auth.backends.ModelBackend',
    # Allauth backend (email/social)
    'allauth.account.auth_backends.AuthenticationBackend',
]

# Allauth Settings (Sintaxis moderna)
ACCOUNT_LOGIN_METHODS = {'email'}  # Login solo con email
ACCOUNT_SIGNUP_FIELDS = ['email*', 'password1*', 'password2*']  # Campos requeridos en registro
ACCOUNT_EMAIL_VERIFICATION = 'optional'  # 'mandatory', 'optional', or 'none'
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_SESSION_REMEMBER = True
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True

# Deshabilitar registro público (solo super admin puede crear clientes)
ACCOUNT_ALLOW_REGISTRATION = False

# Redirect URLs
LOGIN_REDIRECT_URL = '/'  # Redirige al dashboard después de login
ACCOUNT_LOGOUT_REDIRECT_URL = '/accounts/login/'
ACCOUNT_EMAIL_CONFIRMATION_ANONYMOUS_REDIRECT_URL = '/accounts/login/'

# Adaptadores personalizados
ACCOUNT_ADAPTER = 'accounts.adapters.AccountAdapter'
