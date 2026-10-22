import streamlit as st
from utils.branding import mostrar_fondo_inicio, mostrar_logo
from utils.albaranes import (
    finalizar_albaranes_vencidos,
    iniciar_finalizador_automatico,
)
from utils.db import init_db

init_db()
finalizar_albaranes_vencidos()

st.set_page_config(page_title="Almacén Mator", layout="wide")
iniciar_finalizador_automatico()

paginas = [
    ("pages/01_Entrada.py", "Entrada", "📥"),
    ("pages/02_Procesando.py", "Procesando", "⚙️"),
    ("pages/03_Finalizados.py", "Finalizados", "✅"),
    ("pages/04_Reportes.py", "Reportes", "📊"),
    ("pages/05_Equipos.py", "Equipos", "🧰"),
    ("pages/07_Almacen.py", "Almacen Virtual", "📦"),
]


def mostrar_inicio():
    mostrar_fondo_inicio()
    mostrar_logo()
    st.markdown("""
        <h1 style='text-align: center; color: #e6001a; font-family: Arial, sans-serif; font-weight: 900; font-style: italic; letter-spacing: -1.5px;'>
            Almacen Mator - Virtual storage
        </h1>
    """, unsafe_allow_html=True)
    st.write("Selecciona una sección:")

    for ruta, nombre, icono in paginas:
        st.page_link(ruta, label=nombre, icon=icono)


pagina = st.navigation(
    [
        st.Page(mostrar_inicio, title="Inicio", icon="🏠"),
        *[
            st.Page(ruta, title=nombre, icon=icono)
            for ruta, nombre, icono in paginas
        ],
    ]
)
pagina.run()
