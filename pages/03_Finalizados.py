import os
from datetime import datetime

import streamlit as st
from utils.branding import mostrar_logo
from utils.db import get_conn
from utils.csv_storage import guardar_albaran_finalizado

mostrar_logo()
st.title("Albaranes Finalizados")

conn = get_conn()
cur = conn.cursor()

empresa_filtro = st.text_input("Filtrar por empresa")
nombre_filtro = st.text_input("Filtrar por nombre")
estado_filtro = st.selectbox("Estado", ["todos", "entrada", "procesando", "finalizado"])
buscar_historial = bool(empresa_filtro.strip() or nombre_filtro.strip())

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

st.caption("Mostrando todos los albaranes guardados. Puedes filtrar por empresa, nombre o estado.")

for albaran in resultados:
    id_, nombre, empresa, solicitado_por, materiales, comentario, envio_recogida, estado, obs, _msg_final, fecha, foto_preparacion, numero_serie = albaran

    with st.expander(f"#{id_} - {nombre} ({empresa}) [{estado}]"):
        st.write(f"Fecha: {fecha}")
        st.write(f"Número de serie / código Zebra: {numero_serie or 'No leído'}")
        st.write(f"Materiales:\n{materiales}")
        st.write(f"Comentario: {comentario}")
        st.write(f"Entrega: {envio_recogida}")
        st.write(f"Observaciones: {obs}")

        if foto_preparacion:
            ruta_foto = os.path.join(os.path.dirname(os.path.dirname(__file__)), foto_preparacion)
            if os.path.isfile(ruta_foto):
                st.subheader("Foto de la preparación")
                st.image(ruta_foto, caption="Preparación del material", width=400)
                with open(ruta_foto, "rb") as archivo_foto:
                    st.download_button(
                        "Descargar foto de la preparación",
                        data=archivo_foto.read(),
                        file_name=os.path.basename(ruta_foto),
                        mime="image/jpeg",
                        key=f"descargar_foto_preparacion_{id_}",
                    )

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
            if estado != "procesando":
                st.error("Este albarán debe pasar primero por Procesando.")
                continue

            cur.execute(
                "UPDATE albaranes SET estado='finalizado' WHERE id=? AND estado='procesando'",
                (id_,),
            )
            if cur.rowcount != 1:
                st.error("El albarán ya no está disponible para finalizarse.")
                continue
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
# DESCARGA DE ARCHIVOS XLSX ORDENADOS POR FECHA
# ---------------------------------------------------------

st.header("Descargar albaranes finalizados")

cur.execute(
    "SELECT * FROM albaranes WHERE estado = 'finalizado' ORDER BY fecha DESC"
)
albaranes_finalizados = cur.fetchall()

data_path = "/app/data" if os.path.isdir("/app/data") else "data"
albaranes_hoy = {f"albaran_{albaran[0]}.xlsx" for albaran in albaranes_finalizados}

files = []
for file_name in os.listdir(data_path):
    if file_name in albaranes_hoy:
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





