import base64
from pathlib import Path

import streamlit as st


LOGO_PATH = Path(__file__).resolve().parents[1] / "assets" / "logo.png"
LOGO_DATA = base64.b64encode(LOGO_PATH.read_bytes()).decode("ascii")
HOME_BACKGROUND_PATH = (
    Path(__file__).resolve().parents[1] / "assets" / "fondo_maquinas.webp"
)
HOME_BACKGROUND_DATA = base64.b64encode(
    HOME_BACKGROUND_PATH.read_bytes()
).decode("ascii")


def mostrar_fondo_inicio():
    st.markdown(
        f"""
        <style>
        section[data-testid="stMain"]:has(.mator-home-background) {{
            background-image:
                linear-gradient(rgba(255, 255, 255, 0.12), rgba(255, 255, 255, 0.12)),
                url("data:image/webp;base64,{HOME_BACKGROUND_DATA}");
            background-position: center;
            background-repeat: no-repeat;
            background-size: cover;
            background-attachment: fixed;
        }}
        </style>
        <span class="mator-home-background" aria-hidden="true" style="display: none;"></span>
        """,
        unsafe_allow_html=True,
    )


def mostrar_logo():
    st.markdown(
        """
        <style>
        section[data-testid="stSidebar"] > div {
            background-color: #f7f9fb;
            background-image:
                radial-gradient(ellipse at 12% 16%, rgba(174, 202, 218, 0.36), transparent 42%),
                radial-gradient(ellipse at 86% 38%, rgba(186, 193, 201, 0.28), transparent 40%),
                radial-gradient(ellipse at 38% 82%, rgba(198, 220, 232, 0.32), transparent 46%),
                linear-gradient(145deg, #ffffff 0%, #f5f7f9 52%, #edf4f8 100%);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    imagen = f"<img src='data:image/png;base64,{LOGO_DATA}' width='220' alt='Logo Mator'>"
    imagen_lateral = f"<img src='data:image/png;base64,{LOGO_DATA}' width='180' alt='Logo Mator'>"
    st.markdown(imagen, unsafe_allow_html=True)
    st.sidebar.markdown(imagen_lateral, unsafe_allow_html=True)