import base64
from pathlib import Path

import streamlit as st


LOGO_PATH = Path(__file__).resolve().parents[1] / "assets" / "logo.png"
LOGO_DATA = base64.b64encode(LOGO_PATH.read_bytes()).decode("ascii")
MARBLE_TEXTURE_PATH = (
    Path(__file__).resolve().parents[1] / "assets" / "textura_marmol.webp"
)
MARBLE_TEXTURE_DATA = base64.b64encode(
    MARBLE_TEXTURE_PATH.read_bytes()
).decode("ascii")


def mostrar_fondo_inicio():
    st.markdown(
        f"""
        <style>
        section:has(.mator-home-background) h1 {{
            box-sizing: border-box;
            max-width: 220px;
            margin: 0 0 0.6rem;
            padding: 0;
            font-size: clamp(1.05rem, 1.7vw, 1.2rem);
            line-height: 1.12;
            color: #e6001a !important;
        }}
        section:has(.mator-home-background) :is([data-testid="element-container"], [data-testid="stElementContainer"]):has(.mator-home-background),
        section:has(.mator-home-menu) :is([data-testid="element-container"], [data-testid="stElementContainer"]):has(.mator-home-menu) {{
            display: none !important;
        }}
        section:has(.mator-home-label) .mator-home-label {{
            margin: 0 0 0.25rem;
            color: var(--text-color) !important;
            font-size: 0.88rem;
            font-weight: 500;
        }}
        section:has(.mator-home-menu) :is([data-testid="stVerticalBlockBorderWrapper"], [data-testid="stLayoutWrapper"]):has(.mator-home-menu) {{
            box-sizing: border-box;
            width: fit-content;
            max-width: 100%;
            margin: 0;
            padding: 0;
            background: transparent;
            border: 0;
            box-shadow: none;
        }}
        section:has(.mator-home-menu) :is([data-testid="stVerticalBlockBorderWrapper"], [data-testid="stLayoutWrapper"]):has(.mator-home-menu) > [data-testid="stVerticalBlock"] {{
            display: flex !important;
            flex-direction: row;
            flex-wrap: wrap;
            align-items: center;
            justify-content: flex-start;
            gap: 0.1rem 0.25rem !important;
        }}
        section:has(.mator-home-menu) :is([data-testid="stVerticalBlockBorderWrapper"], [data-testid="stLayoutWrapper"]):has(.mator-home-menu) > [data-testid="stVerticalBlock"] > :is([data-testid="element-container"], [data-testid="stElementContainer"]) {{
            flex: 0 0 auto;
            width: auto !important;
            margin: 0;
            padding: 0;
        }}
        section:has(.mator-home-menu) [data-testid="stVerticalBlockBorderWrapper"]:has(.mator-home-menu) [data-testid="stMarkdownContainer"] > p {{
            margin: 0;
            padding: 0.28rem 0.45rem;
            color: var(--text-color) !important;
            font-size: 0.88rem;
            font-weight: 500;
            background: transparent;
        }}
        section:has(.mator-home-menu) [data-testid="stPageLink"] {{
            width: auto !important;
            margin: 0 !important;
            padding: 0 !important;
            background: transparent !important;
            border: 0 !important;
        }}
        section:has(.mator-home-menu) [data-testid="stPageLink"] a {{
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            min-height: 1.8rem;
            padding: 0.22rem 0.45rem;
            color: var(--text-color) !important;
            font-size: 0.88rem;
            font-weight: 500;
            text-decoration: none;
            border-radius: 7px;
            transition: background-color 140ms ease, color 140ms ease, box-shadow 140ms ease;
        }}
        section:has(.mator-home-menu) [data-testid="stPageLink"] a:hover,
        section:has(.mator-home-menu) [data-testid="stPageLink"] a:focus-visible {{
            color: #25320d !important;
            background-color: rgba(174, 222, 82, 0.62) !important;
            box-shadow: 0 2px 6px rgba(104, 145, 35, 0.16);
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