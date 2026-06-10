#!/bin/bash
set -e

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
cat .env.example > .env || true

echo "Checking files in root..."
ls -la / || true

echo "Installing Python dependencies..."
$PYTHON_CMD -m pip install --user --no-cache-dir -r requirements.txt || $PYTHON_CMD -m pip install --no-cache-dir -r requirements.txt

# Add user site-packages to PYTHONPATH
export PYTHONPATH=$PYTHONPATH:$($PYTHON_CMD -m site --user-site)

echo "Creating static directory..."
mkdir -p static

echo "Checking Django version..."
$PYTHON_CMD -m django --version || echo "Django not found!"

echo "Generating migrations..."
$PYTHON_CMD manage.py makemigrations accounts
$PYTHON_CMD manage.py makemigrations apice

echo "Applying migrations..."
$PYTHON_CMD manage.py migrate

echo "Collecting static files..."
$PYTHON_CMD manage.py collectstatic --noinput

echo "Setting up initial data..."
$PYTHON_CMD manage.py shell <<EOF
try:
    from accounts.models import Company, User
    from apice.models import Stage, Contact, Deal
    
    if not Company.objects.exists():
        company = Company.objects.create(name="Empresa Demo")
        if not User.objects.filter(username='admin').exists():
            user = User.objects.create_superuser('admin', 'admin@demo.com', 'admin123', company=company)
        else:
            user = User.objects.get(username='admin')
        
        stages = ['Prospecto', 'Calificado', 'Propuesta', 'Negociación', 'Cerrada Ganada', 'Cerrada Perdida']
        stages_objs = []
        for i, name in enumerate(stages):
            stages_objs.append(Stage.objects.create(company=company, name=name, order=i))
        
        # Add some contacts
        c1 = Contact.objects.create(company=company, name="Juan Pérez", email="juan@example.com", company_name="Tech Corp", status="Calificado", owner=user)
        c2 = Contact.objects.create(company=company, name="María García", email="maria@example.com", company_name="Global Solutions", status="Nuevo", owner=user)
        
        # Add some deals
        Deal.objects.create(company=company, title="Implementación Apice", value=5000, probability=70, contact=c1, stage=stages_objs[2], owner=user)
        Deal.objects.create(company=company, title="Consultoría IT", value=2500, probability=40, contact=c2, stage=stages_objs[1], owner=user)
        print("Initial data created successfully.")
    else:
        print("Data already exists, skipping setup.")
except Exception as e:
    print(f"Error setting up data: {e}")
EOF

echo "Setup complete. Starting server..."
$PYTHON_CMD manage.py runserver 0.0.0.0:3000
