"""
Interfaz de consola modular — NEXORA (Guías 05 a 10).
Separa estrictamente procedimientos de interfaz (entrada/salida) de las funciones puras
definidas en `app.domain.nexora_rules`.
"""

from typing import Any, Callable, Dict, List, Optional, Sequence
from app.domain.nexora_rules import (
    CAMPANAS_MATRIZ_DEFAULT,
    DIAS_MATRIZ_DEFAULT,
    ESTADOS_VALIDOS,
    MODULOS,
    PLATAFORMAS,
    agregar_campana,
    analizar_matriz_rendimiento,
    buscar_campana_por_codigo,
    buscar_indice_por_codigo as _buscar_indice_puro,
    calcular_comision_nexora,
    calcular_costo_total_campana,
    calcular_engagement_rate,
    calcular_valor_colaboracion,
    clasificar_creador_y_tarifa,
    crear_campana_dict,
    emparejar_campanas_y_creadores,
    filtrar_campanas_por_nicho,
    metricas_financieras_nexora,
    ordenar_campanas,
    registrar_creador as _registrar_creador_puro,
)

# Estado en memoria para uso interactivo de consola
_REGISTRO_CREADORES_VECTOR: List[List[Any]] = [
    ["CR01", "Sofía Castro", "Gastronomía", "Cúcuta", 8650, 6.84, 100.0, True],
    ["CR02", "Carlos Méndez", "Fitness", "Medellín", 24500, 4.90, 500.0, True],
]

_CATALOGO_CAMPANAS: List[Dict[str, Any]] = [
    crear_campana_dict("CMP01", "Auriculares X200", "Tecnología", 1200.0, 5000, "Activa"),
    crear_campana_dict("CMP02", "Moda Urbana Verano", "Moda", 850.0, 5000, "Activa"),
    crear_campana_dict("CMP03", "Gamer Energy Pro", "Gaming", 2400.0, 10000, "Borrador"),
]


def buscar_indice_por_codigo(
    codigo: str,
    creadores: Optional[Sequence[Sequence[Any]]] = None,
) -> int:
    """Wrapper compatible con Guía 05: acepta `buscar_indice_por_codigo(codigo)`."""
    objetivo = _REGISTRO_CREADORES_VECTOR if creadores is None else creadores
    return _buscar_indice_puro(codigo, objetivo)


def registrar_matriz_rendimiento(
    input_fn: Callable[[str], str] = input,
    campanas: Sequence[str] = CAMPANAS_MATRIZ_DEFAULT,
    dias: Sequence[str] = DIAS_MATRIZ_DEFAULT,
) -> List[List[float]]:
    """
    Guía 09: Captura validada de montos float para la matriz 3x3:
    3 campañas ('Auriculares X200', 'Moda Urbana Verano', 'Gamer Energy Pro')
    x 3 jornadas ('Lunes', 'Miércoles', 'Viernes').
    """
    matriz: List[List[float]] = []
    for campana in campanas:
        fila: List[float] = []
        for dia in dias:
            while True:
                raw = input_fn(f"Ingrese monto USD para '{campana}' el día {dia}: ")
                try:
                    monto = float(raw)
                    if monto < 0:
                        print("Error: el monto debe ser >= 0.")
                        continue
                    fila.append(round(monto, 2))
                    break
                except ValueError:
                    print("Error: ingrese un valor numérico válido.")
        matriz.append(fila)
    return matriz


def mostrar_ficha_campana(campana: Dict[str, Any]) -> None:
    """Guía 10: Procedimiento de interfaz para imprimir la ficha de una campaña."""
    comision = calcular_comision_nexora(float(campana["presupuesto"]))
    total = calcular_costo_total_campana(float(campana["presupuesto"]), comision)
    print(
        f"[{campana['codigo']}] {campana['titulo']} | Nicho: {campana['nicho']} | "
        f"Estado: {campana['estado']} | Presupuesto: ${campana['presupuesto']:.2f} USD | "
        f"Comisión 10%: ${comision:.2f} USD | Total: ${total:.2f} USD"
    )


def mostrar_catalogo_completo(campanas: Sequence[Dict[str, Any]]) -> None:
    """Guía 10: Muestra todas las campañas del catálogo y su analítica."""
    print("\n--- CATÁLOGO DE CAMPAÑAS NEXORA ---")
    if not campanas:
        print("No hay campañas registradas.")
        return
    for campana in campanas:
        mostrar_ficha_campana(campana)
    metricas = metricas_financieras_nexora(campanas)
    print(
        f"Analítica -> Total: {metricas['total_campanas']} | "
        f"Max: ${metricas['presupuesto_maximo']:.2f} | "
        f"Min: ${metricas['presupuesto_minimo']:.2f} | "
        f"Promedio: ${metricas['presupuesto_promedio']:.2f}"
    )


def registrar_campana(
    campanas: List[Dict[str, Any]],
    input_fn: Callable[[str], str] = input,
) -> List[Dict[str, Any]]:
    """Guía 10: Procedimiento de entrada de datos para registrar nueva campaña."""
    codigo = input_fn("Código de campaña (ej. CMP04): ")
    titulo = input_fn("Título de campaña: ")
    nicho = input_fn("Nicho: ")
    presupuesto = float(input_fn("Presupuesto (USD >= 100): "))
    min_seg = int(input_fn("Seguidores mínimos (>= 5000): "))
    estado = input_fn(f"Estado {ESTADOS_VALIDOS}: ")
    nueva = crear_campana_dict(codigo, titulo, nicho, presupuesto, min_seg, estado)
    actualizadas = agregar_campana(campanas, nueva)
    print(f"Campaña '{nueva['codigo']}' registrada con estado '{nueva['estado']}'.")
    return actualizadas


def ordenar_campanas_por_presupuesto(
    campanas: Sequence[Dict[str, Any]],
    ascendente: bool = True,
) -> List[Dict[str, Any]]:
    """Guía 08/10: Ordena por presupuesto usando `ordenar_campanas` sin mutar el catálogo."""
    ordenadas = ordenar_campanas(campanas, ascendente=ascendente)
    sentido = "ascendente" if ascendente else "descendente"
    print(f"\n--- CAMPAÑAS ORDENADAS ({sentido}) ---")
    for campana in ordenadas:
        mostrar_ficha_campana(campana)
    return ordenadas


def mostrar_menu() -> None:
    """Guía 06/10: Muestra el menú principal de consola."""
    print("\n=== NEXORA · SISTEMA MODULAR DE GESTIÓN (GUÍAS 01–10) ===")
    print(f"Módulos: {', '.join(MODULOS)}")
    print(f"Plataformas: {', '.join(PLATAFORMAS)}")
    print("1. Mostrar catálogo completo y métricas")
    print("2. Registrar nueva campaña")
    print("3. Ordenar campañas por presupuesto (ascendente/descendente)")
    print("4. Buscar campaña por código y filtrar por nicho")
    print("5. Registrar y analizar matriz 3x3 de rendimiento")
    print("6. Simular tarifa, engagement y descuento por volumen (>= 5 piezas)")
    print("7. Ejecutar matchmaking con filtro de infracciones")
    print("0. Salir")


def iniciar_programa(input_fn: Callable[[str], str] = input) -> None:
    """Guía 06/10: Ciclo `while` sostenido con salida segura en '0' y `break`."""
    campanas = [dict(c) for c in _CATALOGO_CAMPANAS]
    creadores_dict = [
        {
            "codigo": c[0],
            "nombre": c[1],
            "nicho": c[2],
            "ciudad": c[3],
            "seguidores": c[4],
            "engagement": c[5],
            "tarifa": c[6],
            "disponible": c[7],
            "infracciones": False,
        }
        for c in _REGISTRO_CREADORES_VECTOR
    ]

    while True:
        mostrar_menu()
        opcion = input_fn("Seleccione una opción: ").strip()

        if opcion == "0":
            print("Saliendo del sistema NEXORA...")
            break
        elif opcion == "1":
            mostrar_catalogo_completo(campanas)
        elif opcion == "2":
            try:
                campanas = registrar_campana(campanas, input_fn=input_fn)
            except ValueError as exc:
                print(f"Error de validación: {exc}")
        elif opcion == "3":
            sentido = input_fn("¿Orden ascendente? (s/n): ").strip().lower()
            ordenar_campanas_por_presupuesto(campanas, ascendente=(sentido != "n"))
        elif opcion == "4":
            cod = input_fn("Código a buscar: ")
            encontrada = buscar_campana_por_codigo(campanas, cod)
            if encontrada:
                mostrar_ficha_campana(encontrada)
            else:
                print("Campaña no encontrada.")
            nicho = input_fn("Nicho a filtrar: ")
            filtradas = filtrar_campanas_por_nicho(campanas, nicho)
            print(f"Coincidencias en nicho '{nicho}': {len(filtradas)}")
        elif opcion == "5":
            matriz = registrar_matriz_rendimiento(input_fn=input_fn)
            res = analizar_matriz_rendimiento(matriz)
            print("Resumen Matriz 3x3:", res)
        elif opcion == "6":
            seg = int(input_fn("Seguidores del creador: "))
            inter = int(input_fn("Interacciones: "))
            piezas = int(input_fn("Cantidad de piezas: "))
            clasif = clasificar_creador_y_tarifa(seg)
            er = calcular_engagement_rate(seg, inter)
            tarifa = clasif["tarifa_usd"] or 1000.0
            cot = calcular_valor_colaboracion(tarifa, True, piezas)
            print(f"Nivel: {clasif['nivel']} | ER: {er}% | Total: ${cot['total']} USD")
        elif opcion == "7":
            res_mm = emparejar_campanas_y_creadores(campanas, creadores_dict)
            print("Emparejamientos:", res_mm)
        else:
            print("Opción inválida. Intente nuevamente.")


if __name__ == "__main__":
    iniciar_programa()

