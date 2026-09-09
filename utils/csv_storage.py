import csv
import os

from utils.db import get_conn

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(BASE_DIR, "data", "albarans_finalizados.csv")
CSV_HEADERS = ["Albaran ID", "Fecha", "Nombre", "Empresa", "Solicitado Por", "Material", "Unidades"]


def guardar_albaran_finalizado(
    albaran_id, fecha, nombre, empresa, solicitado_por, material, unidades
):
    conn = get_conn()
    try:
        conn.execute(
            """INSERT INTO albaranes_finalizados
            (albaran_id, fecha, nombre, empresa, solicitado_por, material, unidades)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (albaran_id, material, unidades) DO NOTHING""",
            (albaran_id, fecha, nombre, empresa, solicitado_por, material, unidades),
        )
        conn.commit()
    finally:
        conn.close()

    if not os.getenv("DATABASE_URL"):
        os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
        file_exists = os.path.isfile(CSV_PATH)
        with open(CSV_PATH, mode="a", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            if not file_exists:
                writer.writerow(CSV_HEADERS)
            writer.writerow([albaran_id, fecha, nombre, empresa, solicitado_por, material, unidades])
