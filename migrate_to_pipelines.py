import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from accounts.models import Company
from apice.models import Pipeline, Stage

print("Migrando stages a pipelines...")

for company in Company.objects.all():
    # Crear pipeline por defecto si no existe
    pipeline, created = Pipeline.objects.get_or_create(
        company=company,
        is_default=True,
        defaults={
            'name': 'Pipeline Principal',
            'description': 'Pipeline de ventas principal',
            'color': '#10b981'
        }
    )
    
    if created:
        print(f"✓ Pipeline creado para {company.name}")
    
    # Asignar stages sin pipeline al pipeline por defecto
    stages_sin_pipeline = Stage.objects.filter(company=company, pipeline__isnull=True)
    count = stages_sin_pipeline.count()
    
    if count > 0:
        stages_sin_pipeline.update(pipeline=pipeline)
        print(f"✓ {count} etapas asignadas al pipeline por defecto de {company.name}")

print("\n✅ Migración completada!")
