import math

import pandas as pd


ESPACIO_PALET_OPTIONS = (1.0, 0.2)


def limpiar_espacio_palets(valor):
    if valor is None:
        return 1.0

    texto = str(valor).strip().lower().replace(",", ".")
    if not texto:
        return 1.0
    if texto in ("1/5", "1/5 de palet"):
        return 0.2
    if texto in ("palet completo", "completo", "1 palet"):
        return 1.0

    try:
        espacio = float(texto)
    except ValueError as error:
        raise ValueError(
            f"Espacio de palet no válido: {valor!r}. Usa 1 o 1/5."
        ) from error

    if math.isnan(espacio):
        return 1.0
    if any(abs(espacio - opcion) < 0.000001 for opcion in ESPACIO_PALET_OPTIONS):
        return round(espacio, 1)
    raise ValueError(f"Espacio de palet no válido: {valor!r}. Usa 1 o 1/5.")


def mostrar_espacio_palets(valor):
    return "1/5 de palet" if abs(float(valor) - 0.2) < 0.000001 else "Palet completo"


def resumir_ocupacion_por_seccion(equipos):
    datos = equipos.copy()
    datos["Espacio ocupado (palets)"] = (
        datos["cantidad"] * datos["espacio_palets"]
    )
    resumen = (
        datos.groupby(["seccion", "nombre"], as_index=False)["Espacio ocupado (palets)"]
        .sum()
        .rename(columns={"seccion": "Sección", "nombre": "Material"})
    )
    resumen["Espacio ocupado (palets)"] = resumen["Espacio ocupado (palets)"].round(4)
    return resumen
