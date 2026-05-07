SaaS Management Suite — Arquitectura del
Sistema

1. Visión General
El sistema es una plataforma SaaS B2B diseñada para digitalizar y automatizar operaciones de
empresas y profesionales independientes. Su propósito fundamental es ofrecer módulos independientes (control de asistencia, CRM 
analítica de ventas, gestion de stock y de turnos) que las empresas o independientes pueden contratar mediante suscripciones mensuales. La
plataforma está diseñada bajo un modelo multi-tenant, garantizando el aislamiento de datos entre
empresas mientras se comparte la misma infraestructura.

2. Actores del Sistema
SuperAdmin: Propietario de la plataforma SaaS. Tiene control global para gestionar altas de
clientes (Tenants), administrar sus suscripciones a módulos específicos, restablecer contraseñas y
monitorear el estado general de la plataforma.
Tenant (Empresa): Cliente B2B de la plataforma. Administra su propia instancia, configura a sus
empleados, visualiza las métricas de negocio, genera reportes de liquidación de sueldos y sube
los reportes de ventas mensuales. Tambien accede al módulo CRM para la
gestión de pacientes/clientes, turnos y expedientes. Su visibilidad está estrictamente aislada a los datos de su
propia organización.
Empleado: Usuario final que consume los servicios habilitados por su Tenant. Utiliza la aplicación
para el fichaje de asistencia mediante código QR dinámico
Sistema (IA & Background): Agente automatizado encargado de  procesar los
archivos CSV de ventas, ejecutar algoritmos analíticos e inteligencia artificial para devolver
*insights* de negocio, y procesar los cierres automáticos de jornada.

3. Stack Tecnológico
Backend: Desarrollado en FastAPI (Python) con SQLAlchemy y Alembic para migraciones de base
de datos PostgreSQL. La arquitectura es modular, permitiendo separar dominios complejos (QR, Ventas,
CRM) ademas de poder utilizar /activar/descativar cada modulo por separado y para muchas empresas al mismo tiempo.
•

•

•

•

Frontend: Construido con React, integrando animaciones fluidas con Framer Motion y estilizado
mediante Tailwind CSS, priorizando componentes modulares y una experiencia de usuario de alta
calidad para el dashboard de los tenants.

4. Módulos Core y Lógica de Negocio
4.1. Módulo de Control de Asistencia (QR Anti-Spoofing)
El sistema de presentismo utiliza un enfoque de seguridad avanzado. En las instalaciones de la empresa
(Tenant) se muestra un código QR dinámico que se regenera cada 30 segundos, mitigando la
posibilidad de fotos o capturas estáticas.

Flujo de Vinculación y Fichaje:
1. Primer uso: El empleado escanea el QR. El sistema detecta que es un dispositivo nuevo y le
solicita autenticación (nombre/credenciales) de una lista de empleados  previamente cargado por el tenant. El identificador del dispositivo (DeviceID)
queda asociado permanentemente a ese empleado.
2. Uso continuo: En los días subsiguientes, el empleado simplemente escanea el QR. El sistema

lo reconoce silenciosamente por la vinculación de su dispositivo, registrando el Check-In o Check-
Out de forma instantánea al tocar el boton fichar, impidiendo la suplantación de identidad (buddy punching).

4.2. Propuesta de Solución: Jornadas Abiertas (Check-Out Faltante)
Dado que las jornadas no tienen estados de ciclo de vida complejos (simplemente se finalizan), es vital
manejar los olvidos de check-out para no corromper la liquidación.
Solución implementada: Se implementa un job asíncrono (ej. Celery/Cron) que corre a las 03:00 AM
(o a un límite de 14 horas desde el check-in). Si encuentra una jornada sin check-out, la cierra
automáticamente registrando el tiempo esperado del turno del empleado o truncando a un máximo de
horas, y marcando la fila en la BD con un flag booleano requiere_revision = True . Esto alerta al
Tenant en su panel para que confirme o edite la liquidación manualmente.
4.3. Módulo de Liquidación
El sistema genera un reporte automatizado calculando el tiempo trabajado. La fórmula base aplica:
Liquidación = Σ (Horas Trabajadas × Tarifa Empleado). Este reporte se exporta para que el Tenant realice
el pago a través de sus propios medios financieros (el SaaS no es una pasarela de pago de nóminas,
solo genera la información).

4.4. Módulo de Analítica de Ventas (IA + CSV)
El Tenant puede subir un archivo .csv estandarizado con su registro de ventas histórico. El sistema lo
procesa extrayendo KPIs fundamentales:
Ventas totales y ganancia neta.
Ticket promedio (Total Ingresos / Cantidad de Transacciones).
Días u horas pico de ventas.
Posteriormente, el dataset resumido se inyecta en un modelo LLM (ej. vía API de OpenAI/Gemini) como
contexto, generando recomendaciones predictivas de negocio ("Tus ventas bajan los martes, te
sugerimos X promoción").
4.5. Módulo CRM (Pacientes / Turnos)
Pensado principalmente para verticales como clínicas o servicios abogados o medicos individuales, este módulo permite 
gestionar una base de datos de pacientes, un calendario de turnos y expedientes médicos/técnicos.
Está altamente aislado para que un Empleado solo vea los datos del Tenant al que pertenece.

5. Modelo Multi-Tenant y Suscripciones
Cada empresa es un Tenant . El modelo de negocio se basa en suscripciones mensuales por módulo
habilitado ( TenantFeature ). Cuando el SuperAdmin habilita el módulo de CRM para un Tenant, las
rutas y UI del Frontend se desbloquean automáticamente para sus empleados.