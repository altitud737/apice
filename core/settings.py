import os
from pathlib import Path
import environ

env = environ.Env(
    DEBUG=(bool, False)
)

BASE_DIR = Path(__file__).resolve().parent.parent

# Read .env file
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

SECRET_KEY = env('SECRET_KEY', default='django-insecure-apice-secret-key')

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

DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='noreply@tuapice.com')
SERVER_EMAIL = env('SERVER_EMAIL', default='noreply@tuapice.com')

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

# Database - PostgreSQL
DATABASES = {
    'default': env.db('DATABASE_URL', default=f'sqlite:///{BASE_DIR}/db.sqlite3')
}

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
