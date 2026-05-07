# Mapa Completo de Changes — QR Registros SaaS (ACTUALIZADO)

## 📋 Resumen Ejecutivo

Este documento define el **mapa SDD actualizado** para QR Registros basado en análisis arquitectónico exhaustivo. El proyecto tiene:
- ✅ **Infraestructura base funcional** (multitenancy, auth, JWT, modelos)
- ✅ **Módulo QR Attendance 80% completo** (fichajeada entrada/salida funciona, anomalías detectadas)
- ✅ **Módulo Sales Analytics 90% completo** (upload CSV, agregados, charts, pero sin AI)
- ✅ **Módulo CRM 85% completo** (CRUD professionals, clients, appointments, visit reports, pero sin calendar sync)
- ⚠️ **Deuda técnica moderada** (testing insuficiente, sin scheduler, validación incompleta)

**Próximas 13 changes:** Completar funcionalidad, refactorizar, documentar en SDD, mejorar testing.

---

## 🗂️ Mapa de Changes por Épica (PRIORITIZADO)

### **ÉPICA 1: ESTABILIZACIÓN DE INFRAESTRUCTURA**

#### Change 01: `core-infrastructure-documentation`
- **Nombre sugerido (kebab-case):** `core-infrastructure-documentation`
- **Funcionalidad:** Especificación y documentación de la infraestructura base multitenancy, autenticación JWT, middleware de aislamiento.
- **Historias de Usuario:** US-00 (transversal, no es feature sino arquitectura)
- **Dependencias:** ✅ Sin dependencias (FIRST)
- **Estado:** ✅ **Ya implementado** (ver: multitenancy en 18 modelos, JWT auth, ValidationService)
- **Tareas Principales:**
  - Crear `proposal.md` documentando decisiones de multitenancy (row-level security, tenant_id indexed)
  - Crear `design.md` explicando arquitectura de services ↔ routers
  - Crear `tasks.md` con tests faltantes (aislamiento de datos, cascada de borrado)
  - Tests: verificar que admin de Tenant A no puede acceder a Tenant B
- **Impacto:** Documentación → permite a nuevos devs entender arquitectura

---

#### Change 02: `auth-endpoint-completion`
- **Nombre sugerido (kebab-case):** `auth-endpoint-completion`
- **Funcionalidad:** Completar endpoints de autenticación faltantes: `/auth/me`, `/auth/change-password`, `/auth/refresh-token`
- **Historias de Usuario:** US-01 (SuperAdmin crea Tenant + credenciales)
- **Dependencias:** ✅ `core-infrastructure-documentation` (requiere entender flujo de auth)
- **Estado:** ⚠️ **Parcialmente implementado** (login/register existen, pero falta `/auth/me`, `/change-password`)
- **Tareas Principales:**
  - GET `/api/v1/auth/me` — devuelve datos del admin actual (nombre, email, tenant_id, rol)
  - POST `/api/v1/auth/change-password` — valida old_password, set new_password, marca must_change_password=False
  - POST `/api/v1/auth/refresh-token` — emite nuevo access_token antes de expirar
  - POST `/api/v1/auth/logout` — (opcional) invalidar token en blocklist
  - Tests de seguridad: token expirado, token inválido, admin no encontrado
- **Impacto:** Flujo de login completo y usable en frontend

---

#### Change 03: `config-validation-and-bootstrap`
- **Nombre sugerido (kebab-case):** `config-validation-and-bootstrap`
- **Funcionalidad:** Validar configuración al startup, prevenir crashes por config incompleta. Inicializar tenants con features habilitadas automáticamente.
- **Historias de Usuario:** US-02 (SuperAdmin habilita/deshabilita módulos)
- **Dependencias:** ✅ `core-infrastructure-documentation`
- **Estado:** ⚠️ **Parcialmente implementado** (ConfigSettings existe con +50 valores, pero sin validación cruzada)
- **Tareas Principales:**
  - Pydantic validators: si GOOGLE_OAUTH_ENABLED pero CLIENT_ID vacío → raise error
  - Pydantic validators: si BOOKING_ENABLED pero GOOGLE_OAUTH_DISABLED → raise error
  - Función `ensure_superadmin_exists()` que crea SuperAdmin bootstrap si no existen
  - Función `ensure_initial_tenant_features()` que inicializa TenantFeature para todos los tenants existentes
  - Startup event en FastAPI que ejecuta todas las validaciones
  - Tests de missing configuration, incompatible settings
- **Impacto:** Evitar bugs en production por configuración incompleta

---

#### Change 04: `database-indices-optimization`
- **Nombre sugerido (kebab-case):** `database-indices-optimization`
- **Funcionalidad:** Agregar índices compuestos faltantes en modelos críticos para performance.
- **Historias de Usuario:** US-03 (Queries de asistencia/reportes lentas con datasets grandes)
- **Dependencias:** ✅ `core-infrastructure-documentation`
- **Estado:** ⚠️ **Parcialmente implementado** (tenant_id indexed, pero faltan índices compuestos)
- **Tareas Principales:**
  - Alembic migration: crear índices compuestos:
    - Jornada: `(tenant_id, employee_id, fecha DESC)`
    - AttendanceLog: `(tenant_id, employee_id, timestamp DESC)`
    - SalesRecord: `(tenant_id, sale_date DESC)`
    - CRMAppointment: `(tenant_id, professional_id, starts_at DESC)`
    - CRMAppointment: `(tenant_id, subject_id, starts_at DESC)`
  - Query tests: verificar EXPLAIN ANALYZE usa índices
- **Impacto:** 5-10x speedup en queries de reportes

---

### **ÉPICA 2: COMPLETAR MÓDULO ATTENDANCE (QR)**

#### Change 05: `attendance-anomaly-detection-complete`
- **Nombre sugerido (kebab-case):** `attendance-anomaly-detection-and-alerting`
- **Funcionalidad:** Completar detección de anomalías y agregar alertas en tiempo real.
- **Historias de Usuario:** US-04 (Admin detecta empleados con problemas de fichaje)
- **Dependencias:** ✅ `core-infrastructure-documentation` (anomalias endpoint ya existe)
- **Estado:** ✅ **Funcional** (GET `/admin/alerts/anomalies` detecta: missing_checkout, long_shift, duplicate_punch)
- **Tareas Principales:**
  - Alarma: "jornada sin cierre" → alerta a las 3 PM si check-in pero sin check-out
  - Alarma: "jornada > 12h" → alerta roja
  - Alarma: "puntos duplicados en 5 min" → fraude potencial
  - Endpoint PATCH `/api/v1/attendance/anomalies/{id}/resolve` — resolver alerta con nota
  - Almacenar histórico de alertas en tabla `AttendanceAnomaly`
  - Webhook de background: `attendance.anomaly_detected`
  - Tests: diferentes tipos de anomalías, diferentes horas del día
- **Impacto:** Admin informed en tiempo real de problemas

---

#### Change 06: `attendance-manual-adjustment-endpoint`
- **Nombre sugerido (kebab-case):** `attendance-manual-adjustment-and-auditing`
- **Funcionalidad:** Permitir que Admin ajuste fichajes después de creados (con auditoría).
- **Historias de Usuario:** US-05 (Admin corrige error de fichaje de empleado)
- **Dependencias:** ✅ `attendance-anomaly-detection-complete` (requiere tabla de auditoría)
- **Estado:** ❌ **No implementado** (no hay endpoint para editar jornadas)
- **Tareas Principales:**
  - POST `/api/v1/attendance/jornadas/{id}/adjust` — recibe {new_check_in, new_check_out, razon}
  - Validación: no puede ir >24h atrás, no puede cambiar a fecha futura
  - Crear AuditLog con: actor_id=admin.id, action="jornada_adjusted", details={old_check_in, new_check_in, old_check_out, new_check_out}
  - Recalcular total_horas automáticamente
  - Tests: ajuste válido, ajuste futuro rechazado, auditoría registrada
- **Impacto:** Admin puede corregir errores de buena fe

---

#### Change 07: `attendance-export-and-reporting`
- **Nombre sugerido (kebab-case):** `attendance-export-certified-reports`
- **Funcionalidad:** Export de jornadas a CSV/PDF con validación de coherencia (probablemente existe parcialmente).
- **Historias de Usuario:** US-06 (Admin exporta comprobante de asistencia para empleado)
- **Dependencias:** ✅ `attendance-manual-adjustment-endpoint` (requiere datos coherentes)
- **Estado:** ⚠️ **Probablemente existe** (`GET /admin/export/jornadas` → CSV) pero sin PDF
- **Tareas Principales:**
  - GET `/api/v1/attendance/export?format=csv|pdf&from_date=...&to_date=...&employee_id=...`
  - CSV: id, nombre, fecha, check_in, check_out, total_horas, requires_review
  - PDF: similar, con logo empresa, timestamp, firma digital (opcional)
  - Validar: datos no pueden tener gaps de >24h sin nota de admin
  - Tests: export con/sin anomalías, PDF valid, CSV parseable
- **Impacto:** Reportes certificables para auditoría

---

#### Change 08: `attendance-auto-closeout-cron-job`
- **Nombre sugerido (kebab-case):** `attendance-auto-closeout-scheduler`
- **Funcionalidad:** Implementar job asíncrono que cierra jornadas abiertas >14h automáticamente.
- **Historias de Usuario:** US-07 (Sistema cierra jornada olvidada de employee)
- **Dependencias:** ✅ `attendance-export-and-reporting` (requiere datos coherentes)
- **Estado:** ❌ **No implementado** (requiere scheduler)
- **Tareas Principales:**
  - Agregar a requirements.txt: `apscheduler==3.10.4` (o similar)
  - Crear `app/jobs/attendance_jobs.py` con función `auto_closeout_open_shifts()`
  - Job runs @ 03:00 UTC (configurable): busca `Jornada` con `check_out IS NULL AND created_at < NOW() - 14 HOURS`
  - Para cada una: set `check_out = created_at + horas_laborales_por_convenio` y `requires_review = true`
  - Log en `AuditLog` con actor="system", action="jornada_auto_closed"
  - Webhook: `attendance.jornada_auto_closed`
  - Pruebas: job runs correctamente, solo cierra > 14h, respeta timezone
- **Impacto:** Previene jornadas abiertas indefinidas

---

### **ÉPICA 3: COMPLETAR MÓDULO SALES ANALYTICS**

#### Change 09: `sales-analytics-validation-hardening`
- **Nombre sugerido (kebab-case):** `sales-analytics-validation-and-rules-engine`
- **Funcionalidad:** Completar validación de reglas de negocio: fechas futuras, períodos duplicados, range validation.
- **Historias de Usuario:** US-08 (Admin intenta importar CSV con errores)
- **Dependencias:** ✅ `core-infrastructure-documentation`
- **Estado:** ⚠️ **Parcialmente implementado** (parseo básico existe, validación cruzada falta)
- **Tareas Principales:**
  - Validación: rechazar fecha futura en `sale_date`
  - Validación: rechazar período solapado (si ya existe SalesRecord para 2025-05-01..2025-05-31, rechazar otro upload para ese rango)
  - Validación: rechazar cantidad o precio negativo
  - Validación: range consistency (min_amount, max_amount configurable, default USD 0.01 - 999999.99)
  - Endpoint POST `/api/v1/sales/validation-rules?tenant_id=...` — devuelve reglas activas
  - Respuesta de upload incluye: `{validation_errors: [{row, reason, value}]}`
  - Tests: CSV con fechas futuras, período duplicado, valores fuera de range
- **Impacto:** Datos de ventas fiables y sin solapamientos

---

#### Change 10: `sales-analytics-period-auto-closing`
- **Nombre sugerido (kebab-case):** `sales-analytics-period-auto-closing`
- **Funcionalidad:** Automatizar cierre de período mensual (genera comprobante, congela datos).
- **Historias de Usuario:** US-09 (Admin cierra período mayo y no puede volver a editar datos de mayo)
- **Dependencias:** ✅ `attendance-auto-closeout-scheduler` (requiere APScheduler)
- **Estado:** ❌ **No implementado** (requiere scheduler + new model SalesClosingPeriod)
- **Tareas Principales:**
  - Nuevo modelo `SalesClosingPeriod` con: tenant_id, period_month, closed_by_admin_id, closed_at, hash_dados (para immutability)
  - Job asíncrono @ último día del mes 23:59 UTC: crear `SalesClosingPeriod` con datos de ese mes
  - Query adicional: si período está closed, rechaza POST de nuevos SalesRecord para ese mes
  - Endpoint PATCH `/api/v1/sales/periods/{period}/reopen` — solo para SuperAdmin, con auditoría
  - Tests: período cierra auto, no se pueden agregar records después, reapertura auditable
- **Impacto:** Datos de ventas inmutables después de cerrar período

---

#### Change 11: `sales-analytics-ai-insights-openai`
- **Nombre sugerido (kebab-case):** `sales-analytics-ai-insights-integration`
- **Funcionalidad:** Integración con OpenAI/Gemini para generar insights automáticos de datos de ventas.
- **Historias de Usuario:** US-10 (Admin obtiene recomendaciones de ventas generadas por IA)
- **Dependencias:** ✅ `sales-analytics-period-auto-closing` (requiere período cerrado para análisis)
- **Estado:** ❌ **No implementado** (requiere OpenAI SDK)
- **Tareas Principales:**
  - Agregar a requirements.txt: `openai>=1.0.0`
  - Configurar: `OPENAI_API_KEY` en variables de entorno
  - Endpoint GET `/api/v1/sales/insights?period=2025-05` — devuelve insights generados
  - Llamada a OpenAI GPT-4 con prompt anonimizado: "Negocio vendió $X, 500 transacciones, ticket promedio $Y, días pico fueron Z. Qué recomendaciones?"
  - Parseo respuesta: estructura {observaciones: [], recomendaciones: [], confianza: 0.8}
  - Caché en Redis con TTL 24h (sin Redis: en-memory con @lru_cache)
  - Fallback si OpenAI no disponible: devuelve "{status: 'unavailable'}"
  - Tests: prompt construido correctamente, parseo response, timeout handling
- **Impacto:** Insights automáticos accionables para el negocio

---

#### Change 12: `sales-analytics-forecasting`
- **Nombre sugerido (kebab-case):** `sales-analytics-forecasting-timeseries`
- **Funcionalidad:** Predicción de ventas próximas usando time-series (ARIMA/Prophet o simple moving average).
- **Historias de Usuario:** US-11 (Admin predice ventas de junio basado en histórico)
- **Dependencias:** ✅ `sales-analytics-ai-insights-openai` (requiere 6+ meses de histórico)
- **Estado:** ❌ **No implementado** (requiere statsmodels o similar)
- **Tareas Principales:**
  - Agregar a requirements.txt: `statsmodels>=0.13.0` (ARIMA)
  - Endpoint GET `/api/v1/sales/forecast?months_ahead=3` — predice ventas próximos 3 meses
  - Algoritmo: si <6 meses de datos, usa simple moving average; si >=6, usa ARIMA
  - Respuesta: {period: "2025-06", predicted_sales: 15000, confidence_interval: [14000, 16000]}
  - Tests: con/sin histórico suficiente, intervalos confianza válidos
- **Impacto:** Planificación financiera proactiva

---

### **ÉPICA 4: COMPLETAR MÓDULO CRM**

#### Change 13: `crm-endpoints-documentation-and-validation`
- **Nombre sugerido (kebab-case):** `crm-endpoints-full-implementation`
- **Funcionalidad:** Documentar todos los endpoints CRM (CRUD Professionals, Clients, Appointments, VisitReports) y completar validaciones.
- **Historias de Usuario:** US-12 (Profesional gestiona clientes, citas, reportes)
- **Dependencias:** ✅ `core-infrastructure-documentation`
- **Estado:** ⚠️ **Parcialmente implementado** (modelos existen, endpoints probables pero sin completa documentación)
- **Tareas Principales:**
  - Endpoints Professionals: GET (lista + filtros), POST (crear), GET /{id}, PATCH /{id}, DELETE /{id}
  - Endpoints Clients: GET, POST, GET /{id}, PATCH /{id}, DELETE /{id}, PATCH /{id}/professionals (upsert relación M:M)
  - Endpoints Appointments: GET (con filtros: professional, date range, status), POST, GET /{id}, PATCH /{id}, DELETE /{id}
  - Endpoints VisitReports: GET (con filtros), POST, GET /{id}, PATCH /{id}
  - Validaciones: profesional → tipos de cliente permitidos, appointment future only, estado transitions válidas
  - Tests: CRUD básico, validaciones de compatibilidad, aislamiento por tenant
- **Impacto:** CRM endpoints 100% funcionales

---

#### Change 14: `crm-google-calendar-sync`
- **Nombre sugerido (kebab-case):** `crm-google-calendar-integration`
- **Funcionalidad:** Sincronización bidireccional con Google Calendar para appointments.
- **Historias de Usuario:** US-13 (Cita creada en QR Registros aparece en Google Calendar del profesional)
- **Dependencias:** ✅ `crm-endpoints-documentation-and-validation` (requiere appointments funcionales)
- **Estado:** ❌ **No implementado** (requiere Google API)
- **Tareas Principales:**
  - Agregar a requirements.txt: `google-auth-oauthlib>=1.0.0`, `google-auth-httplib2>=0.2.0`, `google-api-python-client>=2.100.0`
  - Configurar OAuth2 para Google Calendar en variables de entorno
  - Endpoint POST `/api/v1/crm/sync/connect-calendar` — inicia flujo OAuth2 de Google
  - Endpoint GET `/api/v1/crm/sync/callback?code=...&state=...` — recibe auth code, persiste en DB
  - Cuando se crea CRMAppointment: crear event en Google Calendar del professional (si está conectado)
  - Cuando se modifica CRMAppointment: update event en Google Calendar
  - Cuando se cancela CRMAppointment: delete event en Google Calendar
  - Sincronización inversa (opcional): job que cada 15 min verifica nuevos eventos en Google y crea CRMAppointment si no existe
  - Tests: flujo OAuth completo, create/update/delete en calendar, manejo de desconexión
- **Impacto:** Calendario profesional sincronizado

---

#### Change 15: `crm-appointment-reminders`
- **Nombre sugerido (kebab-case):** `crm-appointment-reminders-automation`
- **Funcionalidad:** Recordatorios automáticos a profesional y cliente (email/SMS) antes de cita.
- **Historias de Usuario:** US-14 (Professional y client reciben recordatorio 24h antes de cita)
- **Dependencias:** ✅ `crm-google-calendar-sync` (requiere appointments confiables)
- **Estado:** ❌ **No implementado** (requiere email/SMS service)
- **Tareas Principales:**
  - Job asíncrono @ 10:00 AM UTC cada día: buscar appointments para mañana
  - Enviar email a professional con: "Cita con {client_name} a las {time} mañana"
  - Enviar email a client con: "Recordatorio: tu cita con {professional_name} a las {time}"
  - (Opcional) Enviar SMS si teléfono disponible (Twilio o similar)
  - Rastrear en tabla `AppointmentReminder` para no duplicar
  - Tests: reminder enviado al horario correcto, no duplicados, fallback si email falla
- **Impacto:** Reducción de no-shows

---

#### Change 16: `crm-visit-report-templates`
- **Nombre sugerido (kebab-case):** `crm-visit-report-templates`
- **Funcionalidad:** Plantillas de reportes de visita personalizables por professional/especialidad.
- **Historias de Usuario:** US-15 (Professional crea reporte usando template pre-hecho)
- **Dependencias:** ✅ `crm-endpoints-documentation-and-validation` (requiere visit reports)
- **Estado:** ❌ **No implementado** (requiere modelo VisitReportTemplate)
- **Tareas Principales:**
  - Nuevo modelo `CRMVisitReportTemplate`: tenant_id, professional_id, specialty, name, fields (JSON: {reason, summary, findings, actions, next_steps})
  - Endpoint POST `/api/v1/crm/visit-report-templates` — crear template
  - Endpoint GET `/api/v1/crm/visit-report-templates` — listar
  - Endpoint GET `/api/v1/crm/visit-report-templates/{id}` — obtener template
  - Al crear VisitReport, permitir `?template_id=...` para pre-llenar campos
  - Tests: crear template, usar en visita
- **Impacto:** Estandarización de reportes

---

### **ÉPICA 5: INFRAESTRUCTURA Y TESTING**

#### Change 17: `testing-suite-expansion`
- **Nombre sugerido (kebab-case):** `testing-comprehensive-coverage`
- **Funcionalidad:** Expandir tests para cubrir 70%+ del código (hoy: ~20%).
- **Historias de Usuario:** US-16 (Evitar regresiones en cambios futuros)
- **Dependencias:** ✅ Todos los changes anteriores
- **Estado:** ❌ **Crítica deficiencia** (solo 4 test files para codebase completo)
- **Tareas Principales:**
  - Crear test files:
    - `tests/test_auth_endpoints.py` — login, register, change-password, refresh-token
    - `tests/test_attendance_endpoints.py` — check-in/out, device binding, QR validation
    - `tests/test_sales_endpoints.py` — upload, summary, charts, insights
    - `tests/test_crm_endpoints.py` — CRUD todos los tipos
    - `tests/test_multitenancy.py` — isolación de datos, admin A no ve datos de B
    - `tests/test_validation_service.py` — QR token, device token, feature toggle
  - Cobertura meta: 70% del código
  - Integración en CI/CD (GitHub Actions): run tests en cada PR
  - Tests: happy path + error cases + security
- **Impacto:** Confianza en cambios, regresiones detectadas

---

#### Change 18: `monitoring-and-logging-setup`
- **Nombre sugerido (kebab-case):** `monitoring-logging-and-observability`
- **Funcionalidad:** Setup de logging centralizado, error tracking, y monitoring básico.
- **Historias de Usuario:** US-17 (DevOps/Admin puede diagnosticar issues en producción)
- **Dependencias:** ✅ Todos los changes anteriores
- **Estado:** ❌ **No implementado** (solo logging básico)
- **Tareas Principales:**
  - Agregar a requirements.txt: `sentry-sdk>=1.40.0` (o similar)
  - Configurar Sentry para producción (captura excepciones, errores)
  - Setup de logging estructurado (JSON format con context: tenant_id, admin_id, request_id)
  - Métricas básicas: request latency, error rate, database query time (usando Prometheus o similar)
  - Dashboard Grafana (opcional) para visualizar métricas
  - Tests: excepción es capturada en Sentry, logs tienen formato correcto
- **Impacto:** Diagnóstico rápido de issues

---

#### Change 19: `rate-limiting-and-security-hardening`
- **Nombre sugerido (kebab-case):** `rate-limiting-security-hardening`
- **Funcionalidad:** Implementar rate-limiting, CORS correcto, rate-limits por endpoint crítico.
- **Historias de Usuario:** US-18 (Prevenir abuse de endpoints)
- **Dependencias:** ✅ `core-infrastructure-documentation`
- **Estado:** ❌ **No implementado**
- **Tareas Principales:**
  - Agregar a requirements.txt: `slowapi>=0.1.8` (rate limiting middleware para FastAPI)
  - Rate limits:
    - Login: 5 intentos / 15 min por IP
    - Attendance check-in/out: 10 intentos / 60 seg por device_token
    - API general: 100 requests / 60 seg por tenant
  - CORS: permitir solo dominio del frontend (variable de entorno)
  - CSRF protection (si necesario para formularios)
  - Headers de seguridad: X-Content-Type-Options, X-Frame-Options, etc.
  - Tests: verificar rate limit es aplicado, bypass con válidos
- **Impacto:** Protección contra ataques simples, abuse mitigation

---

### **ÉPICA 6: INTERFACES Y FRONTEND (FUTURA)**

#### Change 20: `dashboard-admin-frontend-structure`
- **Nombre sugerido (kebab-case):** `dashboard-admin-frontend-react`
- **Funcionalidad:** Dashboard React para Tenant Admin con navegación, layout base, componentes reutilizables.
- **Historias de Usuario:** US-19 (Admin ve interfaz consistente para todas las funciones)
- **Dependencias:** ✅ Todos los changes backend completados
- **Estado:** ❌ **Probablemente estructura base existe en `app/frontend/`** pero sin documentación
- **Tareas Principales:**
  - Estructura: `src/pages/`, `src/components/`, `src/hooks/`, `src/services/api.ts`
  - Páginas: Login, Dashboard, Employees, QR Reader, Sales, CRM
  - Componentes: Header, Sidebar, Card, Table, Modal, Form
  - Animaciones Framer Motion: transiciones de página, hover effects
  - Integración API: fetch con auth token
  - Tests: componentes render correctamente, navegación funciona
- **Impacto:** Interface profesional para admin

---

---

## 📊 Matriz de Dependencias (ACTUALIZADA)

```
01-core-infrastructure-documentation (FIRST)
    ├─→ 02-auth-endpoint-completion
    ├─→ 03-config-validation-and-bootstrap
    ├─→ 04-database-indices-optimization
    │
    ├─→ 05-attendance-anomaly-detection-complete
    │     ├─→ 06-attendance-manual-adjustment-endpoint
    │     │     ├─→ 07-attendance-export-and-reporting
    │     │     │     └─→ 08-attendance-auto-closeout-scheduler
    │
    ├─→ 09-sales-analytics-validation-hardening
    │     ├─→ 10-sales-analytics-period-auto-closing (requiere: 08-auto-closeout)
    │     │     ├─→ 11-sales-analytics-ai-insights-integration
    │     │     │     └─→ 12-sales-analytics-forecasting
    │
    ├─→ 13-crm-endpoints-documentation-and-validation
    │     ├─→ 14-crm-google-calendar-sync
    │     │     ├─→ 15-crm-appointment-reminders
    │     ├─→ 16-crm-visit-report-templates
    │
    ├─→ 17-testing-comprehensive-coverage (puede iniciar después de 05, 09, 13)
    ├─→ 18-monitoring-logging-and-observability (puede iniciar después de 02)
    ├─→ 19-rate-limiting-security-hardening (puede iniciar después de 01)
    │
    └─→ 20-dashboard-admin-frontend-react (último, requiere todo backend funcional)
```

---

## 🎯 Orden Recomendado de Implementación

| # | Change | Prioridad | Esfuerzo | Estado Actual | Próximo Paso |
|---|--------|-----------|----------|--------------|------------|
| 1 | `core-infrastructure-documentation` | 🔴 CRÍTICA | 4h | ✅ Implementado | Documentar en SDD |
| 2 | `auth-endpoint-completion` | 🔴 CRÍTICA | 3h | ⚠️ Parcial | Completar `/auth/me`, `/change-password` |
| 3 | `config-validation-and-bootstrap` | 🔴 CRÍTICA | 4h | ⚠️ Parcial | Agregar validadores Pydantic |
| 4 | `database-indices-optimization` | 🟠 IMPORTANTE | 2h | ❌ No | Alembic migration |
| 5 | `attendance-anomaly-detection-complete` | 🔴 CRÍTICA | 3h | ✅ Funcional | Completar alertas + tabla AuditLog |
| 6 | `attendance-manual-adjustment-endpoint` | 🟠 IMPORTANTE | 3h | ❌ No | Implementar endpoint PATCH |
| 7 | `attendance-export-and-reporting` | 🟠 IMPORTANTE | 3h | ⚠️ CSV existe | Agregar PDF export |
| 8 | `attendance-auto-closeout-scheduler` | 🟠 IMPORTANTE | 4h | ❌ No | Agregar APScheduler, job |
| 9 | `sales-analytics-validation-hardening` | 🟠 IMPORTANTE | 3h | ⚠️ Parcial | Validación cruzada completa |
| 10 | `sales-analytics-period-auto-closing` | 🟡 MEDIA | 4h | ❌ No | Nuevo modelo + job |
| 11 | `sales-analytics-ai-insights-integration` | 🟡 MEDIA | 5h | ❌ No | OpenAI integration |
| 12 | `sales-analytics-forecasting` | 🟡 MEDIA | 4h | ❌ No | Time-series model |
| 13 | `crm-endpoints-documentation-and-validation` | 🔴 CRÍTICA | 6h | ⚠️ Parcial | Completar CRUD endpoints |
| 14 | `crm-google-calendar-sync` | 🟡 MEDIA | 5h | ❌ No | OAuth2 Google Calendar |
| 15 | `crm-appointment-reminders` | 🟡 MEDIA | 3h | ❌ No | Email scheduler + templates |
| 16 | `crm-visit-report-templates` | 🟡 MEDIA | 3h | ❌ No | Template model + endpoints |
| 17 | `testing-comprehensive-coverage` | 🟠 IMPORTANTE | 12h | ❌ Crítica deficiencia | Crear test files masivamente |
| 18 | `monitoring-logging-and-observability` | 🟠 IMPORTANTE | 6h | ❌ No | Sentry + logging setup |
| 19 | `rate-limiting-security-hardening` | 🔴 CRÍTICA | 3h | ❌ No | slowapi + CORS |
| 20 | `dashboard-admin-frontend-react` | 🟡 MEDIA | 15h | ⚠️ Base existe | Frontend SDD |

---

## 📋 Recomendación de Secuencia PRÁCTICO (3 fases)

### **FASE 1: HARDENING (2 semanas)**
Estabilizar lo que ya funciona.

1. `core-infrastructure-documentation`
2. `auth-endpoint-completion`
3. `config-validation-and-bootstrap`
4. `database-indices-optimization`
5. `testing-comprehensive-coverage` (iniciar en paralelo con testing nuevo código)
6. `rate-limiting-security-hardening`
7. `monitoring-logging-and-observability`

**Salida:** MVP listo para producción, documentado, testeado, securizado.

### **FASE 2: COMPLETAR FEATURES (3 semanas)**
Terminar funcionalidad iniciada.

8. `attendance-anomaly-detection-complete`
9. `attendance-manual-adjustment-endpoint`
10. `attendance-export-and-reporting`
11. `attendance-auto-closeout-scheduler`
12. `sales-analytics-validation-hardening`
13. `crm-endpoints-documentation-and-validation`

**Salida:** Módulos core 100% funcionales, testeados.

### **FASE 3: DIFERENCIADORES (3 semanas)**
Agregar inteligencia y UX.

14. `sales-analytics-period-auto-closing`
15. `sales-analytics-ai-insights-integration`
16. `sales-analytics-forecasting`
17. `crm-google-calendar-sync`
18. `crm-appointment-reminders`
19. `crm-visit-report-templates`
20. `dashboard-admin-frontend-react`

**Salida:** Plataforma completa, diferenciada, lista para SaaS comercial.

---

## 📝 Cómo Usar Este Mapa

### Para cada Change:

1. **Lee este documento** — entiende dependencias y orden.
2. **Comienza con Change 01:** `/opsx:propose core-infrastructure-documentation`
3. **El agente SDD generará:**
   - `proposal.md` — qué se va a hacer y por qué
   - `design.md` — arquitectura de la solución
   - `tasks.md` — checklist paso a paso
4. **Vos revisas y aprobas** — cambios necesarios antes de implementar
5. **Agente implementa:** `/opsx:apply core-infrastructure-documentation`
6. **Se archiva el change** — `/opsx:archive core-infrastructure-documentation`
7. **Próximo change:** ¡repeat!

---

## ✅ Checklist de Inicio

- [ ] Leer este documento COMPLETO
- [ ] Entender matriz de dependencias
- [ ] Verificar que `openspec/` existe: `openspec list`
- [ ] Comenzar con: `/opsx:propose core-infrastructure-documentation`
- [ ] Revisar artefactos generados
- [ ] Aprobar y ejecutar: `/opsx:apply core-infrastructure-documentation`
- [ ] Una vez archivado, pasar a Change 02

---

## 📊 Resumen del Proyecto (ESTADO ACTUAL)

| Aspecto | Cobertura | Notas |
|--------|-----------|-------|
| **Multitenancy** | ✅ 100% | Row-level security, tenant_id indexed |
| **Autenticación** | ⚠️ 80% | Login/register OK, falta `/auth/me`, `/change-password` |
| **QR Attendance** | ✅ 80% | Check-in/out funciona, falta auto-closeout scheduler |
| **Sales Analytics** | ✅ 90% | Upload, agregados, charts OK, falta AI insights, forecasting |
| **CRM Core** | ✅ 85% | CRUD OK, falta Google Calendar sync, reminders |
| **Testing** | ❌ 20% | Solo 4 archivos, cobertura crítica |
| **Monitoring** | ❌ 0% | Sin Sentry, sin logging centralizado |
| **Rate Limiting** | ❌ 0% | Vulnerable a abuse |
| **Frontend** | ⚠️ Desconocido | Estructura base probables, sin documentación SDD |

**Maturity: 3.5 / 5** — MVP funcional pero necesita hardening y documentación SDD.

---

*Documento generado con SDD (Spec-Driven Development) usando OpenSpec Framework.*  
*Última actualización: 2025-05-07*  
*Total Changes Propuestos: 20*  
*Esfuerzo Estimado: 18 semanas (completo) / 2 semanas (FASE 1: MVP)*
