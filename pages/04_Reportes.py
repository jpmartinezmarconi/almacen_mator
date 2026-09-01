import pandas as pd
import streamlit as st

from utils.branding import mostrar_logo
from utils.db import get_conn

mostrar_logo()
st.title("Reportes - Albaranes finalizados")

conn = get_conn()
cur = conn.cursor()

estado_filtro = st.selectbox(
    "Filtrar por estado",
    ["todos", "entrada", "procesando", "finalizado"],
    index=3,
)

query = "SELECT id, nombre, empresa, solicitado_por, materiales, comentario, envio_recogida, estado, observaciones, mensaje_final, fecha FROM albaranes"
params = []

if estado_filtro != "todos":
    query += " WHERE estado = ?"
    params.append(estado_filtro)

query += " ORDER BY fecha DESC, id DESC"

cur.execute(query, params)
registros = cur.fetchall()

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

if not registros:
    st.info("Todavía no hay albaranes guardados en la base de datos.")
    st.stop()

df = pd.DataFrame(registros, columns=columnas)

st.caption(f"Total de albaranes visibles: {len(df)}")
st.dataframe(df, use_container_width=True, hide_index=True)


def csv_bytes(dataframe: pd.DataFrame) -> bytes:
    return dataframe.to_csv(index=False, encoding="utf-8").encode("utf-8")


st.download_button(
    label="Descargar CSV de todos los albaranes visibles",
    data=csv_bytes(df),
    file_name="albaranes_todos.csv",
    mime="text/csv",
    key="descargar_todos_reportes_csv",
)

ids_disponibles = df["ID"].tolist()
ids_seleccionados = st.multiselect(
    "Selecciona los albaranes que quieres descargar:",
    options=ids_disponibles,
    format_func=lambda value: (
        f"#{value} - {df.loc[df['ID'] == value, 'Nombre'].iat[0]} "
        f"({df.loc[df['ID'] == value, 'Empresa'].iat[0]})"
    ),
    key="seleccion_albaranes_reporte",
)

if ids_seleccionados:
    df_seleccionado = df[df["ID"].isin(ids_seleccionados)].copy()
    st.download_button(
        label=f"Descargar CSV de {len(df_seleccionado)} albaranes seleccionados",
        data=csv_bytes(df_seleccionado),
        file_name="albaranes_seleccionados.csv",
        mime="text/csv",
        key="descargar_seleccion_reportes_csv",
    )
else:
    st.info("Selecciona uno o varios albaranes para descargar sólo los que quieras.")
