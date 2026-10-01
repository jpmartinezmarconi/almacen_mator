import streamlit as st
from utils.branding import mostrar_logo
from utils.albaranes import (
    finalizar_albaranes_vencidos,
    iniciar_finalizador_automatico,
)
from utils.db import init_db

init_db()
finalizar_albaranes_vencidos()

st.set_page_config(page_title="Almacén Mator", layout="wide")
mostrar_logo()
iniciar_finalizador_automatico()

st.markdown("""
    <h1 style='text-align: center; color: black; font-family: Arial;'>
        Almacén Mator
    </h1>
""", unsafe_allow_html=True)

st.write("Selecciona una sección:")

paginas = [
    ("pages/01_Entrada.py", "Entrada", "📥"),
    ("pages/02_Procesando.py", "Procesando", "⚙️"),
    ("pages/03_Finalizados.py", "Finalizados", "✅"),
    ("pages/04_Reportes.py", "Reportes", "📊"),
    ("pages/05_Equipos.py", "Equipos", "🧰"),
    ("pages/07_Almacen.py", "Almacen Virtual", "📦"),
]

for ruta, nombre, icono in paginas:
    st.page_link(ruta, label=nombre, icon=icono)

st.sidebar.subheader("Secciones")
for ruta, nombre, icono in paginas:
    st.sidebar.page_link(ruta, label=nombre, icon=icono)
