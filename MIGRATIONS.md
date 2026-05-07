# Migraciones Alembic - QR Registros CRM

## ¿Qué son las migraciones?

Las migraciones son cambios versionados en la estructura de la base de datos. Alembic es una herramienta que permite:
- Versionear cambios de schema
- Aplicar cambios incrementales a producción
- Revertir cambios (downgrade) si es necesario
- Mantener un historial de cambios

## Estructura

```
alembic/
├── env.py                    # Configuración de Alembic
├── script.py.mako            # Template para nuevas migraciones
├── versions/                 # Historial de migraciones
│   └── 60d047b49f5d_initial_schema_with_crm_module.py
└── alembic.ini              # Configuración de conexión
```

## Migraciones disponibles

### Migración inicial (60d047b49f5d)
- **Descripción**: Creación del módulo CRM con 4 tablas principales
- **Tablas creadas**:
  - `crm_professionals`: Profesionales (médicos, abogados, etc.)
  - `crm_client_files`: Expedientes de clientes/pacientes
  - `crm_appointments`: Turnos/citas agendadas
  - `crm_visit_reports`: Reportes de visita realizadas

**Cambios en BD**:
```sql
-- Tablas con multi-tenancy (tenant_id obligatorio)
-- Todas las tablas tienen:
--   - primary key UUID
--   - tenant_id con FK a tenants.id (ON DELETE CASCADE)
--   - created_at / updated_at con timestamps automáticos
--   - índices en campos de búsqueda frecuente
```

## Cómo usar

### 1. Aplicar todas las migraciones pendientes
```bash
python apply_migrations.py
```

### 2. Revertir la última migración
```bash
python apply_migrations.py --downgrade
```

### 3. Ver estado actual
```bash
python apply_migrations.py --status
```

### 4. Usar Alembic directamente
```bash
# Aplicar todas las migraciones pendientes
alembic upgrade head

# Revertir una migración
alembic downgrade -1

# Ir a una migración específica
alembic upgrade 60d047b49f5d

# Ver historial
alembic history
```

## Crear una nueva migración

Cuando agregues nuevos modelos:

```bash
# 1. Crear migración automática (requiere BD sincrónica)
alembic revision --autogenerate -m "descripcion_cambio"

# 2. O crear migración vacía y llenarla manualmente
alembic revision -m "descripcion_cambio"
```

Luego edita el archivo en `alembic/versions/` y agregaOperaciones en las funciones `upgrade()` y `downgrade()`.

## Notas importantes

- ✅ El proyecto usa PostgreSQL con asyncpg
- ✅ Las migraciones se ejecutan con psycopg (driver sincrónico)
- ✅ Multi-tenancy con `tenant_id` para aislamiento de datos
- ✅ Todos los deletes en cascade para simplificar limpieza

## Desarrollo

Para desarrollo local, puedes seguir usando:
```bash
# Crear tablas nuevas desde cero
python init_db.py

# O resetear completamente la BD
python reset_db.py
```

## Producción

Para producción, siempre usa Alembic:
```bash
# En el servidor de producción
python apply_migrations.py
```

Esto mantendrá un historial exacto de todos los cambios en el schema.
