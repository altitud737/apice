#!/bin/bash
set -e

# Posicionarse en la raíz del proyecto (un nivel por encima de scripts/).
cd "$(dirname "$0")/.."

# Detect python command
if command -v python3 &>/dev/null; then
    PYTHON_CMD=python3
elif command -v python &>/dev/null; then
    PYTHON_CMD=python
else
    echo "Python not found!"
    exit 1
fi

echo "Using $PYTHON_CMD"
$PYTHON_CMD --version

echo "Copying environment variables..."
if [ ! -f .env ]; then cp .env.example .env; fi

echo "Installing Python dependencies..."
$PYTHON_CMD -m pip install --user --no-cache-dir -r requirements.txt || $PYTHON_CMD -m pip install --no-cache-dir -r requirements.txt

# Add user site-packages to PYTHONPATH
export PYTHONPATH=$PYTHONPATH:$($PYTHON_CMD -m site --user-site)

echo "Creating static directory..."
mkdir -p static

echo "Checking Django version..."
$PYTHON_CMD -m django --version || echo "Django not found!"

echo "Applying migrations..."
$PYTHON_CMD manage.py migrate

echo "Collecting static files..."
$PYTHON_CMD manage.py collectstatic --noinput

echo "Setting up initial data (only if base is empty)..."
$PYTHON_CMD manage.py shell <<'EOF'
import os
from accounts.models import Company, User

# Solo crea datos minimos si la base esta completamente vacia.
if not Company.objects.exists():
    company = Company.objects.create(name="Empresa Demo")
    admin_email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@example.com')
    admin_password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')
    if admin_password and not User.objects.filter(email=admin_email).exists():
        User.objects.create_superuser(
            username='admin', email=admin_email,
            password=admin_password, company=company,
        )
        print(f"Superuser creado: {admin_email}")
    else:
        print("Empresa creada. Defina DJANGO_SUPERUSER_PASSWORD para crear el superusuario automaticamente.")
else:
    print("Datos existentes, no se realiza setup inicial.")
EOF

echo "Setup complete. Starting server..."
$PYTHON_CMD manage.py runserver 0.0.0.0:3000
