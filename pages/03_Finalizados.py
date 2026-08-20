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
# ---------------------------------------------------------
# 📥 DESCARGA DE ARCHIVOS XLSX ORDENADOS POR FECHA (FECHA EN EL BOTÓN)
# ---------------------------------------------------------

st.header("Descargar albaranes finalizados")

data_path = "/app/data"

files = []
for f in os.listdir(data_path):
    if f.endswith(".xlsx"):
        full_path = os.path.join(data_path, f)
        mod_time = os.path.getmtime(full_path)
        files.append((f, full_path, mod_time))

# Ordenar por fecha (más reciente primero)
files.sort(key=lambda x: x[2], reverse=True)

from datetime import datetime

if not files:
    st.write("No hay albaranes finalizados para descargar.")
else:
    for file_name, file_path, mod_time in files:

        # Convertir fecha a formato legible
        fecha_legible = datetime.fromtimestamp(mod_time).strftime("%Y-%m-%d %H:%M")

        # Botón con fecha incluida
        with open(file_path, "rb") as f:
            st.download_button(
                label=f"Descargar {file_name} ({fecha_legible})",
                data=f,
                file_name=file_name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        st.markdown("---")
