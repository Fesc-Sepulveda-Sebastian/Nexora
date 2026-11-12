# ESPECIFICACIÓN MAESTRA DE ARQUITECTURA Y REGLAS DE NEGOCIO — NEXORA

## 1. Propuesta de Valor y Roles (Guía 01)
- Marketplace B2B/B2C para conectar marcas/PyMEs con creadores UGC e influencers bajo principios de programación funcional (funciones puras e inmutabilidad).
- Roles: Marca, Creador, Administrador.
- Pilares: Registro por roles, Media Kit dinámico, clasificación automática de audiencia, Matchmaking algorítmico y pagos en custodia (Escrow).

## 2. Clasificación, Tarifas y Validaciones (Guías 02 y 03)
- Niveles de Influencer y Tarifas Simulador:
  - Nano (< 10,000 seg.): $100 USD/pub.
  - Micro (10,000 a 99,999 seg.): $500 USD/pub.
  - Medio (100,000 a 1,000,000 seg.): Cotización personalizada.
  - Macro (> 1,000,000 seg.): $2,000 USD/pub (elegible NEXORA Premium).
- Reglas de Validación:
  - Umbral general: >= 5,000 seguidores; presupuesto mínimo >= $100 USD.
  - Engagement Rate estricto: 0.0% <= engagement <= 100.0%.
  - Viabilidad financiera: Costo Total = Tarifa * Publicaciones; Diferencia = Presupuesto - Costo Total (aprobado si Diferencia >= 0).
  - Contratación (condicional anidado, plazo 15 días): Marca verificada AND not tiene_deudas AND influencer disponible.
  - Postulación: campana_abierta == True AND cumple_requisitos (nicho) == True.
  - Liberación Escrow: contenido_aprobado == True AND facturacion_lista == True.
  - Permisos/Beneficios: Métricas para (es_creador or es_administrador); NEXORA Premium sin costo si (es_marca_verificada or es_influencer_top).

## 3. Costeo, Módulos y Prototipo Unidad 1 (Guías 04 y 05)
- Costeo de Pauta: (Días * Costo Diario) + Costo Diseño.
- Módulos: ['Inicio', 'Usuarios', 'Gestión de campañas', 'Analítica y reportes', 'Configuración'].
- Plataformas: ['Instagram', 'TikTok', 'YouTube', 'Facebook', 'Twitch'].
- RF1 (Registrar Creador): Vector [codigo, nombre, nicho, ciudad, seguidores, engagement, tarifa, disponible] con código .strip().upper() único y valores numéricos >= 0.
- RF2 (Consultar Creador): Búsqueda secuencial insensible a mayúsculas con buscar_indice_por_codigo(codigo) (retorna índice o -1).
- RF3 (Valor Colaboración): Requiere creador disponible y piezas > 0; aplica 10% de descuento automático si piezas >= 5.

## 4. Motor de Matchmaking (Guía 06)
- Menú sostenido con ciclo while (salida segura con '0' y break) y recorrido de colecciones con for.
- Filtro de seguridad: Si creador['infracciones'] == True, alerta y omite con continue.
- Emparejamiento anidado: Cruza campañas activas y creadores disponibles validando (creador.nicho == campana.nicho and creador.seguidores >= campana.min_seguidores).

## 5. Entidad Campaña, Ordenamiento y Matrices (Guías 07, 08 y 09)
- Tupla inmutable ESTADOS_VALIDOS = ('Borrador', 'Activa', 'Pausada', 'Finalizada'), con fallback a 'Borrador'.
- Diccionario de campaña: codigo, titulo, nicho, presupuesto, min_seguidores, estado + CRUD completo.
- RF-04 (Guía 08): Ordenamiento bidireccional con sorted() y lambda por presupuesto sin mutar original; búsqueda unívoca con break; filtro por nicho con list comprehension; analítica con max(), min() y promedio.
- Matriz 3x3 (Guía 09): Filas (3 campañas) x Columnas (Lunes, Miércoles, Viernes), captura validada y cálculo de suma por filas, suma por columnas, total general y promedio por celda.

## 6. Backend Modular y Funciones Puras (Guía 10)
- Funciones puras obligatorias:
  - calcular_comision_nexora(presupuesto: float, tasa: float = 0.10) -> float
  - calcular_costo_total_campana(presupuesto: float, comision: float) -> float
  - calcular_engagement_rate(seguidores: int, interacciones: int) -> float (controlando seguidores <= 0)
- Separación estricta entre funciones puras y procedimientos de interfaz, con punto de entrada if __name__ == '__main__':.

## 7. Arquitectura Full-Stack y Pendientes Críticos (H01–H13)
- Stack: React + TS + Vite (PWA, Service Worker, IndexedDB) + FastAPI/SQLAlchemy/Pydantic + PostgreSQL, MongoDB y MinIO en Docker Compose.
- Alcance: 31 RF, 22 RNF, 6 RN y 16 HU.
- Hallazgos por cerrar (H01–H13):
  - H01–H03: Restringir alta pública de admin y proteger lecturas de borradores, acuerdos, mensajes y WebSockets.
  - H04: Aislar claves de idempotencia por actor y payload.
  - H05–H07: Corregir errores HTTP 500 en aceptación de acuerdos, conflictos 409 de campaña y solicitudes de privacidad.
  - H08: Completar subida binaria PUT y verificación SHA-256 de evidencias.
  - H09: Etiquetar métricas simuladas como DEMO.
  - H10–H13: Conectar vista IU-06 y cola offline IndexedDB con persistencia real.