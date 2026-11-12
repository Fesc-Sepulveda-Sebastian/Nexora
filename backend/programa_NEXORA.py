"""
Punto de entrada de la Guía 05 (`programa_NEXORA.py`).
Expone las funciones requeridas de prototipo y delega en `app.guias_cli`.
"""

from app.domain.nexora_rules import (
    calcular_valor_colaboracion,
    registrar_creador,
)
from app.guias_cli import (
    buscar_indice_por_codigo,
    iniciar_programa,
    mostrar_catalogo_completo,
    mostrar_ficha_campana,
    mostrar_menu,
    ordenar_campanas_por_presupuesto,
    registrar_campana,
    registrar_matriz_rendimiento,
)

__all__ = [
    "buscar_indice_por_codigo",
    "registrar_creador",
    "calcular_valor_colaboracion",
    "registrar_matriz_rendimiento",
    "mostrar_ficha_campana",
    "mostrar_catalogo_completo",
    "registrar_campana",
    "ordenar_campanas_por_presupuesto",
    "mostrar_menu",
    "iniciar_programa",
]

if __name__ == "__main__":
    iniciar_programa()

