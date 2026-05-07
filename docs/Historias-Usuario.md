SaaS App — Backlog e Historias de Usuario

Organizado por orden lógico de implementación bajo el framework OpenSpec (Spec-Driven Development).
EPIC 01 — Core Multi-Tenant y Suscripciones
US-01: Alta de nuevo Tenant (Empresa) Alta
Historia: Como SuperAdmin, quiero dar de alta a una nueva empresa cliente (Tenant) con sus datos
base, para que puedan comenzar a usar la plataforma.
Criterios de Aceptación:
El SuperAdmin crea el Tenant generando las credenciales del dueño.
Se asigna un ID único de Tenant que se propagará a todas sus entidades (aislamiento de datos).
El sistema envía un email de bienvenida con la contraseña temporal.

US-02: Gestión de Suscripciones a Módulos Alta
Historia: Como SuperAdmin, quiero habilitar o deshabilitar módulos específicos (QR, CRM, Analítica)
para un Tenant, para controlar su facturación y acceso a funcionalidades.
Criterios de Aceptación:
Si el Tenant no tiene activo el módulo "CRM", la API rechaza peticiones a rutas `/api/v1/crm/*` con
error 403.
El Frontend oculta las opciones de menú correspondientes al módulo inactivo.

EPIC 02 — Módulo de Control de Asistencia (QR)
US-03: Carga de empleados via csv/excel
Historia: Como Tenant, quiero cargar tener la posibilidad de cargar a mis empleados en bache mediante un csv el cual va a tener como campos, nombre apellido, sector, convenio y precio x hr
Criterios de Aceptación:
El sistema tiene un boton para subir un archivo csv y excel que va a ser leido y automaticamente se devolverá un modal con la cantidad de empleados encontrados y cargados al sistema y a la db.


US-03.1: Generación de QR Dinámico Alta
Historia: Como Tenant, quiero tener una pantalla que muestre un código QR que se actualice cada 1min
segundos, para que mis empleados lo escaneen físicamente en el local.
Criterios de Aceptación:
El QR contiene un token encriptado que expira a los 60 segundos.
Si un empleado escanea un QR vencido (foto antigua), el servidor lo rechaza.
•
•
•

•

•

•
•

US-04: Vinculación Inicial de Dispositivo Anti-Spoofing Alta
Historia: Como Empleado, al escanear el QR por primera vez, quiero identificarme para vincular mi
dispositivo a mi cuenta.
Criterios de Aceptación:
El sistema captura un deviceid del dispositivo web/app del empleado.
Una vez vinculado, ese  se guarda en la tabla `DispositivoVinculado` asociado al ID del
Empleado.

US-05: Fichaje Rápido (Check-In / Check-Out) Alta
Historia: Como Empleado con dispositivo vinculado, quiero escanear el QR diario y registrar mi
entrada/salida automáticamente sin volver a loguearme.
Criterios de Aceptación:
El sistema lee el token del QR y valida el deviceid del dispositivo del empleado en background.
Luego del escaneo Los empleados deben tocar un boton que diga "Fichar" para registrar la entrada salida
Si no hay jornada abierta hoy, crea una con la hora actual (Check-In).
Si hay una jornada abierta, la finaliza registrando la hora actual (Check-Out).

US-06: Cierre Automático de Jornada (Failsafe) Media
Historia: Como Sistema, quiero cerrar automáticamente las jornadas que llevan más de 14 horas
abiertas, para evitar errores en la liquidación cuando un empleado olvida el check-out.
Criterios de Aceptación:
Un proceso asíncrono revisa jornadas abiertas de más de 14h.
Las cierra estableciendo una hora de salida truncada y marca la fila con `requiere_revision = True`.
•
•

•
•
•

•
•

EPIC 03 — Liquidación de Sueldos
US-07: Reporte de Liquidación Alta
Historia: Como Tenant, quiero ver un reporte consolidado con las horas trabajadas de mis empleados y
el monto a pagar, para procesar los pagos de nómina externamente.
Criterios de Aceptación:
El sistema suma las horas de jornadas finalizadas en un mes calendario.
Multiplica las horas por la tarifa horaria asignada al perfil del empleado.
Permite exportar el resumen (CSV o PDF).

EPIC 04 — Analítica de Ventas con IA

US-08: Subida y Parseo de CSV de Ventas Media
Historia: Como Tenant, quiero subir el registro mensual de ventas en formato CSV, para que la
plataforma extraiga las métricas clave.
Criterios de Aceptación:
El sistema valida el formato de columnas (producto, venta, cantidad, precio, día).
Calcula internamente: Ventas Totales, Ganancia, Ticket Promedio y Días Pico.

US-09: Insights de Negocio generados por IA Alta
Historia: Como Tenant, quiero recibir recomendaciones automáticas basadas en mis ventas recientes,
para mejorar la rentabilidad.
Criterios de Aceptación:
El backend envía el dataset resumido (anonimizado) a un LLM via API.
La IA devuelve 3 observaciones clave y 2 recomendaciones accionables que se muestran en el
dashboard de Ventas.
•
•
•

•
•

•
•

EPIC 05 — Módulo CRM (Pacientes / Turnos)
US-10: Gestión de Pacientes y Expedientes Media
Historia: Como Empleado, quiero registrar pacientes y guardar notas en sus expedientes, para
mantener el historial de atención.
Criterios de Aceptación:
Alta, baja y modificación de registros de pacientes aislados por Tenant.
Sistema de notas cronológicas (expediente) en el perfil del paciente.