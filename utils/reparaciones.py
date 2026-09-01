import os
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPAIRS_DIR = os.path.join(BASE_DIR, "data", "reparaciones")

REPAIR_COLUMNS = [
    "ID", "Fecha de entrada", "Empresa", "Reparacion", "Piezas pendientes",
    "Presupuesto", "Archivo presupuesto", "Estado presupuesto", "Estado", "Fotos", "Fecha finalizacion",
]


def save_upload(uploaded_file, repair_id, folder_name):
    if uploaded_file is None:
        return ""
    folder = os.path.join(REPAIRS_DIR, str(repair_id), folder_name)
    os.makedirs(folder, exist_ok=True)
    safe_name = os.path.basename(uploaded_file.name).replace(" ", "_")
    path = os.path.join(folder, safe_name)
    with open(path, "wb") as output:
        output.write(uploaded_file.getbuffer())
    return os.path.relpath(path, BASE_DIR).replace(os.sep, "/")


def repair_dataframe(records):
    return pd.DataFrame(records, columns=REPAIR_COLUMNS)


def repair_excel(records):
    output = BytesIO()
    repair_dataframe(records).to_excel(output, index=False)
    return output.getvalue()


def repair_zip(records):
    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        archive.writestr("reparaciones.xlsx", repair_excel(records))
        for record in records:
            repair_id = record[0]
            for folder_name in ("presupuesto", "fotos"):
                folder = os.path.join(REPAIRS_DIR, str(repair_id), folder_name)
                if not os.path.isdir(folder):
                    continue
                for file_name in os.listdir(folder):
                    path = os.path.join(folder, file_name)
                    if os.path.isfile(path):
                        archive.write(path, f"reparacion_{repair_id}/{folder_name}/{file_name}")
    return output.getvalue()
