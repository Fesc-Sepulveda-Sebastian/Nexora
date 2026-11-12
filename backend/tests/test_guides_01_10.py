import pytest

from app.domain.nexora_rules import (
    CAMPANAS_MATRIZ_DEFAULT,
    DIAS_MATRIZ_DEFAULT,
    ESTADOS_VALIDOS,
    MODULOS,
    PLATAFORMAS,
    analizar_matriz_rendimiento,
    buscar_campana_por_codigo,
    buscar_indice_por_codigo as buscar_indice_puro,
    calcular_comision_nexora,
    calcular_costeo_pauta,
    calcular_costo_total_campana,
    calcular_engagement_rate,
    calcular_valor_colaboracion,
    clasificar_creador_y_tarifa,
    crear_campana_dict,
    emparejar_campanas_y_creadores,
    es_elegible_premium_sin_costo,
    evaluar_viabilidad_financiera,
    filtrar_campanas_por_nicho,
    filtrar_creadores_sin_infracciones,
    metricas_financieras_nexora,
    normalizar_estado_campana,
    ordenar_campanas,
    puede_ver_metricas,
    registrar_creador,
    validar_contratacion,
    validar_engagement_estricto,
    validar_liberacion_escrow,
    validar_postulacion,
    validar_presupuesto_minimo,
    validar_umbral_seguidores,
)
from app.guias_cli import (
    buscar_indice_por_codigo,
    iniciar_programa,
    registrar_matriz_rendimiento,
)


def test_guias_02_03_clasificacion_tarifas_y_validaciones():
    nano = clasificar_creador_y_tarifa(8500)
    assert nano["nivel"] == "Nano" and nano["tarifa_usd"] == 100.0

    micro = clasificar_creador_y_tarifa(25000)
    assert micro["nivel"] == "Micro" and micro["tarifa_usd"] == 500.0

    medio = clasificar_creador_y_tarifa(250000)
    assert medio["nivel"] == "Medio" and medio["cotizacion_personalizada"] is True

    macro = clasificar_creador_y_tarifa(1_500_000)
    assert macro["nivel"] == "Macro" and macro["tarifa_usd"] == 2000.0
    assert macro["elegible_nexora_premium"] is True

    assert validar_umbral_seguidores(5000) is True
    assert validar_umbral_seguidores(4999) is False
    assert validar_presupuesto_minimo(100.0) is True
    assert validar_presupuesto_minimo(99.99) is False
    assert validar_engagement_estricto(0.0) is True
    assert validar_engagement_estricto(100.0) is True
    assert validar_engagement_estricto(100.1) is False
    assert validar_engagement_estricto(-0.1) is False

    viable = evaluar_viabilidad_financiera(tarifa=500.0, publicaciones=2, presupuesto=1200.0)
    assert viable == {"costo_total": 1000.0, "diferencia": 200.0, "aprobado": True}
    inviable = evaluar_viabilidad_financiera(tarifa=500.0, publicaciones=3, presupuesto=1200.0)
    assert inviable["aprobado"] is False

    contrato_ok = validar_contratacion(True, False, True)
    assert contrato_ok["aprobado"] is True and contrato_ok["plazo_dias"] == 15
    assert validar_contratacion(False, False, True)["aprobado"] is False
    assert validar_contratacion(True, True, True)["aprobado"] is False

    assert validar_postulacion(True, True) is True
    assert validar_postulacion(False, True) is False
    assert validar_liberacion_escrow(True, True) is True
    assert validar_liberacion_escrow(True, False) is False

    assert puede_ver_metricas(True, False) is True
    assert puede_ver_metricas(False, True) is True
    assert puede_ver_metricas(False, False) is False

    assert es_elegible_premium_sin_costo(True, False) is True
    assert es_elegible_premium_sin_costo(False, True) is True
    assert es_elegible_premium_sin_costo(False, False) is False


def test_guias_04_05_costeo_catalogos_rf1_rf2_rf3():
    assert MODULOS == ("Inicio", "Usuarios", "Gestión de campañas", "Analítica y reportes", "Configuración")
    assert PLATAFORMAS == ("Instagram", "TikTok", "YouTube", "Facebook", "Twitch")
    assert calcular_costeo_pauta(dias=10, costo_diario=25.0, costo_diseno=150.0) == 400.0

    # RF1 & RF2 pure inmutability + .strip().upper()
    lista_inicial = []
    lista_1 = registrar_creador(
        lista_inicial,
        "  cr10 ",
        "Laura Tech",
        "Tecnología",
        "Bogotá",
        15000,
        5.5,
        500.0,
        True,
    )
    assert lista_inicial == []  # original list not mutated
    assert lista_1[0][0] == "CR10"
    assert buscar_indice_puro("cr10", lista_1) == 0
    assert buscar_indice_puro("NOEXISTE", lista_1) == -1
    assert buscar_indice_por_codigo("cr01") == 0

    with pytest.raises(ValueError):
        registrar_creador(lista_1, "CR10", "Dup", "Moda", "Cali", 5000, 3.0, 100.0, True)

    # RF3: 10% discount when piezas >= 5
    sin_desc = calcular_valor_colaboracion(tarifa=100.0, disponible=True, piezas=4)
    assert sin_desc["descuento_porcentaje"] == 0 and sin_desc["total"] == 400.0

    con_desc = calcular_valor_colaboracion(tarifa=100.0, disponible=True, piezas=5)
    assert con_desc["descuento_porcentaje"] == 10
    assert con_desc["descuento_monto"] == 50.0
    assert con_desc["total"] == 450.0


def test_guia_06_infracciones_continue_y_emparejamiento():
    creadores = [
        {"codigo": "C1", "nombre": "Ana", "nicho": "Tecnología", "seguidores": 12000, "disponible": True, "infracciones": True},
        {"codigo": "C2", "nombre": "Luis", "nicho": "Tecnología", "seguidores": 8000, "disponible": True, "infracciones": False},
        {"codigo": "C3", "nombre": "Eva", "nicho": "Tecnología", "seguidores": 3000, "disponible": True, "infracciones": False},
    ]
    habilitados, alertas = filtrar_creadores_sin_infracciones(creadores)
    assert len(habilitados) == 2
    assert len(alertas) == 1 and "Ana" in alertas[0]

    campanas = [
        crear_campana_dict("CMP1", "Tech Launch", "Tecnología", 1000.0, 5000, "Activa"),
        crear_campana_dict("CMP2", "Borrador Tech", "Tecnología", 1000.0, 5000, "Borrador"),
    ]
    res = emparejar_campanas_y_creadores(campanas, creadores)
    assert len(res["emparejamientos"]) == 1
    assert res["emparejamientos"][0]["creador_codigo"] == "C2"


def test_guias_07_08_estados_ordenamiento_lambda_y_metricas():
    assert ESTADOS_VALIDOS == ("Borrador", "Activa", "Pausada", "Finalizada")
    assert normalizar_estado_campana("activa") == "Activa"
    assert normalizar_estado_campana("EstadoInventado") == "Borrador"

    c1 = crear_campana_dict("C1", "Camp 1", "Moda", 800.0, 5000, "Activa")
    c2 = crear_campana_dict("C2", "Camp 2", "Tech", 2000.0, 10000, "Activa")
    c3 = crear_campana_dict("C3", "Camp 3", "Moda", 400.0, 5000, "Pausada")
    original = [c1, c2, c3]

    asc = ordenar_campanas(original, ascendente=True)
    desc = ordenar_campanas(original, ascendente=False)
    assert [c["codigo"] for c in original] == ["C1", "C2", "C3"]  # original untouched
    assert [c["codigo"] for c in asc] == ["C3", "C1", "C2"]
    assert [c["codigo"] for c in desc] == ["C2", "C1", "C3"]

    assert buscar_campana_por_codigo(original, "c2")["titulo"] == "Camp 2"
    assert len(filtrar_campanas_por_nicho(original, "moda")) == 2

    metricas = metricas_financieras_nexora(original)
    assert metricas["presupuesto_maximo"] == 2000.0
    assert metricas["presupuesto_minimo"] == 400.0
    assert metricas["presupuesto_total"] == 3200.0


def test_guia_09_matriz_3x3():
    entradas = iter(["100.5", "200.5", "300.0", "50", "50", "100", "400", "100", "200"])
    matriz = registrar_matriz_rendimiento(input_fn=lambda _: next(entradas))
    res = analizar_matriz_rendimiento(matriz, CAMPANAS_MATRIZ_DEFAULT, DIAS_MATRIZ_DEFAULT)

    assert res["suma_filas"]["Auriculares X200"] == 601.0
    assert res["suma_filas"]["Moda Urbana Verano"] == 200.0
    assert res["suma_filas"]["Gamer Energy Pro"] == 700.0
    assert res["suma_columnas"]["Lunes"] == 550.5
    assert res["total_general"] == 1501.0
    assert res["promedio_celda"] == round(1501.0 / 9.0, 2)


def test_guia_10_funciones_puras_y_cli():
    comision = calcular_comision_nexora(1500.0)
    assert comision == 150.0
    assert calcular_costo_total_campana(1500.0, comision) == 1650.0

    assert calcular_engagement_rate(0, 500) == 0.0
    assert calcular_engagement_rate(-10, 500) == 0.0
    assert calcular_engagement_rate(10_000, 650) == 6.5

    # Verify while-loop safe exit with '0'
    inputs = iter(["0"])
    iniciar_programa(input_fn=lambda _: next(inputs))

