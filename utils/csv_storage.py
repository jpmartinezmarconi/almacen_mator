import os
import csv

CSV_PATH = "/app/data/albarans_finalizados.csv"
CSV_HEADERS = ["Fecha", "Nombre", "Empresa", "Solicitado Por", "Material", "Unidades"]


def guardar_albaran_finalizado(fecha, nombre, empresa, solicitado_por, material, unidades):
    """
    Guarda una línea de un albarán finalizado en el CSV persistente.

    Si el fichero no existe, lo crea con las cabeceras correspondientes.
    Si ya existe, añade la nueva fila al final.
    """
    os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
    file_exists = os.path.isfile(CSV_PATH)

    with open(CSV_PATH, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(CSV_HEADERS)
        writer.writerow([fecha, nombre, empresa, solicitado_por, material, unidades])
