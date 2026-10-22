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
MARBLE_TEXTURE_PATH = (
    Path(__file__).resolve().parents[1] / "assets" / "textura_marmol.svg"
)
MARBLE_TEXTURE_DATA = base64.b64encode(
    MARBLE_TEXTURE_PATH.read_bytes()
).decode("ascii")


def mostrar_fondo_inicio():
    st.markdown(
        f"""
        <style>
        section.main:has(.mator-home-background) {{
            background-image:
                linear-gradient(rgba(255, 255, 255, 0.08), rgba(255, 255, 255, 0.08)),
                url("data:image/webp;base64,{HOME_BACKGROUND_DATA}");
            background-position: center;
            background-repeat: no-repeat;
            background-size: cover;
            background-attachment: fixed;
            background-color: #f8fafc;
        }}
        </style>
        <span class="mator-home-background" aria-hidden="true" style="display: none;"></span>
        """,
        unsafe_allow_html=True,
    )


def mostrar_logo():
    st.markdown(
        f"""
        <style>
        section[data-testid="stSidebar"] > div {{
            background-color: #f7f9fb;
            background-image:
                url("data:image/svg+xml;base64,{MARBLE_TEXTURE_DATA}"),
                radial-gradient(ellipse at 12% 16%, rgba(174, 202, 218, 0.43), transparent 42%),
                radial-gradient(ellipse at 86% 38%, rgba(186, 193, 201, 0.35), transparent 40%),
                radial-gradient(ellipse at 38% 82%, rgba(198, 220, 232, 0.40), transparent 46%),
                linear-gradient(145deg, #ffffff 0%, #f5f7f9 52%, #edf4f8 100%);
            background-position: center;
            background-size: cover;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
    imagen = f"<img src='data:image/png;base64,{LOGO_DATA}' width='220' alt='Logo Mator'>"
    imagen_lateral = f"<img src='data:image/png;base64,{LOGO_DATA}' width='180' alt='Logo Mator'>"
    st.markdown(imagen, unsafe_allow_html=True)
    st.sidebar.markdown(imagen_lateral, unsafe_allow_html=True)