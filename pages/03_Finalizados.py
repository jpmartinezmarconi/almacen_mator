import os
from datetime import date, datetime
from io import BytesIO

import pandas as pd
import streamlit as st
from utils.db import get_conn
from utils.csv_storage import guardar_albaran_finalizado

st.title("Albaranes Finalizados")

conn = get_conn()
cur = conn.cursor()

empresa_filtro = st.text_input("Filtrar por empresa")
nombre_filtro = st.text_input("Filtrar por nombre")
estado_filtro = st.selectbox("Estado", ["todos", "entrada", "procesando", "finalizado"])
buscar_historial = bool(empresa_filtro.strip() or nombre_filtro.strip())

query = "SELECT * FROM albaranes WHERE 1=1"
params = []

if not buscar_historial:
    query += " AND fecha = ?"
    params.append(date.today().isoformat())

if empresa_filtro:
    query += " AND empresa LIKE ?"
    params.append(f"%{empresa_filtro}%")

if nombre_filtro:
    query += " AND nombre LIKE ?"
    params.append(f"%{nombre_filtro}%")

if estado_filtro != "todos":
    query += " AND estado = ?"
    params.append(estado_filtro)

cur.execute(query, params)
resultados = cur.fetchall()

if buscar_historial:
    st.caption("Buscando en todo el historial de albaranes.")
else:
    st.caption("Mostrando los albaranes de hoy. Usa empresa o nombre para buscar anteriores.")

for albaran in resultados:
    id_, nombre, empresa, solicitado_por, materiales, comentario, envio_recogida, estado, obs, msg_final, fecha = albaran

    with st.expander(f"#{id_} - {nombre} ({empresa}) [{estado}]"):
        st.write(f"Fecha: {fecha}")
        st.write(f"Materiales:\n{materiales}")
        st.write(f"Comentario: {comentario}")
        st.write(f"Entrega: {envio_recogida}")
        st.write(f"Observaciones: {obs}")
        st.write(f"Mensaje final: {msg_final}")

        ruta_excel = f"data/albaran_{id_}.xlsx"
        if os.path.isfile(ruta_excel):
            with open(ruta_excel, "rb") as archivo_excel:
                st.download_button(
                    label="Descargar Excel",
                    data=archivo_excel.read(),
                    file_name=f"albaran_{id_}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=f"descargar_excel_{id_}",
                )
        else:
            st.caption("No hay un archivo Excel disponible para este albarán.")

        if st.button(f"Finalizar definitivamente #{id_}"):
            cur.execute("UPDATE albaranes SET estado='finalizado' WHERE id=?", (id_,))
            conn.commit()

            for linea in materiales.split("\n"):
                linea = linea.strip()
                if not linea:
                    continue

                material_nombre = linea
                unidades = ""

                if " - " in linea:
                    material_nombre, unidades_texto = linea.rsplit(" - ", 1)
                    unidades = unidades_texto.replace("unidades", "").strip()

                guardar_albaran_finalizado(
                    fecha=fecha,
                    nombre=nombre,
                    empresa=empresa,
                    solicitado_por=solicitado_por,
                    material=material_nombre,
                    unidades=unidades,
                )

            st.success("Albarán marcado como finalizado")

st.header("Descargar albaranes por fecha")

cur.execute("SELECT * FROM albaranes WHERE estado = 'finalizado' ORDER BY fecha DESC")
albaranes_finalizados = cur.fetchall()

def convertir_a_excel(albaranes):
    columnas = [
        "ID",
        "Nombre",
        "Empresa",
        "Solicitado Por",
        "Materiales",
        "Comentario",
        "Entrega",
        "Estado",
        "Observaciones",
        "Mensaje final",
        "Fecha",
    ]
    datos_excel = [dict(zip(columnas, albaran)) for albaran in albaranes]
    archivo_excel = BytesIO()
    pd.DataFrame(datos_excel).to_excel(archivo_excel, index=False)
    return archivo_excel.getvalue()


if not albaranes_finalizados:
    st.info("No hay albaranes finalizados para descargar.")
else:
    fechas_albaranes = [
        datetime.strptime(albaran[10], "%Y-%m-%d").date()
        for albaran in albaranes_finalizados
    ]
    fecha_inicio, fecha_fin = st.date_input(
        "Selecciona el rango de fechas",
        value=(min(fechas_albaranes), max(fechas_albaranes)),
        min_value=min(fechas_albaranes),
        max_value=max(fechas_albaranes),
        key="rango_descarga_albaranes",
    )

    albaranes_periodo = [
        albaran
        for albaran in albaranes_finalizados
        if fecha_inicio <= datetime.strptime(albaran[10], "%Y-%m-%d").date() <= fecha_fin
    ]

    st.download_button(
        label="Descargar todos los albaranes",
        data=convertir_a_excel(albaranes_finalizados),
        file_name="albaranes_finalizados.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="descargar_todos_albaranes",
    )

    st.download_button(
        label=f"Descargar albaranes del {fecha_inicio} al {fecha_fin}",
        data=convertir_a_excel(albaranes_periodo),
        file_name=f"albaranes_{fecha_inicio}_{fecha_fin}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        disabled=not albaranes_periodo,
        key="descargar_albaranes_periodo",
    )

    st.caption(f"Albaranes encontrados en el periodo: {len(albaranes_periodo)}")

# ---------------------------------------------------------
# DESCARGA DE ARCHIVOS XLSX ORDENADOS POR FECHA
# ---------------------------------------------------------

st.header("Descargar albaranes finalizados")

data_path = "/app/data" if os.path.isdir("/app/data") else "data"

files = []
for file_name in os.listdir(data_path):
    if file_name.endswith(".xlsx"):
        full_path = os.path.join(data_path, file_name)
        mod_time = os.path.getmtime(full_path)
        files.append((file_name, full_path, mod_time))

files.sort(key=lambda item: item[2], reverse=True)

if not files:
    st.write("No hay albaranes finalizados para descargar.")
else:
    for file_name, file_path, mod_time in files:
        fecha_legible = datetime.fromtimestamp(mod_time).strftime("%Y-%m-%d %H:%M")

        with open(file_path, "rb") as archivo_excel:
            st.download_button(
                label=f"Descargar {file_name} ({fecha_legible})",
                data=archivo_excel.read(),
                file_name=file_name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key=f"descargar_archivo_{file_name}",
            )

        st.markdown("---")





