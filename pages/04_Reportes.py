import os
import streamlit as st
import pandas as pd

from utils.branding import mostrar_logo
from utils.csv_storage import CSV_PATH

mostrar_logo()
st.title("Reportes - Albaranes Finalizados")

if not os.path.isfile(CSV_PATH):
    st.info("Todavía no hay albaranes finalizados guardados.")
else:
    df = pd.read_csv(CSV_PATH)

    st.dataframe(df)

    csv_bytes = df.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="Descargar CSV",
        data=csv_bytes,
        file_name="albarans_finalizados.csv",
        mime="text/csv",
    )
