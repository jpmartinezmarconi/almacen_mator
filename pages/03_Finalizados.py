import os

import streamlit as st
from utils.db import get_conn
from utils.csv_storage import guardar_albaran_finalizado

st.title("Albaranes Finalizados")

conn = get_conn()
cur = conn.cursor()

empresa_filtro = st.text_input("Filtrar por empresa")
nombre_filtro = st.text_input("Filtrar por nombre")
estado_filtro = st.selectbox("Estado", ["todos", "entrada", "procesando", "finalizado"])

query = "SELECT * FROM albaranes WHERE 1=1"
params = []

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
