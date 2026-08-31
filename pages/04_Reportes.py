import pandas as pd
import streamlit as st

from utils.branding import mostrar_logo
from utils.db import get_conn

mostrar_logo()
st.title("Reportes - Albaranes Finalizados")

conn = get_conn()
cur = conn.cursor()

cur.execute(
    "SELECT id, nombre, empresa, solicitado_por, materiales, comentario, envio_recogida, estado, observaciones, mensaje_final, fecha FROM albaranes WHERE estado = 'finalizado' ORDER BY fecha DESC, id DESC"
)
finalizados = cur.fetchall()

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

if not finalizados:
    st.info("Todavía no hay albaranes finalizados guardados desde que se creó la página.")
    st.stop()

df = pd.DataFrame(finalizados, columns=columnas)

st.caption(f"Total de albaranes finalizados: {len(df)}")
st.dataframe(df, use_container_width=True, hide_index=True)


def csv_bytes(dataframe: pd.DataFrame) -> bytes:
    return dataframe.to_csv(index=False, encoding="utf-8").encode("utf-8")


st.download_button(
    label="Descargar CSV de todos los albaranes",
    data=csv_bytes(df),
    file_name="albaranes_finalizados_todos.csv",
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
        file_name="albaranes_finalizados_seleccionados.csv",
        mime="text/csv",
        key="descargar_seleccion_reportes_csv",
    )
else:
    st.info("Selecciona uno o varios albaranes para descargar sólo los que quieras.")
