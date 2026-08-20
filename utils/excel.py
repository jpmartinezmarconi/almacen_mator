import pandas as pd

def generar_excel(datos, id_albaran):
    df = pd.DataFrame([datos])
    ruta = f"data/albaran_{id_albaran}.xlsx"
    df.to_excel(ruta, index=False)
    return ruta
