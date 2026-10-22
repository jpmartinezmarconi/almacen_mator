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
MARBLE_TEXTURE_PATH = Path(__file__).resolve().parents[1] / "assets" / "textura_marmol.webp"
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
        section.main:has(.mator-home-background) h1 {{
            box-sizing: border-box;
            width: fit-content;
            max-width: 100%;
            margin: 0 auto 0.8rem;
            padding: 0.3rem 0.75rem;
            font-size: clamp(1.5rem, 3vw, 2.35rem);
            line-height: 1.15;
            color: #111111 !important;
            background: rgba(255, 255, 255, 0.78);
            border: 1px solid rgba(137, 153, 165, 0.45);
            border-radius: 9px;
        }}
        section.main:has(.mator-home-background) [data-testid="element-container"]:has(.mator-home-background),
        section.main:has(.mator-home-menu) [data-testid="element-container"]:has(.mator-home-menu) {{
            display: none !important;
        }}
        section.main:has(.mator-home-menu) [data-testid="stVerticalBlockBorderWrapper"]:has(.mator-home-menu) {{
            box-sizing: border-box;
            width: fit-content;
            max-width: 100%;
            margin: 0 auto;
            padding: 0.35rem 0.7rem;
            background: rgba(255, 255, 255, 0.76);
            border: 1px solid rgba(137, 153, 165, 0.5);
            border-radius: 10px;
            box-shadow: 0 2px 9px rgba(35, 52, 66, 0.08);
        }}
        section.main:has(.mator-home-menu) [data-testid="stVerticalBlockBorderWrapper"]:has(.mator-home-menu) > [data-testid="stVerticalBlock"] {{
            display: flex;
            flex-direction: row;
            flex-wrap: wrap;
            align-items: center;
            justify-content: center;
            gap: 0.2rem 0.35rem;
        }}
        section.main:has(.mator-home-menu) [data-testid="stVerticalBlockBorderWrapper"]:has(.mator-home-menu) > [data-testid="stVerticalBlock"] > [data-testid="element-container"] {{
            flex: 0 0 auto;
            width: auto !important;
            margin: 0;
            padding: 0;
        }}
        section.main:has(.mator-home-menu) [data-testid="stVerticalBlockBorderWrapper"]:has(.mator-home-menu) [data-testid="stMarkdownContainer"] > p {{
            margin: 0;
            padding: 0.32rem 0.55rem;
            color: #111111 !important;
            font-size: 0.92rem;
            font-weight: 500;
        }}
        section.main:has(.mator-home-menu) [data-testid="stPageLink"] {{
            width: auto !important;
            margin: 0 !important;
            padding: 0 !important;
            background: transparent !important;
            border: 0 !important;
        }}
        section.main:has(.mator-home-menu) [data-testid="stPageLink"] a {{
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            min-height: 2rem;
            padding: 0.28rem 0.55rem;
            color: #111111 !important;
            font-size: 0.92rem;
            font-weight: 500;
            text-decoration: none;
            border-radius: 7px;
            transition: background-color 140ms ease, color 140ms ease, box-shadow 140ms ease;
        }}
        section.main:has(.mator-home-menu) [data-testid="stPageLink"] a:hover,
        section.main:has(.mator-home-menu) [data-testid="stPageLink"] a:focus-visible {{
            color: #ffffff !important;
            background-color: #bd1023 !important;
            box-shadow: 0 2px 6px rgba(115, 10, 24, 0.24);
            outline: none;
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
                radial-gradient(ellipse at 12% 16%, rgba(174, 202, 218, 0.22), transparent 42%),
                radial-gradient(ellipse at 86% 38%, rgba(186, 193, 201, 0.18), transparent 40%),
                radial-gradient(ellipse at 38% 82%, rgba(198, 220, 232, 0.20), transparent 46%),
                url("data:image/webp;base64,{MARBLE_TEXTURE_DATA}");
            background-position: center;
            background-size: cover;
        }}
        [data-testid="stSidebarNavItems"] {{
            height: auto !important;
            max-height: none !important;
            overflow: visible !important;
        }}
        [data-testid="stSidebarNavViewButton"] {{
            display: none !important;
        }}
        [data-testid="stSidebarNavLink"] {{
            color: #111111 !important;
            font-weight: 700 !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
    imagen = f"<img src='data:image/png;base64,{LOGO_DATA}' width='220' alt='Logo Mator'>"
    imagen_lateral = f"<img src='data:image/png;base64,{LOGO_DATA}' width='180' alt='Logo Mator'>"
    st.markdown(imagen, unsafe_allow_html=True)
    st.sidebar.markdown(imagen_lateral, unsafe_allow_html=True)