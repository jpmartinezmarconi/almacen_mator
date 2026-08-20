import base64
from pathlib import Path

import streamlit as st


LOGO_PATH = Path(__file__).resolve().parents[1] / "assets" / "logo.png"
LOGO_DATA = base64.b64encode(LOGO_PATH.read_bytes()).decode("ascii")


def mostrar_logo():
    imagen = f"<img src='data:image/png;base64,{LOGO_DATA}' width='220' alt='Logo Mator'>"
    imagen_lateral = f"<img src='data:image/png;base64,{LOGO_DATA}' width='180' alt='Logo Mator'>"
    st.markdown(imagen, unsafe_allow_html=True)
    st.sidebar.markdown(imagen_lateral, unsafe_allow_html=True)