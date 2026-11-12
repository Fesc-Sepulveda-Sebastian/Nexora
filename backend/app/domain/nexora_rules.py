"""
Módulo de dominio puro e inmutable — NEXORA (Guías 01 a 10).

Reglas de diseño:
- Todas las funciones definidas aquí son puras: no leen stdin, no imprimen en stdout,
  no realizan I/O de red/disco y no mutan las colecciones recibidas como argumento.
"""

from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

# Catálogos y tuplas inmutables (Guías 04 y 07)
MODULOS: Tuple[str, ...] = (
    "Inicio",
    "Usuarios",
    "Gestión de campañas",
    "Analítica y reportes",
    "Configuración",
)

PLATAFORMAS: Tuple[str, ...] = (
    "Instagram",
    "TikTok",
    "YouTube",
    "Facebook",
    "Twitch",
)

ESTADOS_VALIDOS: Tuple[str, ...] = (
    "Borrador",
    "Activa",
    "Pausada",
    "Finalizada",
)

CAMPANAS_MATRIZ_DEFAULT: Tuple[str, ...] = (
    "Auriculares X200",
    "Moda Urbana Verano",
    "Gamer Energy Pro",
)

DIAS_MATRIZ_DEFAULT: Tuple[str, ...] = (
    "Lunes",
    "Miércoles",
    "Viernes",
)


# ---------------------------------------------------------------------------
# Guías 02 y 03: Clasificación, Tarifas Simulador y Validaciones de Negocio
# ---------------------------------------------------------------------------

def clasificar_creador_y_tarifa(seguidores: int) -> Dict[str, Any]:
    """
    Clasifica al creador y determina su tarifa base en USD según Guía 02:
    - Nano (< 10,000 seg.): $100 USD/pub.
    - Micro (10,000 a 99,999 seg.): $500 USD/pub.
    - Medio (100,000 a 1,000,000 seg.): Cotización personalizada.
    - Macro (> 1,000,000 seg.): $2,000 USD/pub (elegible NEXORA Premium).
    """
    if seguidores < 0:
        raise ValueError("El número de seguidores no puede ser negativo.")

    if seguidores < 10_000:
        return {
            "nivel": "Nano",
            "tarifa_usd": 100.0,
            "cotizacion_personalizada": False,
            "etiqueta_tarifa": "$100 USD/pub.",
            "elegible_nexora_premium": False,
        }
    if seguidores <= 99_999:
        return {
            "nivel": "Micro",
            "tarifa_usd": 500.0,
            "cotizacion_personalizada": False,
            "etiqueta_tarifa": "$500 USD/pub.",
            "elegible_nexora_premium": False,
        }
    if seguidores <= 1_000_000:
        return {
            "nivel": "Medio",
            "tarifa_usd": None,
            "cotizacion_personalizada": True,
            "etiqueta_tarifa": "Cotización personalizada",
            "elegible_nexora_premium": False,
        }
    return {
        "nivel": "Macro",
        "tarifa_usd": 2000.0,
        "cotizacion_personalizada": False,
        "etiqueta_tarifa": "$2,000 USD/pub.",
        "elegible_nexora_premium": True,
    }


def validar_umbral_seguidores(seguidores: int, minimo: int = 5000) -> bool:
    """Umbral general (Guía 02–03): >= 5,000 seguidores."""
    return int(seguidores) >= minimo


def validar_presupuesto_minimo(presupuesto_usd: float, minimo_usd: float = 100.0) -> bool:
    """Presupuesto mínimo general (Guía 02–03): >= $100 USD."""
    return float(presupuesto_usd) >= minimo_usd


def validar_engagement_estricto(engagement: float) -> bool:
    """Engagement Rate estricto (Guía 02–03): 0.0% <= engagement <= 100.0%."""
    valor = float(engagement)
    return 0.0 <= valor <= 100.0


def evaluar_viabilidad_financiera(
    tarifa: float,
    publicaciones: int,
    presupuesto: float,
) -> Dict[str, Any]:
    """
    Viabilidad financiera (Guía 02–03):
    Costo Total = Tarifa * Publicaciones;
    Diferencia = Presupuesto - Costo Total (aprobado si Diferencia >= 0).
    """
    if tarifa < 0 or publicaciones <= 0 or presupuesto < 0:
        raise ValueError("Tarifa y presupuesto deben ser >= 0 y publicaciones > 0.")

    costo_total = round(float(tarifa) * int(publicaciones), 2)
    diferencia = round(float(presupuesto) - costo_total, 2)
    return {
        "costo_total": costo_total,
        "diferencia": diferencia,
        "aprobado": diferencia >= 0.0,
    }


def validar_contratacion(
    marca_verificada: bool,
    tiene_deudas: bool,
    influencer_disponible: bool,
    plazo_dias: int = 15,
) -> Dict[str, Any]:
    """
    Contratación (condicional anidado, plazo 15 días):
    Marca verificada AND not tiene_deudas AND influencer disponible.
    """
    if marca_verificada:
        if not tiene_deudas:
            if influencer_disponible:
                return {
                    "aprobado": True,
                    "plazo_dias": plazo_dias,
                    "motivo": "Contratación autorizada con plazo estándar de 15 días.",
                }
            return {
                "aprobado": False,
                "plazo_dias": plazo_dias,
                "motivo": "El creador/influencer no se encuentra disponible.",
            }
        return {
            "aprobado": False,
            "plazo_dias": plazo_dias,
            "motivo": "La marca presenta deudas pendientes.",
        }
    return {
        "aprobado": False,
        "plazo_dias": plazo_dias,
        "motivo": "La marca no está verificada.",
    }


def cumple_requisitos_nicho(nicho_campana: Optional[str], nicho_creador: Optional[str]) -> bool:
    if not nicho_campana or not nicho_creador:
        return False
    return nicho_campana.strip().lower() == nicho_creador.strip().lower()


def validar_postulacion(campana_abierta: bool, cumple_requisitos: bool) -> bool:
    """Postulación (Guía 02–03): campana_abierta == True AND cumple_requisitos == True."""
    return (campana_abierta is True) and (cumple_requisitos is True)


def validar_liberacion_escrow(contenido_aprobado: bool, facturacion_lista: bool) -> bool:
    """Liberación Escrow (Guía 02–03): contenido_aprobado == True AND facturacion_lista == True."""
    return (contenido_aprobado is True) and (facturacion_lista is True)


def puede_ver_metricas(es_creador: bool, es_administrador: bool) -> bool:
    """Permiso de métricas (Guía 03): es_creador OR es_administrador."""
    return bool(es_creador or es_administrador)


def es_elegible_premium_sin_costo(es_marca_verificada: bool, es_influencer_top: bool) -> bool:
    """NEXORA Premium sin costo (Guía 03): es_marca_verificada OR es_influencer_top."""
    return bool(es_marca_verificada or es_influencer_top)


# ---------------------------------------------------------------------------
# Guías 04 y 05: Costeo de Pauta y Prototipo Unidad 1 (RF1, RF2, RF3)
# ---------------------------------------------------------------------------

def calcular_costeo_pauta(dias: int, costo_diario: float, costo_diseno: float) -> float:
    """Costeo de Pauta (Guía 04): (Días * Costo Diario) + Costo Diseño."""
    if dias < 0 or costo_diario < 0 or costo_diseno < 0:
        raise ValueError("Días, costo diario y costo de diseño deben ser >= 0.")
    return round((int(dias) * float(costo_diario)) + float(costo_diseno), 2)


def buscar_indice_por_codigo(
    codigo: str,
    creadores: Optional[Sequence[Sequence[Any]]] = None,
) -> int:
    """
    RF2 (Guía 05): Búsqueda secuencial insensible a mayúsculas.
    Retorna el índice del creador en la lista o -1 si no existe.
    """
    if not creadores:
        return -1
    codigo_buscado = str(codigo or "").strip().upper()
    for idx, creador in enumerate(creadores):
        if len(creador) > 0 and str(creador[0]).strip().upper() == codigo_buscado:
            return idx
    return -1


def registrar_creador(
    creadores: Sequence[Sequence[Any]],
    codigo: str,
    nombre: str,
    nicho: str,
    ciudad: str,
    seguidores: int,
    engagement: float,
    tarifa: float,
    disponible: bool = True,
) -> List[List[Any]]:
    """
    RF1 (Guía 05): Registra vector [codigo, nombre, nicho, ciudad, seguidores, engagement, tarifa, disponible]
    de forma inmutable (retorna una nueva lista sin mutar la original).
    """
    codigo_norm = str(codigo or "").strip().upper()
    if not codigo_norm:
        raise ValueError("El código del creador es obligatorio.")
    if not str(nombre or "").strip():
        raise ValueError("El nombre del creador es obligatorio.")
    if int(seguidores) < 0 or float(engagement) < 0 or float(tarifa) < 0:
        raise ValueError("Seguidores, engagement y tarifa deben ser >= 0.")
    if not validar_engagement_estricto(float(engagement)):
        raise ValueError("El engagement debe estar entre 0.0% y 100.0%.")
    if buscar_indice_por_codigo(codigo_norm, creadores) != -1:
        raise ValueError(f"Ya existe un creador registrado con el código '{codigo_norm}'.")

    nuevo_vector: List[Any] = [
        codigo_norm,
        str(nombre).strip(),
        str(nicho).strip(),
        str(ciudad).strip(),
        int(seguidores),
        float(engagement),
        float(tarifa),
        bool(disponible),
    ]
    nueva_lista = [list(item) for item in creadores]
    nueva_lista.append(nuevo_vector)
    return nueva_lista


def calcular_valor_colaboracion(
    tarifa: float,
    disponible: bool,
    piezas: int,
) -> Dict[str, Any]:
    """
    RF3 (Guía 05): Requiere creador disponible y piezas > 0;
    aplica 10% de descuento automático si piezas >= 5.
    """
    if not disponible:
        raise ValueError("El creador no se encuentra disponible para colaborar.")
    if int(piezas) <= 0:
        raise ValueError("La cantidad de piezas debe ser mayor a 0.")
    if float(tarifa) < 0:
        raise ValueError("La tarifa no puede ser negativa.")

    subtotal = round(float(tarifa) * int(piezas), 2)
    tasa_descuento = 0.10 if int(piezas) >= 5 else 0.0
    descuento = round(subtotal * tasa_descuento, 2)
    total = round(subtotal - descuento, 2)
    return {
        "piezas": int(piezas),
        "subtotal": subtotal,
        "descuento_porcentaje": int(tasa_descuento * 100),
        "descuento_monto": descuento,
        "total": total,
    }


# ---------------------------------------------------------------------------
# Guía 06: Motor de Matchmaking y Filtro de Infracciones con continue
# ---------------------------------------------------------------------------

def filtrar_creadores_sin_infracciones(
    creadores: Sequence[Mapping[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Filtro de seguridad (Guía 06):
    Recorre con `for`; si creador['infracciones'] == True, registra alerta y omite con `continue`.
    """
    habilitados: List[Dict[str, Any]] = []
    alertas: List[str] = []

    for creador in creadores:
        if creador.get("infracciones") is True:
            nombre = creador.get("nombre") or creador.get("codigo") or "Desconocido"
            alertas.append(f"ALERTA SEGURIDAD: Creador '{nombre}' omitido por infracciones activas.")
            continue
        habilitados.append(dict(creador))

    return habilitados, alertas


def emparejar_campanas_y_creadores(
    campanas: Sequence[Mapping[str, Any]],
    creadores: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    """
    Emparejamiento anidado (Guía 06):
    Cruza campañas activas y creadores disponibles validando:
    - Filtro de infracciones con `continue`
    - creador.nicho == campana.nicho AND creador.seguidores >= campana.min_seguidores
    """
    emparejamientos: List[Dict[str, Any]] = []
    alertas: List[str] = []

    for campana in campanas:
        estado = str(campana.get("estado", "")).strip()
        if estado != "Activa":
            continue

        nicho_camp = str(campana.get("nicho", "")).strip().lower()
        min_seg = int(campana.get("min_seguidores", 0))

        for creador in creadores:
            if creador.get("infracciones") is True:
                nombre = creador.get("nombre") or creador.get("codigo") or "Desconocido"
                alerta = f"ALERTA SEGURIDAD: Creador '{nombre}' omitido por infracciones."
                if alerta not in alertas:
                    alertas.append(alerta)
                continue

            if not creador.get("disponible", True):
                continue

            nicho_creador = str(creador.get("nicho", "")).strip().lower()
            seguidores = int(creador.get("seguidores", 0))

            if nicho_creador == nicho_camp and seguidores >= min_seg:
                emparejamientos.append({
                    "campana_codigo": campana.get("codigo"),
                    "campana_titulo": campana.get("titulo"),
                    "creador_codigo": creador.get("codigo"),
                    "creador_nombre": creador.get("nombre"),
                    "nicho": creador.get("nicho"),
                    "seguidores": seguidores,
                })

    return {"emparejamientos": emparejamientos, "alertas": alertas}


# ---------------------------------------------------------------------------
# Guías 07 y 08: Entidad Campaña, CRUD Inmutable y Ordenamiento Funcional
# ---------------------------------------------------------------------------

def normalizar_estado_campana(estado: Optional[str]) -> str:
    """Valida contra tupla inmutable ESTADOS_VALIDOS, con fallback a 'Borrador'."""
    if not estado:
        return "Borrador"
    limpio = str(estado).strip().capitalize()
    if limpio in ESTADOS_VALIDOS:
        return limpio
    return "Borrador"


def crear_campana_dict(
    codigo: str,
    titulo: str,
    nicho: str,
    presupuesto: float,
    min_seguidores: int,
    estado: str = "Borrador",
) -> Dict[str, Any]:
    codigo_norm = str(codigo or "").strip().upper()
    if not codigo_norm:
        raise ValueError("El código de campaña es obligatorio.")
    if float(presupuesto) < 0 or int(min_seguidores) < 0:
        raise ValueError("Presupuesto y mínimo de seguidores deben ser >= 0.")
    return {
        "codigo": codigo_norm,
        "titulo": str(titulo).strip(),
        "nicho": str(nicho).strip(),
        "presupuesto": float(presupuesto),
        "min_seguidores": int(min_seguidores),
        "estado": normalizar_estado_campana(estado),
    }


def agregar_campana(
    campanas: Sequence[Mapping[str, Any]],
    nueva_campana: Mapping[str, Any],
) -> List[Dict[str, Any]]:
    codigo_norm = str(nueva_campana.get("codigo", "")).strip().upper()
    if buscar_campana_por_codigo(campanas, codigo_norm) is not None:
        raise ValueError(f"Ya existe una campaña con código '{codigo_norm}'.")
    resultado = [dict(c) for c in campanas]
    resultado.append(dict(nueva_campana))
    return resultado


def actualizar_campana(
    campanas: Sequence[Mapping[str, Any]],
    codigo: str,
    cambios: Mapping[str, Any],
) -> List[Dict[str, Any]]:
    codigo_norm = str(codigo or "").strip().upper()
    encontrada = False
    resultado: List[Dict[str, Any]] = []
    for c in campanas:
        copia = dict(c)
        if str(copia.get("codigo", "")).strip().upper() == codigo_norm:
            encontrada = True
            for k, v in cambios.items():
                if k == "estado":
                    copia["estado"] = normalizar_estado_campana(v)
                elif k != "codigo":
                    copia[k] = v
        resultado.append(copia)
    if not encontrada:
        raise ValueError(f"Campaña '{codigo_norm}' no encontrada.")
    return resultado


def eliminar_campana(
    campanas: Sequence[Mapping[str, Any]],
    codigo: str,
) -> List[Dict[str, Any]]:
    codigo_norm = str(codigo or "").strip().upper()
    resultado = [
        dict(c)
        for c in campanas
        if str(c.get("codigo", "")).strip().upper() != codigo_norm
    ]
    if len(resultado) == len(campanas):
        raise ValueError(f"Campaña '{codigo_norm}' no encontrada.")
    return resultado


def ordenar_campanas(
    campanas: Sequence[Mapping[str, Any]],
    ascendente: bool = True,
) -> List[Dict[str, Any]]:
    """
    Guía 08: Ordenamiento bidireccional con sorted() y lambda por presupuesto
    sin mutar la lista original.
    """
    return sorted(
        (dict(c) for c in campanas),
        key=lambda campana: float(campana.get("presupuesto", 0.0)),
        reverse=not ascendente,
    )


def buscar_campana_por_codigo(
    campanas: Sequence[Mapping[str, Any]],
    codigo: str,
) -> Optional[Dict[str, Any]]:
    """Guía 08: Búsqueda unívoca con recorrido secuencial y `break`."""
    codigo_norm = str(codigo or "").strip().upper()
    encontrada: Optional[Dict[str, Any]] = None
    for campana in campanas:
        if str(campana.get("codigo", "")).strip().upper() == codigo_norm:
            encontrada = dict(campana)
            break
    return encontrada


def filtrar_campanas_por_nicho(
    campanas: Sequence[Mapping[str, Any]],
    nicho: str,
) -> List[Dict[str, Any]]:
    """Guía 08: Filtro por nicho usando list comprehension."""
    nicho_norm = str(nicho or "").strip().lower()
    return [
        dict(c)
        for c in campanas
        if str(c.get("nicho", "")).strip().lower() == nicho_norm
    ]


def metricas_financieras_nexora(
    campanas: Sequence[Mapping[str, Any]],
) -> Dict[str, float]:
    """
    Guía 08: Analítica financiera con max(), min() y promedio sobre presupuestos.
    """
    if not campanas:
        return {
            "total_campanas": 0,
            "presupuesto_maximo": 0.0,
            "presupuesto_minimo": 0.0,
            "presupuesto_promedio": 0.0,
            "presupuesto_total": 0.0,
        }

    presupuestos = [float(c.get("presupuesto", 0.0)) for c in campanas]
    total = round(sum(presupuestos), 2)
    return {
        "total_campanas": len(presupuestos),
        "presupuesto_maximo": round(max(presupuestos), 2),
        "presupuesto_minimo": round(min(presupuestos), 2),
        "presupuesto_promedio": round(total / len(presupuestos), 2),
        "presupuesto_total": total,
    }


# ---------------------------------------------------------------------------
# Guía 09: Matriz 3x3 de Rendimiento
# ---------------------------------------------------------------------------

def analizar_matriz_rendimiento(
    matriz: Sequence[Sequence[float]],
    campanas: Sequence[str] = CAMPANAS_MATRIZ_DEFAULT,
    dias: Sequence[str] = DIAS_MATRIZ_DEFAULT,
) -> Dict[str, Any]:
    """
    Guía 09: Analiza matriz 3x3 de montos float (3 campañas x Lunes/Miércoles/Viernes).
    Calcula suma por filas, suma por columnas, total general y promedio por celda.
    """
    if len(matriz) != 3 or len(campanas) != 3 or len(dias) != 3:
        raise ValueError("La matriz de rendimiento debe ser estrictamente de 3x3.")

    matriz_float: List[List[float]] = []
    for fila in matriz:
        if len(fila) != 3:
            raise ValueError("Cada fila de la matriz debe tener exactamente 3 columnas.")
        fila_norm: List[float] = []
        for valor in fila:
            monto = float(valor)
            if monto < 0:
                raise ValueError("Los montos de la matriz deben ser >= 0.")
            fila_norm.append(round(monto, 2))
        matriz_float.append(fila_norm)

    suma_filas: Dict[str, float] = {
        campanas[i]: round(sum(matriz_float[i]), 2)
        for i in range(3)
    }
    suma_columnas: Dict[str, float] = {
        dias[j]: round(sum(matriz_float[i][j] for i in range(3)), 2)
        for j in range(3)
    }
    total_general = round(sum(suma_filas.values()), 2)
    promedio_celda = round(total_general / 9.0, 2)

    return {
        "matriz": matriz_float,
        "suma_filas": suma_filas,
        "suma_columnas": suma_columnas,
        "total_general": total_general,
        "promedio_celda": promedio_celda,
    }


# ---------------------------------------------------------------------------
# Guía 10: Funciones Puras Obligatorias de Backend Modular
# ---------------------------------------------------------------------------

def calcular_comision_nexora(presupuesto: float, tasa: float = 0.10) -> float:
    """Calcula la comisión de plataforma NEXORA (10% por defecto)."""
    if presupuesto < 0 or tasa < 0:
        raise ValueError("Presupuesto y tasa de comisión deben ser >= 0.")
    return round(float(presupuesto) * float(tasa), 2)


def calcular_costo_total_campana(presupuesto: float, comision: float) -> float:
    """Calcula el costo total de la campaña sumando presupuesto y comisión."""
    if presupuesto < 0 or comision < 0:
        raise ValueError("Presupuesto y comisión deben ser >= 0.")
    return round(float(presupuesto) + float(comision), 2)


def calcular_engagement_rate(seguidores: int, interacciones: int) -> float:
    """
    Calcula la tasa de engagement ((interacciones / seguidores) * 100),
    controlando explícitamente el caso borde seguidores <= 0.
    """
    if int(seguidores) <= 0:
        return 0.0
    if int(interacciones) < 0:
        raise ValueError("Las interacciones no pueden ser negativas.")
    return round((int(interacciones) / int(seguidores)) * 100.0, 2)

